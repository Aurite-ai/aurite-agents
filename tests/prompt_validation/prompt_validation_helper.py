import json
import asyncio
import logging
from src.host.models import AgentConfig
from src.host_manager import HostManager

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
    
    qa_system_prompt = f"""You are a Quality Assurance Agent, your job is to review the output from the {testing_config["id"]}.
    You have been provided with a prompt explaining how you should evaluate it.
    Here is the system prompt provided: "{testing_config["testing_prompt"]}"
    This prompt explains how to evaluate the output using this rubric: {json.dumps(testing_config["rubric"])}

    Format your output as JSON. Do not include any other text, and do not format it as a code block (```). Start with {{ and end with }}. Here is a template: {{
        "analysis": "<your analysis here>",
        "output": {type_prompts[evaluation_type]}
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
        
    return output

async def _run_single_iteration(host_manager: HostManager, testing_config, prompts, i) -> dict:
    logging.info(f"Prompt Validation: Iteration {i+1}")
    
    # call the agent/workflow being tested
    match testing_config["type"]:
        case "agent":
            output = await host_manager.execute_agent(agent_name=testing_config["id"], user_message=testing_config["input"])
        case "workflow":
            output = await host_manager.execute_workflow(workflow_name=testing_config["id"], initial_user_message=testing_config["input"])
        case "custom_workflow":
            output = await host_manager.execute_custom_workflow(workflow_name=testing_config["id"], initial_input=testing_config["input"])
        case _:
            raise ValueError(f"Unrecognized type {testing_config['type']}")
    
    logging.info(f'Agent result {i+1}: {output.get("final_response").content[0].text}')
    
    # analyze the agent/workflow output, overriding system prompt
    analysis_output = await host_manager.execute_agent(agent_name="Quality Assurance Agent", user_message=output.get("final_response").content[0].text, system_prompt=prompts["qa_system_prompt"])
            
    logging.info(f'Analysis result {i+1}: {analysis_output.get("final_response").content[0].text}')
    
    try:
        analysis_json = json.loads(clean_thinking_output(analysis_output.get("final_response").content[0].text))
    except Exception as e:
        raise ValueError(f"Error converting agent output to json: {e}")
    
    return analysis_json

async def run_iterations(host_manager: HostManager, testing_config) -> list:
    """Run iterations of the agent/workflow and the analysis agent.
    
    Returns:
        List of analysis results"""
    prompts = prepare_prompts(testing_config)
                    
    num_iterations = testing_config.get("iterations", 1)
    if type(num_iterations) is not int or num_iterations < 1:
        raise ValueError("iterations must be a positive integer")
    
    tasks = [_run_single_iteration(host_manager,testing_config,prompts,i) for i in range(num_iterations)]
    
    results = await asyncio.gather(*tasks)
        
    return results

async def evaluate_results(host_manager: HostManager, testing_config, results: list):
    num_iterations = testing_config.get("iterations", 1)
    prompts = prepare_prompts(testing_config)
    
    match testing_config.get("evaluation_type", "default"):
        case "numeric":
            final_results = {}
            final_score = 0
            for key in results[0]["output"].keys():
                total = 0
                for i in range(num_iterations):
                    total += results[i]["output"][key]
                final_results[key] = total/num_iterations
                
            for criteria in testing_config["rubric"]["criteria"]:
                final_score += final_results[criteria["name"]] * criteria["weight"]
                
            logging.info(f"Final Prompt Validation Results: {final_results}")
            logging.info(f"Final Prompt Validation Weighted Score: {final_score}/10")
            
            return {
                "criteria_results": final_results,
                "weighted_score": final_score,
            }
        case "default":
            if num_iterations > 1:
                aggregation_output = await host_manager.execute_agent(agent_name="Aggregation Agent", user_message=",\n".join([json.dumps(r) for r in results]))
                logging.info(f"Aggregated Validation Output: {aggregation_output.get("final_response").content[0].text}")
                
                return aggregation_output.get("final_response").content[0].text
            else:
                logging.info(f"Prompt Validation Output: {json.dumps(results[0])}")
                
                return json.dumps(results[0])