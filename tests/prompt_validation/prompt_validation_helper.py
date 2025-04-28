import json
import yaml
import asyncio
import logging
from google import genai
from pydantic import BaseModel, Field
from src.host import MCPHost
from src.agents import Agent

class ValidationCriteria(BaseModel):
    name: str
    description: str
    weight: float | None = None
    
class ValidationRubric(BaseModel):
    criteria: list[ValidationCriteria]
    
class ExpectedToolCall(BaseModel):
    name: str
    eq: int | None = None
    lt: int | None = None
    le: int | None = None
    gt: int | None = None
    ge: int | None = None
    
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
    expected_tools: list[ExpectedToolCall] = Field([], description="A list of tool calls expected to occur, ignored if test_type is not agent")

def prepare_prompts(testing_config: ValidationConfig):
    type_prompts = {
        "numeric": """{
            "<first criteria name>": <score from 1-10 here>,
            "<second criteria name>": <score from 1-10 here>,
            ...
        }""",
        "default": """<overall assessment (Very Bad, Poor, Average, Good, Excellent)>"""
    }
    
    evaluation_type = testing_config.evaluation_type
    
    if evaluation_type not in type_prompts:
        raise ValueError(f"Evaluation type not recognized '{evaluation_type}', Expected types: {list(type_prompts.keys())}")
    
    qa_system_prompt = f"""You are a Quality Assurance Agent, your job is to review the output from the {testing_config.name} based on a given input.
    You have been provided with a prompt explaining how you should evaluate it.
    Here is the system prompt provided: "{testing_config.testing_prompt}"
    This prompt explains how to evaluate the output using this rubric: {testing_config.rubric.model_dump_json()}

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

async def _get_agent_result(host_instance: MCPHost, testing_config: ValidationConfig, test_input, override_system_prompt: str | None = None) -> str:
    if override_system_prompt:
        if testing_config.test_type != "agent":
            raise ValueError(f"Invalid type {testing_config.test_type}, overriding system prompt only works with agents")
        else:
            output = await call_agent(host_instance=host_instance, agent_name=testing_config.name, user_message=test_input, system_prompt=override_system_prompt)
    else:
        # call the agent/workflow being tested
        match testing_config.test_type:
            case "agent":
                output = await call_agent(host_instance=host_instance, agent_name=testing_config.name, user_message=test_input)
            case "workflow":
                output = await call_workflow(host_instance=host_instance, workflow_name=testing_config.name, initial_user_message=test_input)
            case "custom_workflow":
                output = await call_custom_workflow(host_instance=host_instance, workflow_name=testing_config.name, initial_input=test_input)
            case _:
                raise ValueError(f"Unrecognized type {testing_config.test_type}")
    
    if testing_config.test_type == "agent":
        if testing_config.expected_tools:
            tool_check = check_tool_calls(output, testing_config.expected_tools)
            if not tool_check["success"]:
                raise RuntimeError(tool_check["message"])
            
        output = output.get("final_response").content[0].text
    
    logging.info(f'Agent result: {output}')
    
    return output
    
async def _run_single_iteration(host_instance: MCPHost, testing_config: ValidationConfig, test_input, prompts, i, override_system_prompt: str | None = None) -> dict:
    logging.info(f"Prompt Validation: Iteration {i+1}")
    
    output = await _get_agent_result(host_instance, testing_config, test_input, override_system_prompt)
    
    # analyze the agent/workflow output, overriding system prompt
    analysis_output = await call_agent(host_instance=host_instance, agent_name="Quality Assurance Agent", user_message=f"Input:{test_input}\n\nOutput:{output}", system_prompt=prompts["qa_system_prompt"])
    analysis_output = analysis_output.get("final_response").content[0].text
    
    logging.info(f'Analysis result {i+1}: {analysis_output}')
    
    try:
        analysis_json = json.loads(clean_thinking_output(analysis_output))
    except Exception as e:
        raise ValueError(f"Error converting agent output to json: {e}")
    
    analysis_json["input"] = test_input
    analysis_json["output"] = output
    
    return analysis_json

async def run_iterations(host_instance: MCPHost, testing_config: ValidationConfig, override_system_prompt: str | None = None) -> list:
    """Run iterations of the agent/workflow and the analysis agent for prompt validation
    
    Returns:
        List of analysis results"""
    prompts = prepare_prompts(testing_config)
                    
    num_iterations = testing_config.iterations
    if type(num_iterations) is not int or num_iterations < 1:
        raise ValueError("iterations must be a positive integer")
    
    # convert to list[str] if given input is a single string
    test_input = [testing_config.user_input] if type(testing_config.user_input) is str else testing_config.user_input
    
    tasks = [_run_single_iteration(host_instance,testing_config,t_in,prompts,i,override_system_prompt) for i in range(num_iterations) for t_in in test_input]
    
    results = await asyncio.gather(*tasks)
        
    return results

async def evaluate_results(host_instance: MCPHost, testing_config: ValidationConfig, results: list):
    prompts = prepare_prompts(testing_config)
    
    match testing_config.evaluation_type:
        case "numeric":
            final_results = {}
            final_score = 0
            for key in results[0]["grade"].keys():
                total = 0
                for i in range(len(results)):
                    total += results[i]["grade"][key]
                final_results[key] = total/len(results)
                
            for criteria in testing_config.rubric.criteria:
                final_score += final_results[criteria.name] * criteria.weight
                
            logging.info(f"Final Prompt Validation Results: {final_results}")
            logging.info(f"Final Prompt Validation Weighted Score: {final_score}/10")
            
            return {
                "criteria_results": final_results,
                "weighted_score": final_score,
            }
        case "default":
            if len(results) > 1:
                aggregation_output = await call_agent(host_instance=host_instance, agent_name="Aggregation Agent", user_message=",\n".join([json.dumps(r) for r in results]))
                logging.info(f"Aggregated Validation Output: {aggregation_output.get("final_response").content[0].text}")
                
                return aggregation_output.get("final_response").content[0].text
            else:
                logging.info(f"Prompt Validation Output: {json.dumps(results[0])}")
                
                return json.dumps(results[0])
            
async def evaluate_results_ab(host_instance: MCPHost, testing_config: ValidationConfig, results: dict):
    ab_output = await call_agent(host_instance=host_instance, agent_name="A/B Agent", user_message=json.dumps(results))
    
    logging.info(f"A/B Output: {ab_output.get("final_response").content[0].text}")
                
    return ab_output.get("final_response").content[0].text

async def improve_prompt(host_instance: MCPHost, model, results, current_prompt):    
    match model:
        case "claude":
            for res in results: #remove output to reduce tokens
                res.pop("output")
            
            user_message = f"""System Prompt: {current_prompt}\n\nAssessment:{results}"""
            
            new_prompt_output = await call_agent(host_instance=host_instance, agent_name="Prompt Editor Agent", user_message=user_message)
            
            return new_prompt_output.get("final_response").content[0].text
            
        case "gemini":
            #now use gemini to improve the prompt
            
            #TODO: call as an agent once gemini is added to models
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
    

def load_config(testing_config_path: str) -> ValidationConfig:
    """Load the config from path and validate the file path and data within"""
    
    if not testing_config_path.exists():
        raise FileNotFoundError(f"Testing config file not found at {testing_config_path}")
    
    with open(testing_config_path, "r") as f:
        match testing_config_path.suffix:
            case ".json":
                testing_config_data = json.load(f)
            case ".yaml":
                testing_config_data = yaml.load(f, Loader=yaml.SafeLoader)
            case _:
                raise ValueError("Testing config file has wrong extension (.json or .yaml expected)")
    
    testing_config = ValidationConfig.model_validate(testing_config_data, strict=True)
            
    return testing_config

def extract_tool_calls(agent_response) -> list[dict]:
    """Extract a list of tool calls from agent response"""
    tool_calls = []
    for item in agent_response.get("conversation", []):
        if item.get("role") == "assistant":
            for c in item.get("content", []):
                if c.type == "tool_use":
                    tool_calls.append({
                        "name": c.name,
                        "input": c.input
                    })
                    
    return tool_calls

def count_tool_calls(tool_calls: list[dict]) -> dict[str, int]:
    """Count how many times tools are called by name"""
    results = {}
    for call in tool_calls:
        if call["name"] not in results:
            results[call["name"]] = 0
        results[call["name"]] += 1
        
    return results

def check_tool_calls(agent_response, expected_tools) -> dict:
    """Check if the expected tools appear in the agent response
    
    Returns:
        {
            "success": bool, true if all expected tools appear
            "message": str, error message if not successful }"""
    
    tool_calls = extract_tool_calls(agent_response)
    call_counts = count_tool_calls(tool_calls)
    
    for expected in expected_tools:
        count = call_counts.get(expected.name, 0)
        
        if expected.eq is not None and count != expected.eq:
            return {
                "success": False,
                "message": f"Expected tool {expected.name} to be called == {expected.eq} time(s). Called {count} time(s) instead"
            }
        if expected.le is not None and count > expected.le:
            return {
                "success": False,
                "message": f"Expected tool {expected.name} to be called <= {expected.le} time(s). Called {count} time(s) instead"
            }
        if expected.lt is not None and count >= expected.lt:
            return {
                "success": False,
                "message": f"Expected tool {expected.name} to be called < {expected.lt} time(s). Called {count} time(s) instead"
            }
        if expected.ge is not None and count < expected.ge:
            return {
                "success": False,
                "message": f"Expected tool {expected.name} to be called >= {expected.ge} time(s). Called {count} time(s) instead"
            }
        if expected.gt is not None and count <= expected.gt:
            return {
                "success": False,
                "message": f"Expected tool {expected.name} to be called > {expected.gt} time(s). Called {count} time(s) instead"
            }
        
    return {
        "success": True
    }
    
async def call_agent(host_instance: MCPHost, agent_name: str, user_message: str, system_prompt: str | None = None):
    """Calls an agent using the MCP host, returns its full output"""
    
    agent_config = host_instance.get_agent_config(agent_name)
    agent = Agent(config=agent_config)

    agent_result = await agent.execute_agent(
        user_message=user_message,
        host_instance=host_instance,
        system_prompt=system_prompt,
    )
    
    return agent_result

async def call_workflow(host_instance: MCPHost, workflow_name: str, initial_user_message: str):
    """Calls a workflow using the MCP host, returns its full output"""
    # TODO
    pass

async def call_custom_workflow(host_instance: MCPHost, workflow_name: str, initial_input):
    """Calls a custom workflow using dynamic import, returns its full output"""
    # TODO
    pass