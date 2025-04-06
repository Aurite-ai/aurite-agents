"""
Root management for MCP host.
"""

from typing import Dict, List, Set
import logging
from urllib.parse import urlparse

# Import the Pydantic model
from ..models import RootConfig  # Renamed config.py to models.py

logger = logging.getLogger(__name__)


class RootManager:
    """
    Manages root URIs and their capabilities.
    Handles access control and resource boundaries.
    """

    def __init__(self):
        # client_id -> List[RootConfig] (Using Pydantic model now)
        self._client_roots: Dict[str, List[RootConfig]] = {}

        # client_id -> Set[str] (normalized URIs)
        self._client_uris: Dict[str, Set[str]] = {}

        # tool_name -> Set[str] (required root URIs)
        self._tool_requirements: Dict[str, Set[str]] = {}

    async def initialize(self):
        """Initialize the root manager"""
        logger.info("Initializing root manager")

    async def register_roots(
        self, client_id: str, roots: List[RootConfig]
    ):  # Type hint uses imported RootConfig
        """
        Register roots for a client using Pydantic RootConfig models.
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
                # Pydantic model validation handles URI format implicitly if using AnyUrl,
                # but explicit check for scheme is still good practice.
                parsed = urlparse(str(root.uri))  # Ensure URI is string for urlparse
                if not parsed.scheme:
                    raise ValueError(f"Root URI {root.uri} must have a scheme")
            except Exception as e:
                # Catch potential validation errors or other issues
                raise ValueError(f"Invalid root URI configuration for {root.uri}: {e}")

            normalized_roots.append(root)  # Store the validated Pydantic model
            normalized_uris.add(str(root.uri))  # Store URI as string

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
        # If client has no registered roots, assume unrestricted access
        # This allows tools to work even when no roots are defined
        if client_id not in self._client_roots:
            logger.info(
                f"No roots registered for client: {client_id}, assuming unrestricted access"
            )
            return True

        if tool_name in self._tool_requirements:
            required_roots = self._tool_requirements[tool_name]
            client_roots = self._client_uris[client_id]

            missing_roots = required_roots - client_roots
            if missing_roots:
                raise ValueError(
                    f"Client {client_id} missing required roots for {tool_name}: {missing_roots}"
                )

        return True

    async def get_client_roots(
        self, client_id: str
    ) -> List[RootConfig]:  # Type hint uses imported RootConfig
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
