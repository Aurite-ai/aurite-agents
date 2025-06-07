"""
LLM Client Abstraction for interacting with different LLM providers.
"""

import os
import logging
from typing import List, Optional, Dict, Any, AsyncGenerator

from pydantic import ValidationError
from typing import cast

from ...agents.agent_models import (
    AgentOutputMessage,
    AgentOutputContentBlock,
)

import httpx  # Added import
from anthropic import AsyncAnthropic, APIConnectionError, RateLimitError
from anthropic._types import NOT_GIVEN
from anthropic.types import (
    Message as AnthropicMessage,
    TextBlock as AnthropicTextBlock,
    ToolUseBlock as AnthropicToolUseBlock,
    MessageParam,
    ToolParam,
)
from typing import Iterable

from ..base_client import (
    BaseLLM,
    DEFAULT_MAX_TOKENS as BASE_DEFAULT_MAX_TOKENS,
)
from ....config.config_models import LLMConfig

logger = logging.getLogger(__name__)

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
        api_key: Optional[str] = None,
    ):
        super().__init__(model_name, temperature, max_tokens, system_prompt)
        resolved_api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_api_key:
            logger.error(
                "Anthropic API key not provided or found in ANTHROPIC_API_KEY environment variable."
            )
            raise ValueError("Anthropic API key is required.")

        try:
            # Create an httpx.AsyncClient configured to prefer HTTP/1.1
            # We also increase the default timeouts slightly as a precaution,
            # though the main test is http1.
            http1_client = httpx.AsyncClient(
                http2=False,  # Force HTTP/1.1
                timeout=httpx.Timeout(15.0, connect=5.0),  # 15s total, 5s connect
            )

            self.anthropic_sdk_client = AsyncAnthropic(
                api_key=resolved_api_key,
                http_client=http1_client,  # Pass the pre-configured client
                timeout=30.0,  # Explicitly set SDK-level timeout (seconds)
                max_retries=3,  # Explicitly set SDK-level retries
            )
            logger.info(
                f"AnthropicLLM client initialized successfully for model {self.model_name}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic SDK client: {e}")
            raise ValueError(f"Failed to initialize Anthropic SDK client: {e}") from e

    async def aclose(self):
        """Closes the underlying httpx client."""
        if self.anthropic_sdk_client and hasattr(self.anthropic_sdk_client, "_client"):
            await self.anthropic_sdk_client._client.aclose()
            logger.debug("AnthropicLLM client session closed.")

    async def create_message(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        system_prompt_override: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        llm_config_override: Optional[LLMConfig] = None,
    ) -> AgentOutputMessage:
        model_to_use = self.model_name
        if llm_config_override and llm_config_override.model_name:
            model_to_use = llm_config_override.model_name
        temperature_to_use = self.temperature
        if llm_config_override and llm_config_override.temperature is not None:
            temperature_to_use = llm_config_override.temperature
        max_tokens_to_use = self.max_tokens
        if llm_config_override and llm_config_override.max_tokens is not None:
            max_tokens_to_use = llm_config_override.max_tokens
        if max_tokens_to_use is None:
            max_tokens_to_use = BASE_DEFAULT_MAX_TOKENS
        resolved_system_prompt = self.system_prompt
        if llm_config_override and llm_config_override.default_system_prompt:
            resolved_system_prompt = llm_config_override.default_system_prompt
        if system_prompt_override is not None:
            resolved_system_prompt = system_prompt_override
        if schema:
            import json

            try:
                schema_str = json.dumps(schema, indent=2)
                schema_injection = f"""
Your response must be valid JSON matching this schema:
{schema_str}

Remember to format your response as a valid JSON object."""
                if resolved_system_prompt:
                    resolved_system_prompt = (
                        f"{resolved_system_prompt}\n{schema_injection}"
                    )
                else:
                    resolved_system_prompt = schema_injection
            except Exception as json_err:
                logger.error(f"Failed to serialize schema for injection: {json_err}")
        tools_for_api = tools if tools else None
        logger.debug(f"Making Anthropic API call to model '{model_to_use}'")
        try:
            typed_messages = cast(Iterable[MessageParam], messages)
            typed_tools = cast(Optional[Iterable[ToolParam]], tools_for_api)
            anthropic_response: AnthropicMessage = (
                await self.anthropic_sdk_client.messages.create(
                    model=model_to_use,
                    max_tokens=max_tokens_to_use,
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
                            input=cast(Dict[str, Any], block.input),
                        )
                    )
            role = anthropic_response.role
            usage_dict = None
            if anthropic_response.usage:
                usage_dict = {
                    "input_tokens": anthropic_response.usage.input_tokens,
                    "output_tokens": anthropic_response.usage.output_tokens,
                }
            stop_reason_str = None
            if anthropic_response.stop_reason:
                stop_reason_str = str(anthropic_response.stop_reason)
            validated_output_message = AgentOutputMessage(
                id=anthropic_response.id,
                model=anthropic_response.model,
                role=role,
                content=output_content_blocks,
                stop_reason=stop_reason_str,
                stop_sequence=anthropic_response.stop_sequence,
                usage=usage_dict,
            )
            return validated_output_message
        except (APIConnectionError, RateLimitError) as e:
            logger.error(f"Anthropic API call failed: {type(e).__name__}: {e}")
            raise
        except ValidationError as e:
            error_msg = (
                f"Failed to validate Anthropic response against internal model: {e}"
            )
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg) from e
        except Exception as e:
            logger.error(
                f"Unexpected error during Anthropic API call or response processing: {e}",
                exc_info=True,
            )
            raise

    async def stream_message(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        system_prompt_override: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        llm_config_override: Optional[LLMConfig] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        model_to_use = self.model_name
        if llm_config_override and llm_config_override.model_name:
            model_to_use = llm_config_override.model_name
        temperature_to_use = self.temperature
        if llm_config_override and llm_config_override.temperature is not None:
            temperature_to_use = llm_config_override.temperature
        max_tokens_to_use = self.max_tokens
        if llm_config_override and llm_config_override.max_tokens is not None:
            max_tokens_to_use = llm_config_override.max_tokens
        if max_tokens_to_use is None:
            max_tokens_to_use = BASE_DEFAULT_MAX_TOKENS
        resolved_system_prompt = self.system_prompt
        if llm_config_override and llm_config_override.default_system_prompt:
            resolved_system_prompt = llm_config_override.default_system_prompt
        if system_prompt_override is not None:
            resolved_system_prompt = system_prompt_override
        tools_for_api = tools if tools else None
        logger.debug(f"Streaming Anthropic API call to model '{model_to_use}'")
        try:
            typed_messages = cast(Iterable[MessageParam], messages)
            typed_tools = cast(Optional[Iterable[ToolParam]], tools_for_api)
            async with self.anthropic_sdk_client.messages.stream(
                model=model_to_use,
                max_tokens=max_tokens_to_use,
                messages=typed_messages,
                system=resolved_system_prompt if resolved_system_prompt else NOT_GIVEN,
                tools=typed_tools if typed_tools is not None else NOT_GIVEN,
                temperature=temperature_to_use
                if temperature_to_use is not None
                else NOT_GIVEN,
            ) as stream:
                async for event in stream:
                    logger.debug(
                        f"Anthropic stream event received: {event.type} | Full event: {event}"
                    )
                    if event.type == "message_start":
                        yield {
                            "event_type": "message_start",
                            "data": {
                                "message_id": event.message.id,
                                "role": event.message.role,
                                "model": event.message.model,
                                "input_tokens": event.message.usage.input_tokens,
                            },
                        }
                    elif event.type == "content_block_start":
                        if event.content_block.type == "text":
                            yield {
                                "event_type": "text_block_start",
                                "data": {"index": event.index},
                            }
                        elif event.content_block.type == "tool_use":
                            yield {
                                "event_type": "tool_use_start",
                                "data": {
                                    "index": event.index,
                                    "tool_id": event.content_block.id,
                                    "tool_name": event.content_block.name,
                                },
                            }
                        elif event.content_block.type == "thinking":
                            yield {
                                "event_type": "thinking_block_start",
                                "data": {
                                    "index": event.index,
                                    "content_block_type": "thinking",
                                },
                            }
                    elif event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            yield {
                                "event_type": "text_delta",
                                "data": {
                                    "index": event.index,
                                    "text_chunk": event.delta.text,
                                },
                            }
                        elif event.delta.type == "input_json_delta":
                            yield {
                                "event_type": "tool_use_input_delta",
                                "data": {
                                    "index": event.index,
                                    "json_chunk": event.delta.partial_json,
                                },
                            }
                        elif event.delta.type == "thinking_delta":
                            yield {
                                "event_type": "text_delta",
                                "data": {
                                    "index": event.index,
                                    "text_chunk": event.delta.thinking,
                                    "is_thinking": True,
                                },
                            }
                        # No explicit handler for signature_delta needed for content
                    elif event.type == "content_block_stop":
                        yield {
                            "event_type": "content_block_stop",
                            "data": {"index": event.index},
                        }
                    elif event.type == "message_delta":
                        yield {
                            "event_type": "message_delta",
                            "data": {
                                "stop_reason": str(event.delta.stop_reason)
                                if event.delta.stop_reason
                                else None,
                                "stop_sequence": event.delta.stop_sequence,
                                "output_tokens": event.usage.output_tokens,
                            },
                        }
                    elif event.type == "message_stop":
                        # The MessageStopEvent contains the final Message object
                        final_message_stop_reason = None
                        if event.message and event.message.stop_reason:
                            final_message_stop_reason = str(event.message.stop_reason)
                        logger.info(
                            f"Anthropic message_stop event, stop_reason: {final_message_stop_reason}"
                        )
                        yield {
                            "event_type": "stream_end",  # This signifies the end of THIS LLM call
                            "data": {
                                "stop_reason": final_message_stop_reason,
                                "raw_message_stop_event": event.model_dump(mode="json")
                                if hasattr(event, "model_dump")
                                else str(event),
                            },
                        }
                    elif event.type == "ping":
                        yield {"event_type": "ping", "data": {}}
                    elif event.type == "error":
                        logger.error(
                            f"Error event from Anthropic stream: {event.error}"
                        )
                        yield {
                            "event_type": "error",
                            "data": {
                                "type": event.error.type,
                                "message": event.error.message,
                            },
                        }
                    else:
                        logger.warning(
                            f"Unhandled Anthropic stream event type (fallback): {event.type}"
                        )
                        parsed_unknown_data: Dict[str, Any] = {}
                        try:
                            if hasattr(event, "model_dump"):
                                parsed_unknown_data = event.model_dump(mode="json")
                            elif isinstance(event, dict):
                                parsed_unknown_data = event
                            else:
                                logger.warning(
                                    f"Unhandled event '{event.type}' is not Pydantic/dict: {type(event)}"
                                )
                                parsed_unknown_data = {
                                    "raw_event_type": event.type,
                                    "details": str(event),
                                }
                        except Exception as e_parse:
                            logger.error(
                                f"Could not serialize/parse unhandled event {event.type}: {e_parse}"
                            )
                            parsed_unknown_data = {
                                "raw_event_type": event.type,
                                "error": "failed to serialize/parse data",
                                "original_type": str(type(event)),
                            }
                        logger.warning(
                            f"Unhandled Anthropic stream event (fallback) (type: {event.type}) full structure: {event}"
                        )
                        yield {"event_type": "unknown", "data": parsed_unknown_data}
        except (APIConnectionError, RateLimitError) as e:
            logger.error(f"Anthropic API stream failed: {type(e).__name__}: {e}")
            yield {
                "event_type": "error",
                "data": {"type": "sdk_error", "message": str(e)},
            }
        except Exception as e:
            logger.error(
                f"Unexpected error during Anthropic stream: {e}", exc_info=True
            )
            yield {
                "event_type": "error",
                "data": {"type": "unexpected_error", "message": str(e)},
            }
