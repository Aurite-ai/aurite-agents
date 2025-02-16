"""
Resource management for MCP host.
"""

from typing import Dict, List, Set, Optional, Any
import logging
from dataclasses import dataclass
from urllib.parse import urlparse

import mcp.types as types

logger = logging.getLogger(__name__)


@dataclass
class ResourceConfig:
    """Configuration for a resource"""

    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None


class ResourceManager:
    """
    Manages resources across MCP clients.
    Handles resource discovery, access, and updates.
    """

    def __init__(self):
        # client_id -> {resource_uri -> Resource}
        self._resources: Dict[str, Dict[str, types.Resource]] = {}

        # resource_uri -> set(client_ids)
        self._subscriptions: Dict[str, Set[str]] = {}

    async def initialize(self):
        """Initialize the resource manager"""
        logger.info("Initializing resource manager")

    async def register_client_resources(
        self, client_id: str, resources: List[types.Resource]
    ):
        """Register resources available from a client"""
        logger.info(
            f"Registering resources for client {client_id}: {[r.uri for r in resources]}"
        )

        if client_id not in self._resources:
            self._resources[client_id] = {}

        for resource in resources:
            self._resources[client_id][resource.uri] = resource

    async def get_resource(self, uri: str, client_id: str) -> Optional[types.Resource]:
        """Get a specific resource"""
        if client_id not in self._resources or uri not in self._resources[client_id]:
            return None
        return self._resources[client_id][uri]

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

    async def subscribe(self, uri: str, client_id: str):
        """Subscribe a client to resource updates"""
        if uri not in self._subscriptions:
            self._subscriptions[uri] = set()
        self._subscriptions[uri].add(client_id)
        logger.info(f"Client {client_id} subscribed to resource {uri}")

    async def unsubscribe(self, uri: str, client_id: str):
        """Unsubscribe a client from resource updates"""
        if uri in self._subscriptions:
            self._subscriptions[uri].discard(client_id)
            if not self._subscriptions[uri]:
                del self._subscriptions[uri]
        logger.info(f"Client {client_id} unsubscribed from resource {uri}")

    async def get_subscribers(self, uri: str) -> Set[str]:
        """Get all clients subscribed to a resource"""
        return self._subscriptions.get(uri, set())

    async def validate_resource_access(
        self, uri: str, client_id: str, root_manager: Any
    ) -> bool:
        """Validate resource access against client's root boundaries"""
        # Parse the resource URI
        parsed = urlparse(uri)

        # Get client's root URIs
        roots = await root_manager.get_client_roots(client_id)

        # Check if resource URI is within any of the client's roots
        for root in roots:
            root_parsed = urlparse(root.uri)
            if (
                parsed.scheme == root_parsed.scheme
                and parsed.netloc == root_parsed.netloc
                and parsed.path.startswith(root_parsed.path)
            ):
                return True

        raise ValueError(
            f"Resource {uri} is not accessible within client {client_id}'s roots"
        )

    async def shutdown(self):
        """Shutdown the resource manager"""
        logger.info("Shutting down resource manager")
        self._resources.clear()
        self._subscriptions.clear()
