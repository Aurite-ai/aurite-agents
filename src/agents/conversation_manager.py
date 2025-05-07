"""
Manages the multi-turn conversation loop for an Agent.
"""

import logging
import json
from typing import Dict, Any, Optional, List, TYPE_CHECKING

from pydantic import ValidationError
from anthropic.types import MessageParam

# Project imports
from ..host.host import MCPHost
from .agent_models import AgentExecutionResult, AgentOutputMessage
from .agent_turn_processor import AgentTurnProcessor
from .agent import (
    Agent,
    _serialize_content_blocks,
)  # Need Agent for type hint, _serialize for history

# Type hinting imports
if TYPE_CHECKING:
    pass  # Add other necessary type hints here if needed

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Orchestrates the multi-turn conversation flow for an agent,
    managing the message history, loop iterations, and interactions
    with the AgentTurnProcessor.
    """

    def __init__(
        self,
        agent: Agent,  # Pass the agent instance
        host_instance: MCPHost,
        initial_messages: List[MessageParam],
        system_prompt_override: Optional[str] = None,
    ):
        """
        Initializes the ConversationManager.

        Args:
            agent: The Agent instance containing config and LLM client.
            host_instance: The MCPHost instance for tool execution.
            initial_messages: The starting list of messages for the conversation.
            system_prompt_override: Optional system prompt to override the agent's default.
        """
        self.agent = agent
        self.host = host_instance
        self.messages = list(initial_messages)  # Start with a copy
        self.system_prompt_override = system_prompt_override
        self.conversation_history: List[Dict[str, Any]] = [
            _serialize_content_blocks(msg) for msg in initial_messages
        ]
        self.final_response: Optional[AgentOutputMessage] = None
        self.tool_uses_in_last_turn: List[Dict[str, Any]] = []
        logger.debug("ConversationManager initialized.")

    async def run_conversation(self) -> AgentExecutionResult:
        """
        Executes the conversation loop until a final response is reached,
        max iterations are hit, or an error occurs.

        Returns:
            An AgentExecutionResult containing the full conversation and outcome.
        """
        logger.debug(
            f"ConversationManager starting run for agent '{self.agent.config.name or 'Unnamed'}'."
        )

        # Determine effective system prompt
        effective_system_prompt = (
            self.system_prompt_override
            or self.agent.config.system_prompt
            or "You are a helpful assistant."
        )

        # Prepare tools (delegated to host)
        tools_data = self.host.get_formatted_tools(agent_config=self.agent.config)
        logger.debug(f"Formatted tools for LLM: {[t['name'] for t in tools_data]}")

        max_iterations = self.agent.config.max_iterations or 10
        current_iteration = 0

        while current_iteration < max_iterations:
            current_iteration += 1
            logger.debug(f"Conversation loop iteration {current_iteration}")

            # Instantiate and run the turn processor
            turn_processor = AgentTurnProcessor(
                config=self.agent.config,
                llm_client=self.agent.llm,  # Get LLM client from agent
                host_instance=self.host,
                current_messages=list(self.messages),  # Pass copy for this turn
                tools_data=tools_data,
                effective_system_prompt=effective_system_prompt,
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
                    # Append the user message containing tool results for the next LLM call
                    self.messages.append(  # type: ignore[typeddict-item] # This appends the 'user' message containing tool results for the *next* LLM call
                        {"role": "user", "content": turn_tool_results_params}
                    )
                    # Append the *individual* tool result message dicts to the conversation_history log
                    # turn_tool_results_params is List[MessageParam], which are dicts.
                    # We need to ensure the content within these dicts is also serializable if complex.
                    # _serialize_content_blocks should handle the inner content.
                    for tool_result_msg_param in turn_tool_results_params:
                        # Ensure the content block(s) within the message param are serialized dicts
                        if isinstance(tool_result_msg_param.get("content"), list):
                            serialized_content = _serialize_content_blocks(
                                tool_result_msg_param["content"]
                            )
                            # Create a new dict to avoid modifying the original MessageParam potentially used elsewhere
                            history_entry = {
                                "role": tool_result_msg_param.get(
                                    "role", "user"
                                ),  # Default to user if role missing
                                "content": serialized_content,
                            }
                            self.conversation_history.append(history_entry)
                        else:
                            # Handle cases where content might not be a list (though it should be)
                            logger.warning(
                                f"Tool result message param content is not a list: {tool_result_msg_param}"
                            )
                            # Append as is, validation might fail later but preserves data
                            self.conversation_history.append(tool_result_msg_param)  # type: ignore[arg-type]

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
                    if self.agent.config.config_validation_schema:
                        correction_message_content = f"""Your response must be a valid JSON object matching this schema:
{json.dumps(self.agent.config.config_validation_schema, indent=2)}

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
                    for msg in reversed(self.conversation_history)  # Use self.
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
            f"ConversationManager finished run for agent '{self.agent.config.name or 'Unnamed'}'."
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
        # Prepare conversation history for return.
        return_conversation_history_dicts = []
        for message_item in self.conversation_history:  # Use self.conversation_history
            if isinstance(message_item, dict):
                try:
                    # Validate each item to ensure it matches AgentOutputMessage structure before final dump
                    validated_msg_for_conv = AgentOutputMessage.model_validate(
                        message_item
                    )
                    return_conversation_history_dicts.append(
                        validated_msg_for_conv.model_dump(mode="json")
                    )
                except ValidationError as ve:
                    logger.warning(
                        f"Could not validate message for return conversation history: {ve}. Original item: {message_item}"
                    )
                    # Fallback: try to serialize what we have, might be incomplete/invalid structure
                    return_conversation_history_dicts.append(
                        _serialize_content_blocks(message_item)
                    )  # Best effort
            else:
                logger.warning(
                    f"Skipping non-dict item in conversation_history for return: {type(message_item)}"
                )

        # Prepare final_response for return.
        return_final_response_dict = None
        if self.final_response:  # Use self.final_response
            try:
                return_final_response_dict = self.final_response.model_dump(mode="json")
            except Exception as e:
                logger.error(
                    f"Failed to serialize final_response (AgentOutputMessage) for return: {e}",
                    exc_info=True,
                )
                # If final response serialization fails, set an error in the result
                execution_error = (
                    execution_error
                    or f"Serialization of final_response failed: {str(e)}"
                )
                return_final_response_dict = (
                    None  # Ensure it's None if serialization fails
                )

        # Construct the final dictionary to be validated
        output_dict = {
            "conversation": return_conversation_history_dicts,  # List of dicts
            "final_response": return_final_response_dict,  # Dict or None
            "tool_uses_in_final_turn": self.tool_uses_in_last_turn,  # Use self.tool_uses_in_last_turn
            "error": execution_error,  # Use passed error or None
        }

        # Validate the final dictionary against the Pydantic model
        try:
            agent_result = AgentExecutionResult.model_validate(output_dict)
            if execution_error and not agent_result.error:
                logger.warning(
                    "Execution error was provided but not set in validated AgentExecutionResult. Overriding."
                )
                agent_result.error = execution_error

            return agent_result
        except ValidationError as e:
            # This should ideally not happen if preparation is correct, but handle defensively.
            error_msg = f"Failed to validate final agent output dictionary: {e}"
            logger.error(error_msg, exc_info=True)
            # Try to return history even if final validation fails
            validated_conversation_for_error = []
            try:
                for msg_dict_err in return_conversation_history_dicts:
                    # Attempt validation again, might fail if structure is bad
                    validated_conversation_for_error.append(
                        AgentOutputMessage.model_validate(msg_dict_err)
                    )
            except Exception:
                logger.error(
                    "Could not even validate individual messages for error reporting during final validation failure."
                )
                validated_conversation_for_error = []

            combined_error = (
                f"{execution_error}\n{error_msg}" if execution_error else error_msg
            )

            return AgentExecutionResult(
                conversation=validated_conversation_for_error,
                final_response=None,
                tool_uses_in_final_turn=self.tool_uses_in_last_turn,  # Use self.
                error=combined_error,
            )
        except Exception as e:
            # Catch any other unexpected error during validation
            error_msg = f"Unexpected error during final output preparation/validation: {type(e).__name__}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            combined_error = (
                f"{execution_error}\n{error_msg}" if execution_error else error_msg
            )
            return AgentExecutionResult(
                conversation=[],
                final_response=None,
                tool_uses_in_final_turn=self.tool_uses_in_last_turn,  # Use self.
                error=combined_error,
            )
