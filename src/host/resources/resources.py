"""
Resource management for MCP host.
"""

from typing import Dict, List, Optional
import logging
from urllib.parse import urlparse

import mcp.types as types

# Import RootManager for type hinting
from ..foundation.roots import RootManager


logger = logging.getLogger(__name__)


# Removed internal ResourceConfig dataclass as it was unused


class ResourceManager:
    """
    Manages resource definitions across MCP clients.
    Handles resource registration, retrieval, and access validation based on roots.
    """

    def __init__(self):
        # client_id -> {resource_uri_string -> Resource}
        self._resources: Dict[str, Dict[str, types.Resource]] = {}

        # _subscriptions removed as unused

    async def initialize(self):
        """Initialize the resource manager"""
        logger.info("Initializing resource manager")

    async def register_client_resources(
        self,
        client_id: str,
        resources: List[types.Resource],
        exclude_list: Optional[List[str]] = None,
    ) -> List[types.Resource]:  # Return list of registered resources
        """Register resources available from a client, excluding specified ones."""
        logger.info(
            f"Registering resources for client {client_id}: {[str(r.uri) for r in resources]}"
        )
        registered_resources = []

        if client_id not in self._resources:
            self._resources[client_id] = {}

        for resource in resources:
            # Check against exclude list using resource.name
            # Note: Resources might not always have a name, rely on URI primarily.
            # Exclude list should ideally support URIs too, but currently based on name.
            if exclude_list and resource.name and resource.name in exclude_list:
                logger.debug(
                    f"Excluding resource '{resource.name}' (URI: {resource.uri}) for client {client_id} as per config."
                )
                continue
            uri_str = str(resource.uri)
            self._resources[client_id][uri_str] = resource
            registered_resources.append(resource)
        return registered_resources

    async def get_resource(self, uri: str, client_id: str) -> Optional[types.Resource]:
        """Get a specific resource"""
        uri_str = str(uri)
        if (
            client_id not in self._resources
            or uri_str not in self._resources[client_id]
        ):
            return None
        return self._resources[client_id][uri_str]

    async def list_resources(
        self, client_id: Optional[str] = None
    ) -> List[types.Resource]:
        """List all available resources, optionally filtered by client"""
        if client_id:
            return list(self._resources.get(client_id, {}).values())

        all_resources = []
        for client_resources in self._resources.values():
            all_resources.extend(client_resources.values())
        return all_resources

    def get_clients_for_resource(self, uri: str) -> List[str]:
        """Find all client IDs that provide a resource with the given URI."""
        uri_str = str(uri)  # Ensure URI is string for dict key lookup
        client_ids = []
        for client_id, resources in self._resources.items():
            if uri_str in resources:
                client_ids.append(client_id)
        return client_ids

    # subscribe method removed.
    # unsubscribe method removed.
    # get_subscribers method removed.

    async def validate_resource_access(
        self,
        uri: str,
        client_id: str,
        root_manager: RootManager,  # Updated type hint
    ) -> bool:
        """Validate resource access against client's root boundaries"""
        # Convert URI to string
        uri_str = str(uri)
        parsed = urlparse(uri_str)

        # Get client's root URIs
        roots = await root_manager.get_client_roots(client_id)

        # Check if resource URI is within any of the client's roots
        for root in roots:
            root_str = str(root.uri)  # Convert root URI to string
            root_parsed = urlparse(root_str)

            # For custom schemes like weather://, just check if the URI starts with the root URI
            if parsed.scheme == root_parsed.scheme:
                resource_path = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                root_path = (
                    f"{root_parsed.scheme}://{root_parsed.netloc}{root_parsed.path}"
                )

                if resource_path.startswith(root_path):
                    logger.info(f"Resource {uri_str} validated against root {root_str}")
                    return True

        raise ValueError(
            f"Resource {uri_str} is not accessible within client {client_id}'s roots"
        )

    async def shutdown(self):
        """Shutdown the resource manager"""
        logger.info("Shutting down resource manager")
        self._resources.clear()
        # _subscriptions removed
