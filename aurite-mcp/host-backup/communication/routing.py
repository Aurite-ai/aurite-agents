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

        # prompt_name -> client_id
        self._prompt_routes: Dict[str, str] = {}

        # client_id -> Set[str] (prompt names)
        self._client_prompts: Dict[str, Set[str]] = {}

        # New server-specific mappings
        self._server_capabilities: Dict[str, Set[str]] = {}  # server_id -> capabilities
        self._server_weights: Dict[str, float] = {}  # server_id -> routing weight

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

    async def register_prompt(self, prompt_name: str, client_id: str):
        """Register which client provides a prompt"""
        if prompt_name in self._prompt_routes:
            logger.warning(f"Overwriting existing route for prompt: {prompt_name}")
        self._prompt_routes[prompt_name] = client_id

        # Update client prompts
        if client_id not in self._client_prompts:
            self._client_prompts[client_id] = set()
        self._client_prompts[client_id].add(prompt_name)

        logger.info(f"Registered prompt {prompt_name} for client {client_id}")

    async def get_client_for_tool(self, tool_name: str) -> Optional[str]:
        """Get the client ID that provides a specific tool"""
        return self._tool_routes.get(tool_name)

    async def get_client_for_prompt(self, prompt_name: str) -> Optional[str]:
        """Get the client ID that provides a specific prompt"""
        return self._prompt_routes.get(prompt_name)

    async def get_tools_for_client(self, client_id: str) -> Set[str]:
        """Get all tools provided by a specific client"""
        return self._client_tools.get(client_id, set())

    async def get_prompts_for_client(self, client_id: str) -> Set[str]:
        """Get all prompts provided by a specific client"""
        return self._client_prompts.get(client_id, set())

    async def get_tool_capabilities(self, tool_name: str) -> List[str]:
        """Get the capabilities of a specific tool"""
        return self._tool_capabilities.get(tool_name, [])

    async def find_tool_by_capability(self, capability: str) -> Optional[str]:
        """Find a tool that provides a specific capability"""
        for tool_name, capabilities in self._tool_capabilities.items():
            if capability in capabilities:
                return tool_name
        return None

    async def register_server(
        self, server_id: str, capabilities: Set[str], weight: float = 1.0
    ):
        """Register an MCP server with its capabilities and routing weight"""
        self._server_capabilities[server_id] = capabilities
        self._server_weights[server_id] = weight
        logger.info(f"Registered server {server_id} with capabilities: {capabilities}")

    async def select_server_for_tool(
        self, tool_name: str, required_capabilities: Set[str] = None
    ) -> Optional[str]:
        """Select best server for a tool based on capabilities and weights"""
        # First check for direct routes (servers with weight 1.0)
        if tool_name in self._tool_routes:
            server_id = self._tool_routes[tool_name]
            if self._server_weights.get(server_id, 1.0) == 1.0:
                return server_id

        # Only consider alternative servers (weight < 1.0) for routing
        eligible_servers = []
        for server_id, capabilities in self._server_capabilities.items():
            if (
                self._server_weights.get(server_id, 1.0) < 1.0
            ):  # Only consider backup servers
                if not required_capabilities or required_capabilities.issubset(
                    capabilities
                ):
                    if tool_name in self._client_tools.get(server_id, set()):
                        eligible_servers.append(server_id)

        if not eligible_servers:
            # If no backup servers found, return the original direct route if it exists
            return self._tool_routes.get(tool_name)

        # Select based on weights among backup servers
        return max(eligible_servers, key=lambda s: self._server_weights[s])

    async def shutdown(self):
        """Shutdown the message router"""
        logger.info("Shutting down message router")

        # Clear all routing data
        self._tool_routes.clear()
        self._client_tools.clear()
        self._tool_capabilities.clear()
        self._prompt_routes.clear()
        self._client_prompts.clear()
        self._server_capabilities.clear()
        self._server_weights.clear()

    async def get_server_capabilities(self, server_id: str) -> Set[str]:
        """Get the capabilities of a specific server"""
        return self._server_capabilities.get(server_id, set())

    async def update_server_weight(self, server_id: str, weight: float):
        """Update the routing weight for a server"""
        if server_id not in self._server_capabilities:
            raise ValueError(f"Server not registered: {server_id}")
        self._server_weights[server_id] = weight
        logger.info(f"Updated weight for server {server_id}: {weight}")

    async def remove_server(self, server_id: str):
        """Remove a server and its capabilities"""
        self._server_capabilities.pop(server_id, None)
        self._server_weights.pop(server_id, None)

        # Clean up any routes pointing to this server
        self._tool_routes = {
            tool: client
            for tool, client in self._tool_routes.items()
            if client != server_id
        }
        self._prompt_routes = {
            prompt: client
            for prompt, client in self._prompt_routes.items()
            if client != server_id
        }

        logger.info(f"Removed server {server_id} and its routes")
