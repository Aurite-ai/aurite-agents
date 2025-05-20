"""
Executor for Simple Sequential Workflows.
"""

import logging
from typing import Dict, Any, TYPE_CHECKING  # Added TYPE_CHECKING

# Relative imports assuming this file is in src/workflows/
from ..config.config_models import WorkflowConfig, AgentConfig  # Updated import path

# Import LLM client and Facade for type hinting only
if TYPE_CHECKING:
    from ..execution.facade import ExecutionFacade  # Added Facade import

logger = logging.getLogger(__name__)


class SimpleWorkflowExecutor:
    """
    Executes a simple sequential workflow defined by a WorkflowConfig.
    """

    def __init__(
        self,
        config: WorkflowConfig,
        agent_configs: Dict[
            str, AgentConfig
        ],  # This is passed by Facade from current_project
        facade: "ExecutionFacade",
    ):
        """
        Initializes the SimpleWorkflowExecutor.

        Args:
            config: The configuration for the specific workflow to execute.
            agent_configs: A dictionary containing all available agent configurations
                           from the current project, keyed by agent name.
                           (Used by the facade when it runs agents for this workflow).
            facade: The ExecutionFacade instance, used to run agents.
        """
        if not isinstance(config, WorkflowConfig):
            raise TypeError("config must be an instance of WorkflowConfig")
        if not isinstance(agent_configs, dict):
            raise TypeError("agent_configs must be a dictionary")
        if not facade:
            raise ValueError("ExecutionFacade instance is required.")

        self.config = config
        # _agent_configs is not strictly needed by SimpleWorkflowExecutor itself if facade handles agent lookup,
        # but keeping it for now as it was passed by the updated facade.
        # If facade.run_agent can fully resolve agents using its own _current_project.agent_configs,
        # this could potentially be removed too. For now, it's harmless.
        self._agent_configs = agent_configs
        self.facade = facade
        logger.debug(
            f"SimpleWorkflowExecutor initialized for workflow: {self.config.name}"
        )

    async def execute(self, initial_input: str) -> Dict[str, Any]:
        """
        Executes the configured simple workflow sequentially.

        Args:
            initial_input: The initial input message for the first agent in the sequence.

        Returns:
            A dictionary containing the final status, the final message from the last agent,
            and any error message encountered.
        """
        workflow_name = self.config.name
        logger.info(f"Executing simple workflow: {workflow_name}")
        
        component_input = {
            "workflow": self.config.steps,
            "input": initial_input,
        }

        result = await self.facade.run_custom_workflow(workflow_name="ComponentWorkflow", initial_input=component_input)

        # Return final result
        return {
            "workflow_name": workflow_name,
            "status": result.get("status", "failed"),
            "final_message": result.get("final_message", None),
            "error": result.get("error", None),
        }
