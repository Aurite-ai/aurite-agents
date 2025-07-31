"""
The ToolHost acts as a central router for all tool-related operations,
managing both MCP-based tools via an MCPHost and custom in-process tools
via a pluggable provider system.
"""

import logging
from typing import Any, Dict, List

import mcp.types as types

from ..config.config_models import AgentConfig
from .base_provider import BaseToolProvider
from .filtering import FilteringManager
from .host import MCPHost

logger = logging.getLogger(__name__)


class ToolHost:
    """
    A unified tool router that manages and delegates tool discovery and
    execution to either the MCPHost for external tools or to registered
    ToolProviders for custom, in-process tools.
    """

    def __init__(self, mcp_host: MCPHost):
        self._mcp_host = mcp_host
        self._providers: Dict[str, BaseToolProvider] = {}
        self._filtering_manager = FilteringManager()
        logger.debug("ToolHost initialized.")

    def register_provider(self, provider: BaseToolProvider):
        """
        Registers a custom tool provider with the ToolHost.

        Args:
            provider: An instance of a class that implements BaseToolProvider.
        """
        provider_name = provider.provider_name()
        if provider_name in self._providers:
            logger.warning(f"A ToolProvider with the name '{provider_name}' is already registered. Overwriting.")
        self._providers[provider_name] = provider
        logger.info(f"ToolProvider '{provider_name}' registered successfully.")

    async def register_component(self, component_type: str, config: Any):
        """
        Finds the appropriate provider for a given component type and
        delegates the registration of the component's configuration to it.

        Args:
            component_type: The type of the component (e.g., 'storage').
            config: The configuration object for the component instance.
        """
        if component_type in self._providers:
            provider = self._providers[component_type]
            await provider.register_component(config)
        else:
            logger.error(f"No ToolProvider registered for component type '{component_type}'.")
            raise ValueError(f"No ToolProvider registered for component type '{component_type}'")

    def get_formatted_tools(self, agent_config: AgentConfig) -> List[Dict[str, Any]]:
        """
        Gathers tool schemas from the MCPHost and all registered providers,
        merges them into a single list, and applies agent-specific filtering.

        Args:
            agent_config: The configuration of the agent requesting the tools.

        Returns:
            A list of tool schemas formatted for use by an LLM.
        """
        # 1. Get tools from MCPHost
        all_tools = list(self._mcp_host.tools.values())

        # 2. Get tools from all custom providers
        for provider in self._providers.values():
            all_tools.extend(provider.get_tool_schemas())

        # 3. Format and filter the unified list
        formatted_tools = [tool.model_dump(exclude_none=True) for tool in all_tools]
        return self._filtering_manager.filter_component_list(formatted_tools, agent_config)

    async def call_tool(self, name: str, args: Dict[str, Any]) -> types.CallToolResult:
        """
        Routes a tool call to the correct handler. It first checks all
        registered custom providers, and if none can handle the tool,
        it delegates the call to the MCPHost.

        Args:
            name: The unique name of the tool to execute.
            args: The arguments for the tool call.

        Returns:
            The result of the tool execution.
        """
        # Check custom providers first
        for provider in self._providers.values():
            if provider.can_handle(name):
                logger.debug(f"Routing tool call '{name}' to provider '{provider.provider_name()}'.")
                return await provider.call_tool(name, args)

        # If no custom provider claims it, delegate to MCPHost
        logger.debug(f"Routing tool call '{name}' to MCPHost.")
        return await self._mcp_host.call_tool(name, args)
