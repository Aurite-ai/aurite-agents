# src/execution/facade.py
"""
Provides a unified facade for executing Agents, Simple Workflows, and Custom Workflows.
"""

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING, Callable, Coroutine

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from ..host_manager import HostManager
    from ..host.host import MCPHost  # Needed for passing to executors/workflows
    from ..agents.agent import Agent  # Keep type hint here
    from ..workflows.simple_workflow import (
        SimpleWorkflowExecutor,
    )  # Import for type hint
    from ..workflows.custom_workflow import CustomWorkflowExecutor
    from ..storage.db_manager import StorageManager # Import StorageManager for type hint

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

    It uses the appropriate executor for each component type and passes
    the StorageManager if available.
    """

    def __init__(self, host_manager: "HostManager", storage_manager: Optional["StorageManager"] = None):
        """
        Initializes the ExecutionFacade.

        Args:
            host_manager: The initialized HostManager instance containing
                          configurations and the MCPHost instance.
            storage_manager: An optional initialized StorageManager instance for persistence.
        """
        if not host_manager:
            raise ValueError("HostManager instance is required.")
        if not host_manager.host:
            raise ValueError("HostManager must be initialized with an active MCPHost.")

        self._manager = host_manager
        self._host: "MCPHost" = host_manager.host
        self._storage_manager = storage_manager # Store storage manager instance
        logger.debug(f"ExecutionFacade initialized (StorageManager {'present' if storage_manager else 'absent'}).")

    # --- Private Execution Helper ---

    async def _execute_component(
        self,
        component_type: str,
        component_name: str,
        config_lookup: Callable[[str], Any],
        executor_setup: Callable[[Any], Any],
        execution_func: Callable[..., Coroutine[Any, Any, Any]],
        error_structure_factory: Callable[[str, str], Dict[str, Any]],
        **execution_kwargs: Any,
    ) -> Any:
        """
        Generic helper to execute a component (Agent, Workflow).

        Handles config lookup, instantiation, execution, and error handling.

        Args:
            component_type: String description (e.g., "Agent", "Simple Workflow").
            component_name: The name of the component instance to execute.
            config_lookup: Callable that takes component_name and returns its config.
            executor_setup: Callable that takes the config and returns the executor/agent instance.
            execution_func: The async execution method of the executor/agent instance.
            error_structure_factory: Callable that takes component_name and error message
                                     and returns the standardized error dictionary.
            **execution_kwargs: Arguments to pass to the execution_func.

        Returns:
            The result of the execution or a standardized error dictionary.
        """
        logger.info(
            f"Facade: Received request to run {component_type} '{component_name}'"
        )

        # 1. Get Configuration
        try:
            config = config_lookup(component_name)
            logger.debug(  # Already DEBUG
                f"Facade: Found {component_type}Config for '{component_name}'"
            )
        except KeyError:
            error_msg = (
                f"Configuration error: {component_type} '{component_name}' not found."
            )
            logger.error(f"Facade: {error_msg}")
            # Call factory with positional arguments
            return error_structure_factory(component_name, error_msg)
        except Exception as config_err:
            # Catch unexpected errors during config lookup
            error_msg = f"Unexpected error retrieving config for {component_type} '{component_name}': {config_err}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            return error_structure_factory(component_name, error_msg)

        # Add explicit check if config lookup succeeded but returned None
        if config is None:
            error_msg = (
                f"{component_type} '{component_name}' not found (lookup returned None)."
            )
            logger.error(f"Facade: {error_msg}")
            # Call factory with positional arguments
            return error_structure_factory(component_name, error_msg)

        # 2. Instantiate Executor/Agent
        try:
            instance = executor_setup(config)
            logger.debug(  # Already DEBUG
                f"Facade: Instantiated {component_type} '{component_name}'"
            )
        except Exception as setup_err:
            error_msg = f"Initialization error for {component_type} '{component_name}': {setup_err}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            # Call factory with positional arguments
            return error_structure_factory(component_name, error_msg)

        # 3. Execute
        try:
            result = await execution_func(instance, **execution_kwargs)
            logger.info(  # Keep final success as INFO
                f"Facade: {component_type} '{component_name}' execution finished."
            )
            return result
        except (
            KeyError,
            FileNotFoundError,
            AttributeError,
            ImportError,
            PermissionError,
            TypeError,
            RuntimeError,
        ) as exec_err:
            # Catch specific errors known to occur during execution/setup within executors
            error_msg = f"Runtime error during {component_type} '{component_name}' execution: {type(exec_err).__name__}: {exec_err}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            # Re-raise these specific errors so API handlers can catch them
            raise exec_err
        except Exception as e:
            # Catch other unexpected errors during execution
            error_msg = f"Unexpected runtime error during {component_type} '{component_name}' execution: {e}"
            logger.error(f"Facade: {error_msg}", exc_info=True)
            # Return standardized error structure for generic exceptions, passing positional args
            return error_structure_factory(component_name, error_msg)

    # --- Public Execution Methods ---

    async def run_agent(
        self, agent_name: str, user_message: str, system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Executes a configured agent by name using the helper."""

        def error_factory(name: str, msg: str) -> Dict[str, Any]:
            return {
                "conversation": [],
                "final_response": None,
                "tool_uses": [],
                "error": msg,
            }

        return await self._execute_component(
            component_type="Agent",
            component_name=agent_name,
            config_lookup=lambda name: self._manager.agent_configs[name],
            # Pass storage_manager to execute_agent, not Agent constructor
            executor_setup=lambda config: Agent(config=config),
            execution_func=lambda instance, **kwargs: instance.execute_agent(**kwargs),
            error_structure_factory=error_factory,
            # Execution kwargs:
            user_message=user_message,
            host_instance=self._host,
            storage_manager=self._storage_manager, # Pass storage manager here
            system_prompt=system_prompt,
        )

    async def run_simple_workflow(
        self, workflow_name: str, initial_input: Any
    ) -> Dict[str, Any]:
        """Executes a configured simple workflow by name using the helper."""

        def error_factory(name: str, msg: str) -> Dict[str, Any]:
            return {
                "workflow_name": name,
                "status": "failed",
                "final_message": None,
                "error": msg,
            }

        return await self._execute_component(
            component_type="Simple Workflow",
            component_name=workflow_name,
            config_lookup=lambda name: self._manager.workflow_configs[name],
            # Pass storage_manager to SimpleWorkflowExecutor if it needs it (currently doesn't)
            executor_setup=lambda config: SimpleWorkflowExecutor(
                config=config,
                agent_configs=self._manager.agent_configs,
                host_instance=self._host,
                # storage_manager=self._storage_manager # Add if needed later for workflow history
            ),
            execution_func=lambda instance, **kwargs: instance.execute(**kwargs),
            error_structure_factory=error_factory,
            # Execution kwargs:
            initial_input=initial_input,
        )

    async def run_custom_workflow(self, workflow_name: str, initial_input: Any) -> Any:
        """Executes a configured custom workflow by name using the helper."""

        def error_factory(name: str, msg: str) -> Dict[str, Any]:
            # Custom workflows can return anything, so error structure is simpler
            return {"status": "failed", "error": msg}

        return await self._execute_component(
            component_type="Custom Workflow",
            component_name=workflow_name,
            config_lookup=lambda name: self._manager.custom_workflow_configs[name],
            # Pass storage_manager to CustomWorkflowExecutor if it needs it
            executor_setup=lambda config: CustomWorkflowExecutor(
                config=config,
                # storage_manager=self._storage_manager # Add if needed later
                ),
            execution_func=lambda instance, **kwargs: instance.execute(**kwargs),
            error_structure_factory=error_factory,
            # Execution kwargs:
            initial_input=initial_input,
            executor=self,  # Pass the facade itself to the custom workflow
        )
