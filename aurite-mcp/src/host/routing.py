"""
Message routing for MCP host.
"""

from typing import Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


class MessageRouter:
    """
    Routes messages between agents and tool servers.
    Manages tool registration and client selection.
    """

    def __init__(self):
        # tool_name -> client_id
        self._tool_routes: Dict[str, str] = {}

        # client_id -> Set[str] (tool names)
        self._client_tools: Dict[str, Set[str]] = {}

        # tool_name -> List[str] (capabilities)
        self._tool_capabilities: Dict[str, List[str]] = {}

    async def initialize(self):
        """Initialize the message router"""
        logger.info("Initializing message router")

    async def register_tool(
        self, tool_name: str, client_id: str, capabilities: List[str]
    ):
        """
        Register a tool with its providing client and capabilities.
        This information is used for routing decisions.
        """
        # Register the route
        if tool_name in self._tool_routes:
            logger.warning(f"Overwriting existing route for tool: {tool_name}")
        self._tool_routes[tool_name] = client_id

        # Update client tools
        if client_id not in self._client_tools:
            self._client_tools[client_id] = set()
        self._client_tools[client_id].add(tool_name)

        # Store capabilities
        self._tool_capabilities[tool_name] = capabilities

        logger.info(
            f"Registered tool {tool_name} for client {client_id} "
            f"with capabilities: {capabilities}"
        )

    async def get_client_for_tool(self, tool_name: str) -> Optional[str]:
        """Get the client ID that provides a specific tool"""
        return self._tool_routes.get(tool_name)

    async def get_tools_for_client(self, client_id: str) -> Set[str]:
        """Get all tools provided by a specific client"""
        return self._client_tools.get(client_id, set())

    async def get_tool_capabilities(self, tool_name: str) -> List[str]:
        """Get the capabilities of a specific tool"""
        return self._tool_capabilities.get(tool_name, [])

    async def find_tool_by_capability(self, capability: str) -> Optional[str]:
        """Find a tool that provides a specific capability"""
        for tool_name, capabilities in self._tool_capabilities.items():
            if capability in capabilities:
                return tool_name
        return None

    async def shutdown(self):
        """Shutdown the message router"""
        logger.info("Shutting down message router")

        # Clear all routing data
        self._tool_routes.clear()
        self._client_tools.clear()
        self._tool_capabilities.clear()
