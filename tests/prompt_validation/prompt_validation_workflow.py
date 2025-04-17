# tests/fixtures/custom_workflows/example_workflow.py
import logging
import json
from typing import Any

# Need to adjust import path based on how tests are run relative to src
# Assuming tests run from project root, this should work:
from src.host.host import MCPHost
from src.agents.agent import Agent
from tests.prompt_validation.prompt_validation_helper import prepare_prompts, clean_thinking_output
from src.host.models import AgentConfig

logger = logging.getLogger(__name__)


class PromptValidationWorkflow:
    """
    Custom workflow for prompt validation
    """

    async def execute_workflow(self, initial_input: Any, host_instance: MCPHost) -> Any:
        """
        Executes the prompt validation workflow.

        Args:
            initial_input: The path to the config json file.
            host_instance: The MCPHost instance to interact with agents/tools.

        Returns:
            A dictionary containing the result or an error.
        """
        logger.info(f"PromptValidationWorkflow started with input: {initial_input}")

        try:
            host_manager = initial_input["host_manager"]
            
            testing_config_path = initial_input["config_path"]
            
            if not testing_config_path.exists():
                raise FileNotFoundError(f"Testing config file not found at {testing_config_path}")
                
            with open(testing_config_path, "r") as f:
                testing_config = json.load(f)
                
            prompts = prepare_prompts(testing_config)

            await host_manager.register_agent(AgentConfig(name="Quality Assurance Agent", client_ids=None, system_prompt=prompts["qa_system_prompt"]))
                
            num_iterations = testing_config.get("iterations", 1)
            if type(num_iterations) is not int or num_iterations < 1:
                raise ValueError("iterations must be a positive integer")
            
            results = []
            
            for i in range(num_iterations):
                logging.info(f"Prompt Validation: Iteration {i+1} of {num_iterations}")
                
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
                
                logging.info(f'Agent result: {output.get("final_response").content[0].text}')
                
                # analyze the agent/workflow output
                analysis_output = await host_manager.execute_agent(agent_name="Quality Assurance Agent", user_message=output.get("final_response").content[0].text)
                        
                logging.info(f'Analysis result: {analysis_output.get("final_response").content[0].text}')
                
                try:
                    analysis_json = json.loads(clean_thinking_output(analysis_output.get("final_response").content[0].text))
                except Exception as e:
                    raise ValueError(f"Error converting agent output to json: {e}")
                
                results.append(analysis_json)
                
            
            return_value = {
                "status": "success",
                "input_received": initial_input,
                "result": "",
            }
            
            # aggregate final results based on eval type
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
                    
                    return_value["result"] = {
                        "criteria_results": final_results,
                        "weighted_score": final_score,
                    }
                case "default":
                    if num_iterations > 1:
                        await host_manager.register_agent(AgentConfig(name="Aggregation Agent", client_ids=None, system_prompt=prompts["aggregation_system_prompt"]))
                        aggregation_output = await host_manager.execute_agent(agent_name="Aggregation Agent", user_message=",\n".join([json.dumps(r) for r in results]))
                        logging.info(f"Aggregated Validation Output: {aggregation_output.get("final_response").content[0].text}")
                        
                        return_value["result"] = aggregation_output.get("final_response").content[0].text
                    else:
                        logging.info(f"Prompt Validation Output: {json.dumps(results[0])}")
                        
                        return_value["result"] = json.dumps(results[0])
            
            logger.info("PromptValidationWorkflow finished successfully.")
            
            # Add detailed log before returning
            logger.debug(
                f"PromptValidationWorkflow returning: type={type(return_value)}, value={return_value}"
            )
            return return_value

        
        except Exception as e:
            logger.error(
                f"Error within PromptValidationWorkflow execution: {e}", exc_info=True
            )
            return {"status": "failed", "error": f"Internal workflow error: {str(e)}"}
