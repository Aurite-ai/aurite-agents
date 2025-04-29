# tests/fixtures/custom_workflows/example_workflow.py
import logging
import json
from typing import Any

# Need to adjust import path based on how tests are run relative to src
# Assuming tests run from project root, this should work:
from src.host.host import MCPHost
from src.prompt_validation.prompt_validation_helper import run_iterations, evaluate_results, improve_prompt, load_config, ValidationConfig, generate_config
from src.config import PROJECT_ROOT_DIR  # Import project root

logger = logging.getLogger(__name__)


class PromptValidationWorkflow:
    """
    Custom workflow for prompt validation
    """

    async def execute_workflow(self, initial_input: Any, host_instance: MCPHost) -> Any:
        """
        Executes the prompt validation workflow.

        Args:
            initial_input: An object containing the path to the config json file ("config_path"), a ValidationConfig ("validation_config"), or the info for simple validation ("agent_name", "testing_prompt", and "user_input").
            host_instance: The MCPHost instance to interact with agents/tools.

        Returns:
            A dictionary containing the result or an error.
        """
        logger.info(f"PromptValidationWorkflow started with input: {initial_input}")

        try:                        
            if "config_path" in initial_input:
                testing_config = load_config(initial_input["config_path"])
            elif "validation_config" in initial_input:
                testing_config = ValidationConfig.model_validate(initial_input["validation_config"], strict=True)
            elif "agent_name" in initial_input and "testing_prompt" in initial_input and "user_input" in initial_input:
                testing_config = generate_config(initial_input["agent_name"], initial_input["user_input"], initial_input["testing_prompt"])
            else:
                raise ValueError("Testing config not found. Expected ValidationConfig or path to config file")                
                
            improved_prompt = None
            
            for i in range(1+testing_config.max_retries):
                results = await run_iterations(host_instance=host_instance, testing_config=testing_config, override_system_prompt=improved_prompt)
                    
                # final results based on eval type
                final_result = await evaluate_results(host_instance, testing_config, results)
                
                if not final_result.get("pass", False):
                    # didn't pass, edit prompt / retry
                    if testing_config.edit_prompt:
                        current_prompt = improved_prompt or host_instance.get_agent_config(testing_config.name).system_prompt
                        improved_prompt = await improve_prompt(host_instance, testing_config.editor_model, results, current_prompt) 
                else:
                    # passed, break out of retry loop
                    break
                
            full_agent_responses = [{"input": res["input"], "output": res["full_output"]} for res in results]
            simple_agent_responses = [{"input": res["input"], "output": res["output"]} for res in results]
            
            return_value = {
                "status": "success",
                "input_received": initial_input,
                "validation_result": final_result,
                "agent_responses": full_agent_responses
            }
            
            logger.info("PromptValidationWorkflow finished successfully.")
            
            # write output 
            output = {
                "validation_result": final_result,
                "agent_responses": simple_agent_responses
            }
            if improved_prompt:
                output["new_prompt"] = improved_prompt
                
            
 
            if "config_path" in initial_input:
                output_path = initial_input["config_path"].with_name(initial_input["config_path"].stem + "_output.json")
            else:
                output_path = PROJECT_ROOT_DIR / "config/testing/default_output.json"
            
            logger.info(f"Writing to file: {output}")
            
            with open(output_path, "w") as f:
                json.dump(output, f, indent=4)
            
            return return_value
        except Exception as e:
            logger.error(
                f"Error within PromptValidationWorkflow execution: {e}", exc_info=True
            )
            return {"status": "failed", "error": f"Internal workflow error: {str(e)}"}
