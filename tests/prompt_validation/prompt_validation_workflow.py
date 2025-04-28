# tests/fixtures/custom_workflows/example_workflow.py
import logging
import json
from typing import Any

# Need to adjust import path based on how tests are run relative to src
# Assuming tests run from project root, this should work:
from src.host.host import MCPHost
from tests.prompt_validation.prompt_validation_helper import run_iterations, evaluate_results, improve_prompt, load_config

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
            testing_config_path = initial_input["config_path"]
            
            testing_config = load_config(testing_config_path)
                
            improved_prompt = None
            
            for i in range(1+testing_config.max_retries):
                results = await run_iterations(host_instance=host_instance, testing_config=testing_config, override_system_prompt=improved_prompt)
                    
                # final results based on eval type
                final_result = await evaluate_results(host_instance, testing_config, results)
                
                if "weighted_score" in final_result and testing_config.threshold is not None:
                    if final_result["weighted_score"] < testing_config.threshold:
                        if testing_config.edit_prompt:
                            current_prompt = improved_prompt or host_instance.get_agent_config(testing_config.name).system_prompt
                            improved_prompt = await improve_prompt(host_instance, testing_config.editor_model, results, current_prompt)
                    else:
                        logger.info(f"Weighted score satisfied threshold ({final_result["weighted_score"]} >= {testing_config.threshold})")
                        break
                else:
                    break
            
            return_value = {
                "status": "success",
                "input_received": initial_input,
                "result": final_result,
            }
            
            logger.info("PromptValidationWorkflow finished successfully.")
            
            # Add detailed log before returning
            logger.debug(
                f"PromptValidationWorkflow returning: type={type(return_value)}, value={return_value}"
            )
            
            # write output 
            output = {
                "output": final_result
            }
            if improved_prompt:
                output["new_prompt"] = improved_prompt
            output_path = testing_config_path.with_name(testing_config_path.stem + "_output.json")
            with open(output_path, "w") as f:
                json.dump(output, f, indent=4)
            
            return return_value
        except Exception as e:
            logger.error(
                f"Error within PromptValidationWorkflow execution: {e}", exc_info=True
            )
            return {"status": "failed", "error": f"Internal workflow error: {str(e)}"}
