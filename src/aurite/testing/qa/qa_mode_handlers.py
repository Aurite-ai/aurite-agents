"""
Mode handlers for QA evaluation.

This module provides different execution strategies for the three evaluation modes:
- Aurite: Execute components via AuriteEngine
- Manual: Use pre-recorded outputs from test cases
- Function: Execute custom run functions
"""

import inspect
import logging
import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

from aurite.lib.config.config_manager import ConfigManager
from aurite.lib.models.config.components import EvaluationCase, EvaluationConfig

from ..runners.agent_runner import AgentRunner

if TYPE_CHECKING:
    from aurite.execution.aurite_engine import AuriteEngine

logger = logging.getLogger(__name__)


class BaseModeHandler(ABC):
    """
    Base class for mode-specific evaluation handlers.

    Each mode handler is responsible for:
    1. Preparing/loading component configuration
    2. Executing test cases and obtaining output
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize the mode handler.

        Args:
            config_manager: Optional ConfigManager for loading configurations
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def prepare_config(
        self, request: EvaluationConfig, executor: Optional["AuriteEngine"] = None
    ) -> Optional[str]:
        """
        Prepare configuration for evaluation.

        Args:
            request: The evaluation request (will be modified in place)
            executor: Optional AuriteEngine for component execution

        Returns:
            Component name if applicable, None otherwise
        """
        pass

    @abstractmethod
    async def get_output(
        self,
        case: EvaluationCase,
        request: EvaluationConfig,
        executor: Optional["AuriteEngine"] = None,
    ) -> Any:
        """
        Get output for a test case.

        Args:
            case: The test case to execute
            request: The evaluation request containing execution parameters
            executor: Optional AuriteEngine for component execution

        Returns:
            The output from execution

        Raises:
            ValueError: If execution is not possible with the given parameters
        """
        pass


class AuriteModeHandler(BaseModeHandler):
    """
    Handler for Aurite mode evaluation.

    This mode loads component configurations and executes them via AuriteEngine.
    Supports agents, workflows, and MCP servers.
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None, mcp_test_agents: Optional[dict] = None):
        """
        Initialize the Aurite mode handler.

        Args:
            config_manager: Optional ConfigManager for loading configurations
            mcp_test_agents: Optional dict to cache MCP test agents
        """
        super().__init__(config_manager)
        # Cache for MCP server test agents to reuse across test cases
        self._mcp_test_agents = mcp_test_agents if mcp_test_agents is not None else {}

    async def prepare_config(
        self, request: EvaluationConfig, executor: Optional["AuriteEngine"] = None
    ) -> Optional[str]:
        """
        Load component configuration for Aurite mode.

        Args:
            request: The evaluation request (will be modified in place)
            executor: Optional AuriteEngine (unused in this method)

        Returns:
            The component name
        """
        component_name = None

        # Get component name from component_refs
        if request.component_refs and len(request.component_refs) >= 1:
            component_name = request.component_refs[0]

        # If component_config is already provided, use it
        if request.component_config:
            component_name = request.component_config.get("name", component_name or "unknown")
            self.logger.info(f"Using provided component config for {component_name}")
        elif self.config_manager and component_name and request.component_type:
            # Load component config from ConfigManager
            try:
                self.logger.info(f"Loading component config for {request.component_type}.{component_name}")
                config = self.config_manager.get_config(
                    component_type=request.component_type, component_id=component_name
                )
                if config:
                    request.component_config = config
                    self.logger.info("Successfully loaded component config")
                else:
                    self.logger.warning(f"No config found for {request.component_type}.{component_name}")
            except Exception as e:
                self.logger.warning(f"Could not load component config: {e}")

        return component_name

    async def get_output(
        self,
        case: EvaluationCase,
        request: EvaluationConfig,
        executor: Optional["AuriteEngine"] = None,
    ) -> Any:
        """
        Execute component via AuriteEngine and get output.

        Args:
            case: The test case to execute
            request: The evaluation request containing execution parameters
            executor: AuriteEngine for component execution

        Returns:
            The output from component execution

        Raises:
            ValueError: If executor is not provided or component name is not specified
        """
        if not executor:
            raise ValueError(f"Case {case.id}: AuriteEngine executor required for Aurite mode")

        # Get component name
        component_name = None
        if request.component_config:
            component_name = request.component_config.get("name")
        if not component_name and request.component_refs:
            component_name = request.component_refs[0]
        if not component_name:
            raise ValueError(f"Case {case.id}: No component name specified for execution")

        component_type = request.component_type
        self.logger.debug(f"Executing {component_type} '{component_name}' for case {case.id}")

        # Execute based on component type
        if component_type == "agent":
            result = await executor.run_agent(
                agent_name=component_name,
                user_message=case.input,
            )
            # Return the primary text response
            return result.primary_text if hasattr(result, "primary_text") else str(result)

        elif component_type in ["workflow", "linear_workflow"]:
            return await executor.run_linear_workflow(
                workflow_name=component_name,
                initial_input=case.input,
            )

        elif component_type == "custom_workflow":
            return await executor.run_custom_workflow(
                workflow_name=component_name,
                initial_input=case.input,
            )

        elif component_type == "graph_workflow":
            return await executor.run_graph_workflow(
                workflow_name=component_name,
                initial_input=case.input,
            )

        elif component_type == "mcp_server":
            # Check if we already have a test agent for this MCP server
            if component_name in self._mcp_test_agents:
                agent_name = self._mcp_test_agents[component_name]
                self.logger.debug(f"Reusing existing test agent '{agent_name}' for MCP server '{component_name}'")
            else:
                # Create a new test agent for this MCP server
                agent_name = f"qa_test_agent_{component_name}_{uuid.uuid4().hex[:8]}"
                agent_config = {
                    "name": agent_name,
                    "type": "agent",
                    "mcp_servers": [component_name],
                    "llm_config_id": request.review_llm,
                    "system_prompt": f"""You are an expert test engineer who has been tasked with testing an MCP server named {component_name}. You have access to the tools defined by that server.
The user will give you a message which should inform which tool to call. If arguments for the tool are given, use those, and if not generate appropriate arguments yourself.
Finally, respond with the information returned by the tool.""",
                }
                executor._config_manager.create_component(component_type="agent", component_config=agent_config)
                self.logger.info(f"Created test agent '{agent_name}' for MCP server '{component_name}'")

                # Store in cache
                self._mcp_test_agents[component_name] = agent_name

            result = await executor.run_agent(
                agent_name=agent_name,
                user_message=case.input,
            )

            # Return the primary text response
            return result.primary_text if hasattr(result, "primary_text") else str(result)

        else:
            raise ValueError(f"Unsupported component type for execution: {component_type}")


class ManualModeHandler(BaseModeHandler):
    """
    Handler for Manual mode evaluation.

    This mode uses pre-recorded outputs from test cases.
    No component execution is performed.
    """

    async def prepare_config(
        self, request: EvaluationConfig, executor: Optional["AuriteEngine"] = None
    ) -> Optional[str]:
        """
        No configuration loading needed for manual mode.

        Args:
            request: The evaluation request (unused)
            executor: Optional AuriteEngine (unused)

        Returns:
            None (no component name in manual mode)
        """
        self.logger.info("Manual mode - no component loading required")
        return None

    async def get_output(
        self,
        case: EvaluationCase,
        request: EvaluationConfig,
        executor: Optional["AuriteEngine"] = None,
    ) -> Any:
        """
        Get pre-recorded output from test case.

        Args:
            case: The test case with pre-recorded output
            request: The evaluation request (unused)
            executor: Optional AuriteEngine (unused)

        Returns:
            The pre-recorded output

        Raises:
            ValueError: If output is not provided in the test case
        """
        if case.output is None:
            raise ValueError(f"Case {case.id}: Manual mode requires output to be provided in test case")

        self.logger.debug(f"Using pre-recorded output for case {case.id}")
        return case.output


class FunctionModeHandler(BaseModeHandler):
    """
    Handler for Function mode evaluation.

    This mode executes custom run functions provided in the evaluation request.
    Supports string agent names, async functions, and regular callables.
    """

    async def prepare_config(
        self, request: EvaluationConfig, executor: Optional["AuriteEngine"] = None
    ) -> Optional[str]:
        """
        No configuration loading needed for function mode.

        Args:
            request: The evaluation request (unused)
            executor: Optional AuriteEngine (unused)

        Returns:
            None (no component name in function mode)
        """
        self.logger.info("Function mode - using custom run function")
        return None

    async def get_output(
        self,
        case: EvaluationCase,
        request: EvaluationConfig,
        executor: Optional["AuriteEngine"] = None,
    ) -> Any:
        """
        Execute custom run function and get output.

        Args:
            case: The test case to execute
            request: The evaluation request containing run_agent function
            executor: Optional AuriteEngine (unused)

        Returns:
            The output from the run function

        Raises:
            ValueError: If run_agent is not provided
        """
        run_agent = getattr(request, "run_agent", None)
        if not run_agent:
            raise ValueError(f"Case {case.id}: Function mode requires run_agent to be provided")

        self.logger.debug(f"Using custom execution function for case {case.id}")
        run_agent_kwargs = getattr(request, "run_agent_kwargs", {})

        if isinstance(run_agent, str):
            # It's an agent name - use AgentRunner
            runner = AgentRunner(run_agent)
            return await runner.execute(case.input, **run_agent_kwargs)
        elif inspect.iscoroutinefunction(run_agent):
            # It's an async function
            return await run_agent(case.input, **run_agent_kwargs)
        else:
            # It's a regular callable
            return run_agent(case.input, **run_agent_kwargs)


def get_mode_handler(
    mode: str,
    config_manager: Optional[ConfigManager] = None,
    mcp_test_agents: Optional[dict] = None,
) -> BaseModeHandler:
    """
    Factory function to get the appropriate mode handler.

    Args:
        mode: The evaluation mode ('aurite', 'manual', or 'function')
        config_manager: Optional ConfigManager for loading configurations
        mcp_test_agents: Optional dict to cache MCP test agents (for Aurite mode)

    Returns:
        The appropriate mode handler instance

    Raises:
        ValueError: If mode is not recognized
    """
    if mode == "aurite":
        return AuriteModeHandler(config_manager=config_manager, mcp_test_agents=mcp_test_agents)
    elif mode == "manual":
        return ManualModeHandler(config_manager=config_manager)
    elif mode == "function":
        return FunctionModeHandler(config_manager=config_manager)
    else:
        raise ValueError(f"Unknown evaluation mode: {mode}")
