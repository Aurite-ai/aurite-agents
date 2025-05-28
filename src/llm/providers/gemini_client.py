"""
LLM Client for Gemini
"""

import os
import logging
from typing import List, Optional, Dict, Any, AsyncGenerator

from typing import cast
from anthropic.types import (
    Message as AnthropicMessage,
    TextBlock as AnthropicTextBlock,
    ToolUseBlock as AnthropicToolUseBlock,
    MessageParam,
    ToolParam,
)

from ...agents.agent_models import (
    AgentOutputMessage,
    AgentOutputContentBlock,
    ConversationHistoryMessage,
    ToolDefinition
)

from typing import Iterable
from google import genai
from google.genai import types

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
            self.gemini_client = genai.Client(api_key=resolved_api_key)
            logger.info(
                f"GeminiLLM client initialized successfully for model {self.model_name}"
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
        
        tools_for_api = tools if tools else []
        logger.debug(f"Making Gemini API call to model '{model_to_use}'")
        try:
            typed_messages = cast(Iterable[MessageParam], messages)
            typed_messages = [self._convert_message_history(m) for m in messages]
            
            typed_tools = cast(Optional[Iterable[ToolParam]], tools_for_api)
            typed_tools = [self._convert_tool_definition(t) for t in tools_for_api]
            
            if schema:
                config = types.GenerateContentConfig(
                    tools=[typed_tools],
                    system_instruction=resolved_system_prompt,
                    temperature=temperature_to_use,
                    max_output_tokens=max_tokens_to_use,
                    response_mime_type="application/json",
                    response_schema=schema
                )
            else:
                config = types.GenerateContentConfig(
                    tools=[typed_tools],
                    system_instruction=resolved_system_prompt,
                    temperature=temperature_to_use,
                    max_output_tokens=max_tokens_to_use
                )
            
            gemini_response = self.client.models.generate_content(
                model=model_to_use, config=config, contents=typed_messages
            )
            
            return self._convert_agent_output_message(gemini_response)
        except Exception as e:
            logger.error(
                f"Unexpected error during Gemini API call or response processing: {e}",
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
        # TODO
        pass

    def _convert_agent_output_message(self, response) -> AgentOutputMessage:
        content_blocks = []

        for part in response.candidates[0].content.parts:
            if part.text is not None:
                content_blocks.append(AgentOutputContentBlock(
                    type="text",
                    text=part.text
                ))
            elif part.function_call is not None:
                function_call = part.function_call
                tool_use = {
                    "id": function_call.id,
                    "name": function_call.name,
                    "input": function_call.args
                }
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
            model=response.model_version,
            stop_reason=response.candidates[0].finish_reason,
            usage={
                "input_tokens": response.usage_metadata.prompt_token_count,
                "output_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count
            }
        )

        return output_message

    def _convert_tool_definition(self, tool_def: ToolParam):
        """Convert a ToolDefinition into the Gemini Format"""
        
        return types.Tool(function_declarations=[{
            "name": tool_def.get("name"),
            "description": tool_def.get("description"),
            "parameters": tool_def.get("input_schema"),
        }])

    def _convert_message_history(self, message: MessageParam):
        """Convert a ConversationHistoryMessage into the Gemini Format"""
        
        role_dict = {
            "user": "user",
            "assistant": "model",
        }
        
        if message.get("role") in role_dict:
            return types.Content(
                role = role_dict[message.get("role")],
                parts = self._message_param_to_parts(message.get("content"))
            )
        else:
            raise ValueError(f"Unrecognized role when converting ConversationHistoryMessage to Gemini format: {message.get("role")}")
        
    def _message_param_to_parts(self, param):
        if type(param) is str:
            return [types.Part.from_text(text=param)]
        
        parts = []
        for p in param:
            if p.get("type") == "text":
                parts.append(types.Part.from_text(text=p.get("text")))
            # for now, only works for text
            # TODO: implement other types
        return parts