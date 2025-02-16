"""
Prompt management for MCP host.
"""

from typing import Dict, List, Set, Optional, Any
import logging
from dataclasses import dataclass

import mcp.types as types

logger = logging.getLogger(__name__)


@dataclass
class PromptConfig:
    """Configuration for a prompt"""

    name: str
    description: Optional[str] = None
    arguments: Optional[List[Dict[str, Any]]] = None


class PromptManager:
    """
    Manages prompts across MCP clients.
    Handles prompt registration, validation, and execution.
    """

    def __init__(self):
        # client_id -> {prompt_name -> Prompt}
        self._prompts: Dict[str, Dict[str, types.Prompt]] = {}

        # prompt_name -> set(client_ids)
        self._subscriptions: Dict[str, Set[str]] = {}

    async def initialize(self):
        """Initialize the prompt manager"""
        logger.info("Initializing prompt manager")

    async def register_client_prompts(
        self, client_id: str, prompts: List[types.Prompt]
    ):
        """Register prompts available from a client"""
        logger.info(
            f"Registering prompts for client {client_id}: {[p.name for p in prompts]}"
        )

        if client_id not in self._prompts:
            self._prompts[client_id] = {}

        for prompt in prompts:
            self._prompts[client_id][prompt.name] = prompt

    async def get_prompt(self, name: str, client_id: str) -> Optional[types.Prompt]:
        """Get a specific prompt template"""
        if client_id not in self._prompts or name not in self._prompts[client_id]:
            return None
        return self._prompts[client_id][name]

    async def list_prompts(self, client_id: Optional[str] = None) -> List[types.Prompt]:
        """List all available prompts, optionally filtered by client"""
        if client_id:
            return list(self._prompts.get(client_id, {}).values())

        all_prompts = []
        for client_prompts in self._prompts.values():
            all_prompts.extend(client_prompts.values())
        return all_prompts

    async def validate_prompt_arguments(
        self, prompt: types.Prompt, arguments: Dict[str, Any]
    ) -> bool:
        """Validate that all required arguments are provided"""
        if not prompt.arguments:
            return True

        for arg in prompt.arguments:
            if arg.required and arg.name not in arguments:
                raise ValueError(f"Missing required argument: {arg.name}")

        return True

    async def shutdown(self):
        """Shutdown the prompt manager"""
        logger.info("Shutting down prompt manager")
        self._prompts.clear()
        self._subscriptions.clear()
