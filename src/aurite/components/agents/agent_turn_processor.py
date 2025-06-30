"""
Helper class for processing a single turn in an Agent's conversation loop.
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
)
from jsonschema import validate, ValidationError as JsonSchemaValidationError

from ...config.config_models import AgentConfig, LLMConfig
from ...host.host import MCPHost
from ..llm.providers.litellm_client import LiteLLMClient

logger = logging.getLogger(__name__)


class AgentTurnProcessor:
    """
    Handles the logic for a single turn of interaction within the Agent's
    execution loop, including LLM calls, response parsing, schema validation,
    and tool execution coordination.
    """

    def __init__(
        self,
        config: AgentConfig,
        llm_client: LiteLLMClient,
        host_instance: MCPHost,
        current_messages: List[Dict[str, Any]],
        tools_data: Optional[List[Dict[str, Any]]],
        effective_system_prompt: Optional[str],
        llm_config_for_override: Optional[LLMConfig] = None,
    ):
        self.config = config
        self.llm = llm_client
        self.host = host_instance
        self.messages = current_messages
        self.tools = tools_data
        self.system_prompt = effective_system_prompt
        self.llm_config_for_override = llm_config_for_override
        self._last_llm_response: Optional[ChatCompletionMessage] = None
        self._tool_uses_this_turn: List[ChatCompletionMessageToolCall] = []
        logger.debug("AgentTurnProcessor initialized.")

    def get_last_llm_response(self) -> Optional[ChatCompletionMessage]:
        return self._last_llm_response

    def get_tool_uses_this_turn(self) -> List[ChatCompletionMessageToolCall]:
        return self._tool_uses_this_turn

    async def process_turn(
        self,
    ) -> Tuple[Optional[ChatCompletionMessage], Optional[List[Dict[str, Any]]], bool]:
        logger.debug("Processing conversation turn...")
        try:
            llm_response = await self.llm.create_message(
                messages=self.messages,
                tools=self.tools,
                system_prompt_override=self.system_prompt,
                schema=self.config.config_validation_schema,
                llm_config_override=self.llm_config_for_override,
            )
        except Exception as e:
            logger.error(f"LLM call failed within turn processor: {e}", exc_info=True)
            raise

        self._last_llm_response = llm_response
        is_final_turn = False

        if llm_response.tool_calls:
            tool_results_for_next_turn = await self._process_tool_calls(llm_response)
            return None, tool_results_for_next_turn, is_final_turn
        else:
            validated_response = self._handle_final_response(llm_response)
            if validated_response:
                is_final_turn = True
            return validated_response, None, is_final_turn

    async def stream_turn_response(self) -> AsyncGenerator[Dict[str, Any], None]:
        # This method will need significant rework to align with the new model
        # For now, we focus on the non-streaming path.
        # A full implementation would require accumulating deltas to build tool calls
        # and then executing them, which is complex.
        logger.warning(
            "Streaming turn processing is not fully implemented in this refactored version."
        )
        # To satisfy the generator requirement:
        if False:
            yield {}

        # Fallback to non-streaming logic for now
        final_response, tool_results, is_final = await self.process_turn()

        yield {
            "type": "full_response",
            "data": {
                "final_response": final_response.model_dump()
                if final_response
                else None,
                "tool_results": tool_results,
                "is_final": is_final,
            },
        }

    async def _process_tool_calls(
        self, llm_response: ChatCompletionMessage
    ) -> List[Dict[str, Any]]:
        tool_results_for_next_turn: List[Dict[str, Any]] = []
        if not llm_response.tool_calls:
            return tool_results_for_next_turn

        self._tool_uses_this_turn = llm_response.tool_calls

        for tool_call in llm_response.tool_calls:
            tool_name = tool_call.function.name
            tool_input = {}
            try:
                tool_input = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                logger.warning(
                    f"Failed to parse JSON for tool '{tool_name}' arguments: {tool_call.function.arguments}"
                )
                tool_result_content = f"Error: Invalid JSON arguments provided: {tool_call.function.arguments}"
            else:
                try:
                    tool_result_content = await self.host.execute_tool(
                        tool_name=tool_name,
                        arguments=tool_input,
                        agent_config=self.config,
                    )
                except Exception as e:
                    logger.error(
                        f"Error executing tool {tool_name}: {e}", exc_info=True
                    )
                    tool_result_content = (
                        f"Error executing tool '{tool_name}': {str(e)}"
                    )

            # Format the result into an OpenAI-compatible tool message
            tool_message = {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_name,
                "content": json.dumps(tool_result_content)
                if not isinstance(tool_result_content, str)
                else tool_result_content,
            }
            tool_results_for_next_turn.append(tool_message)

        return tool_results_for_next_turn

    def _handle_final_response(
        self, llm_response: ChatCompletionMessage
    ) -> Optional[ChatCompletionMessage]:
        if not self.config.config_validation_schema:
            return llm_response

        text_content = llm_response.content or ""
        try:
            json_content = json.loads(text_content)
            validate(instance=json_content, schema=self.config.config_validation_schema)
            return llm_response
        except (json.JSONDecodeError, JsonSchemaValidationError) as e:
            logger.warning(f"Schema validation failed for final response: {e}")
            return None
