"""
Prompt management for MCP host.
"""

from typing import Dict, List, Set, Optional, Any, Union
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

    def _convert_to_prompt_result(self, result_data: Any) -> types.GetPromptResult:
        """Convert various response formats to MCP GetPromptResult type"""
        # Already in correct format
        if isinstance(result_data, types.GetPromptResult):
            return result_data

        # Handle string format (most basic case)
        if isinstance(result_data, str):
            return types.GetPromptResult(
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(type="text", text=result_data),
                    )
                ]
            )

        # Handle dict format with messages
        if isinstance(result_data, dict):
            if "messages" in result_data:
                # Convert each message to proper type if needed
                messages = []
                for msg in result_data["messages"]:
                    if isinstance(msg, types.PromptMessage):
                        messages.append(msg)
                    elif isinstance(msg, dict):
                        content = msg.get("content", "")
                        if isinstance(content, str):
                            content = types.TextContent(type="text", text=content)
                        messages.append(
                            types.PromptMessage(
                                role=msg.get("role", "user"), content=content
                            )
                        )
                return types.GetPromptResult(messages=messages)

            # Handle dict with direct text content
            if "text" in result_data:
                return types.GetPromptResult(
                    messages=[
                        types.PromptMessage(
                            role="user",
                            content=types.TextContent(
                                type="text", text=result_data["text"]
                            ),
                        )
                    ]
                )

        # Handle list of messages
        if isinstance(result_data, list):
            messages = []
            for msg in result_data:
                if isinstance(msg, types.PromptMessage):
                    messages.append(msg)
                elif isinstance(msg, dict):
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        content = types.TextContent(type="text", text=content)
                    messages.append(
                        types.PromptMessage(
                            role=msg.get("role", "user"), content=content
                        )
                    )
                elif isinstance(msg, str):
                    messages.append(
                        types.PromptMessage(
                            role="user",
                            content=types.TextContent(type="text", text=msg),
                        )
                    )
            return types.GetPromptResult(messages=messages)

        raise ValueError(f"Cannot convert {type(result_data)} to GetPromptResult")

    async def register_client_prompts(
        self, client_id: str, prompts: Union[List[types.Prompt], List[Dict], List[str]]
    ):
        """Register prompts available from a client"""
        logger.info(f"Registering prompts for client {client_id}")

        if client_id not in self._prompts:
            self._prompts[client_id] = {}

        for prompt_data in prompts:
            try:
                prompt = self._convert_to_prompt(prompt_data)
                self._prompts[client_id][prompt.name] = prompt
            except Exception as e:
                logger.warning(f"Failed to register prompt {prompt_data}: {e}")

    async def get_prompt(
        self, name: str, client_id: str, response_data: Any = None
    ) -> Optional[Union[types.Prompt, types.GetPromptResult]]:
        """
        Get a specific prompt template or convert a prompt response.

        Args:
            name: Name of the prompt
            client_id: ID of the client
            response_data: Optional response data to convert to GetPromptResult

        Returns:
            - If response_data is None: Returns the Prompt template
            - If response_data is provided: Returns the converted GetPromptResult
        """
        if response_data is not None:
            try:
                return self._convert_to_prompt_result(response_data)
            except Exception as e:
                logger.error(f"Failed to convert prompt response: {e}")
                raise

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
