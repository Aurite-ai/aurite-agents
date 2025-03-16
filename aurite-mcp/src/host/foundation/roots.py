"""
Root management for MCP host.
"""

from dataclasses import dataclass
from typing import Dict, List, Set
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class RootConfig:
    """Configuration for a root URI"""

    uri: str
    name: str
    capabilities: List[str]


class RootManager:
    """
    Manages root URIs and their capabilities.
    Handles access control and resource boundaries.
    """

    def __init__(self):
        # client_id -> List[RootConfig]
        self._client_roots: Dict[str, List[RootConfig]] = {}

        # client_id -> Set[str] (normalized URIs)
        self._client_uris: Dict[str, Set[str]] = {}

        # tool_name -> Set[str] (required root URIs)
        self._tool_requirements: Dict[str, Set[str]] = {}

    async def initialize(self):
        """Initialize the root manager"""
        logger.info("Initializing root manager")

    async def register_roots(self, client_id: str, roots: List[RootConfig]):
        """
        Register roots for a client.
        This defines the operational boundaries for the client.
        """
        if client_id in self._client_roots:
            logger.warning(f"Overwriting existing roots for client: {client_id}")

        # Validate and normalize roots
        normalized_roots = []
        normalized_uris = set()

        for root in roots:
            # Validate URI format
            try:
                parsed = urlparse(root.uri)
                if not parsed.scheme:
                    raise ValueError("URI must have a scheme")
            except Exception as e:
                raise ValueError(f"Invalid root URI {root.uri}: {e}")

            normalized_roots.append(root)
            normalized_uris.add(root.uri)

        # Store the roots
        self._client_roots[client_id] = normalized_roots
        self._client_uris[client_id] = normalized_uris

        logger.info(f"Registered roots for client {client_id}: {normalized_uris}")

    async def register_tool_requirements(
        self, tool_name: str, required_roots: Set[str]
    ):
        """Register the root URIs required by a tool"""
        self._tool_requirements[tool_name] = required_roots

    async def validate_access(self, client_id: str, tool_name: str) -> bool:
        """
        Validate that a client has access to all roots required by a tool.
        Raises ValueError if access is not allowed.
        """
        if client_id not in self._client_roots:
            raise ValueError(f"No roots registered for client: {client_id}")

        if tool_name in self._tool_requirements:
            required_roots = self._tool_requirements[tool_name]
            client_roots = self._client_uris[client_id]

            missing_roots = required_roots - client_roots
            if missing_roots:
                raise ValueError(
                    f"Client {client_id} missing required roots for {tool_name}: {missing_roots}"
                )

        return True

    async def get_client_roots(self, client_id: str) -> List[RootConfig]:
        """Get all roots registered for a client"""
        return self._client_roots.get(client_id, [])

    async def get_tool_requirements(self, tool_name: str) -> Set[str]:
        """Get all root URIs required by a tool"""
        return self._tool_requirements.get(tool_name, set())

    async def shutdown(self):
        """Shutdown the root manager"""
        logger.info("Shutting down root manager")

        # Clear all stored data
        self._client_roots.clear()
        self._client_uris.clear()
        self._tool_requirements.clear()
