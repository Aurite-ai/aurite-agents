"""
Registry for mapping tools and prompts to the clients that provide them.
"""

from typing import Dict, List, Set
import logging
from collections import defaultdict  # Import defaultdict

logger = logging.getLogger(__name__)


class MessageRouter:
    """
    Maintains mappings between tool/prompt names and the client IDs that offer them.
    Also stores basic server information like capabilities and weights.
    Does NOT handle client selection logic (this is done by managers/host).
    """

    def __init__(self):
        # tool_name -> List[client_id]
        self._tool_routes: Dict[str, List[str]] = defaultdict(list)

        # client_id -> Set[str] (tool names provided by this client)
        self._client_tools: Dict[str, Set[str]] = defaultdict(set)

        # prompt_name -> List[client_id]
        self._prompt_routes: Dict[str, List[str]] = defaultdict(list)

        # client_id -> Set[str] (prompt names provided by this client)
        self._client_prompts: Dict[str, Set[str]] = defaultdict(set)

        # resource_uri -> List[client_id]
        self._resource_routes: Dict[str, List[str]] = defaultdict(list)

        # client_id -> Set[str] (resource URIs provided by this client)
        self._client_resources: Dict[str, Set[str]] = defaultdict(set)

        # Server-specific mappings (kept for now, might be useful)
        self._server_capabilities: Dict[str, Set[str]] = {}  # server_id -> capabilities
        self._server_weights: Dict[str, float] = {}  # server_id -> routing weight

    async def initialize(self):
        """Initialize the message router"""
        logger.debug("Initializing message router")  # INFO -> DEBUG

    async def register_tool(self, tool_name: str, client_id: str):
        """
        Register that a specific client provides a given tool.
        """
        # Append client_id to the list for this tool_name, ensuring no duplicates per tool
        if client_id not in self._tool_routes[tool_name]:
            self._tool_routes[tool_name].append(client_id)

        # Add tool_name to the set for this client_id
        self._client_tools[client_id].add(tool_name)

        logger.debug(f"Registered tool '{tool_name}' for client '{client_id}'")

    async def register_prompt(self, prompt_name: str, client_id: str):
        """Register that a specific client provides a given prompt."""
        # Append client_id to the list for this prompt_name, ensuring no duplicates per prompt
        if client_id not in self._prompt_routes[prompt_name]:
            self._prompt_routes[prompt_name].append(client_id)

        # Add prompt_name to the set for this client_id
        self._client_prompts[client_id].add(prompt_name)

        logger.debug(f"Registered prompt '{prompt_name}' for client '{client_id}'")

    async def register_resource(self, resource_uri: str, client_id: str):
        """Register that a specific client provides a given resource."""
        # Append client_id to the list for this resource_uri, ensuring no duplicates
        if client_id not in self._resource_routes[resource_uri]:
            self._resource_routes[resource_uri].append(client_id)

        # Add resource_uri to the set for this client_id
        self._client_resources[client_id].add(resource_uri)

        logger.debug(f"Registered resource '{resource_uri}' for client '{client_id}'")

    async def get_clients_for_tool(self, tool_name: str) -> List[str]:
        """Get the list of client IDs that provide a specific tool."""
        # Return a copy to prevent modification of the internal list
        return list(self._tool_routes.get(tool_name, []))

    async def get_clients_for_prompt(self, prompt_name: str) -> List[str]:
        """Get the list of client IDs that provide a specific prompt."""
        # Return a copy
        return list(self._prompt_routes.get(prompt_name, []))

    async def get_clients_for_resource(self, resource_uri: str) -> List[str]:
        """Get the list of client IDs that provide a specific resource."""
        # Return a copy
        return list(self._resource_routes.get(resource_uri, []))

    async def get_tools_for_client(self, client_id: str) -> Set[str]:
        """Get the set of tool names provided by a specific client."""
        # Return a copy
        return set(self._client_tools.get(client_id, set()))

    async def get_prompts_for_client(self, client_id: str) -> Set[str]:
        """Get the set of prompt names provided by a specific client."""
        # Return a copy
        return set(self._client_prompts.get(client_id, set()))

    async def get_resources_for_client(self, client_id: str) -> Set[str]:
        """Get the set of resource URIs provided by a specific client."""
        # Return a copy
        return set(self._client_resources.get(client_id, set()))

    # Removed get_tool_capabilities
    # Removed find_tool_by_capability

    async def register_server(
        self, server_id: str, capabilities: Set[str], weight: float = 1.0
    ):
        """Register an MCP server (client) with its capabilities and routing weight."""
        self._server_capabilities[server_id] = capabilities
        self._server_weights[server_id] = weight
        logger.debug(  # Changed to DEBUG
            f"Registered server '{server_id}' with weight {weight} and capabilities: {capabilities}"
        )

    # Removed select_server_for_tool method

    async def shutdown(self):
        """Shutdown the message router and clear registry data."""
        logger.debug("Shutting down message router")  # Changed to DEBUG

        # Clear registry data
        self._tool_routes.clear()
        self._client_tools.clear()
        self._prompt_routes.clear()
        self._client_prompts.clear()
        self._resource_routes.clear()  # Clear resource routes
        self._client_resources.clear()  # Clear client resources
        self._server_capabilities.clear()
        self._server_weights.clear()

    async def get_server_capabilities(self, server_id: str) -> Set[str]:
        """Get the capabilities registered for a specific server (client)."""
        # Return a copy
        return set(self._server_capabilities.get(server_id, set()))

    async def update_server_weight(self, server_id: str, weight: float):
        """Update the routing weight for a server (client)."""
        if server_id not in self._server_capabilities:
            # Check against server_capabilities as the primary indicator of registration
            raise ValueError(f"Server not registered: {server_id}")
        self._server_weights[server_id] = weight
        logger.debug(
            f"Updated weight for server '{server_id}' to: {weight}"
        )  # Changed to DEBUG

    async def unregister_server(self, server_id: str):
        """Unregister a server (client) and remove all its associated registrations."""
        if server_id not in self._server_capabilities:
            logger.debug(f"Attempted to unregister non-existent server: {server_id}")
            return  # Nothing to remove

        self._server_capabilities.pop(server_id, None)
        self._server_weights.pop(server_id, None)

        # Remove the client from tool routes
        tools_to_update = list(self._tool_routes.keys())  # Iterate over keys copy
        for tool_name in tools_to_update:
            if server_id in self._tool_routes[tool_name]:
                self._tool_routes[tool_name].remove(server_id)
                # If the list becomes empty, remove the tool entry itself
                if not self._tool_routes[tool_name]:
                    del self._tool_routes[tool_name]

        # Remove the client from prompt routes
        prompts_to_update = list(self._prompt_routes.keys())  # Iterate over keys copy
        for prompt_name in prompts_to_update:
            if server_id in self._prompt_routes[prompt_name]:
                self._prompt_routes[prompt_name].remove(server_id)
                # If the list becomes empty, remove the prompt entry itself
                if not self._prompt_routes[prompt_name]:
                    del self._prompt_routes[prompt_name]

        # Remove the client from resource routes
        resources_to_update = list(
            self._resource_routes.keys()
        )  # Iterate over keys copy
        for resource_uri in resources_to_update:
            if server_id in self._resource_routes[resource_uri]:
                self._resource_routes[resource_uri].remove(server_id)
                # If the list becomes empty, remove the resource entry itself
                if not self._resource_routes[resource_uri]:
                    del self._resource_routes[resource_uri]

        # Remove the client's tool, prompt, and resource sets
        self._client_tools.pop(server_id, None)
        self._client_prompts.pop(server_id, None)
        self._client_resources.pop(server_id, None)  # Remove client resources

        logger.debug(
            f"Removed server '{server_id}' and its registrations."
        )  # Changed to DEBUG
