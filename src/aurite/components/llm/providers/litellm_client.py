"""
LLM Client for interacting with models via the LiteLLM library.
"""

import os
import logging
import json
from typing import List, Optional, Dict, Any, AsyncGenerator

import litellm
from openai.types.chat import (
    ChatCompletionMessage,
    ChatCompletionChunk,
)

from ....config.config_models import LLMConfig

logger = logging.getLogger(__name__)

# Default values
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."


class LiteLLMClient:
    """A client for interacting with LLMs via the LiteLLM library."""

    def __init__(
        self,
        model_name: str,
        provider: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
    ):
        self.model_name = model_name
        self.temperature = (
            temperature if temperature is not None else DEFAULT_TEMPERATURE
        )
        self.max_tokens = max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS
        self.system_prompt = (
            system_prompt if system_prompt is not None else DEFAULT_SYSTEM_PROMPT
        )
        self.provider = provider
        self.api_base = api_base
        self.api_key = api_key
        self.api_version = api_version

        if provider == "gemini":
            if "GEMINI_API_KEY" not in os.environ and "GOOGLE_API_KEY" in os.environ:
                os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]
        logger.info(f"LiteLLM initialized for {self.provider}/{self.model_name}.")

    def _convert_messages_to_openai_format(
        self, messages: List[Dict[str, Any]], system_prompt: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Converts our internal dictionary message format to the OpenAI API format.
        This is now simpler as we will store history in the OpenAI format directly.
        """
        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})

        # The messages are now expected to be in OpenAI's format already.
        # This function primarily just prepends the system prompt.
        openai_messages.extend(messages)
        return openai_messages

    def _convert_tools_to_openai_format(
        self, tools: Optional[List[Dict[str, Any]]]
    ) -> Optional[List[Dict[str, Any]]]:
        if not tools:
            return None
        openai_tools = []
        for tool_def in tools:
            if "name" in tool_def and "input_schema" in tool_def:
                openai_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool_def["name"],
                            "description": tool_def.get("description", ""),
                            "parameters": tool_def["input_schema"],
                        },
                    }
                )
        return openai_tools if openai_tools else None

    def _build_request_params(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        system_prompt_override: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        llm_config_override: Optional[LLMConfig] = None,
    ) -> Dict[str, Any]:
        # Determine final parameters by layering configurations
        model_to_use = self.model_name
        if llm_config_override and llm_config_override.model_name:
            model_to_use = llm_config_override.model_name

        provider_to_use = self.provider
        if llm_config_override and llm_config_override.provider:
            provider_to_use = llm_config_override.provider

        api_base_to_use = self.api_base
        if llm_config_override and llm_config_override.api_base:
            api_base_to_use = llm_config_override.api_base

        api_key_to_use = self.api_key
        if llm_config_override and llm_config_override.api_key:
            api_key_to_use = llm_config_override.api_key

        api_version_to_use = self.api_version
        if llm_config_override and llm_config_override.api_version:
            api_version_to_use = llm_config_override.api_version

        temperature_to_use = self.temperature
        if llm_config_override and llm_config_override.temperature is not None:
            temperature_to_use = llm_config_override.temperature

        max_tokens_to_use = self.max_tokens
        if llm_config_override and llm_config_override.max_tokens is not None:
            max_tokens_to_use = llm_config_override.max_tokens

        resolved_system_prompt = self.system_prompt
        if llm_config_override and llm_config_override.default_system_prompt:
            resolved_system_prompt = llm_config_override.default_system_prompt
        if system_prompt_override is not None:
            resolved_system_prompt = system_prompt_override

        if schema:
            json_instruction = f"Your response MUST be a single valid JSON object that conforms to the provided schema. Do NOT add any text or characters before or after, including code block formatting (NO ```) {json.dumps(schema, indent=2)}"
            if resolved_system_prompt:
                resolved_system_prompt = f"{resolved_system_prompt}\n{json_instruction}"
            else:
                resolved_system_prompt = json_instruction

        api_messages = self._convert_messages_to_openai_format(
            messages, resolved_system_prompt
        )
        api_tools = self._convert_tools_to_openai_format(tools)

        request_params: Dict[str, Any] = {
            "model": f"{provider_to_use}/{model_to_use}",
            "messages": api_messages,
            "temperature": temperature_to_use,
            "max_tokens": max_tokens_to_use,
            "api_base": api_base_to_use,
            "api_key": api_key_to_use,
            "api_version": api_version_to_use,
        }

        if api_tools:
            request_params["tools"] = api_tools
            request_params["tool_choice"] = "auto"

        return request_params

    async def create_message(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        system_prompt_override: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        llm_config_override: Optional[LLMConfig] = None,
    ) -> ChatCompletionMessage:
        request_params = self._build_request_params(
            messages, tools, system_prompt_override, schema, llm_config_override
        )

        logger.debug(f"Making LiteLLM call with params: {request_params}")

        try:
            completion: Any = litellm.completion(**request_params)
            return completion.choices[0].message
        except Exception as e:
            logger.error(
                f"LiteLLM API call failed: {type(e).__name__}: {e}", exc_info=True
            )
            raise

    async def stream_message(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        system_prompt_override: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        llm_config_override: Optional[LLMConfig] = None,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        request_params = self._build_request_params(
            messages, tools, system_prompt_override, schema, llm_config_override
        )
        request_params["stream"] = True

        logger.debug(f"Making LiteLLM streaming call with params: {request_params}")

        try:
            response_stream: Any = await litellm.acompletion(**request_params)
            async for chunk in response_stream:
                yield chunk
        except Exception as e:
            logger.error(f"Error in LiteLLMClient.stream_message: {e}", exc_info=True)
            # In case of an error, we might want to yield a specific error chunk or just raise
            raise
