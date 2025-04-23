import json
import asyncio
import logging
from google import genai
from pydantic import BaseModel, Field
from src.host_manager import HostManager

class ValidationCriteria(BaseModel):
    name: str
    description: str
    weight: float | None = None
    
class ValidationRubric(BaseModel):
    criteria: list[ValidationCriteria]

class ValidationConfig(BaseModel):
    test_type: str = Field(..., description="The type of object being tested", pattern="^(agent|workflow|custom_workflow)$")
    name: str = Field(..., description="The name of the object being tested. Should match the name in config file")
    user_input: str | list[str] = Field(..., description="The input to be used as the initial user input. If a list of strings, it will run it with each separately")
    iterations: int = Field(default=1, description="The total number of iterations to do when running the agent/workflow")
    testing_prompt: str = Field(..., description="The prompt to be passed to the evaluation agent")
    rubric: ValidationRubric = Field(..., description="The rubric to use when evaluating the agent")
    evaluation_type: str = Field(default="default", description="If the output should be a score from 0-10 (numeric), or semantic (default)", pattern="^(numeric|default)$")
    threshold: float | None = Field(None, description="The expected score threshold for the numeric evaluation_type", ge=0, le=10)
    retry: bool = Field(default=False, description="If the process should retry if it fails to pass the threshold score")
    max_retries: int = Field(default=0, description="The maximum retries, after the initial run")
    edit_prompt: bool = Field(default=False, description="If the prompt validator should try to improve the prompt if it fails to meet threshold")
    editor_model: str = Field(default="gemini", description="The model to use for prompt editing", pattern="^(gemini|claude)$")
    new_prompt: str | None = Field(None, description="For A/B Testing. The new prompt to try and compare to the original prompt")

def prepare_prompts(testing_config: dict):
    type_prompts = {
        "numeric": """{
            "<first criteria name>": <score from 1-10 here>,
            "<second criteria name>": <score from 1-10 here>,
            ...
        }""",
        "default": """<overall assessment (Very Bad, Poor, Average, Good, Excellent)>"""
    }
    
    evaluation_type = testing_config.get("evaluation_type", "default")
    
    if evaluation_type not in type_prompts:
        raise ValueError(f"Evaluation type not recognized '{evaluation_type}', Expected types: {list(type_prompts.keys())}")
    
    qa_system_prompt = f"""You are a Quality Assurance Agent, your job is to review the output from the {testing_config["name"]} based on a given input.
    You have been provided with a prompt explaining how you should evaluate it.
    Here is the system prompt provided: "{testing_config["testing_prompt"]}"
    This prompt explains how to evaluate the output using this rubric: {json.dumps(testing_config["rubric"])}

    Format your output as JSON. IMPORTANT: Do not include any other text before or after, and do not format it as a code block (```). Here is a template: {{
        "analysis": "<your analysis here>",
        "grade": {type_prompts[evaluation_type]}
    }}
    """
    aggregation_system_prompt = """You are a Quality Assurance Agent. Your task is to aggregate multiple reports from a coworker into a single report. 
    Give your report output as a three sentence summary of the analysis, with an overall assessment at the bottom (Very Bad, Poor, Average, Good, Excellent)."""
    
    return {
        "type_prompts": type_prompts,
        "qa_system_prompt": qa_system_prompt,
        "aggregation_system_prompt": aggregation_system_prompt,
    }

def clean_thinking_output(output: str) -> str:
    """Removes all text up to and including </thinking>"""
    substring = "</thinking>"
    index = output.rfind(substring)
    
    if index > 0:
        output = output[index + len(substring):]
        
    # also trim to first curly brace to remove any preambles like "Here is the json: {}" 
    index = output.find("{")
    if index > 0:
        output = output[index:]
        
    return output

async def _get_agent_result(host_manager: HostManager, test_type, test_id, test_input, override_system_prompt: str | None = None) -> str:
    if override_system_prompt:
        if test_type != "agent":
            raise ValueError(f"Invalid type {test_type}, overriding system prompt only works with agents")
        else:
            output = await host_manager.execute_agent(agent_name=test_id, user_message=test_input, system_prompt=override_system_prompt)
    else:
        # call the agent/workflow being tested
        match test_type:
            case "agent":
                output = await host_manager.execute_agent(agent_name=test_id, user_message=test_input)
            case "workflow":
                output = await host_manager.execute_workflow(workflow_name=test_id, initial_user_message=test_input)
            case "custom_workflow":
                output = await host_manager.execute_custom_workflow(workflow_name=test_id, initial_input=test_input)
            case _:
                raise ValueError(f"Unrecognized type {test_type}")
    
    if test_type == "agent":
        output = output.get("final_response").content[0].text
    
    logging.info(f'Agent result: {output}')
    
    return output
    
async def _run_single_iteration(host_manager: HostManager, test_type, test_id, test_input, prompts, i, override_system_prompt: str | None = None) -> dict:
    logging.info(f"Prompt Validation: Iteration {i+1}")
    
    output = await _get_agent_result(host_manager, test_type, test_id, test_input, override_system_prompt)
    
    # analyze the agent/workflow output, overriding system prompt
    analysis_output = await host_manager.execute_agent(agent_name="Quality Assurance Agent", user_message=f"Input:{test_input}\n\nOutput:{output}", system_prompt=prompts["qa_system_prompt"])
    analysis_output = analysis_output.get("final_response").content[0].text
    
    logging.info(f'Analysis result {i+1}: {analysis_output}')
    
    try:
        analysis_json = json.loads(clean_thinking_output(analysis_output))
    except Exception as e:
        raise ValueError(f"Error converting agent output to json: {e}")
    
    analysis_json["input"] = test_input
    analysis_json["output"] = output
    
    return analysis_json

async def run_iterations(host_manager: HostManager, testing_config, override_system_prompt: str | None = None) -> list:
    """Run iterations of the agent/workflow and the analysis agent for prompt validation
    
    Returns:
        List of analysis results"""
    prompts = prepare_prompts(testing_config)
                    
    num_iterations = testing_config.get("iterations", 1)
    if type(num_iterations) is not int or num_iterations < 1:
        raise ValueError("iterations must be a positive integer")
    
    test_input = [testing_config["user_input"]] if type(testing_config["user_input"]) is str else testing_config["user_input"]
    
    tasks = [_run_single_iteration(host_manager,testing_config["test_type"],testing_config["name"],t_in,prompts,i,override_system_prompt) for i in range(num_iterations) for t_in in test_input]
    
    results = await asyncio.gather(*tasks)
        
    return results

async def evaluate_results(host_manager: HostManager, testing_config, results: list):
    prompts = prepare_prompts(testing_config)
    
    match testing_config.get("evaluation_type", "default"):
        case "numeric":
            final_results = {}
            final_score = 0
            for key in results[0]["grade"].keys():
                total = 0
                for i in range(len(results)):
                    total += results[i]["grade"][key]
                final_results[key] = total/len(results)
                
            for criteria in testing_config["rubric"]["criteria"]:
                final_score += final_results[criteria["name"]] * criteria["weight"]
                
            logging.info(f"Final Prompt Validation Results: {final_results}")
            logging.info(f"Final Prompt Validation Weighted Score: {final_score}/10")
            
            return {
                "criteria_results": final_results,
                "weighted_score": final_score,
            }
        case "default":
            if len(results) > 1:
                aggregation_output = await host_manager.execute_agent(agent_name="Aggregation Agent", user_message=",\n".join([json.dumps(r) for r in results]))
                logging.info(f"Aggregated Validation Output: {aggregation_output.get("final_response").content[0].text}")
                
                return aggregation_output.get("final_response").content[0].text
            else:
                logging.info(f"Prompt Validation Output: {json.dumps(results[0])}")
                
                return json.dumps(results[0])
            
async def evaluate_results_ab(host_manager: HostManager, testing_config, results: dict):
    ab_output = await host_manager.execute_agent(agent_name="A/B Agent", user_message=json.dumps(results))
    
    logging.info(f"A/B Output: {ab_output.get("final_response").content[0].text}")
                
    return ab_output.get("final_response").content[0].text

async def improve_prompt(host_manager: HostManager, model, results, current_prompt):    
    match model:
        case "claude":
            for res in results: #remove output to reduce tokens
                res.pop("output")
            
            user_message = f"""System Prompt: {current_prompt}\n\nAssessment:{results}"""
            
            new_prompt_output = await host_manager.execute_agent(agent_name="Prompt Editor Agent", user_message=user_message)
            
            return new_prompt_output.get("final_response").content[0].text
            
        case "gemini":
            #now use gemini to improve the prompt
            client = genai.Client()
            
            response = client.models.generate_content(
                model="gemini-2.5-pro-preview-03-25",
                config=genai.types.GenerateContentConfig(
                    system_instruction="You are an expert prompt engineer. Your task is to make edits to agent system prompts to improve their output quality. You will be given the original system prompt and a list of samples of its performance. You will analyze the existing system prompt and output an improved version which will address any failings in the samples. Key points to remember: 1. Make use of short examples to communicate the expected output. 2. Clearly label different parts of the prompt. 3. Return only the new system prompt, with no other text before or after."
                ),
                contents=json.dumps({"current_prompt": current_prompt, "samples": results})
            )
            
            return response.text
        case _:
            raise ValueError(f"Unrecognized prompt editor model {model}")
    

def load_config(testing_config_path: str) -> dict:
    """Load the config from path and validate the file path and data within"""
    
    if testing_config_path.suffix != ".json":
        raise ValueError("Testing config file has wrong extension (.json expected)")
    if not testing_config_path.exists():
        raise FileNotFoundError(f"Testing config file not found at {testing_config_path}")
        
    with open(testing_config_path, "r") as f:
        testing_config = json.load(f)
        
    ValidationConfig.model_validate(testing_config, strict=True)
    
    return testing_config