"""
LLM Client for Gemini
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

import httpx # Added import
from typing import Iterable
from google import genai

from ..base_client import (
    BaseLLM,
    DEFAULT_MAX_TOKENS as BASE_DEFAULT_MAX_TOKENS,
)
from ...config.config_models import LLMConfig

logger = logging.getLogger(__name__)

DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."


class GeminiLLM(BaseLLM):
    """LLM Client implementation for Gemini models."""

    def __init__(
        self,
        model_name: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        super().__init__(model_name, temperature, max_tokens, system_prompt)
        resolved_api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not resolved_api_key:
            logger.error(
                "Google API key not provided or found in GOOGLE_API_KEY environment variable."
            )
            raise ValueError("Google API key is required.")

        try:
            # Create an httpx.AsyncClient configured to prefer HTTP/1.1
            # We also increase the default timeouts slightly as a precaution,
            # though the main test is http1.
            http1_client = httpx.AsyncClient(
                http2=False,  # Force HTTP/1.1
                timeout=httpx.Timeout(15.0, connect=5.0) # 15s total, 5s connect
            )

            self.gemini_client = genai.Client(api_key=resolved_api_key)
            logger.info(
                f"GeminiLLM client initialized successfully for model {self.model_name} using HTTP/1.1 client with extended timeouts/retries."
            )
        except Exception as e:
            logger.error(f"Failed to initialize Gemini SDK client: {e}")
            raise ValueError(f"Failed to initialize Gemini SDK client: {e}") from e

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
            #TODO: gemini supports structured output, change to use that rather than adding it to the prompt
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
        logger.debug(f"Making Gemini API call to model '{model_to_use}'")
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
                            input=block.input,
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


def _convert_gemini_response_to_agent_output_message(gemini_response: Dict[str, Any]) -> AgentOutputMessage:
    content_blocks = []
    tool_uses = []

    for part in gemini_response["candidates"][0]["content"]["parts"]:
        if part["text"] is not None:
            content_blocks.append(AgentOutputContentBlock(
                type="text",
                text=part["text"]
            ))
        elif part["function_call"] is not None:
            function_call = part["function_call"]
            tool_use = {
                "id": function_call.get("id", str(len(tool_uses))),  # Generate an ID if not provided
                "name": function_call["name"],
                "input": function_call["args"]
            }
            tool_uses.append(tool_use)
            content_blocks.append(AgentOutputContentBlock(
                type="tool_use",
                id=tool_use["id"],
                name=tool_use["name"],
                input=tool_use["input"]
            ))

    # Create an AgentOutputMessage
    output_message = AgentOutputMessage(
        role="assistant",
        content=content_blocks,
        model=gemini_response["model_version"],
        stop_reason=gemini_response["candidates"][0]["finish_reason"],
        usage={
            "input_tokens": gemini_response["usage_metadata"]["prompt_token_count"],
            "output_tokens": gemini_response["usage_metadata"]["candidates_token_count"],
            "total_tokens": gemini_response["usage_metadata"]["total_token_count"]
        }
    )

    return output_message