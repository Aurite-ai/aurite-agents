# tests/fixtures/custom_workflows/example_workflow.py
import logging
import json
import asyncio
from typing import Any

# Need to adjust import path based on how tests are run relative to src
# Assuming tests run from project root, this should work:
from aurite.components.workflows.custom.prompt_validation.prompt_validation_helper import (
    run_iterations,
    evaluate_results_ab,
    load_config,
)
from typing import TYPE_CHECKING

# Type hint for ExecutionFacade to avoid circular import
if TYPE_CHECKING:
    from aurite.execution.facade import ExecutionFacade

logger = logging.getLogger(__name__)


class ABTestingWorkflow:
    """
    Custom workflow for A/B testing
    """

    async def execute_workflow(
        self, initial_input: Any, executor: "ExecutionFacade"
    ) -> Any:
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
            testing_config_path = initial_input["config_path"]

            testing_config = load_config(testing_config_path)

            results = await asyncio.gather(
                run_iterations(executor=executor, testing_config=testing_config),
                run_iterations(
                    executor=executor,
                    testing_config=testing_config,
                    override_system_prompt=testing_config.new_prompt,
                ),
            )

            formatted_results = {"A": results[0][0], "B": results[1][0]}

            # final results based on eval type
            final_result = await evaluate_results_ab(
                executor, testing_config, formatted_results
            )

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

            # write output
            output = {"output": final_result}
            output_path = testing_config_path.with_name(
                testing_config_path.stem + "_output.json"
            )
            with open(output_path, "w") as f:
                json.dump(output, f, indent=4)

            return return_value
        except Exception as e:
            logger.error(
                f"Error within ABTestingWorkflow execution: {e}", exc_info=True
            )
            return {"status": "failed", "error": f"Internal workflow error: {str(e)}"}
