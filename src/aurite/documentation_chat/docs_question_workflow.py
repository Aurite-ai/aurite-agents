# tests/fixtures/custom_workflows/example_workflow.py
import logging

# Need to adjust import path based on how tests are run relative to src
# Assuming tests run from project root, this should work:
from aurite.servers.storage.vector.pgvector_server import search
from typing import TYPE_CHECKING, Optional, Any

# Type hint for ExecutionFacade to avoid circular import
if TYPE_CHECKING:
    from aurite.execution.facade import ExecutionFacade

logger = logging.getLogger(__name__)


class DocsQuestionWorkflow:
    """
    Custom workflow for asking the documentation agent a question
    """

    async def execute_workflow(
        self,
        initial_input: Any,
        executor: "ExecutionFacade",
        session_id: Optional[str] = None,
    ) -> Any:
        """
        Executes the initialize docs workflow.

        Args:
            initial_input: Object containing the user_input
            executor: The ExecutionFacade
            session_id: Optional, id of the session for logging

        Returns:
            A dictionary containing the result or an error.
        """
        logger.info("DocsQuestionWorkflow started")

        try:
            user_input = initial_input["user_input"]

            context = search(user_input)

            docs_output = await executor.run_agent(
                agent_name="Documentation Question Agent",
                user_message=f"QUESTION: {user_input}, CONTEXT: {context}",
            )

            return_value = {
                "status": "success",
                "answer": docs_output,
            }

            return return_value
        except Exception as e:
            logger.error(
                f"Error within DocsQuestionWorkflow execution: {e}", exc_info=True
            )
            return {"status": "failed", "error": f"Internal workflow error: {str(e)}"}
