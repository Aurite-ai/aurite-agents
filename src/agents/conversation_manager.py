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
from .agent import Agent  # Need Agent for type hint

# Type hinting imports
if TYPE_CHECKING:
    pass  # Add other necessary type hints here if needed

logger = logging.getLogger(__name__)


# _serialize_content_blocks function removed as it's deemed redundant here.


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
        # Initial messages are already dicts, no need for serialization here.
        self.conversation_history: List[Dict[str, Any]] = list(initial_messages)
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
