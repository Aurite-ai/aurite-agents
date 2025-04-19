# tests/fixtures/custom_workflows/example_workflow.py
import logging
import json
from typing import Any

# Need to adjust import path based on how tests are run relative to src
# Assuming tests run from project root, this should work:
from src.host.host import MCPHost
from tests.prompt_validation.prompt_validation_helper import run_iterations_ab, evaluate_results_ab

logger = logging.getLogger(__name__)


class ABTestingWorkflow:
    """
    Custom workflow for A/B testing
    """

    async def execute_workflow(self, initial_input: Any, host_instance: MCPHost) -> Any:
        """
        Executes the A/B testing workflow.

        Args:
            initial_input: The path to the config json file.
            host_instance: The MCPHost instance to interact with agents/tools.

        Returns:
            A dictionary containing the result or an error.
        """
        logger.info(f"ABTestingWorkflow started with input: {initial_input}")

        try:
            host_manager = initial_input["host_manager"]
            
            testing_config_path = initial_input["config_path"]
            
            if not testing_config_path.exists():
                raise FileNotFoundError(f"Testing config file not found at {testing_config_path}")
                
            with open(testing_config_path, "r") as f:
                testing_config = json.load(f)
                
            results = await run_iterations_ab(host_manager=host_manager, testing_config=testing_config)
                
            # final results based on eval type
            final_result = await evaluate_results_ab(host_manager, testing_config, results)
            
            return_value = {
                "status": "success",
                "input_received": initial_input,
                "result": final_result,
            }
            
            logger.info("ABTestingWorkflow finished successfully.")
            
            # Add detailed log before returning
            logger.debug(
                f"ABTestingWorkflow returning: type={type(return_value)}, value={return_value}"
            )
            
            # write output into config file
            testing_config["output"] = final_result
            with open(testing_config_path, "w") as f:
                json.dump(testing_config, f, indent=4)
            
            return return_value
        except Exception as e:
            logger.error(
                f"Error within ABTestingWorkflow execution: {e}", exc_info=True
            )
            return {"status": "failed", "error": f"Internal workflow error: {str(e)}"}
