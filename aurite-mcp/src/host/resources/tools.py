"""
Tool management for MCP Host.

This module provides a ToolManager class that handles:
1. Tool registration and discovery
2. Tool execution and validation
3. Tool capability mapping
4. Integration with agent frameworks
"""

from typing import Dict, List, Any, Optional
import logging
import asyncio

import mcp.types as types

# Import from lower layers for dependencies
from ..foundation import RootManager
from ..communication import MessageRouter

logger = logging.getLogger(__name__)


class ToolManager:
    """
    Manages tool registration, discovery, and execution.
    Part of the resource management layer of the Host system.

    This manager allows the agent framework to interact with tools
    without requiring the entire host system.
    """

    def __init__(self, root_manager: RootManager, message_router: MessageRouter):
        """
        Initialize the tool manager.

        Args:
            root_manager: The root manager for access control
            message_router: The message router for routing decisions
        """
        self._root_manager = root_manager
        self._message_router = message_router

        # Tool registry
        self._tools: Dict[str, types.Tool] = {}
        self._tool_metadata: Dict[str, Dict[str, Any]] = {}

        # Client registry - will be populated during client initialization
        self._clients: Dict[str, Any] = {}  # Client ID to client session

        # Active requests
        self._active_requests: Dict[str, asyncio.Task] = {}

    async def initialize(self):
        """Initialize the tool manager"""
        logger.info("Initializing tool manager")
        # No initialization needed beyond the constructor at this point

    def register_client(self, client_id: str, client_session):
        """Register a client session with the tool manager"""
        self._clients[client_id] = client_session

    async def register_tool(
        self, tool_name: str, tool: types.Tool, client_id: str, capabilities: List[str]
    ):
        """
        Register a tool with its providing client and capabilities.

        Args:
            tool_name: The name of the tool
            tool: The tool definition
            client_id: The ID of the client providing the tool
            capabilities: The capabilities of the tool
        """
        # Store the tool
        self._tools[tool_name] = tool

        # Store metadata
        self._tool_metadata[tool_name] = {
            "client_id": client_id,
            "capabilities": capabilities,
            "description": tool.description if hasattr(tool, "description") else "",
            "parameters": tool.parameters if hasattr(tool, "parameters") else {},
        }

        # Register with the message router
        await self._message_router.register_tool(tool_name, client_id, capabilities)

        logger.info(f"Registered tool {tool_name} for client {client_id}")

    async def discover_client_tools(self, client_id: str, client_session):
        """
        Discover tools provided by a client.

        Args:
            client_id: The client ID
            client_session: The client session

        Returns:
            List of discovered tools
        """
        try:
            # Get tools from the client
            tools_response = await client_session.list_tools()

            # Register each tool
            for tool in tools_response.tools:
                await self.register_tool(
                    tool_name=tool.name,
                    tool=tool,
                    client_id=client_id,
                    capabilities=[],  # Will be updated by the host
                )

            return tools_response.tools
        except Exception as e:
            logger.error(f"Failed to discover tools for client {client_id}: {e}")
            raise

    async def execute_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> List[types.TextContent]:
        """
        Execute a tool with the given arguments.

        Args:
            tool_name: The name of the tool to execute
            arguments: The arguments to pass to the tool

        Returns:
            The result of the tool execution
        """
        # Validate tool exists
        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Get server for this tool
        server_id = await self._message_router.select_server_for_tool(
            tool_name,
            required_capabilities=set(),  # Could be derived from arguments/context
        )
        if not server_id:
            raise ValueError(f"No server found for tool: {tool_name}")

        # Get client session
        client = self._clients.get(server_id)
        if not client:
            raise ValueError(f"Client not found for server: {server_id}")

        # Validate access through root manager
        await self._root_manager.validate_access(
            client_id=server_id, tool_name=tool_name
        )

        # Execute the tool
        try:
            result = await client.call_tool(tool_name, arguments)

            # Convert result to proper types if it's been serialized to tuples
            if isinstance(result, tuple):
                result_dict = dict(result)
                return [
                    types.TextContent(type="text", text=c.text)
                    if hasattr(c, "text")
                    else types.TextContent(type="text", text=str(c))
                    for c in result_dict.get("content", [])
                ]

            # Handle the result directly as a CallToolResult
            if hasattr(result, "isError") and result.isError:
                raise ValueError(
                    result.content[0].text if result.content else "Unknown error"
                )

            if hasattr(result, "content"):
                return result.content

            return result
        except Exception as e:
            logger.error(f"Tool execution failed - {tool_name}: {e}")
            raise

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all available tools with metadata.

        Returns:
            List of tools with metadata
        """
        return [
            {
                "name": name,
                "description": self._tool_metadata[name].get("description", ""),
                "capabilities": self._tool_metadata[name].get("capabilities", []),
                "parameters": self._tool_metadata[name].get("parameters", {}),
            }
            for name in self._tools
        ]

    def get_tool(self, tool_name: str) -> Optional[types.Tool]:
        """
        Get a tool by name.

        Args:
            tool_name: The name of the tool

        Returns:
            The tool if found, None otherwise
        """
        return self._tools.get(tool_name)

    def has_tool(self, tool_name: str) -> bool:
        """
        Check if a tool exists.

        Args:
            tool_name: The name of the tool

        Returns:
            True if the tool exists, False otherwise
        """
        return tool_name in self._tools

    async def find_tools_by_capability(self, capability: str) -> List[str]:
        """
        Find tools that provide a specific capability.

        Args:
            capability: The capability to search for

        Returns:
            List of tool names that provide the capability
        """
        return [
            name
            for name, metadata in self._tool_metadata.items()
            if capability in metadata.get("capabilities", [])
        ]

    async def shutdown(self):
        """Shutdown the tool manager"""
        logger.info("Shutting down tool manager")

        # Cancel any active requests
        for task in self._active_requests.values():
            task.cancel()

        # Clear registries
        self._tools.clear()
        self._tool_metadata.clear()
        self._clients.clear()
