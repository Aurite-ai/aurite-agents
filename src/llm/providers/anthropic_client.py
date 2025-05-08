"""
LLM Client Abstraction for interacting with different LLM providers.
"""

import os
import logging
from typing import List, Optional, Dict, Any

# Import Pydantic validation error
from pydantic import ValidationError
from typing import cast  # Added cast

# Import our standardized output models from the agents module
from ...agents.agent_models import (
    AgentOutputMessage,
    AgentOutputContentBlock,
)  # Corrected path

# Import Anthropic specific types and client
from anthropic import AsyncAnthropic, APIConnectionError, RateLimitError
from anthropic._types import NOT_GIVEN  # Import NotGiven
from anthropic.types import (
    Message as AnthropicMessage,
    TextBlock as AnthropicTextBlock,
    ToolUseBlock as AnthropicToolUseBlock,
    MessageParam,  # Added
    ToolParam,  # Added
)
from typing import Iterable  # Added

# Import the base LLM class
from ..base_client import (
    BaseLLM,
    DEFAULT_MAX_TOKENS as BASE_DEFAULT_MAX_TOKENS,
)  # Import default for fallback
from ...config.config_models import LLMConfig  # Corrected relative import

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
        llm_config_override: Optional[LLMConfig] = None,  # New parameter
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
            llm_config_override: Optional LLMConfig to override client defaults for this call.

        Returns:
            An AgentOutputMessage instance.

        Raises:
            APIConnectionError: If connection to Anthropic fails.
            RateLimitError: If Anthropic rate limits are exceeded.
            Exception: For other API call errors.
        """
        # --- Parameter Resolution ---
        # Model
        model_to_use = self.model_name
        if llm_config_override and llm_config_override.model_name:
            model_to_use = llm_config_override.model_name
            logger.debug(
                f"Overriding model to '{model_to_use}' from LLMConfig override."
            )

        # Temperature
        temperature_to_use = self.temperature  # Instance default
        if llm_config_override and llm_config_override.temperature is not None:
            temperature_to_use = llm_config_override.temperature
            logger.debug(
                f"Overriding temperature to '{temperature_to_use}' from LLMConfig override."
            )

        # Max Tokens
        max_tokens_to_use = self.max_tokens  # Instance default
        if llm_config_override and llm_config_override.max_tokens is not None:
            max_tokens_to_use = llm_config_override.max_tokens
            logger.debug(
                f"Overriding max_tokens to '{max_tokens_to_use}' from LLMConfig override."
            )
        # Ensure max_tokens has a value for the API call, falling back to a base default if needed
        if max_tokens_to_use is None:
            max_tokens_to_use = (
                BASE_DEFAULT_MAX_TOKENS  # Use imported default from base_client
            )
            logger.debug(f"Max tokens resolved to base default: {max_tokens_to_use}")

        # System Prompt Resolution
        # 1. system_prompt_override (method argument)
        # 2. llm_config_override.default_system_prompt
        # 3. self.system_prompt (instance default)
        resolved_system_prompt = self.system_prompt  # Start with instance default
        if llm_config_override and llm_config_override.default_system_prompt:
            resolved_system_prompt = llm_config_override.default_system_prompt
            logger.debug("Using system prompt from LLMConfig override.")
        if system_prompt_override is not None:  # Highest precedence
            resolved_system_prompt = system_prompt_override
            logger.debug("Using system prompt from method argument override.")

        # Inject schema if provided, into the resolved system prompt
        if schema:
            import json

            try:
                schema_str = json.dumps(schema, indent=2)
                schema_injection = f"""
Your response must be valid JSON matching this schema:
{schema_str}

Remember to format your response as a valid JSON object."""
                if resolved_system_prompt:  # Append if there's an existing prompt
                    resolved_system_prompt = (
                        f"{resolved_system_prompt}\n{schema_injection}"
                    )
                else:  # Otherwise, schema injection becomes the prompt
                    resolved_system_prompt = schema_injection
            except Exception as json_err:
                logger.error(f"Failed to serialize schema for injection: {json_err}")
                # Proceed without schema injection on error

        # Ensure tools is None if not provided or empty for the API call
        tools_for_api = tools if tools else None
        if tools_for_api:
            logger.debug(f"Including {len(tools_for_api)} tools in Anthropic API call.")
        else:
            logger.debug("No tools included in Anthropic API call.")

        logger.debug(f"Making Anthropic API call to model '{model_to_use}'")
        try:
            # Cast messages and tools to expected Iterable types
            typed_messages = cast(Iterable[MessageParam], messages)
            typed_tools = cast(Optional[Iterable[ToolParam]], tools_for_api)

            anthropic_response: AnthropicMessage = (
                await self.anthropic_sdk_client.messages.create(
                    model=model_to_use,
                    max_tokens=max_tokens_to_use,  # Already ensured to be non-None
                    messages=typed_messages,
                    system=resolved_system_prompt
                    if resolved_system_prompt
                    else NOT_GIVEN,
                    tools=typed_tools if typed_tools is not None else NOT_GIVEN,
                    temperature=temperature_to_use
                    if temperature_to_use is not None
                    else NOT_GIVEN,
                )
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
