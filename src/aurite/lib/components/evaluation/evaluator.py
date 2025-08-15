# tests/fixtures/custom_workflows/example_workflow.py
import logging

# from aurite.lib.config import PROJECT_ROOT_DIR  # Import project root - REMOVED
from typing import TYPE_CHECKING, Any, Optional

from ...models.api.requests import EvaluationRequest

# Need to adjust import path based on how tests are run relative to src
# Assuming tests run from project root, this should work:
from .prompt_validation_helper import (  # Changed to relative import
    evaluate_results,
    generate_config,
    run_iterations,
)

# Type hint for AuriteEngine to avoid circular import
if TYPE_CHECKING:
    from aurite.execution.aurite_engine import AuriteEngine  # This is now correct

logger = logging.getLogger(__name__)


async def evaluate_agent(
    input: EvaluationRequest,
    executor: "AuriteEngine",
    session_id: Optional[str] = None,
) -> Any:
    """
    Evaluates an agent

    Args:
        input: The info for validation ("agent_name", "testing_prompt", and "user_input").
        executor: The AuriteEngine instance to run agents
        session_id: An optional session_id for the agent run

    Returns:
        A dictionary containing the result or an error.
    """
    logger.info(f"Evaluation started with input: {input}")

    try:
        testing_config = generate_config(
            input.name,
            input.user_input,
            input.expected_output,
        )

        results, full_agent_responses = await run_iterations(
            executor=executor,
            testing_config=testing_config,
        )

        final_result = await evaluate_results(executor, testing_config, results, full_agent_responses)

        return_value = {
            "status": "success",
            "input_received": input,
            "validation_result": final_result,
            "agent_responses": full_agent_responses,
        }

        logger.info("Evaluation finished successfully.")

        return return_value
    except Exception as e:
        logger.error(f"Error within component evaluation: {e}")
        return {"status": "failed", "error": f"Error within component evaluation: {str(e)}"}
