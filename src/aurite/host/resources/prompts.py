"""
Prompt management for MCP host.
"""

from typing import List, Optional  # Removed Union
import logging
import mcp.types as types

# Import necessary types and models for filtering
from ..foundation import MessageRouter  # Import MessageRouter

from mcp.client.session_group import ClientSessionGroup

logger = logging.getLogger(__name__)


# Removed internal PromptConfig dataclass as it was unused


class PromptManager:
    """
    Manages prompt definitions across MCP clients.
    Handles prompt registration and retrieval.
    """

    def __init__(
        self, message_router: MessageRouter, session_group: ClientSessionGroup
    ):  # Inject MessageRouter
        self._message_router = message_router  # Store router instance
        self._session_group = session_group

    async def initialize(self):
        """Initialize the prompt manager"""
        logger.debug("Initializing prompt manager")
        for prompt in self._session_group.prompts.values():
            # This assumes that the session_group provides a way to identify the client per component.
            # If not, we may need to adjust this logic.
            # For now, we'll assume a single "owner" or that the router can handle duplicates.
            client_id = getattr(prompt, "client_id", "unknown")
            await self._message_router.register_prompt(
                prompt_name=prompt.name, client_id=client_id
            )

    async def get_prompt(self, name: str) -> Optional[types.Prompt]:
        """
        Get a specific prompt template definition.
        """
        return self._session_group.prompts.get(name)

    async def list_prompts(self) -> List[types.Prompt]:
        """List all available prompts."""
        return list(self._session_group.prompts.values())

    async def shutdown(self):
        """Shutdown the prompt manager"""
        logger.debug("Shutting down prompt manager")
