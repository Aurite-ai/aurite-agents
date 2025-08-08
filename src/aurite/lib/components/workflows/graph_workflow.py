"""
Executor for Linear Sequential Workflows.
"""

import logging
import uuid
from typing import TYPE_CHECKING, Any, Optional

from ...models.api.responses import GraphWorkflowExecutionResult, GraphWorkflowNodeResult

# Relative imports assuming this file is in src/workflows/
from ...models.config.components import GraphWorkflowConfig

# Import LLM client and Facade for type hinting only
if TYPE_CHECKING:
    from ...execution.aurite_engine import AuriteEngine

logger = logging.getLogger(__name__)


class GraphWorkflowExecutor:
    """
    Executes a graph workflow defined by a GraphWorkflowConfig.
    """

    def __init__(
        self,
        config: GraphWorkflowConfig,
        engine: "AuriteEngine",
    ):
        """
        Initializes the GraphWorkflowExecutor.

        Args:
            config: The configuration for the specific workflow to execute.
            engine: The AuriteEngine instance, used to run agents.
        """
        if not isinstance(config, GraphWorkflowConfig):
            raise TypeError("config must be an instance of GraphWorkflowConfig")
        if not engine:
            raise ValueError("AuriteEngine instance is required.")

        self.config = config
        self.engine = engine
        logger.debug(f"GraphWorkflowExecutor initialized for workflow: {self.config.name}")

    async def execute(
        self,
        initial_input: str,
        session_id: Optional[str] = None,
        base_session_id: Optional[str] = None,
        force_logging: Optional[bool] = None,
    ) -> GraphWorkflowExecutionResult:
        """
        Executes the configured graph workflow.

        Args:
            initial_input: The initial input message for the initial node(s).
            session_id: Optional session ID to use for conversation history tracking.
            base_session_id: The original, user-provided session ID for the workflow.

        Returns:
            A LinearWorkflowExecutionResult object containing the final status,
            step-by-step results, the final output, and any error message.
        """
        workflow_name = self.config.name

        if not session_id and self.config.include_history:
            session_id = f"workflow-{uuid.uuid4().hex[:8]}"
            logger.info(f"Auto-generated session_id for graph workflow '{workflow_name}': {session_id}")

        logger.info(f"Executing graph workflow: '{workflow_name}' with session_id: {session_id}")

        node_results: dict[str, GraphWorkflowNodeResult] = []
        current_message: Any = initial_input

        try:
            pass
        except Exception as e:
            logger.error(f"Error within graph workflow execution: {e}", exc_info=True)
            return GraphWorkflowExecutionResult(
                workflow_name=workflow_name,
                status="failed",
                node_results=node_results,
                final_output=current_message,
                error=f"Workflow setup error: {str(e)}",
                session_id=session_id,
            )
