# tests/fixtures/custom_workflows/example_workflow.py
import logging

# from aurite.lib.config import PROJECT_ROOT_DIR  # Import project root - REMOVED
from typing import TYPE_CHECKING, Any, Optional

from aurite.lib.models.config.components import LLMConfig

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


async def evaluate(
    input: EvaluationRequest,
    executor: "AuriteEngine",
    session_id: Optional[str] = None,
) -> Any:
    """
    Evaluates an component

    Args:
        input: The info for validation
        executor: The AuriteEngine instance to run agents
        session_id: An optional session_id for the component run

    Returns:
        A dictionary containing the result or an error.
    """
    logger.info(f"Evaluation started with input: {input}")

    try:
        if input.review_llm:
            config_manager = executor._config_manager

            llm_config = config_manager.get_config(component_id=input.review_llm, component_type="llm")

            if not llm_config:
                raise ValueError(f"No config found for llm id {input.review_llm}")

            llm_config = LLMConfig(**llm_config)
        else:
            # default to hardcoded openai llm config
            llm_config = LLMConfig(
                name="Default Eval",
                type="llm",
                model="gpt-3.5-turbo",
                provider="openai",
                temperature=0.5,
            )

        testing_config = generate_config(input, llm_config)

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
