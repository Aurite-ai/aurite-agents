"""
LLM Client for Gemini
"""

import os
import logging
import json
from typing import List, Optional, Dict, Any, AsyncGenerator

from typing import cast
from anthropic.types import (
    MessageParam,
    ToolParam,
)

from ...agents.agent_models import (
    AgentOutputMessage,
    AgentOutputContentBlock,
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
            
            tool = types.Tool(function_declarations=typed_tools)
            
            if schema:
                config = types.GenerateContentConfig(
                    tools=[tool],
                    system_instruction=resolved_system_prompt,
                    temperature=temperature_to_use,
                    max_output_tokens=max_tokens_to_use,
                    response_mime_type="application/json",
                    response_schema=schema
                )
            else:
                config = types.GenerateContentConfig(
                    tools=[tool],
                    system_instruction=resolved_system_prompt,
                    temperature=temperature_to_use,
                    max_output_tokens=max_tokens_to_use
                )
            
            gemini_response = self.gemini_client.models.generate_content(
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
        
        tools_for_api = tools if tools else []
        logger.debug(f"Making Gemini API call to model '{model_to_use}'")
        try:
            logger.info(f"MESSAGES: {messages}")
            typed_messages = cast(Iterable[MessageParam], messages)
            typed_messages = [self._convert_message_history(m) for m in messages]
            
            typed_tools = cast(Optional[Iterable[ToolParam]], tools_for_api)
            typed_tools = [self._convert_tool_definition(t) for t in tools_for_api]
            
            tool = types.Tool(function_declarations=typed_tools)
            
            config = types.GenerateContentConfig(
                tools=[tool],
                system_instruction=resolved_system_prompt,
                temperature=temperature_to_use,
                max_output_tokens=max_tokens_to_use
            )
            
            state = None # "thinking", "text", "tool"
            current_index = 0 # manually count index, as indices given by gemini are reused between types
            started_message = False
            sent_tool = False
            
            for event in self.gemini_client.models.generate_content_stream(
                model=model_to_use, config=config, contents=typed_messages
            ):
                if not started_message:
                    started_message = True
                    yield {
                        "event_type": "message_start",
                        "data": {
                            # "message_id": 0,
                            "role": "assistant",
                            "model": model_to_use,
                            "input_tokens": event.usage_metadata.prompt_token_count,
                        },
                    }
                    
                for part in event.candidates[0].content.parts:
                    if part.function_call:
                        next_state = "tool"
                    elif part.text:
                        next_state = "text"
                    elif part.thought:
                        next_state = "thinking"
                    else:
                        logger.error(f"Unknown stream state: {event}")
                        
                    if state == next_state:
                        # ONGOING
                        match state:
                            case "thinking":
                                # gemini does not seem to give text while thinking. do nothing
                                pass
                            case "text":
                                yield {
                                    "event_type": "text_delta",
                                    "data": {
                                        "index": current_index,
                                        "text_chunk": part.text,
                                    },
                                }
                            case "tool":
                                yield {
                                    "event_type": "tool_use_input_delta",
                                    "data": {
                                        "index": current_index,
                                        "json_chunk": part.function_call.args
                                    },
                                }
                    else:
                        # ENDING
                        if state and state != "tool":
                            yield {
                                "event_type": "content_block_stop",
                                "data": {"index": current_index},
                            }
                            current_index += 1
                        
                        # BEGINNING
                        state = next_state
                        match state:
                            case "thinking":
                                yield {
                                    "event_type": "thinking_block_start",
                                    "data": {
                                        "index": current_index,
                                        "content_block_type": "thinking",
                                    },
                                }
                            case "text":
                                yield {
                                    "event_type": "text_block_start",
                                    "data": {"index": current_index},
                                }
                                yield {
                                    "event_type": "text_delta",
                                    "data": {
                                        "index": current_index,
                                        "text_chunk": part.text,
                                    },
                                }
                                logger.info(f"Streamed text: {part.text}")
                            case "tool":
                                yield {
                                    "event_type": "tool_use_start",
                                    "data": {
                                        "index": current_index,
                                        "tool_id": part.function_call.id if part.function_call.id is not None else current_index,
                                        "tool_name": part.function_call.name,
                                    },
                                }
                                yield {
                                    "event_type": "tool_use_input_delta",
                                    "data": {
                                        "index": current_index,
                                        "json_chunk": json.dumps(part.function_call.args)
                                    },
                                }
                                yield {
                                    "event_type": "content_block_stop",
                                    "data": {"index": current_index},
                                }
                                sent_tool = True
                                current_index += 1
                            
            #finally, send a stream_end block:
            yield {
                "event_type": "stream_end",  # This signifies the end of THIS LLM call
                "data": {
                    "stop_reason": "tool_use" if sent_tool else "end_turn",
                    "raw_message_stop_event": event.model_dump(mode="json")
                    if hasattr(event, "model_dump")
                    else str(event),
                },
            }
                
        except Exception as e:
            logger.error(
                f"Unexpected error during Gemini stream: {e}", exc_info=True
            )
            yield {
                "event_type": "error",
                "data": {"type": "unexpected_error", "message": str(e)},
            }


    def _convert_agent_output_message(self, response) -> AgentOutputMessage:
        content_blocks = []
        num_tools = 0
        
        match response.candidates[0].finish_reason:
            case types.FinishReason.MAX_TOKENS:
                stop_reason = "max_tokens"
            case _:
                stop_reason = "end_turn"

        for part in response.candidates[0].content.parts:
            if part.text is not None:
                content_blocks.append(AgentOutputContentBlock(
                    type="text",
                    text=part.text
                ))
            elif part.function_call is not None:
                function_call = part.function_call
                tool_use = {
                    "id": function_call.id if function_call.id is not None else f'{function_call.name}_{num_tools}', # use # of tool call as id if not supplied
                    "name": function_call.name,
                    "input": function_call.args
                }
                content_blocks.append(AgentOutputContentBlock(
                    type="tool_use",
                    id=tool_use["id"],
                    name=tool_use["name"],
                    input=tool_use["input"]
                ))
                num_tools += 1
                stop_reason = "tool_use" # overwrite stop reason to tool use if one or more tools are used
        
        # Create an AgentOutputMessage
        output_message = AgentOutputMessage(
            role="assistant",
            content=content_blocks,
            model=response.model_version,
            stop_reason=stop_reason,
            usage={
                "input_tokens": response.usage_metadata.prompt_token_count,
                "output_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count
            }
        )
        logger.info(f"Gemini output message: {output_message}")

        return output_message
    
    def _convert_streaming_event(self, event) -> dict[str, Any]:
        candidate = event.candidates[0]

    def _convert_tool_definition(self, tool_def: ToolParam):
        """Convert a ToolDefinition into the Gemini Format"""
        
        return types.FunctionDeclaration(
            name = tool_def.get("name"),
            description = tool_def.get("description"),
            parameters = tool_def.get("input_schema"),
        )

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
            match p.get("type"):
                case "text":
                    parts.append(types.Part.from_text(text=p.get("text")))
                case "tool_use":
                    parts.append(types.Part.from_function_call(name=p.get("name"), args=p.get("input")))
                case "tool_result":
                    content = p.get("content")
                    if type(content) is dict:
                        response = content
                    elif type(content) is list:
                        response = content[0]
                    elif type(content) is str:
                        response = {"result": content}
                    else:
                        raise ValueError(f"Unrecognized tool result content type when converting to Gemini format: {p.get("content")}")
                    parts.append(types.Part.from_function_response(name=p.get("tool_use_id"), response=response))
                case _:
                    raise ValueError(f"Unrecognized message parameter type when converting to Gemini format: {p.get("type")}")
                
            # TODO: implement other types if they are used
        return parts