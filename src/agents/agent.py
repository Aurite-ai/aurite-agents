"""
Core Agent implementation for interacting with MCP Hosts and executing tasks.
"""

import logging
import json # Added for schema validation message formatting
# APIConnectionError and RateLimitError might be raised by the LLMClient, so keep them if used in try-except blocks.
# For now, assuming LLMClient handles these and agent only catches generic Exception or specific LLMClient exceptions.
# If Agent needs to catch these specific Anthropic errors directly from LLMClient, this import might need adjustment.
from anthropic.types import MessageParam # These are for constructing messages/tool results
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from pydantic import ValidationError # Import for validation error handling

from ..host.models import AgentConfig
from ..host.host import MCPHost
# Import the new models
from .agent_models import AgentExecutionResult, AgentOutputMessage
# Import the new turn processor
from .turn_processor import AgentTurnProcessor

# Import StorageManager for type hinting only if needed
if TYPE_CHECKING:
    # Import the LLM base class for type hinting
    from ..llm.base_client import BaseLLM

logger = logging.getLogger(__name__)


# --- Helper Function for Serialization ---
def _serialize_content_blocks(content: Any) -> Any:
    """Recursively converts Anthropic content blocks into JSON-serializable dicts."""
    if isinstance(content, list):
        # Process each item in the list
        return [_serialize_content_blocks(item) for item in content]
    elif isinstance(content, dict):
        # Recursively process dictionary values
        return {k: _serialize_content_blocks(v) for k, v in content.items()}
    elif hasattr(content, "model_dump") and callable(content.model_dump):
        # Use Pydantic's model_dump for TextBlock, ToolUseBlock, etc.
        try:
            # model_dump typically returns a dict suitable for JSON
            return content.model_dump(mode="json")
        except Exception as e:
            logger.warning(
                f"Could not serialize object of type {type(content)} using model_dump: {e}. Falling back to string representation."
            )
            return str(content)  # Fallback if model_dump fails
    # Handle primitive types that are already JSON-serializable
    elif isinstance(content, (str, int, float, bool, type(None))):
        return content
    else:
        # Fallback for any other unknown types
        logger.warning(
            f"Attempting to serialize unknown type {type(content)}. Using string representation."
        )
        return str(content)


class Agent:
    """
    Represents an agent capable of executing tasks using an MCP Host.

    The agent is configured via an AgentConfig object and interacts with
    the LLM and tools provided by the specified MCPHost instance during execution.
    """

    def __init__(self, config: AgentConfig, llm_client: "BaseLLM"):
        """
        Initializes the Agent instance.

        Args:
            config: The configuration object for this agent.
            llm_client: An initialized instance of a BaseLLM subclass.
        """
        if not isinstance(config, AgentConfig):
            raise TypeError("config must be an instance of AgentConfig")
        if not isinstance(llm_client, BaseLLM): # Add type check for llm_client
             raise TypeError("llm_client must be an instance of BaseLLM or its subclass")

        self.config = config
        self.llm = llm_client # Store the passed LLM client instance

        # The Anthropic client (self.anthropic_client) is no longer initialized here.
        # The agent relies on the self.llm (BaseLLM instance) passed to it.

        logger.info(f"Agent '{self.config.name or 'Unnamed'}' initialized with LLM client: {type(self.llm).__name__}")

    async def execute_agent(
        self,
        initial_messages: List[MessageParam], # Changed from user_message
        host_instance: MCPHost,
        # storage_manager: Optional["StorageManager"] = None, # Removed
        system_prompt: Optional[str] = None,
        # session_id: Optional[str] = None, # Removed
    ) -> AgentExecutionResult:
        """
        Executes a standard agent task based on an initial list of messages, using the
        provided MCP Host and potentially a filtered set of its available tools
        in a multi-turn conversation.

        This method orchestrates the interaction with the LLM, including prompt
        preparation, tool definition, and handling tool calls based on the
        agent's configuration and the host's capabilities within the specified filter.
        History loading and saving should be handled by the caller (e.g., ExecutionFacade).

        Args:
            initial_messages: The list of messages representing the conversation state
                              so far, including the latest user message. Expected format
                              is List[MessageParam] compatible with LLM client.
            host_instance: The instantiated MCPHost to use for accessing prompts,
                           resources, and tools. Agent-specific filtering (client_ids,
                           exclude_components) is applied based on self.config.
            system_prompt: Optional override for the agent's system prompt.

        Returns:
            An AgentExecutionResult Pydantic model instance containing the
            conversation history, final response, tool uses, and any errors.

        Raises:
            ValueError: If host_instance is not provided.
            TypeError: If host_instance is not an instance of MCPHost.
        """
        # --- Start of standard agent execution logic ---
        logger.debug(
            f"Agent '{self.config.name or 'Unnamed'}' starting standard execution."
        )

        # 1. Validate Host Instance
        if not host_instance:
            raise ValueError("MCPHost instance is required for execution.")
        if not isinstance(host_instance, MCPHost):
            raise TypeError("host_instance must be an instance of MCPHost")

        # Determine LLM Parameters (AgentConfig -> Defaults)
        # Note: LLMClient might handle these internally based on its config,
        # but we keep system_prompt override logic here.
        if system_prompt is None:
            system_prompt = self.config.system_prompt
        if not system_prompt:
            system_prompt = "You are a helpful assistant."

        logger.debug(
            f"Using system prompt: '{system_prompt[:100]}...'"
        )

        # Prepare Tools
        tools_data = host_instance.get_formatted_tools(agent_config=self.config)
        logger.debug(
            f"Formatted tools for LLM (agent-filtered): {[t['name'] for t in tools_data]}"
        )

        # Initialize Message History
        messages: List[MessageParam] = list(initial_messages) # Copy for modification
        conversation_history: List[Dict[str, Any]] = [_serialize_content_blocks(msg) for msg in initial_messages]

        logger.debug(f"Agent execution starting with {len(messages)} initial messages.")

        # Execute Conversation Loop
        final_response: Optional[AgentOutputMessage] = None
        tool_uses_in_last_turn: List[Dict[str, Any]] = []
        max_iterations = self.config.max_iterations or 10
        current_iteration = 0

        while current_iteration < max_iterations:
            current_iteration += 1
            logger.debug(f"Conversation loop iteration {current_iteration}")

            # Instantiate and run the turn processor
            turn_processor = AgentTurnProcessor(
                config=self.config,
                llm_client=self.llm,
                host_instance=host_instance,
                current_messages=messages, # Pass the current message list for the LLM
                tools_data=tools_data,
                effective_system_prompt=system_prompt, # Pass the potentially overridden prompt
            )

            try:
                # Process the turn
                turn_final_response, turn_tool_results_params, is_final_turn = await turn_processor.process_turn()

                # --- Update state based on turn processor results ---
                assistant_message_this_turn = turn_processor.get_last_llm_response()

                if assistant_message_this_turn:
                     # Append assistant message dict to conversation_history log
                     conversation_history.append(assistant_message_this_turn.model_dump(mode="json"))
                     # Convert assistant message content to MessageParam format for the *next* LLM call
                     next_turn_content_blocks = []
                     if assistant_message_this_turn.content:
                         for block in assistant_message_this_turn.content:
                             if block.type == "text" and block.text is not None:
                                 next_turn_content_blocks.append({"type": "text", "text": block.text})
                             elif block.type == "tool_use" and block.id and block.name and block.input is not None:
                                 # This is the assistant requesting a tool use
                                 next_turn_content_blocks.append({
                                     "type": "tool_use",
                                     "id": block.id,
                                     "name": block.name,
                                     "input": block.input
                                 })
                     # Append the assistant message (in MessageParam format) to the list for the next LLM call
                     messages.append({
                         "role": "assistant",
                         "content": next_turn_content_blocks
                     })

                if turn_tool_results_params: # If the processor returned tool results (List[MessageParam])
                    # Append the user message containing tool results for the next LLM call
                    messages.append({"role": "user", "content": turn_tool_results_params})
                    # Append the user message containing tool results (serialized) to the conversation_history log
                    conversation_history.append({"role": "user", "content": _serialize_content_blocks(turn_tool_results_params)})
                    # Update tool uses for the final result
                    tool_uses_in_last_turn = turn_processor.get_tool_uses_this_turn()

                if is_final_turn:
                    if turn_final_response is not None:
                        # Final response received and validated (if schema was present)
                        final_response = turn_final_response # Store the final AgentOutputMessage
                        logger.debug("Turn processor indicated final turn. Breaking loop.")
                        break # Exit the loop
                    else:
                        # This case means schema validation failed in the processor
                        logger.warning("Schema validation failed. Preparing correction message.")
                        # Construct and append correction message for the next iteration
                        if self.config.schema: # Ensure schema exists before creating message
                            correction_message_content = f"""Your response must be a valid JSON object matching this schema:
{json.dumps(self.config.schema, indent=2)}

Please correct your previous response to conform to the schema."""
                            correction_message: MessageParam = {"role": "user", "content": correction_message_content}
                            messages.append(correction_message)
                            conversation_history.append(_serialize_content_blocks(correction_message))
                            # Continue the loop to let the LLM retry
                        else:
                            # Should not happen if _handle_final_response logic is correct, but log warning
                            logger.error("Schema validation failed but no schema found in config. Cannot send correction.")
                            # Decide how to handle this - maybe break with error? For now, break loop.
                            # Set an error state?
                            # Let's just break and the final result will likely show the unvalidated response.
                            final_response = assistant_message_this_turn # Use the unvalidated response if available
                            break

                # else: loop continues because is_final_turn is False (due to tool use or schema failure handled above)

                # --- End of state update ---

            except Exception as e:
                # Catch errors raised from turn_processor.process_turn() (e.g., LLM call failures)
                error_msg = f"Error during conversation turn processing: {type(e).__name__}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                # Ensure conversation history is properly serialized before returning
                validated_history_for_error = []
                try:
                    # Use _serialize_content_blocks directly on conversation_history items
                    for m in conversation_history:
                         validated_history_for_error.append(AgentOutputMessage.model_validate(_serialize_content_blocks(m)))
                except Exception as val_err:
                     logger.error(f"Could not validate conversation history for error reporting: {val_err}")
                return AgentExecutionResult(
                    conversation=validated_history_for_error,
                    final_response=None,
                    tool_uses_in_final_turn=tool_uses_in_last_turn, # Use the last known state
                    error=error_msg,
                )

        # Check if loop finished due to max iterations
        if (
            current_iteration >= max_iterations and final_response is None
        ):
            logger.warning(f"Reached max iterations ({max_iterations}). Aborting loop.")
            # Try to use the last assistant message from history as final response, if available
            last_assistant_message_dict = next((msg for msg in reversed(conversation_history) if msg.get("role") == "assistant"), None)
            if last_assistant_message_dict:
                try:
                    # Attempt to validate the last message as AgentOutputMessage
                    final_response = AgentOutputMessage.model_validate(last_assistant_message_dict)
                    logger.debug("Using last assistant message as final response due to max iterations.")
                except Exception as val_err_max_iter:
                    logger.error(f"Could not validate last assistant message for max iterations fallback: {val_err_max_iter}")
                    final_response = None # Ensure it's None if validation fails
            else:
                 final_response = None # Ensure it's None if no assistant message found


        # --- History Saving Removed ---
        # History saving is now the responsibility of the caller (e.g., ExecutionFacade).

        # Return Results using the helper function
        logger.info(f"Agent '{self.config.name or 'Unnamed'}' execution finished.")
        # Pass execution_error=None explicitly for the success path
        return self._prepare_agent_result(conversation_history, final_response, tool_uses_in_last_turn, execution_error=None)


    def _prepare_agent_result(
        self,
        conversation_history: List[Dict[str, Any]],
        final_response: Optional[AgentOutputMessage],
        tool_uses_in_last_turn: List[Dict[str, Any]],
        execution_error: Optional[str] = None # Allow passing execution errors
    ) -> AgentExecutionResult:
        """
        Constructs and validates the final AgentExecutionResult.
        """
        logger.debug("Preparing final agent execution result...")
        # Prepare conversation history for return.
        # conversation_history should contain dicts representing AgentOutputMessage or MessageParam
        return_conversation_history_dicts = []
        for message_item in conversation_history:
            if isinstance(message_item, dict):
                try:
                    # Validate each item to ensure it matches AgentOutputMessage structure before final dump
                    # This handles items that might already be dicts from MessageParam or model_dump
                    validated_msg_for_conv = AgentOutputMessage.model_validate(message_item)
                    return_conversation_history_dicts.append(validated_msg_for_conv.model_dump(mode="json"))
                except ValidationError as ve:
                    logger.warning(f"Could not validate message for return conversation history: {ve}. Original item: {message_item}")
                    # Fallback: try to serialize what we have, might be incomplete/invalid structure
                    return_conversation_history_dicts.append(_serialize_content_blocks(message_item)) # Best effort
            else:
                logger.warning(f"Skipping non-dict item in conversation_history for return: {type(message_item)}")


        # Prepare final_response for return.
        # final_response is an AgentOutputMessage object or None.
        return_final_response_dict = None
        if final_response: # final_response is AgentOutputMessage
            try:
                return_final_response_dict = final_response.model_dump(mode="json")
            except Exception as e:
                logger.error(f"Failed to serialize final_response (AgentOutputMessage) for return: {e}", exc_info=True)
                # If final response serialization fails, set an error in the result
                execution_error = execution_error or f"Serialization of final_response failed: {str(e)}"
                return_final_response_dict = None # Ensure it's None if serialization fails


        # Construct the final dictionary to be validated
        output_dict = {
            "conversation": return_conversation_history_dicts, # List of dicts
            "final_response": return_final_response_dict,     # Dict or None
            "tool_uses_in_final_turn": tool_uses_in_last_turn,
            "error": execution_error, # Use passed error or None
        }

        # Validate the final dictionary against the Pydantic model
        try:
            agent_result = AgentExecutionResult.model_validate(output_dict)
            if execution_error and not agent_result.error:
                 logger.warning("Execution error was provided but not set in validated AgentExecutionResult. Overriding.")
                 # Manually set the error if validation somehow cleared it
                 # This requires AgentExecutionResult.error to be mutable or recreate the object
                 # Assuming it's mutable for now, otherwise recreate:
                 # agent_result = AgentExecutionResult(**output_dict) # Recreate with error
                 agent_result.error = execution_error # If mutable

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
                     validated_conversation_for_error.append(AgentOutputMessage.model_validate(msg_dict_err))
            except Exception:
                 logger.error("Could not even validate individual messages for error reporting during final validation failure.")
                 # Fallback to the dicts we prepared if individual validation fails
                 validated_conversation_for_error = return_conversation_history_dicts

            # Combine original execution error (if any) with validation error
            combined_error = f"{execution_error}\n{error_msg}" if execution_error else error_msg

            return AgentExecutionResult(
                conversation=validated_conversation_for_error, # Return best effort history
                final_response=None, # Unsafe to assume final_response is valid
                tool_uses_in_final_turn=tool_uses_in_last_turn,
                error=combined_error,
            )
        except Exception as e:
            # Catch any other unexpected error during validation
            error_msg = f"Unexpected error during final output preparation/validation: {type(e).__name__}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # Combine original execution error (if any) with this new error
            combined_error = f"{execution_error}\n{error_msg}" if execution_error else error_msg
            return AgentExecutionResult(
                conversation=[], # Safest to return empty list
                final_response=None,
                tool_uses_in_final_turn=tool_uses_in_last_turn,
                error=combined_error,
            )
