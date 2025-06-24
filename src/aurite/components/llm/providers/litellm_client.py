"""
LLM Client for OpenAI models.
"""

import os
import logging
import json  # For parsing tool arguments
import litellm
from typing import List, Optional, Dict, Any, AsyncGenerator

from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
)
from openai.types.chat.chat_completion import Choice
from pydantic import ValidationError


from ..base_client import (
    BaseLLM,
    DEFAULT_MAX_TOKENS as BASE_DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE as BASE_DEFAULT_TEMPERATURE,
    # DEFAULT_SYSTEM_PROMPT is also available if needed
)
from ...agents.agent_models import AgentOutputMessage, AgentOutputContentBlock
from ....config.config_models import LLMConfig

logger = logging.getLogger(__name__)


class LiteLLMClient(BaseLLM):
    """LLM Client implementation for LiteLLM."""

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
        super().__init__(model_name, temperature, max_tokens, system_prompt)
        self.provider = provider
        self.api_base = api_base
        self.api_key = api_key
        self.api_version = api_version
        
        if provider == "gemini":
            # litellm expects GEMINI_API_KEY, however we expect GOOGLE_API_KEY
            # so, we copy it over for the process
            if 'GEMINI_API_KEY' not in os.environ and 'GOOGLE_API_KEY' in os.environ:
                os.environ['GEMINI_API_KEY'] = os.environ['GOOGLE_API_KEY']
        logger.info(
            f"LiteLLM initialized for {self.provider}/{self.model_name}."
        )

    async def aclose(self):
        """Closes the underlying httpx client used. Not needed for LiteLLM"""
        pass

    def _convert_messages_to_openai_format(
        self, messages: List[Dict[str, Any]], system_prompt: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Converts Aurite internal message format to OpenAI's expected format."""
        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            # Priority 1: Handle Aurite's tool result messages (role="user", content.type="tool_result")
            # These must be converted to OpenAI's role="tool" messages.
            if (
                role == "user"
                and isinstance(content, list)
                and content
                and content[0].get("type") == "tool_result"
            ):
                tool_result_block = content[0]
                tool_output_content = tool_result_block.get("content")
                tool_output_str = ""
                if isinstance(tool_output_content, list):  # If list of blocks
                    text_parts = [
                        block.get("text", "")
                        for block in tool_output_content
                        if block.get("type") == "text"
                    ]
                    tool_output_str = "\n".join(text_parts)
                elif isinstance(tool_output_content, str):
                    tool_output_str = tool_output_content
                else:  # Fallback: stringify, OpenAI expects string content for tool role.
                    try:
                        tool_output_str = json.dumps(tool_output_content)
                    except TypeError:  # If not JSON serializable, just stringify
                        tool_output_str = str(tool_output_content)

                openai_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_result_block.get("tool_use_id"),
                        "content": tool_output_str,
                    }
                )
            # Priority 2: Handle standard user messages
            elif role == "user":
                text_parts = []
                if isinstance(content, list):
                    for block in content:  # Should be text blocks
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                elif isinstance(content, str):
                    text_parts.append(content)
                openai_messages.append(
                    {"role": "user", "content": " ".join(text_parts)}
                )
            # Priority 3: Handle assistant messages
            elif role == "assistant":
                assistant_content_parts = []
                tool_calls_for_api = []
                if isinstance(content, list):
                    for block in content:
                        if block.get("type") == "text":
                            assistant_content_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_use":  # Aurite's tool_use block
                            tool_calls_for_api.append(
                                {
                                    "id": block.get("id"),
                                    "type": "function",
                                    "function": {
                                        "name": block.get("name"),
                                        "arguments": json.dumps(
                                            block.get("input", {})
                                        ),  # OpenAI expects arguments as JSON string
                                    },
                                }
                            )

                assistant_msg_for_api: Dict[str, Any] = {"role": "assistant"}
                text_content = " ".join(assistant_content_parts).strip()
                if text_content:
                    assistant_msg_for_api["content"] = text_content
                if tool_calls_for_api:
                    assistant_msg_for_api["tool_calls"] = tool_calls_for_api

                # Add message only if it has content or tool_calls
                if (
                    "content" in assistant_msg_for_api
                    or "tool_calls" in assistant_msg_for_api
                ):
                    openai_messages.append(assistant_msg_for_api)
            else:
                logger.warning(
                    f"Unhandled message role for OpenAI conversion: {role} in message: {msg}"
                )
        return openai_messages

    def _convert_tools_to_openai_format(
        self, tools: Optional[List[Dict[str, Any]]]
    ) -> Optional[List[Dict[str, Any]]]:
        if not tools:
            return None
        openai_tools = []
        for tool_def in tools:
            # Assuming Aurite tool format is:
            # {"name": "tool_name", "description": "...", "input_schema": {...JSONSchema...}}
            # Convert to OpenAI format:
            # {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}
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
            else:
                logger.warning(f"Skipping tool with unexpected format: {tool_def}")
        return openai_tools if openai_tools else None
    
    def _build_request_params(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        system_prompt_override: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,  # For JSON mode
        llm_config_override: Optional[LLMConfig] = None,
    ):
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
        elif temperature_to_use is None:  # Ensure a default if not set at all
            temperature_to_use = BASE_DEFAULT_TEMPERATURE

        max_tokens_to_use = self.max_tokens
        if llm_config_override and llm_config_override.max_tokens is not None:
            max_tokens_to_use = llm_config_override.max_tokens
        elif max_tokens_to_use is None:  # Ensure a default
            max_tokens_to_use = BASE_DEFAULT_MAX_TOKENS

        resolved_system_prompt = self.system_prompt
        if llm_config_override and llm_config_override.default_system_prompt:
            resolved_system_prompt = llm_config_override.default_system_prompt
        if system_prompt_override is not None:  # Highest precedence
            resolved_system_prompt = system_prompt_override
            
        if schema:  # For JSON mode
            # Note: Only certain models support JSON mode, so we add to the system prompt
            json_instruction = f"Your response MUST be a single valid JSON object that conforms to the provided schema. Do NOT add any text or characters before or after, including code block formatting (NO ```) {json.dumps(schema, indent=2)}"
            if resolved_system_prompt:
                resolved_system_prompt = (
                    f"{resolved_system_prompt}\n{json_instruction}"
                )
            else:
                resolved_system_prompt = json_instruction

        # Convert messages and tools to OpenAI format
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
            request_params["tool_choice"] = (
                "auto"  # Let the model decide if it wants to use tools
            )

        return request_params

    async def create_message(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        system_prompt_override: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,  # For JSON mode
        llm_config_override: Optional[LLMConfig] = None,
    ) -> AgentOutputMessage:
        
        request_params = self._build_request_params(messages, tools, system_prompt_override, schema, llm_config_override)

        logger.debug(
            f"Making LiteLLM call with params: {request_params}"
        )

        try:
            completion: ChatCompletion = litellm.completion(
                **request_params
            )
        except Exception as e:
            logger.error(
                f"LiteLLM API call failed: {type(e).__name__}: {e}", exc_info=True
            )
            raise  # Re-raise the original exception

        # Adapt LiteLLM response to AgentOutputMessage
        choice: Choice = completion.choices[0]
        message_from_litellm = choice.message

        output_content_blocks: List[AgentOutputContentBlock] = []

        if message_from_litellm.content:  # Text content
            text_content = str(message_from_litellm.content)
            if schema and '{' in text_content and '}' in text_content:
                # trim to curly braces if structured output
                text_content = text_content[text_content.find('{'): text_content.rfind('}')+1]
            else:
                text_content = text_content
            
            output_content_blocks.append(
                AgentOutputContentBlock(
                    type="text", text=str(message_from_litellm.content)
                )
            )

        if message_from_litellm.tool_calls:
            for tool_call in message_from_litellm.tool_calls:
                tool_call_data: ChatCompletionMessageToolCall = tool_call
                try:
                    arguments = json.loads(tool_call_data.function.arguments)
                except json.JSONDecodeError:
                    logger.error(
                        f"Failed to parse JSON arguments for tool {tool_call_data.function.name}: {tool_call_data.function.arguments}"
                    )
                    arguments = {
                        "error": "failed to parse arguments",
                        "raw_arguments": tool_call_data.function.arguments,
                    }

                output_content_blocks.append(
                    AgentOutputContentBlock(
                        type="tool_use",
                        id=tool_call_data.id,
                        name=tool_call_data.function.name,
                        input=arguments,
                    )
                )

        usage_dict = None
        if completion.usage:
            usage_dict = {
                "input_tokens": completion.usage.prompt_tokens,
                "output_tokens": completion.usage.completion_tokens,
            }

        try:
            agent_output_message = AgentOutputMessage(
                id=completion.id,
                model=completion.model,
                role="assistant",  # OpenAI's response role is always assistant
                content=output_content_blocks,
                stop_reason=str(choice.finish_reason) if choice.finish_reason else None,
                stop_sequence=None,  # OpenAI API doesn't typically return stop_sequence here
                usage=usage_dict,
            )
            return agent_output_message
        except ValidationError as e:
            error_msg = f"Failed to validate LiteLLM response against internal AgentOutputMessage model: {e}"
            logger.error(error_msg, exc_info=True)
            # Fallback or re-raise
            raise Exception(error_msg) from e

    async def stream_message(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        system_prompt_override: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        llm_config_override: Optional[LLMConfig] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        
        request_params = self._build_request_params(messages, tools, system_prompt_override, schema, llm_config_override)
        request_params["stream"] = True

        logger.debug(
            f"Making LiteLLM call with params: {request_params}"
        )
        
        try:
            response = litellm.completion(
                **request_params
            )
            
            for event in response:
                yield event

        except Exception as e:
            logger.error(
                f"Error in OpenAIClient.stream_message (simulated): {e}", exc_info=True
            )
            yield {"event_type": "error", "data": {"message": str(e)}}
