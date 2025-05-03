# src/execution/facade.py
"""
Provides a unified facade for executing Agents, Simple Workflows, and Custom Workflows.
"""

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from ..host_manager import HostManager
    from ..host.host import MCPHost  # Needed for passing to executors/workflows
    from ..agents.agent import Agent  # Keep type hint here
    from ..workflows.simple_workflow import (
        SimpleWorkflowExecutor,
    )  # Import for type hint
    from ..workflows.custom_workflow import (
        CustomWorkflowExecutor,
    )  # Import for type hint

# Import Agent at runtime for instantiation
from ..agents.agent import Agent

# Import SimpleWorkflowExecutor at runtime
from ..workflows.simple_workflow import SimpleWorkflowExecutor

# Import CustomWorkflowExecutor at runtime
from ..workflows.custom_workflow import CustomWorkflowExecutor

logger = logging.getLogger(__name__)


class ExecutionFacade:
    """
    A facade that simplifies the execution of different component types
    (Agents, Simple Workflows, Custom Workflows) managed by the HostManager.

    It uses the appropriate executor for each component type.
    """

    def __init__(self, host_manager: "HostManager"):
        """
        Initializes the ExecutionFacade.

        Args:
            host_manager: The initialized HostManager instance containing
                          configurations and the MCPHost instance.
        """
        if not host_manager:
            raise ValueError("HostManager instance is required.")
        if not host_manager.host:
            raise ValueError("HostManager must be initialized with an active MCPHost.")

        self._manager = host_manager
        self._host: "MCPHost" = (
            host_manager.host
        )  # Store direct ref to host for convenience
        logger.info("ExecutionFacade initialized.")

    # --- Execution Methods (to be implemented in subsequent steps) ---

    async def run_agent(
        self, agent_name: str, user_message: str, system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a configured agent by name.
        (Implementation to follow)
        """
        logger.info(f"Facade: Received request to run agent '{agent_name}'")
        # Implementation will involve:
        # 1. Getting AgentConfig from self._manager.agent_configs
        # 2. Instantiating AgentExecutor (or directly Agent if we keep it simple)
        # 1. Get AgentConfig
        try:
            agent_config = self._manager.agent_configs[agent_name]
            logger.debug(f"Facade: Found AgentConfig for '{agent_name}'")
        except KeyError:
            logger.error(
                f"Facade: Agent configuration not found for name: {agent_name}"
            )
            # Return an error structure consistent with Agent execution failures
            return {
                "conversation": [],
                "final_response": None,
                "tool_uses": [],
                "error": f"Configuration error: Agent '{agent_name}' not found.",
            }

        # 2. Instantiate Agent
        try:
            agent_instance = Agent(config=agent_config)
            logger.debug(f"Facade: Instantiated Agent '{agent_name}'")
        except Exception as e:
            logger.error(
                f"Facade: Error instantiating agent '{agent_name}': {e}", exc_info=True
            )
            return {
                "conversation": [],
                "final_response": None,
                "tool_uses": [],
                "error": f"Initialization error for agent '{agent_name}': {e}",
            }

        # 3. Execute Agent
        try:
            result = await agent_instance.execute_agent(
                user_message=user_message,
                host_instance=self._host,  # Pass the host instance
                system_prompt=system_prompt,
            )
            logger.info(f"Facade: Agent '{agent_name}' execution finished.")
            return result
        except Exception as e:
            logger.error(
                f"Facade: Error during agent '{agent_name}' execution: {e}",
                exc_info=True,
            )
            # Return error structure
            return {
                "conversation": [],  # May want to include partial history if available
                "final_response": None,
                "tool_uses": [],
                "error": f"Runtime error during agent '{agent_name}' execution: {e}",
            }

    async def run_simple_workflow(
        self, workflow_name: str, initial_input: Any
    ) -> Dict[str, Any]:
        """
        Executes a configured simple workflow by name.
        (Implementation to follow)
        """
        logger.info(
            f"Facade: Received request to run simple workflow '{workflow_name}'"
        )
        # Implementation will involve:
        # 1. Getting WorkflowConfig from self._manager.workflow_configs
        # 2. Getting required AgentConfigs from self._manager.agent_configs
        # 3. Instantiating SimpleWorkflowExecutor
        # 1. Get WorkflowConfig
        try:
            workflow_config = self._manager.workflow_configs[workflow_name]
            logger.debug(f"Facade: Found WorkflowConfig for '{workflow_name}'")
        except KeyError:
            logger.error(
                f"Facade: Workflow configuration not found for name: {workflow_name}"
            )
            return {
                "workflow_name": workflow_name,
                "status": "failed",
                "final_message": None,
                "error": f"Configuration error: Workflow '{workflow_name}' not found.",
            }

        # 2. Get required AgentConfigs (all needed for the workflow steps)
        # The SimpleWorkflowExecutor handles checking if specific step agents exist
        all_agent_configs = self._manager.agent_configs

        # 3. Instantiate SimpleWorkflowExecutor
        try:
            executor = SimpleWorkflowExecutor(
                config=workflow_config,
                agent_configs=all_agent_configs,
                host_instance=self._host,
            )
            logger.debug(
                f"Facade: Instantiated SimpleWorkflowExecutor for '{workflow_name}'"
            )
        except Exception as e:
            logger.error(
                f"Facade: Error instantiating SimpleWorkflowExecutor for '{workflow_name}': {e}",
                exc_info=True,
            )
            return {
                "workflow_name": workflow_name,
                "status": "failed",
                "final_message": None,
                "error": f"Initialization error for workflow '{workflow_name}': {e}",
            }

        # 4. Execute Workflow
        try:
            result = await executor.execute(initial_input=initial_input)
            logger.info(
                f"Facade: Simple workflow '{workflow_name}' execution finished."
            )
            return result
        except Exception as e:
            logger.error(
                f"Facade: Error during simple workflow '{workflow_name}' execution: {e}",
                exc_info=True,
            )
            return {
                "workflow_name": workflow_name,
                "status": "failed",
                "final_message": None,  # Or potentially the last successful message? Keep None for now.
                "error": f"Runtime error during simple workflow '{workflow_name}' execution: {e}",
            }

    async def run_custom_workflow(self, workflow_name: str, initial_input: Any) -> Any:
        """
        Executes a configured custom workflow by name.
        (Implementation to follow)
        """
        logger.info(
            f"Facade: Received request to run custom workflow '{workflow_name}'"
        )
        # Implementation will involve:
        # 1. Getting CustomWorkflowConfig from self._manager.custom_workflow_configs
        # 2. Instantiating CustomWorkflowExecutor
        # 1. Get CustomWorkflowConfig
        try:
            custom_config = self._manager.custom_workflow_configs[workflow_name]
            logger.debug(f"Facade: Found CustomWorkflowConfig for '{workflow_name}'")
        except KeyError:
            logger.error(
                f"Facade: Custom workflow configuration not found for name: {workflow_name}"
            )
            # Return a generic error structure, as custom workflows can return anything
            return {
                "status": "failed",
                "error": f"Configuration error: Custom workflow '{workflow_name}' not found.",
            }

        # 2. Instantiate CustomWorkflowExecutor
        try:
            # CustomWorkflowExecutor __init__ only takes config now
            executor = CustomWorkflowExecutor(config=custom_config)
            logger.debug(
                f"Facade: Instantiated CustomWorkflowExecutor for '{workflow_name}'"
            )
        except Exception as e:
            logger.error(
                f"Facade: Error instantiating CustomWorkflowExecutor for '{workflow_name}': {e}",
                exc_info=True,
            )
            return {
                "status": "failed",
                "error": f"Initialization error for custom workflow '{workflow_name}': {e}",
            }

        # 3. Execute Workflow, passing self (the facade) as the executor argument
        try:
            # The executor handles dynamic loading and calls the workflow's execute_workflow
            result = await executor.execute(
                initial_input=initial_input,
                executor=self,  # Pass the facade instance itself
            )
            logger.info(
                f"Facade: Custom workflow '{workflow_name}' execution finished."
            )
            return result
        except Exception as e:
            # Catch errors from executor setup OR from within the workflow's execution
            logger.error(
                f"Facade: Error during custom workflow '{workflow_name}' execution: {e}",
                exc_info=True,
            )
            # Return a generic error structure
            return {
                "status": "failed",
                "error": f"Runtime error during custom workflow '{workflow_name}' execution: {e}",
            }

    # --- Helper/Internal Methods (Optional) ---
    # May add methods later if needed for shared logic between run_* methods.
