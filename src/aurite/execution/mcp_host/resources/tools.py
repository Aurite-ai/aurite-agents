"""
Tool management for MCP Host.

This module provides a ToolManager class that handles:
1. Tool registration and discovery
2. Tool execution and validation
3. Tool capability mapping
4. Integration with agent frameworks
"""

import logging
from typing import Any, Dict, List, Optional

# import asyncio # No longer needed after removing _active_requests
import mcp.types as types
from mcp.client.session_group import ClientSessionGroup

from aurite.lib.config.config_models import AgentConfig

from ..filtering import FilteringManager

# Import from lower layers for dependencies
from ..foundation import MessageRouter, RootManager

logger = logging.getLogger(__name__)


class ToolManager:
    """
    Manages tool registration, discovery, and execution.
    Part of the resource management layer of the Host system.
    """

    def __init__(
        self,
        root_manager: RootManager,
        message_router: MessageRouter,
        session_group: ClientSessionGroup,
    ):
        self._root_manager = root_manager
        self._message_router = message_router
        self._session_group = session_group

    async def initialize(self):
        """Initialize the tool manager"""
        logger.debug("Initializing tool manager")
        for tool in self._session_group.tools.values():
            client_id = getattr(tool, "client_id", "unknown")
            await self._message_router.register_tool(tool.name, client_id)

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        client_name: Optional[str] = None,
    ) -> Any:
        """
        Execute a tool with the given arguments.
        """
        # The session group handles routing and execution
        return await self._session_group.call_tool(tool_name, arguments)

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all available tools with basic metadata.
        """
        tool_list = []
        for tool in self._session_group.tools.values():
            tool_list.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                }
            )
        return tool_list

    def get_tool(self, tool_name: str) -> Optional[types.Tool]:
        """
        Get a tool by name.
        """
        return self._session_group.tools.get(tool_name)

    def has_tool(self, tool_name: str) -> bool:
        """
        Check if a tool exists.
        """
        return tool_name in self._session_group.tools

    def format_tools_for_llm(
        self,
        filtering_manager: FilteringManager,
        agent_config: Optional[AgentConfig] = None,
        tool_names: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Format tools for use with LLM APIs, applying agent-specific filters.
        """
        all_tools = list(self._session_group.tools.values())

        if tool_names:
            all_tools = [tool for tool in all_tools if tool.name in tool_names]

        formatted_tools = [tool.model_dump() for tool in all_tools]

        if agent_config:
            return filtering_manager.filter_component_list(formatted_tools, agent_config)

        return formatted_tools

    def format_tool_result(self, tool_result) -> str:
        """
        Format a tool result as text.
        """
        if isinstance(tool_result, list):
            return "\n".join([getattr(item, "text", str(item)) for item in tool_result])
        else:
            return str(tool_result)

    def create_tool_result_blocks(self, tool_use_id: str, tool_result: Any, is_error: bool = False) -> Dict[str, Any]:
        """
        Create a properly formatted tool result block for LLM APIs.
        """
        if isinstance(tool_result, list) and all(hasattr(item, "text") for item in tool_result):
            content_list = [{"type": "text", "text": item.text} for item in tool_result]
        elif isinstance(tool_result, str):
            content_list = [{"type": "text", "text": tool_result}]
        else:
            logger.warning(f"Formatting unexpected tool result type: {type(tool_result)}")
            content_list = [{"type": "text", "text": str(tool_result)}]

        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": content_list,
            "is_error": is_error,
        }

    async def shutdown(self):
        """Shutdown the tool manager"""
        logger.debug("Shutting down tool manager")
