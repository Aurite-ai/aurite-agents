"""
Prompt management for MCP host.
"""

from typing import Dict, List, Optional, Any  # Removed Union
import logging
import mcp.types as types

# Import necessary types and models for filtering
from ..filtering import FilteringManager
from aurite.config.config_models import ClientConfig
from ..foundation import MessageRouter  # Import MessageRouter

logger = logging.getLogger(__name__)


# Removed internal PromptConfig dataclass as it was unused


class PromptManager:
    """
    Manages prompt definitions across MCP clients.
    Handles prompt registration and retrieval.
    """

    def __init__(self, message_router: MessageRouter):  # Inject MessageRouter
        # client_id -> {prompt_name -> Prompt}
        self._prompts: Dict[str, Dict[str, types.Prompt]] = {}
        self._message_router = message_router  # Store router instance

        # _subscriptions removed as unused

    async def initialize(self):
        """Initialize the prompt manager"""
        logger.debug("Initializing prompt manager")  # INFO -> DEBUG

    def _convert_to_prompt(self, prompt_data: Any) -> types.Prompt:
        """Convert various prompt formats to MCP Prompt type"""
        if isinstance(prompt_data, types.Prompt):
            return prompt_data

        # Handle dict format
        if isinstance(prompt_data, dict):
            return types.Prompt(
                name=prompt_data.get("name", "unnamed"),
                description=prompt_data.get("description"),
                arguments=[
                    types.PromptArgument(**arg) if isinstance(arg, dict) else arg
                    for arg in prompt_data.get("arguments", [])
                ],
            )

        # Handle simple string format (treat as name)
        if isinstance(prompt_data, str):
            return types.Prompt(name=prompt_data)

        raise ValueError(f"Cannot convert {type(prompt_data)} to Prompt")

    # _convert_to_prompt_result method removed.

    async def register_client_prompts(
        self,
        client_id: str,
        prompts: List[Any],
        client_config: ClientConfig,  # Added client_config
        filtering_manager: FilteringManager,  # Added filtering_manager
    ) -> List[types.Prompt]:  # Return list of registered prompts
        """Register prompts available from a client, applying client-level exclusions."""
        logger.debug(f"Registering prompts for client {client_id}")  # INFO -> DEBUG
        registered_prompts = []

        if client_id not in self._prompts:
            self._prompts[client_id] = {}

        for prompt_data in prompts:
            try:
                prompt = self._convert_to_prompt(prompt_data)
                # Check registration allowance using FilteringManager
                if not filtering_manager.is_registration_allowed(
                    prompt.name, client_config
                ):
                    # Logging is handled within is_registration_allowed
                    continue
                self._prompts[client_id][prompt.name] = prompt
                # Register with the message router
                await self._message_router.register_prompt(
                    prompt_name=prompt.name,
                    client_id=client_id,  # Corrected keyword argument
                )
                logger.debug(
                    f"Registered prompt '{prompt.name}' for client '{client_id}' with router."
                )
                registered_prompts.append(
                    prompt
                )  # Add to list of successfully registered
            except Exception as e:
                logger.warning(f"Failed to register prompt {prompt_data}: {e}")
        return registered_prompts  # Return the list

    async def get_prompt(self, name: str, client_id: str) -> Optional[types.Prompt]:
        """
        Get a specific prompt template definition.

        Args:
            name: Name of the prompt.
            client_id: ID of the client providing the prompt.

        Returns:
            The Prompt definition object, or None if not found.
        """
        # Removed response_data handling logic
        if client_id not in self._prompts or name not in self._prompts[client_id]:
            logger.debug(f"Prompt '{name}' not found for client '{client_id}'.")
            return None

        return self._prompts[client_id][name]

    async def list_prompts(self, client_id: Optional[str] = None) -> List[types.Prompt]:
        """List all available prompts, optionally filtered by client"""
        if client_id:
            return list(self._prompts.get(client_id, {}).values())

        all_prompts: List[types.Prompt] = []
        for client_prompts in self._prompts.values():
            all_prompts.extend(client_prompts.values())
        # Ensure unique prompts if the same one is registered by multiple clients?
        # For now, just return the list as registered.
        return all_prompts

    def get_clients_for_prompt(self, prompt_name: str) -> List[str]:
        """Find all client IDs that provide a prompt with the given name."""
        client_ids = []
        # Use items() for potentially better performance if dicts grow large
        for client_id, prompts in self._prompts.items():
            if prompt_name in prompts:
                client_ids.append(client_id)
        return client_ids

    # validate_prompt_arguments method removed.

    async def unregister_client_prompts(self, client_id: str):
        """
        Removes all prompt registrations associated with a specific client ID.

        Args:
            client_id: The ID of the client whose prompts should be unregistered.
        """
        if client_id in self._prompts:
            removed_prompts = list(self._prompts[client_id].keys())
            del self._prompts[client_id]
            logger.debug(
                f"Unregistered {len(removed_prompts)} prompts for client '{client_id}': {removed_prompts}"
            )
        else:
            logger.debug(f"No prompts found to unregister for client '{client_id}'.")

    async def shutdown(self):
        """Shutdown the prompt manager"""
        logger.debug("Shutting down prompt manager")  # Changed to DEBUG
        self._prompts.clear()
        # _subscriptions removed
