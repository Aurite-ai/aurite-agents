"""
Resource management for MCP host.
"""

import logging
from typing import List, Optional
from urllib.parse import urlparse

import mcp.types as types
from mcp.client.session_group import ClientSessionGroup

# Import necessary types and models for filtering
from ..foundation import MessageRouter  # Import MessageRouter

# Import RootManager for type hinting
from ..foundation.roots import RootManager

logger = logging.getLogger(__name__)


class ResourceManager:
    """
    Manages resource definitions across MCP clients.
    Handles resource registration, retrieval, and access validation based on roots.
    """

    def __init__(self, message_router: MessageRouter, session_group: ClientSessionGroup):  # Inject MessageRouter
        self._message_router = message_router
        self._session_group = session_group

    async def initialize(self):
        """Initialize the resource manager"""
        logger.debug("Initializing resource manager")
        for resource in self._session_group.resources.values():
            client_id = getattr(resource, "client_id", "unknown")
            await self._message_router.register_resource(resource_uri=str(resource.uri), client_id=client_id)

    async def get_resource(self, uri: str) -> Optional[types.Resource]:
        """Get a specific resource"""
        return self._session_group.resources.get(uri)

    async def list_resources(self) -> List[types.Resource]:
        """List all available resources"""
        return list(self._session_group.resources.values())

    async def validate_resource_access(
        self,
        uri: str,
        client_id: str,
        root_manager: RootManager,
    ) -> bool:
        """Validate resource access against client's root boundaries"""
        uri_str = str(uri)
        parsed = urlparse(uri_str)

        roots = await root_manager.get_client_roots(client_id)

        for root in roots:
            root_str = str(root.uri)
            root_parsed = urlparse(root_str)

            if parsed.scheme == root_parsed.scheme:
                resource_path = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                root_path = f"{root_parsed.scheme}://{root_parsed.netloc}{root_parsed.path}"

                if resource_path.startswith(root_path):
                    logger.info(f"Resource {uri_str} validated against root {root_str}")
                    return True

        raise ValueError(f"Resource {uri_str} is not accessible within client {client_id}'s roots")

    async def shutdown(self):
        """Shutdown the resource manager"""
        logger.debug("Shutting down resource manager")
