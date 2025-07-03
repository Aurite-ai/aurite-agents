"""
LLM Client for interacting with models via the LiteLLM library.
"""

import os
import logging
import json
from typing import List, Optional, Dict, Any, AsyncGenerator

import litellm
from openai import OpenAIError
from openai.types.chat import (
    ChatCompletionMessage,
    ChatCompletionChunk,
)

from ....config.config_models import LLMConfig

logger = logging.getLogger(__name__)


class LiteLLMClient:
    """
    A client for interacting with LLMs via the LiteLLM library.
    This client is initialized with a resolved LLMConfig and is responsible
    for making the final API calls.
    """

    def __init__(self, config: LLMConfig):
        if not config.provider or not config.model:
            raise ValueError("LLM provider and model must be specified in the config.")

        self.config = config
        litellm.drop_params = (
            True  # Automatically drops unsupported params rather than throwing an error
        )

        litellm_logger = logging.getLogger("LiteLLM")
        litellm_logger.setLevel(logging.ERROR)

        # Handle provider-specific setup if necessary
        if self.config.provider == "gemini":
            if "GEMINI_API_KEY" not in os.environ and "GOOGLE_API_KEY" in os.environ:
                os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

        logger.info(
            f"LiteLLMClient initialized for {self.config.provider}/{self.config.model}."
        )

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
                # Ensure the input_schema has a 'type', defaulting to 'object'.
                # This is required by some providers like Anthropic.
                input_schema = tool_def["input_schema"].copy()
                if "type" not in input_schema:
                    input_schema["type"] = "object"

                openai_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool_def["name"],
                            "description": tool_def.get("description", ""),
                            "parameters": input_schema,
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
    ) -> Dict[str, Any]:
        # Use the resolved system prompt from the config, but allow a final override.
        resolved_system_prompt = (
            system_prompt_override or self.config.default_system_prompt
        )

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
            "model": f"{self.config.provider}/{self.config.model}",
            "messages": api_messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "api_base": self.config.api_base,
            "api_key": self.config.api_key,
            "api_version": self.config.api_version,
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
    ) -> ChatCompletionMessage:
        request_params = self._build_request_params(
            messages, tools, system_prompt_override, schema
        )

        logger.debug(f"Making LiteLLM call with params: {request_params}")

        try:
            completion: Any = litellm.completion(**request_params)
            return completion.choices[0].message
        except OpenAIError as e:
            logger.error(
                f"LiteLLM API call failed with specific error: {type(e).__name__}: {e}"
            )
            raise  # Re-raise the specific, informative exception
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during LiteLLM API call: {type(e).__name__}: {e}"
            )
            raise  # Re-raise as a generic exception

    async def stream_message(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        system_prompt_override: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        request_params = self._build_request_params(
            messages, tools, system_prompt_override, schema
        )
        request_params["stream"] = True

        logger.debug(f"Making LiteLLM streaming call with params: {request_params}")

        try:
            response_stream: Any = await litellm.acompletion(**request_params)
            async for chunk in response_stream:
                yield chunk
        except OpenAIError as e:
            logger.error(
                f"LiteLLM streaming call failed with specific error: {type(e).__name__}: {e}"
            )
            raise  # Re-raise the specific, informative exception
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during LiteLLM streaming call: {type(e).__name__}: {e}"
            )
            # In case of an error, we might want to yield a specific error chunk or just raise
            raise
