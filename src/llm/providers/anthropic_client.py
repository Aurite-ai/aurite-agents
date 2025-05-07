"""
LLM Client Abstraction for interacting with different LLM providers.
"""

import os
import logging
from typing import List, Optional, Dict, Any

# Import Pydantic validation error
from pydantic import ValidationError

# Import our standardized output models from the agents module
from ..agents.agent_models import AgentOutputMessage, AgentOutputContentBlock

# Import Anthropic specific types and client
from anthropic import AsyncAnthropic, APIConnectionError, RateLimitError
from anthropic.types import (
    Message as AnthropicMessage,
    TextBlock as AnthropicTextBlock,
    ToolUseBlock as AnthropicToolUseBlock,
)
# Import the base LLM class
from ..base_client import BaseLLM

logger = logging.getLogger(__name__)

# Default values (consider making these configurable at a higher level later)
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."


class AnthropicLLM(BaseLLM):
    """LLM Client implementation for Anthropic models."""

    def __init__(
        self,
        model_name: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        api_key: Optional[str] = None,  # Allow explicit key pass-through if needed
    ):
        """
        Initializes the Anthropic LLM client.

        Args:
            model_name: The specific Anthropic model name (e.g., "claude-3-opus-20240229").
            temperature: The sampling temperature.
            max_tokens: The maximum number of tokens to generate.
            system_prompt: The default system prompt.
            api_key: Optional Anthropic API key. If None, uses ANTHROPIC_API_KEY env var.
        """
        super().__init__(model_name, temperature, max_tokens, system_prompt)

        resolved_api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_api_key:
            logger.error(
                "Anthropic API key not provided or found in ANTHROPIC_API_KEY environment variable."
            )
            raise ValueError("Anthropic API key is required.")

        try:
            self.anthropic_sdk_client = AsyncAnthropic(api_key=resolved_api_key)
            logger.info(
                f"AnthropicLLM client initialized successfully for model {self.model_name}."
            )
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic SDK client: {e}")
            raise ValueError(f"Failed to initialize Anthropic SDK client: {e}") from e

    async def create_message(
        self,
        messages: List[Dict[str, Any]],  # Expects standardized message format
        tools: Optional[List[Dict[str, Any]]],  # Expects Anthropic tool format for now
        system_prompt_override: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
    ) -> AgentOutputMessage:
        """
        Sends messages to the Anthropic API and returns a standardized response.

        Args:
            messages: List of message dicts [{'role': ..., 'content': ...}]
                      Content should align with Anthropic's MessageParam structure
                      (e.g., list of dicts like {'type': 'text', 'text': ...} or tool results).
            tools: List of tool definitions in Anthropic format.
            system_prompt_override: Optional override for the system prompt.
            schema: Optional JSON schema for response formatting.

        Returns:
            An AgentOutputMessage instance.

        Raises:
            APIConnectionError: If connection to Anthropic fails.
            RateLimitError: If Anthropic rate limits are exceeded.
            Exception: For other API call errors.
        """
        effective_system_prompt = (
            system_prompt_override
            if system_prompt_override is not None
            else self.system_prompt
        )

        # Inject schema if provided
        if schema:
            import json

            try:
                schema_str = json.dumps(schema, indent=2)
                schema_injection = f"""
Your response must be valid JSON matching this schema:
{schema_str}

Remember to format your response as a valid JSON object."""
                effective_system_prompt = (
                    f"{effective_system_prompt}\n{schema_injection}"
                )
            except Exception as json_err:
                logger.error(f"Failed to serialize schema for injection: {json_err}")
                # Decide whether to proceed without schema or raise error
                # For now, proceed without schema injection on error

        # Prepare API arguments
        api_args = {
            "model": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": messages,  # Assume input 'messages' are already in Anthropic format
        }
        if effective_system_prompt:
            api_args["system"] = effective_system_prompt
        if tools:
            api_args["tools"] = tools
            logger.debug(f"Including {len(tools)} tools in Anthropic API call.")
        else:
            logger.debug("No tools included in Anthropic API call.")

        logger.debug(f"Making Anthropic API call to model '{self.model_name}'")
        try:
            # Make the actual API call
            anthropic_response: AnthropicMessage = (
                await self.anthropic_sdk_client.messages.create(**api_args)
            )
            logger.debug(
                f"Anthropic API response received (stop_reason: {anthropic_response.stop_reason}, role: {anthropic_response.role})"
            )

            # Convert Anthropic response to our standardized AgentOutputMessage
            output_content_blocks: List[AgentOutputContentBlock] = []
            for block in anthropic_response.content:
                if isinstance(block, AnthropicTextBlock):
                    output_content_blocks.append(
                        AgentOutputContentBlock(type="text", text=block.text)
                    )
                elif isinstance(block, AnthropicToolUseBlock):
                    output_content_blocks.append(
                        AgentOutputContentBlock(
                            type="tool_use",
                            id=block.id,
                            name=block.name,
                            input=block.input,
                        )
                    )
                # Add handling for other block types if they become relevant

            # Ensure role is correctly passed. Anthropic's Message role is 'assistant'.
            # Our AgentOutputMessage.role can be 'user' or 'assistant'.
            # The LLM client should always produce 'assistant' role messages.
            role = anthropic_response.role

            # Map usage if present
            usage_dict = None
            if anthropic_response.usage:
                usage_dict = {
                    "input_tokens": anthropic_response.usage.input_tokens,
                    "output_tokens": anthropic_response.usage.output_tokens,
                }

            # Stop reason can be an Enum, convert to string
            stop_reason_str = None
            if anthropic_response.stop_reason:
                stop_reason_str = str(anthropic_response.stop_reason)

            try:
                validated_output_message = AgentOutputMessage(
                    id=anthropic_response.id,
                    model=anthropic_response.model,
                    role=role,  # Directly use the role from Anthropic response
                    content=output_content_blocks,
                    stop_reason=stop_reason_str,
                    stop_sequence=anthropic_response.stop_sequence,
                    usage=usage_dict,
                )
                return validated_output_message
            except ValidationError as e:
                error_msg = f"Failed to validate constructed AgentOutputMessage: {e}"
                logger.error(error_msg, exc_info=True)
                raise Exception(error_msg) from e

        except (APIConnectionError, RateLimitError) as e:
            logger.error(f"Anthropic API call failed: {type(e).__name__}: {e}")
            # Re-raise specific, potentially recoverable errors
            raise
        except ValidationError as e:
            # This means the serialized Anthropic response didn't match our AgentOutputMessage model
            error_msg = (
                f"Failed to validate Anthropic response against internal model: {e}"
            )
            logger.error(error_msg, exc_info=True)
            # What should we return here? Raise a custom exception? Return a special error message?
            # For now, re-raise as a generic Exception. Consider a custom exception type later.
            raise Exception(error_msg) from e
        except Exception as e:
            logger.error(
                f"Unexpected error during Anthropic API call or response processing: {e}",
                exc_info=True,
            )
            # Re-raise other unexpected errors
            raise
