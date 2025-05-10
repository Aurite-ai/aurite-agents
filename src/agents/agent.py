"""
Manages the multi-turn conversation loop for an Agent.
"""

import logging
import json
from typing import (
    Dict,
    Any,
    Optional,
    List,
    TYPE_CHECKING,
    AsyncGenerator,
)  # Added AsyncGenerator

from pydantic import ValidationError
from anthropic.types import MessageParam

# Project imports
from ..host.host import MCPHost
from .agent_models import AgentExecutionResult, AgentOutputMessage
from .agent_turn_processor import AgentTurnProcessor

# from .agent import Agent # No longer need the old Agent class import
from ..config.config_models import AgentConfig, LLMConfig  # Import necessary configs
from ..llm.base_client import BaseLLM  # Import BaseLLM for type hint

# Type hinting imports
if TYPE_CHECKING:
    pass  # Add other necessary type hints here if needed

logger = logging.getLogger(__name__)


# _serialize_content_blocks function removed as it's deemed redundant here.


class Agent:  # Renamed from ConversationManager
    """
    Represents an agent capable of executing tasks using an MCP Host.
    Manages the multi-turn conversation flow, including message history,
    loop iterations, and interactions with the AgentTurnProcessor and LLM.
    """

    def __init__(
        self,
        config: AgentConfig,  # New parameter
        llm_client: BaseLLM,  # New parameter
        host_instance: MCPHost,
        initial_messages: List[MessageParam],
        system_prompt_override: Optional[str] = None,
        llm_config_for_override: Optional[LLMConfig] = None,  # New parameter
    ):
        """
        Initializes the Agent.

        Args:
            config: The AgentConfig object for this agent.
            llm_client: An initialized instance of a BaseLLM subclass.
            host_instance: The MCPHost instance for tool execution.
            initial_messages: The starting list of messages for the conversation.
            system_prompt_override: Optional system prompt to override the agent's default.
            llm_config_for_override: Optional LLMConfig to pass to the turn processor for LLM calls.
        """
        self.config = config  # Store config directly
        self.llm = llm_client  # Store LLM client directly
        self.host = host_instance
        self.messages = list(initial_messages)  # Start with a copy
        self.system_prompt_override = system_prompt_override
        self.llm_config_for_override = llm_config_for_override  # Store override config
        # Initial messages are already dicts, no need for serialization here.
        self.conversation_history: List[Dict[str, Any]] = list(initial_messages)
        self.final_response: Optional[AgentOutputMessage] = None
        self.tool_uses_in_last_turn: List[Dict[str, Any]] = []
        logger.debug(
            f"Agent '{self.config.name or 'Unnamed'}' initialized."
        )  # Updated log

    async def run_conversation(self) -> AgentExecutionResult:
        """
        Executes the conversation loop until a final response is reached,
        max iterations are hit, or an error occurs.

        Returns:
            An AgentExecutionResult containing the full conversation and outcome.
        """
        logger.debug(
            f"Agent starting run for agent '{self.config.name or 'Unnamed'}'."  # Use self.config
        )

        # Determine effective system prompt for the turn processor
        effective_system_prompt = (
            self.system_prompt_override
            or self.config.system_prompt  # Use self.config
            or "You are a helpful assistant."
        )

        # Prepare tools (delegated to host)
        tools_data = self.host.get_formatted_tools(
            agent_config=self.config
        )  # Use self.config
        logger.debug(f"Formatted tools for LLM: {[t['name'] for t in tools_data]}")

        max_iterations = self.config.max_iterations or 10  # Use self.config
        current_iteration = 0

        while current_iteration < max_iterations:
            current_iteration += 1
            logger.debug(f"Conversation loop iteration {current_iteration}")

            # Instantiate and run the turn processor
            turn_processor = AgentTurnProcessor(
                config=self.config,  # Use self.config
                llm_client=self.llm,  # Use self.llm
                host_instance=self.host,
                current_messages=list(self.messages),  # Pass copy for this turn
                tools_data=tools_data,
                effective_system_prompt=effective_system_prompt,
                llm_config_for_override=self.llm_config_for_override,  # Pass override config
            )

            try:
                # Process the turn
                (
                    turn_final_response,
                    turn_tool_results_params,
                    is_final_turn,
                ) = await turn_processor.process_turn()

                # --- Update state based on turn processor results ---
                assistant_message_this_turn = turn_processor.get_last_llm_response()

                if assistant_message_this_turn:
                    # Append assistant message dict to conversation_history log
                    self.conversation_history.append(
                        assistant_message_this_turn.model_dump(mode="json")
                    )
                    # Convert assistant message content to MessageParam format for the *next* LLM call
                    next_turn_content_blocks = []
                    if assistant_message_this_turn.content:
                        for block in assistant_message_this_turn.content:
                            if block.type == "text" and block.text is not None:
                                next_turn_content_blocks.append(
                                    {"type": "text", "text": block.text}
                                )
                            elif (
                                block.type == "tool_use"
                                and block.id
                                and block.name
                                and block.input is not None
                            ):
                                # This is the assistant requesting a tool use
                                next_turn_content_blocks.append(
                                    {
                                        "type": "tool_use",
                                        "id": block.id,
                                        "name": block.name,
                                        "input": block.input,
                                    }
                                )
                    # Append the assistant message (in MessageParam format) to the list for the next LLM call
                    self.messages.append(
                        {"role": "assistant", "content": next_turn_content_blocks}
                    )  # type: ignore[dict-item]

                if (
                    turn_tool_results_params
                ):  # If the processor returned tool results (List[MessageParam])
                    # turn_tool_results_params is already a list of MessageParam dicts,
                    # typically [{"role": "user", "content": [ToolResultBlockParam, ...]}, ...]
                    # Append these messages directly to the list for the next LLM call.
                    self.messages.extend(turn_tool_results_params)

                    # For self.conversation_history (log of interaction)
                    # Append the same message dicts directly to the history log.
                    # Ensure the content within these dicts is serializable if complex.
                    for tool_result_msg_param in turn_tool_results_params:
                        # Use _serialize_content_blocks on the *inner* content if needed,
                        # but the message structure itself is already a dict.
                        # Assuming tool_result_msg_param is already a dict like:
                        # {"role": "user", "content": [{"type": "tool_result", ...}]}
                        # The tool_result_msg_param is already a dictionary in the correct format
                        # (e.g., {"role": "user", "content": [{"type": "tool_result", ...}]})
                        # and its inner content should also be JSON-serializable dicts/primitives
                        # as prepared by ToolManager.create_tool_result_blocks.
                        # No need for _serialize_content_blocks here.
                        self.conversation_history.append(tool_result_msg_param)

                    # Update tool uses if tool results were processed this turn
                    self.tool_uses_in_last_turn = (
                        turn_processor.get_tool_uses_this_turn()
                    )

                # --- Decide next action based on turn results ---
                if turn_tool_results_params:
                    # Case 1: Tool results were returned. Loop should continue.
                    logger.debug("Tool results processed. Continuing conversation.")
                    # No break, loop continues naturally

                elif is_final_turn:
                    # Case 2: It's the final turn (and no tool results).
                    self.final_response = (
                        turn_final_response  # This should be the validated response
                    )
                    if self.final_response is None:
                        # Should not happen if TurnProcessor logic is correct for final turn
                        logger.error(
                            "Processor indicated final turn but returned None response. Breaking loop."
                        )
                    else:
                        logger.debug("Final response received. Breaking loop.")
                    break  # Exit the loop

                else:
                    # Case 3: No tool results AND not the final turn. This implies schema validation failed.
                    logger.warning(
                        "Schema validation failed. Preparing correction message."
                    )
                    if self.config.config_validation_schema:  # Use self.config
                        correction_message_content = f"""Your response must be a valid JSON object matching this schema:
{json.dumps(self.config.config_validation_schema, indent=2)}

Please correct your previous response to conform to the schema."""
                        correction_content_blocks = [
                            {"type": "text", "text": correction_message_content}
                        ]
                        correction_message_param: MessageParam = {
                            "role": "user",
                            "content": correction_content_blocks,
                        }
                        self.messages.append(correction_message_param)
                        correction_history_entry = {
                            "role": "user",
                            "content": correction_content_blocks,
                        }
                        self.conversation_history.append(correction_history_entry)
                        # Loop continues naturally to allow LLM to correct
                    else:
                        # Should not happen if TurnProcessor logic is correct
                        logger.error(
                            "Schema validation failed signal received, but no schema found in config. Breaking loop."
                        )
                        self.final_response = assistant_message_this_turn  # Use potentially invalid response
                        break  # Exit loop with potentially invalid response

            # --- End of loop iteration ---

            except Exception as e:
                error_msg = f"Error during conversation turn {current_iteration}: {type(e).__name__}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                # Return error result immediately
                return self._prepare_agent_result(execution_error=error_msg)

        # --- Loop finished (max iterations or final response) ---
        if current_iteration >= max_iterations and self.final_response is None:
            logger.warning(f"Reached max iterations ({max_iterations}). Aborting loop.")
            # Try to use the last assistant message from history as final response, if available
            last_assistant_message_dict = next(
                (
                    msg
                    for msg in reversed(self.conversation_history)
                    if msg.get("role") == "assistant"
                ),
                None,
            )
            if last_assistant_message_dict:
                try:
                    # Attempt to validate the last message as AgentOutputMessage
                    self.final_response = (
                        AgentOutputMessage.model_validate(  # Set self.final_response
                            last_assistant_message_dict
                        )
                    )
                    logger.debug(
                        "Using last assistant message as final response due to max iterations."
                    )
                except Exception as val_err_max_iter:
                    logger.error(
                        f"Could not validate last assistant message for max iterations fallback: {val_err_max_iter}"
                    )
                    self.final_response = None  # Ensure it's None if validation fails
            else:
                self.final_response = (
                    None  # Ensure it's None if no assistant message found
                )

        logger.info(
            f"Agent finished run for agent '{self.config.name or 'Unnamed'}'."  # Use self.config
        )
        return self._prepare_agent_result(execution_error=None)

    def _prepare_agent_result(
        self, execution_error: Optional[str] = None
    ) -> AgentExecutionResult:
        """
        Constructs and validates the final AgentExecutionResult.
        (Adapted from Agent._prepare_agent_result)
        """
        logger.debug("Preparing final agent execution result...")

        # Prepare final_response for return (it's already an AgentOutputMessage instance or None)
        # If it's an instance, AgentExecutionResult validation will handle its dumping if necessary,
        # or it can accept the model instance directly.
        # Forcing it to dict here, then having AgentExecutionResult re-validate from dict is fine.
        return_final_response_model_or_dict = None
        if self.final_response:  # self.final_response is AgentOutputMessage or None
            try:
                # Pydantic models can often be nested, so passing the instance might be okay,
                # but model_dump ensures it's a dict if AgentExecutionResult expects dicts.
                return_final_response_model_or_dict = (
                    self.final_response
                )  # Pass as instance
            except (
                Exception
            ) as e:  # Should not fail if self.final_response is a valid Pydantic model
                logger.error(
                    f"Failed to process final_response (AgentOutputMessage) for return: {e}",
                    exc_info=True,
                )
                execution_error = (
                    execution_error or f"Processing of final_response failed: {str(e)}"
                )
                return_final_response_model_or_dict = None

        # Construct the dictionary for AgentExecutionResult validation.
        # self.conversation_history is already List[Dict[str, Any]]
        # These dicts should be directly parsable by AgentOutputMessage within AgentExecutionResult.
        output_dict_for_validation = {
            "conversation": self.conversation_history,  # Pass the list of dicts directly
            "final_response": return_final_response_model_or_dict,  # Pass model instance or None
            "tool_uses_in_final_turn": self.tool_uses_in_last_turn,
            "error": execution_error,
        }

        try:
            # Validate the final structure. Pydantic will attempt to convert
            # items in 'conversation' (dicts) to AgentOutputMessage instances,
            # and 'final_response' (AgentOutputMessage instance or None) as needed.
            agent_result = AgentExecutionResult.model_validate(
                output_dict_for_validation
            )

            # Ensure error consistency
            if execution_error and not agent_result.error:
                logger.warning(
                    "Execution error was provided but not set in validated AgentExecutionResult. Overriding."
                )
                # This might indicate an issue if model_validate clears a pre-existing error.
                # However, if execution_error is from a different source than model validation,
                # it's correct to ensure it's part of the final result.
                agent_result.error = execution_error
            elif not execution_error and agent_result.error:
                # If model_validate itself found an error, that should be the primary error.
                logger.info(
                    f"AgentExecutionResult validation failed: {agent_result.error}"
                )

            return agent_result
        except ValidationError as e:
            # This is the primary path for validation failures of the overall structure.
            error_msg = f"Failed to validate final AgentExecutionResult: {e}"
            logger.error(error_msg, exc_info=True)

            # Construct a fallback result.
            # Try to include as much valid information as possible.
            # For conversation, use the raw history dicts as they were before validation attempt.
            # This avoids trying to re-validate potentially problematic individual messages here.
            final_error_message = (
                f"{execution_error}\n{error_msg}" if execution_error else error_msg
            )

            # Create a "best-effort" AgentExecutionResult.
            # Pydantic might still raise an error here if fundamental types are wrong,
            # but we provide the raw data hoping some parts are acceptable.
            try:
                return AgentExecutionResult(
                    conversation=[
                        AgentOutputMessage.model_validate(item)
                        for item in self.conversation_history
                        if isinstance(item, dict)
                    ],  # Try to validate items individually for the error response
                    final_response=self.final_response,  # Use the original final_response instance
                    tool_uses_in_final_turn=self.tool_uses_in_last_turn,
                    error=final_error_message,
                )
            except Exception as fallback_e:
                logger.error(
                    f"Failed to create even a fallback AgentExecutionResult: {fallback_e}"
                )
                # Absolute fallback if even individual message validation fails
                return AgentExecutionResult(
                    conversation=[],
                    final_response=None,
                    tool_uses_in_final_turn=self.tool_uses_in_last_turn,
                    error=final_error_message
                    + f"\nAdditionally, fallback result creation failed: {fallback_e}",
                )
        except Exception as e:
            # Catch any other unexpected error during the final validation.
            error_msg = f"Unexpected error during final AgentExecutionResult preparation/validation: {type(e).__name__}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            final_error_message = (
                f"{execution_error}\n{error_msg}" if execution_error else error_msg
            )
            return AgentExecutionResult(
                conversation=[],  # Safest to return empty if something truly unexpected happened
                final_response=None,
                tool_uses_in_final_turn=self.tool_uses_in_last_turn,
                error=final_error_message,
            )

    async def stream_conversation(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Executes the conversation loop, streaming events (text, tool calls, tool results)
        as they happen. This version is designed for streaming and will differ from
        run_conversation in how it handles turns and accumulates history for the stream.

        Yields:
            Dict[str, Any]: Standardized event dictionaries suitable for SSE.
        """
        logger.debug(
            f"Agent starting STREAMING run for agent '{self.config.name or 'Unnamed'}'."
        )

        effective_system_prompt = (
            self.system_prompt_override
            or self.config.system_prompt
            or "You are a helpful assistant."
        )
        tools_data = self.host.get_formatted_tools(agent_config=self.config)

        # For streaming, we manage messages turn by turn more explicitly
        current_turn_messages = list(
            self.messages
        )  # Start with initial messages for the first turn

        max_iterations = self.config.max_iterations or 10
        current_iteration = 0

        # Accumulators for the current assistant message being built from stream
        # These would be reset or managed if the agent makes multiple LLM calls in a single "stream_conversation"
        # For now, assuming one primary LLM interaction per call to stream_conversation,
        # which might involve multiple tool uses.

        # This list will store the content blocks for the *current* assistant message being streamed
        # It's used to reconstruct the full assistant message for history *after* the stream for that message is done.
        current_assistant_message_content_blocks_for_history: List[Dict[str, Any]] = []
        # Removed Agent-level accumulation for tool input JSON, as AgentTurnProcessor handles it.

        while current_iteration < max_iterations:
            current_iteration += 1
            logger.debug(f"Streaming conversation loop iteration {current_iteration}")

            turn_processor = AgentTurnProcessor(
                config=self.config,
                llm_client=self.llm,
                host_instance=self.host,
                current_messages=list(
                    current_turn_messages
                ),  # Messages for this specific LLM call
                tools_data=tools_data,
                effective_system_prompt=effective_system_prompt,
                llm_config_for_override=self.llm_config_for_override,
            )

            # This will be the full assistant message once its parts are streamed
            streamed_assistant_message_id: Optional[str] = None
            streamed_assistant_model: Optional[str] = None
            streamed_assistant_role: str = "assistant"  # Default
            streamed_assistant_stop_reason: Optional[str] = None
            streamed_assistant_usage: Optional[Dict[str, int]] = None

            try:
                async for event in turn_processor.stream_turn_response():
                    yield event  # Yield every event from turn_processor to the caller (facade)

                    # --- Logic to update Agent's internal state based on stream ---
                    event_type = event.get("event_type")
                    event_data = event.get("data", {})

                    if event_type == "message_start":
                        streamed_assistant_message_id = event_data.get("message_id")
                        streamed_assistant_model = event_data.get("model")
                        streamed_assistant_role = event_data.get("role", "assistant")
                        # Input tokens are for this specific call
                        # We don't accumulate usage across multiple LLM calls within stream_conversation here yet

                    elif event_type == "text_block_start":
                        # If it's the first content block for this assistant message, initialize
                        if not any(
                            b.get("index") == event_data.get("index")
                            for b in current_assistant_message_content_blocks_for_history
                            if "index" in b
                        ):
                            current_assistant_message_content_blocks_for_history.append(
                                {
                                    "type": "text",
                                    "text": "",
                                    "index": event_data.get("index"),
                                }
                            )

                    elif event_type == "text_delta":
                        # Find the text block by index and append
                        for (
                            block
                        ) in current_assistant_message_content_blocks_for_history:
                            if (
                                block.get("index") == event_data.get("index")
                                and block["type"] == "text"
                            ):
                                block["text"] += event_data.get("text_chunk", "")
                                break

                    elif event_type == "tool_use_start":
                        tool_id = event_data.get("tool_id")
                        tool_name = event_data.get("tool_name")
                        index = event_data.get("index")
                        current_assistant_message_content_blocks_for_history.append(
                            {
                                "type": "tool_use",
                                "id": tool_id,
                                "name": tool_name,
                                "input": {},
                                "index": index,
                            }
                        )
                        # pending_tool_calls_info was removed, AgentTurnProcessor handles accumulation.

                    elif event_type == "tool_use_input_delta":
                        # Agent.stream_conversation no longer accumulates tool_use_input_delta.
                        # It relies on AgentTurnProcessor to handle tool execution and yield tool_result.
                        # This event is still yielded by TurnProcessor and forwarded by Agent.
                        pass

                    elif event_type == "content_block_stop":
                        # Agent.stream_conversation no longer finalizes tool input here.
                        # AgentTurnProcessor handles parsing and execution upon content_block_stop for a tool_use.
                        # This event is still yielded by TurnProcessor and forwarded by Agent.
                        # We might need to update current_assistant_message_content_blocks_for_history
                        # if the content_block_stop finalizes a text block, but that's usually implicit.
                        pass

                    elif event_type == "tool_result":
                        # A tool result event was yielded by the turn_processor.
                        # This means a tool was executed. We need to add this to `current_turn_messages`
                        # for the *next* LLM interaction if the loop continues.
                        # And also add to conversation_history.
                        tool_use_id = event_data.get("tool_use_id")
                        tool_output_content = event_data.get(
                            "output"
                        )  # This is the raw content from tool

                        # Create the MessageParam structure for tool result
                        # The content of a tool_result can be a list of blocks or a simple string.
                        # Assuming host.tools.create_tool_result_blocks handles this.
                        # For simplicity, let's assume tool_result_content is directly usable or a string.
                        # If it's complex, it should be a list of content blocks.
                        tool_result_block_param_content: List[Dict[str, Any]]
                        if isinstance(tool_output_content, str):
                            tool_result_block_param_content = [
                                {"type": "text", "text": tool_output_content}
                            ]
                        elif isinstance(
                            tool_output_content, list
                        ):  # Expecting list of content blocks
                            tool_result_block_param_content = tool_output_content
                        else:  # Fallback for other types, wrap as text
                            tool_result_block_param_content = [
                                {"type": "text", "text": str(tool_output_content)}
                            ]

                        tool_result_message_param: MessageParam = {
                            "role": "user",  # Tool results are submitted as user role
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_id,
                                    "content": tool_result_block_param_content,
                                    "is_error": event_data.get(
                                        "is_error", False
                                    ),  # Pass along if it's an error result
                                }
                            ],
                        }
                        current_turn_messages.append(tool_result_message_param)
                        self.conversation_history.append(
                            dict(tool_result_message_param)
                        )  # Add to log

                    elif event_type == "tool_execution_error":
                        # Similar to tool_result, but for errors
                        tool_use_id = event_data.get("tool_use_id")
                        error_message = event_data.get(
                            "error_message", "Unknown tool execution error"
                        )
                        tool_error_message_param: MessageParam = {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_id,
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": f"Error: {error_message}",
                                        }
                                    ],  # Simplified error content
                                    "is_error": True,
                                }
                            ],
                        }
                        current_turn_messages.append(tool_error_message_param)
                        self.conversation_history.append(dict(tool_error_message_param))

                    elif event_type == "message_delta":  # From Anthropic stream
                        if (
                            "stop_reason" in event_data
                        ):  # Check if delta contains stop_reason
                            streamed_assistant_stop_reason = event_data.get(
                                "stop_reason"
                            )
                        if "output_tokens" in event_data:  # Check for usage
                            if streamed_assistant_usage is None:
                                streamed_assistant_usage = {}
                            streamed_assistant_usage["output_tokens"] = event_data.get(
                                "output_tokens"
                            )

                    elif event_type == "stream_end":
                        # The LLM part of the turn is over.
                        # Finalize the assistant message for history
                        if (
                            streamed_assistant_message_id
                        ):  # Only if a message actually started
                            full_assistant_message_for_history = AgentOutputMessage(
                                id=streamed_assistant_message_id,
                                model=streamed_assistant_model
                                or self.config.model
                                or "unknown_stream_model",
                                role=streamed_assistant_role,  # type: ignore
                                content=current_assistant_message_content_blocks_for_history,
                                stop_reason=streamed_assistant_stop_reason,
                                usage=streamed_assistant_usage,
                            )
                            self.conversation_history.append(
                                full_assistant_message_for_history.model_dump(
                                    mode="json"
                                )
                            )

                            # Add the fully formed assistant message to current_turn_messages for the next LLM call
                            # if the conversation is to continue (e.g. after tool use)
                            # The content blocks are already suitable for MessageParam
                            current_turn_messages.append(
                                {
                                    "role": streamed_assistant_role,
                                    "content": current_assistant_message_content_blocks_for_history,
                                }
                            )

                        # Reset for a potential next assistant message in the loop (if tools were used)
                        current_assistant_message_content_blocks_for_history = []
                        # pending_tool_calls_info was removed

                        if (
                            streamed_assistant_stop_reason
                            and streamed_assistant_stop_reason != "tool_use"
                        ):
                            logger.debug(
                                f"Final response indicated by stream_end with reason: {streamed_assistant_stop_reason}. Breaking loop."
                            )
                            # This is the final response from the LLM for the whole conversation
                            self.final_response = (
                                full_assistant_message_for_history
                                if streamed_assistant_message_id
                                else None
                            )
                            break  # Exit the while loop for iterations

                        # If it was tool_use, the loop continues, current_turn_messages has been updated with tool_result

            except Exception as e:
                error_msg = f"Error during streaming conversation turn {current_iteration}: {type(e).__name__}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                yield {
                    "event_type": "error",
                    "data": {"message": error_msg, "turn": current_iteration},
                }
                break  # Stop streaming on unhandled error in a turn

            # Check if loop should break due to max_iterations or if final_response is set
            if self.final_response or current_iteration >= max_iterations:
                if current_iteration >= max_iterations and not self.final_response:
                    logger.warning(
                        f"Reached max iterations ({max_iterations}) in streaming. Aborting."
                    )
                    # Yield a final error or completion event if not already done
                    yield {
                        "event_type": "stream_end",
                        "data": {"reason": "max_iterations_reached"},
                    }
                break

        logger.info(
            f"Agent finished STREAMING run for agent '{self.config.name or 'Unnamed'}'."
        )
        # The actual AgentExecutionResult is not built by this streaming method.
        # The caller (Facade) will be responsible for that if needed, or the stream itself is the result.
