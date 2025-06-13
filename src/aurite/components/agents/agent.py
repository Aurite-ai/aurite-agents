"""
Manages the multi-turn conversation loop for an Agent.
"""

import json
import logging
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Optional, cast

from anthropic.types import MessageParam
from pydantic import ValidationError

from ...config.config_models import AgentConfig, LLMConfig

# Project imports
from ...host.host import MCPHost

# from ..llm.base_client import BaseLLM # Moved to TYPE_CHECKING
from .agent_models import (
    AgentExecutionResult,
    AgentOutputContentBlock,
    AgentOutputMessage,
)
from .agent_turn_processor import AgentTurnProcessor

if TYPE_CHECKING:
    from aurite.components.llm.base_client import BaseLLM  # Moved here

    pass

logger = logging.getLogger(__name__)


class Agent:
    def __init__(
        self,
        config: AgentConfig,
        llm_client: "BaseLLM",  # Changed to string literal
        host_instance: MCPHost,
        initial_messages: List[MessageParam],
        system_prompt_override: Optional[str] = None,
        llm_config_for_override: Optional[LLMConfig] = None,
    ):
        self.config = config
        self.llm = llm_client
        self.host = host_instance
        self.system_prompt_override = system_prompt_override
        self.llm_config_for_override = llm_config_for_override
        # The conversation history now exclusively stores AgentOutputMessage objects.
        self.conversation_history: List[AgentOutputMessage] = [
            AgentOutputMessage.model_validate(message) for message in initial_messages
        ]
        self.final_response: Optional[AgentOutputMessage] = None
        self.tool_uses_in_last_turn: List[Dict[str, Any]] = []
        logger.debug(f"Agent '{self.config.name or 'Unnamed'}' initialized.")

    async def run_conversation(self) -> AgentExecutionResult:
        logger.debug(f"Agent starting run for agent '{self.config.name or 'Unnamed'}'.")
        effective_system_prompt = (
            self.system_prompt_override
            or self.config.system_prompt
            or "You are a helpful assistant."
        )
        tools_data = self.host.get_formatted_tools(agent_config=self.config)
        max_iterations = self.config.max_iterations or 10
        current_iteration = 0

        while current_iteration < max_iterations:
            # Create the API-compliant message list for the LLM call in each turn.
            current_messages_for_run: List[MessageParam] = [
                cast(MessageParam, msg.to_api_message_param())
                for msg in self.conversation_history
            ]
            current_iteration += 1
            logger.debug(f"Conversation loop iteration {current_iteration}")

            turn_processor = AgentTurnProcessor(
                config=self.config,
                llm_client=self.llm,
                host_instance=self.host,
                current_messages=current_messages_for_run,
                tools_data=tools_data,
                effective_system_prompt=effective_system_prompt,
                llm_config_for_override=self.llm_config_for_override,
            )

            try:
                (
                    turn_final_response,
                    turn_tool_results_params,
                    is_final_turn,
                ) = await turn_processor.process_turn()

                assistant_message_this_turn = turn_processor.get_last_llm_response()

                if assistant_message_this_turn:
                    # The full AgentOutputMessage is the source of truth.
                    self.conversation_history.append(assistant_message_this_turn)

                if turn_tool_results_params:
                    # Convert tool result dicts (MessageParam) to AgentOutputMessage objects
                    # before adding them to the history.
                    self.conversation_history.extend(
                        [
                            AgentOutputMessage.model_validate(result)
                            for result in turn_tool_results_params
                        ]
                    )
                    # Store tool uses from the turn processor
                    self.tool_uses_in_last_turn = (
                        turn_processor.get_tool_uses_this_turn()
                    )

                if is_final_turn:
                    self.final_response = turn_final_response
                    break
                elif not turn_tool_results_params and not is_final_turn:
                    logger.warning(
                        "Schema validation failed. Preparing correction message."
                    )
                    if self.config.config_validation_schema:
                        correction_message_content = f"""Your response must be a valid JSON object matching this schema:
{json.dumps(self.config.config_validation_schema, indent=2)}

Please correct your previous response to conform to the schema."""
                        correction_message_param: MessageParam = {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": correction_message_content}
                            ],
                        }
                        # Convert the correction message to an AgentOutputMessage before
                        # adding it to the history.
                        self.conversation_history.append(
                            AgentOutputMessage.model_validate(correction_message_param)
                        )
                    else:
                        # If no schema, treat the invalid response as final
                        # Use the full object obtained from the processor
                        self.final_response = assistant_message_this_turn
                        break
            except Exception as e:
                error_msg = f"Error during conversation turn {current_iteration}: {type(e).__name__}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return self._prepare_agent_result(execution_error=error_msg)

        if current_iteration >= max_iterations and self.final_response is None:
            logger.warning(f"Reached max iterations ({max_iterations}). Aborting loop.")
            # Find the last AgentOutputMessage in the history
            last_assistant_message_obj = next(
                (
                    msg
                    for msg in reversed(self.conversation_history)
                    if isinstance(msg, AgentOutputMessage)
                ),
                None,
            )
            if last_assistant_message_obj:
                # It's already the correct type
                self.final_response = last_assistant_message_obj
            else:
                logger.warning(
                    "Could not find a final assistant message in history for max iterations fallback."
                )
                self.final_response = (
                    None  # Ensure it's None if no suitable message found
                )

        logger.debug(f"Agent finished run for agent '{self.config.name or 'Unnamed'}'.")
        return self._prepare_agent_result(execution_error=None)

    def _prepare_agent_result(
        self, execution_error: Optional[str] = None
    ) -> AgentExecutionResult:
        logger.debug("Preparing final agent execution result...")

        # The conversation history is now guaranteed to contain only AgentOutputMessage objects,
        # so no parsing is needed.
        output_dict_for_validation = {
            "conversation": self.conversation_history,
            "final_response": self.final_response,
            "tool_uses_in_final_turn": self.tool_uses_in_last_turn,
            "error": execution_error,
        }
        try:
            agent_result = AgentExecutionResult.model_validate(
                output_dict_for_validation
            )
            if execution_error and not agent_result.error:
                agent_result.error = execution_error
            elif not execution_error and agent_result.error:
                logger.info(
                    f"AgentExecutionResult validation failed: {agent_result.error}"
                )
            return agent_result
        except ValidationError as e:
            error_msg = f"Failed to validate final AgentExecutionResult: {e}"
            logger.error(error_msg, exc_info=True)
            final_error_message = (
                f"{execution_error}\n{error_msg}" if execution_error else error_msg
            )
            try:
                return AgentExecutionResult(
                    conversation=self.conversation_history,
                    final_response=self.final_response,
                    tool_uses_in_final_turn=self.tool_uses_in_last_turn,
                    error=final_error_message,
                )
            except Exception as fallback_e:
                logger.error(
                    f"Failed to create even a fallback AgentExecutionResult: {fallback_e}"
                )
                return AgentExecutionResult(
                    conversation=[],
                    final_response=None,
                    tool_uses_in_final_turn=self.tool_uses_in_last_turn,
                    error=final_error_message
                    + f"\nAdditionally, fallback result creation failed: {fallback_e}",
                )
        except Exception as e:
            error_msg = f"Unexpected error during final AgentExecutionResult preparation/validation: {type(e).__name__}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            final_error_message = (
                f"{execution_error}\n{error_msg}" if execution_error else error_msg
            )
            return AgentExecutionResult(
                conversation=[],
                final_response=None,
                tool_uses_in_final_turn=self.tool_uses_in_last_turn,
                error=final_error_message,
            )

    async def stream_conversation(self) -> AsyncGenerator[Dict[str, Any], None]:
        logger.info(
            f"AGENT: Entered stream_conversation for agent '{self.config.name or 'Unnamed'}'"
        )  # ADDED
        logger.debug(
            f"Agent starting STREAMING run for agent '{self.config.name or 'Unnamed'}'."
        )
        effective_system_prompt = (
            self.system_prompt_override
            or self.config.system_prompt
            or "You are a helpful assistant."
        )
        tools_data = self.host.get_formatted_tools(agent_config=self.config)
        max_iterations = self.config.max_iterations or 10
        current_iteration = 0

        current_assistant_message_content_blocks_for_history_dicts: List[
            Dict[str, Any]
        ] = []
        assistant_message_object_this_turn: Optional[AgentOutputMessage] = None

        while current_iteration < max_iterations:
            current_iteration += 1
            logger.debug(f"Streaming conversation loop iteration {current_iteration}")

            # Create the API-compliant message list for the LLM call in each turn.
            messages_for_this_llm_call: List[MessageParam] = [
                cast(MessageParam, msg.to_api_message_param())
                for msg in self.conversation_history
            ]

            turn_processor = AgentTurnProcessor(
                config=self.config,
                llm_client=self.llm,
                host_instance=self.host,
                current_messages=messages_for_this_llm_call,
                tools_data=tools_data,
                effective_system_prompt=effective_system_prompt,
                llm_config_for_override=self.llm_config_for_override,
            )

            streamed_assistant_message_id: Optional[str] = None
            streamed_assistant_model: Optional[str] = None
            streamed_assistant_role: str = "assistant"
            streamed_assistant_usage: Optional[Dict[str, int]] = None
            llm_turn_stop_reason: Optional[str] = None

            buffered_tool_results_for_this_turn: List[MessageParam] = []

            try:
                logger.info(
                    f"AGENT: About to enter turn_processor.stream_turn_response() loop for iteration {current_iteration}"
                )  # ADDED
                async for event in turn_processor.stream_turn_response():
                    yield event
                    event_type = event.get("event_type")
                    event_data = event.get("data", {})

                    if event_type == "message_start":
                        streamed_assistant_message_id = event_data.get("message_id")
                        streamed_assistant_model = event_data.get("model")
                        streamed_assistant_role = event_data.get("role", "assistant")
                        current_assistant_message_content_blocks_for_history_dicts = []
                        assistant_message_object_this_turn = None

                    elif event_type == "text_block_start":
                        found = False
                        for (
                            block
                        ) in current_assistant_message_content_blocks_for_history_dicts:
                            if block.get("index") == event_data.get("index"):
                                found = True
                                break
                        if not found:
                            current_assistant_message_content_blocks_for_history_dicts.append(
                                {
                                    "type": "text",
                                    "text": "",
                                    "index": event_data.get("index"),
                                }
                            )
                    elif event_type == "text_delta":
                        found_block = False
                        for (
                            block
                        ) in current_assistant_message_content_blocks_for_history_dicts:
                            if (
                                block.get("index") == event_data.get("index")
                                and block.get("type") == "text"
                            ):
                                block["text"] = block.get("text", "") + event_data.get(
                                    "text_chunk", ""
                                )
                                found_block = True
                                break
                        if not found_block:
                            current_assistant_message_content_blocks_for_history_dicts.append(
                                {
                                    "type": "text",
                                    "text": event_data.get("text_chunk", ""),
                                    "index": event_data.get("index"),
                                }
                            )
                    elif event_type == "thinking_block_start":
                        found = False
                        for (
                            block
                        ) in current_assistant_message_content_blocks_for_history_dicts:
                            if block.get("index") == event_data.get("index"):
                                found = True
                                break
                        if not found:
                            current_assistant_message_content_blocks_for_history_dicts.append(
                                {
                                    "type": "text",
                                    "text": "",
                                    "index": event_data.get("index"),
                                }
                            )
                    elif event_type == "tool_use_start":
                        current_assistant_message_content_blocks_for_history_dicts.append(
                            {
                                "type": "tool_use",
                                "id": event_data.get("tool_id"),
                                "name": event_data.get("tool_name"),
                                "input": {},
                                "index": event_data.get("index"),
                            }
                        )
                    elif event_type == "tool_use_input_complete":
                        tool_id = event_data.get("tool_id")
                        final_input = event_data.get("input")
                        for (
                            block
                        ) in current_assistant_message_content_blocks_for_history_dicts:
                            if (
                                block.get("type") == "tool_use"
                                and block.get("id") == tool_id
                            ):
                                block["input"] = final_input
                                break

                    elif (
                        event_type == "tool_result"
                        or event_type == "tool_execution_error"
                    ):
                        tool_use_id = event_data.get("tool_use_id")
                        is_error = (
                            event_type == "tool_execution_error"
                            or event_data.get("is_error", False)
                        )
                        content_data = (
                            event_data.get("output")
                            if not is_error
                            else event_data.get("error_message", "Unknown error")
                        )

                        tool_result_content_list: List[Dict[str, Any]]
                        if isinstance(content_data, str):
                            tool_result_content_list = [
                                {"type": "text", "text": content_data}
                            ]
                        elif isinstance(content_data, list):
                            tool_result_content_list = content_data
                        else:
                            tool_result_content_list = [
                                {"type": "text", "text": str(content_data)}
                            ]

                        tool_result_param: MessageParam = cast(
                            MessageParam,
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": tool_use_id,
                                        "content": tool_result_content_list,
                                        "is_error": is_error,
                                    }
                                ],
                            },
                        )
                        buffered_tool_results_for_this_turn.append(tool_result_param)

                    elif event_type == "message_delta":
                        if "stop_reason" in event_data:
                            llm_turn_stop_reason = event_data.get("stop_reason")
                        if "output_tokens" in event_data:
                            if streamed_assistant_usage is None:
                                streamed_assistant_usage = {}
                            streamed_assistant_usage["output_tokens"] = event_data.get(
                                "output_tokens"
                            )

                    elif event_type == "llm_call_completed":
                        llm_turn_stop_reason = event_data.get("stop_reason")
                        logger.debug(
                            f"Agent: LLM call completed with stop_reason: {llm_turn_stop_reason}"
                        )

                        if streamed_assistant_message_id:
                            validated_content_blocks_for_model = []
                            # Use original_llm_content_blocks from the message_stop event if available,
                            # as it contains the fully formed blocks including tool inputs.
                            original_llm_content_blocks = (
                                event_data.get("original_event_data", {})
                                .get("raw_message_stop_event", {})
                                .get("message", {})
                                .get("content", [])
                            )

                            source_blocks_for_validation = current_assistant_message_content_blocks_for_history_dicts
                            if (
                                original_llm_content_blocks
                            ):  # Prefer original blocks if present
                                source_blocks_for_validation = (
                                    original_llm_content_blocks
                                )
                                # If using original_llm_content_blocks, ensure they are dicts, not Pydantic models yet
                                source_blocks_for_validation = [
                                    block.model_dump(mode="json")
                                    if hasattr(block, "model_dump")
                                    else block
                                    for block in source_blocks_for_validation
                                ]

                            for block_dict_raw in source_blocks_for_validation:
                                try:
                                    # Ensure 'input' is present for tool_use, even if empty, before validation
                                    # This is crucial if source_blocks_for_validation is from current_assistant_message_content_blocks_for_history_dicts
                                    if (
                                        block_dict_raw.get("type") == "tool_use"
                                        and "input" not in block_dict_raw
                                    ):
                                        # Try to find it from tool_use_input_complete if it was missed
                                        # This part is tricky; ideally, current_assistant_message_content_blocks_for_history_dicts
                                        # should have the input updated by tool_use_input_complete.
                                        # If original_llm_content_blocks are used, they should have the input.
                                        block_dict_raw[
                                            "input"
                                        ] = {}  # Default if not found

                                    validated_content_blocks_for_model.append(
                                        AgentOutputContentBlock.model_validate(
                                            block_dict_raw
                                        )
                                    )
                                except Exception as e_val:
                                    logger.error(
                                        f"Error validating block for AgentOutputMessage: {block_dict_raw}, error: {e_val}"
                                    )
                                    validated_content_blocks_for_model.append(
                                        AgentOutputContentBlock(
                                            type="error",
                                            text=f"Invalid block: {str(block_dict_raw)}",
                                        )
                                    )

                            assistant_message_object_this_turn = AgentOutputMessage(
                                id=streamed_assistant_message_id,
                                model=streamed_assistant_model
                                or self.config.model
                                or "unknown_stream_model",
                                role=streamed_assistant_role,
                                content=validated_content_blocks_for_model,
                                stop_reason=llm_turn_stop_reason,
                                stop_sequence=None,  # Explicitly set to None
                                usage=streamed_assistant_usage,
                            )
                            # The full AgentOutputMessage is the source of truth.
                            self.conversation_history.append(
                                assistant_message_object_this_turn
                            )

                        if buffered_tool_results_for_this_turn:
                            # Convert tool result dicts to AgentOutputMessage objects
                            self.conversation_history.extend(
                                [
                                    AgentOutputMessage.model_validate(result)
                                    for result in buffered_tool_results_for_this_turn
                                ]
                            )
                            buffered_tool_results_for_this_turn = []

                        if llm_turn_stop_reason != "tool_use":
                            logger.debug(
                                f"Agent: Final response indicated by LLM stop_reason: {llm_turn_stop_reason}. Breaking conversation loop."
                            )
                            self.final_response = assistant_message_object_this_turn
                            break
                        else:
                            logger.debug(
                                "Agent: LLM stop_reason was 'tool_use'. Agent loop continues for next turn."
                            )
                            current_assistant_message_content_blocks_for_history_dicts = []
                            streamed_assistant_message_id = None
                            streamed_assistant_model = None
                            streamed_assistant_usage = None
                            assistant_message_object_this_turn = None

            except Exception as e:
                error_msg = f"Error during streaming conversation turn {current_iteration}: {type(e).__name__}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                yield {
                    "event_type": "error",
                    "data": {"message": error_msg, "turn": current_iteration},
                }
                break

            if self.final_response or (
                llm_turn_stop_reason and llm_turn_stop_reason != "tool_use"
            ):
                break

            if current_iteration >= max_iterations:
                logger.warning(
                    f"Reached max iterations ({max_iterations}) in streaming. Aborting."
                )
                if not self.final_response and assistant_message_object_this_turn:
                    self.final_response = assistant_message_object_this_turn
                break

        logger.info(
            f"Agent finished STREAMING run for agent '{self.config.name or 'Unnamed'}'."
        )
        final_stop_reason_for_stream = "unknown"
        if self.final_response and self.final_response.stop_reason:
            final_stop_reason_for_stream = self.final_response.stop_reason
        elif current_iteration >= max_iterations:
            final_stop_reason_for_stream = "max_iterations_reached"

        yield {
            "event_type": "stream_end",
            "data": {"reason": final_stop_reason_for_stream},
        }
