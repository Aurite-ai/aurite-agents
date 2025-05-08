"""
Root management for MCP host.
"""

from typing import Dict, List, Set
import logging
from urllib.parse import urlparse

# Import the Pydantic model
from src.config.config_models import RootConfig  # Renamed config.py to models.py

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

        # Tool-specific requirements removed for simplification

    async def initialize(self):
        """Initialize the root manager"""
        logger.debug("Initializing root manager")  # INFO -> DEBUG

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

    # register_tool_requirements method removed.

    async def validate_access(self, client_id: str) -> bool:
        """
        Placeholder validation method. Currently always returns True.
        Original logic checked tool-specific root requirements, which have been removed.
        This method is kept for potential future use or more basic checks if needed.
        """
        # Original logic checked tool-specific requirements here.
        # Since that's removed, and the check for client registration happens
        # before this would be called, we just return True.
        # We could add a basic check like `return client_id in self._client_roots`
        # if we wanted to ensure the client is known, but ToolManager likely handles that.
        if client_id not in self._client_roots:
            # This case might indicate an issue elsewhere if ToolManager calls this
            # for an unknown client, but we'll log a warning just in case.
            logger.warning(
                f"validate_access called for unknown or rootless client: {client_id}"
            )
            # Still return True based on original logic's fallback for rootless clients.
            return True

        return True

    async def get_client_roots(
        self, client_id: str
    ) -> List[RootConfig]:  # Type hint uses imported RootConfig
        """Get all roots registered for a client"""
        # Return a copy to prevent external modification
        return list(self._client_roots.get(client_id, []))

    # get_tool_requirements method removed.

    async def shutdown(self):
        """Shutdown the root manager"""
        logger.info("Shutting down root manager")

        # Clear stored data
        self._client_roots.clear()
        self._client_uris.clear()
