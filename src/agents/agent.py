"""
Core Agent implementation for interacting with MCP Hosts and executing tasks.
"""

import os
import logging
import anthropic  # Keep for types if needed
from anthropic import AsyncAnthropic
from anthropic.types import MessageParam, ToolUseBlock, Message
from typing import Dict, Any, Optional, List, TYPE_CHECKING

from ..host.models import AgentConfig
from ..host.host import MCPHost

# Import StorageManager for type hinting only if needed
if TYPE_CHECKING:
    from ..storage.db_manager import StorageManager

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

    def __init__(self, config: AgentConfig):
        """
        Initializes the Agent instance.

        Args:
            config: The configuration object for this agent.
        """
        if not isinstance(config, AgentConfig):
            raise TypeError("config must be an instance of AgentConfig")

        self.config = config

        # Initialize Anthropic client during agent setup
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            # Log error and raise, as agent cannot function without the key
            logger.error("ANTHROPIC_API_KEY environment variable not found.")
            raise ValueError("ANTHROPIC_API_KEY environment variable not found.")

        try:
            # Use the ASYNC client
            self.anthropic_client = AsyncAnthropic(api_key=api_key)
            logger.info("Anthropic client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            # Re-raise critical initialization error
            raise ValueError(f"Failed to initialize Anthropic client: {e}")

        logger.info(f"Agent '{self.config.name or 'Unnamed'}' initialized.")

    async def _make_llm_call(
        self,
        messages: List[MessageParam],
        system_prompt: Optional[str],
        tools: Optional[List[Dict]],  # Anthropic tool format
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> anthropic.types.Message:
        """
        Internal helper to make a single call to the Anthropic Messages API.

        Args:
            client: The initialized Anthropic client.
            messages: The list of messages for the conversation history.
            system_prompt: The system prompt to use.
            tools: The list of tools in Anthropic format, if any.
            model: The model name.
            temperature: The sampling temperature.
            max_tokens: The maximum number of tokens to generate.

        Returns:
            The Message object from the Anthropic API response.

        Raises:
            Exception: Propagates exceptions from the Anthropic API call.
        """
        logger.debug(f"Making LLM call to model '{model}'")
        try:
            # Add schema to system prompt if available
            final_system_prompt = system_prompt
            if self.config.schema:
                import json

                schema_str = json.dumps(self.config.schema, indent=2)
                final_system_prompt = f"""{system_prompt}

Your response must be valid JSON matching this schema:
{schema_str}

Remember to format your response as a valid JSON object."""

            # Construct arguments, omitting None values for system and tools
            api_args = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }
            if final_system_prompt:
                api_args["system"] = final_system_prompt
            if tools:
                api_args["tools"] = tools
                logger.debug(f"Including {len(tools)} tools in API call.")
            else:
                logger.debug("No tools included in API call.")

            # Use the client initialized in __init__
            # AWAIT the call since the client is async
            response = await self.anthropic_client.messages.create(**api_args)
            logger.debug(
                f"Anthropic API response received (stop_reason: {response.stop_reason})"
            )
            return response
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            # Re-raise the exception for the caller (e.g., execute_agent) to handle
            raise

    async def execute_agent(
        self,
        user_message: str,
        host_instance: MCPHost,
        storage_manager: Optional["StorageManager"] = None,  # Added storage_manager
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,  # Added session_id
    ) -> Dict[str, Any]:
        """
        Executes a standard agent task based on the user message, using the
        provided MCP Host and potentially a filtered set of its available tools
        in a multi-turn conversation.

        This method orchestrates the interaction with the LLM, including prompt
        preparation, tool definition, and handling tool calls based on the
        agent's configuration and the host's capabilities within the specified filter.

        Args:
            user_message: The input message or task description from the user.
            host_instance: The instantiated MCPHost to use for accessing prompts,
                           resources, and tools. Agent-specific filtering (client_ids,
                           exclude_components) is applied based on self.config.

        Returns:
            A dictionary containing the conversation history and final response.

        Raises:
            ValueError: If host_instance is not provided.
            TypeError: If host_instance is not an instance of MCPHost.
        """
        # --- Start of standard agent execution logic ---
        logger.debug(  # Already DEBUG
            f"Agent '{self.config.name or 'Unnamed'}' starting standard execution."
        )

        # 1. Validate Host Instance
        if not host_instance:
            raise ValueError("MCPHost instance is required for execution.")
        if not isinstance(host_instance, MCPHost):
            raise TypeError("host_instance must be an instance of MCPHost")

        # API Key retrieval and client initialization moved to __init__

        # Determine LLM Parameters (AgentConfig -> Defaults) - Renumbered step
        model = self.config.model or "claude-3-opus-20240229"
        temperature = self.config.temperature or 0.7
        max_tokens = self.config.max_tokens or 4096
        if system_prompt is None:
            system_prompt = self.config.system_prompt
        if not system_prompt:
            # Fallback to default system prompt if not provided
            # This is a generic prompt; consider making it configurable
            # or providing a more specific default in the config.
            system_prompt = "You are a helpful assistant."

        include_history = (
            self.config.include_history or False
        )  # Default to not including history unless specified

        logger.debug(  # Already DEBUG
            f"Using LLM parameters: model={model}, temp={temperature}, max_tokens={max_tokens}"
        )
        logger.debug(  # Already DEBUG
            f"Using system prompt: '{system_prompt[:100]}...'"
        )  # Log truncated prompt

        # Prepare Tools (Using Host's get_formatted_tools, which applies agent filtering)
        # This method is synchronous, remove await
        tools_data = host_instance.get_formatted_tools(agent_config=self.config)
        logger.debug(  # Already DEBUG
            f"Formatted tools for LLM (agent-filtered): {[t['name'] for t in tools_data]}"  # This expects tools_data to be a list of dicts
        )

        # Initialize Message History - Renumbered step
        messages: List[MessageParam] = []
        conversation_history: List[
            Dict[str, Any]
        ] = []  # Use Dict for internal history tracking

        # --- History Loading ---
        if self.config.include_history and storage_manager:
            if session_id:  # Only load if session_id is provided
                try:
                    # Load history from DB (returns list in MessageParam format)
                    loaded_history_params = storage_manager.load_history(
                        agent_name=self.config.name,
                        session_id=session_id,  # Pass session_id
                    )
                    if loaded_history_params:
                        messages.extend(loaded_history_params)
                        # Also add to internal history tracker
                        conversation_history.extend(loaded_history_params)
                        logger.info(
                            f"Loaded {len(loaded_history_params)} history turns for agent '{self.config.name}', session '{session_id}'."
                        )
                except Exception as e:
                    logger.error(
                        f"Failed to load history for agent '{self.config.name}', session '{session_id}': {e}",
                        exc_info=True,
                    )
                    # Continue execution without history if loading fails
            else:
                logger.warning(
                    f"History enabled for agent '{self.config.name}' but no session_id provided. History will not be loaded."
                )
                # Continue execution without history if loading fails

        # Add current user message
        current_user_message_param: MessageParam = {
            "role": "user",
            "content": user_message,
        }
        messages.append(current_user_message_param)
        conversation_history.append(
            current_user_message_param
        )  # Add to internal tracker too

        # Execute Conversation Loop - Renumbered step
        final_response = None
        tool_uses_in_last_turn = []  # Track tool uses specifically for the return value
        # Use max_iterations from config or default to 10
        max_iterations = self.config.max_iterations or 10
        logger.debug(
            f"Conversation loop max iterations set to: {max_iterations}"
        )  # Already DEBUG
        current_iteration = 0

        while current_iteration < max_iterations:
            current_iteration += 1
            logger.debug(
                f"Conversation loop iteration {current_iteration}"
            )  # Already DEBUG

            # Make API call using the helper method
            try:
                response = await self._make_llm_call(
                    messages=messages,
                    system_prompt=system_prompt,
                    tools=tools_data,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as e:
                return {
                    "conversation": conversation_history,
                    "final_response": None,
                    "error": f"Anthropic API call failed: {str(e)}",
                    "tool_uses": [],
                }

            # Store assistant response in history (both formats)
            assistant_response_param: MessageParam = {
                "role": "assistant",
                "content": response.content,
            }
            messages.append(
                assistant_response_param
            )  # Add raw response content for next LLM call
            conversation_history.append(
                assistant_response_param
            )  # Add to internal tracker

            # Check stop reason FIRST
            if response.stop_reason != "tool_use":
                # Get the text content from the last block
                text_content = next(
                    (block.text for block in response.content if block.type == "text"),
                    None,
                )
                if not text_content:
                    logger.warning("No text content found in response")
                    messages.append(
                        {
                            "role": "user",
                            "content": "You must provide your response as a valid JSON object.",
                        }
                    )
                    continue

                # For final response, ALWAYS try to parse as JSON if schema is provided
                if self.config.schema:
                    import json
                    from jsonschema import validate

                    # First try to parse JSON
                    try:
                        json_content = json.loads(text_content)
                    except json.JSONDecodeError:
                        # If not valid JSON, force Claude to fix it
                        logger.warning("Response was not valid JSON")
                        messages.append(
                            {
                                "role": "user",
                                "content": f"""Your response MUST be a single JSON object with no additional text or explanation.
The JSON must match this schema exactly:

{json.dumps(self.config.schema, indent=2)}

Format your entire response as valid JSON.""",
                            }
                        )
                        continue

                    # Then try to validate schema
                    try:
                        validate(instance=json_content, schema=self.config.schema)
                        logger.debug("Response validated successfully against schema")
                    except Exception as e:
                        logger.warning(f"Schema validation failed: {e}")
                        messages.append(
                            {
                                "role": "user",
                                "content": f"""Your response must be a valid JSON object matching this schema:
{json.dumps(self.config.schema, indent=2)}

The error was: {str(e)}
Try again with just the JSON object.""",
                            }
                        )
                        continue

                final_response = response
                logger.debug(  # Already DEBUG
                    f"LLM stop reason '{response.stop_reason}' indicates end of turn. Breaking loop."
                )
                break  # Exit the loop

            # If we reach here, stop_reason MUST be 'tool_use'
            logger.debug("LLM requested tool use. Processing tools...")  # Already DEBUG
            tool_results_for_next_turn = []
            tool_uses_in_this_turn = []
            has_tool_calls = False  # Reset for this check

            for block in response.content:
                if block.type == "tool_use":
                    has_tool_calls = True
                    tool_use: ToolUseBlock = block
                    tool_uses_in_this_turn.append(
                        {
                            "id": tool_use.id,
                            "name": tool_use.name,
                            "input": tool_use.input,
                        }
                    )
                    # Execute the tool via Host's ToolManager
                    logger.info(
                        f"Executing tool '{tool_use.name}' via host_instance (ID: {tool_use.id})"
                    )
                    try:
                        # Pass agent_config for filtering within execute_tool
                        tool_result_content = await host_instance.execute_tool(
                            tool_name=tool_use.name,
                            arguments=tool_use.input,
                            agent_config=self.config,
                        )
                        logger.debug(
                            f"Tool '{tool_use.name}' executed successfully (agent filters applied)."
                        )
                        # Create result block *after* successful execution
                        tool_result_block = (
                            host_instance.tools.create_tool_result_blocks(
                                tool_use.id, tool_result_content
                            )
                        )
                        tool_results_for_next_turn.append(tool_result_block)
                    except Exception as e:
                        # Create an error result block if execution fails
                        logger.error(
                            f"Error executing tool {tool_use.name}: {e}", exc_info=True
                        )  # Add exc_info
                        error_content = (
                            f"Error executing tool '{tool_use.name}': {str(e)}"
                        )
                        # Format error message using the standard method
                        tool_result_block = (
                            host_instance.tools.create_tool_result_blocks(
                                tool_use.id,
                                error_content,  # Pass error string as content
                            )
                        )
                        tool_results_for_next_turn.append(tool_result_block)
                    # --- End of try...except for tool execution ---
                # --- End of if block.type == "tool_use" ---
            # --- End of for block in response.content loop ---

            # Ensure we actually processed tool calls if stop_reason was tool_use
            # This check should be *outside* the loop iterating through content blocks
            if not has_tool_calls:
                logger.warning(
                    "LLM stop_reason was 'tool_use' but no tool_use blocks found in content. Breaking loop."
                )
                final_response = response  # Treat as final response in this edge case
                break

            # Prepare messages for the next iteration
            if tool_results_for_next_turn:
                # DO NOT re-append the assistant message here. It was already added.
                # Just append the user message containing the tool results.
                messages.append(
                    {"role": "user", "content": tool_results_for_next_turn}
                )  # Add tool results
                conversation_history.append(
                    {"role": "user", "content": tool_results_for_next_turn}
                )
                tool_uses_in_last_turn = tool_uses_in_this_turn
                logger.debug(  # Already DEBUG
                    f"Added {len(tool_results_for_next_turn)} tool result(s) for next turn."
                )
            else:
                # Should not happen if has_tool_calls is True, but handle defensively
                logger.warning(
                    "Tool calls expected based on stop_reason, but no results generated. Breaking loop."
                )
                final_response = response
                break

        # Check if loop finished due to max iterations
        if (
            current_iteration >= max_iterations and final_response is None
        ):  # Check final_response is None to avoid overwriting a valid break
            logger.warning(f"Reached max iterations ({max_iterations}). Aborting loop.")
            # Potentially return an error or the last response? Return last response for now.
            final_response = (
                response  # Assign the last response before loop termination
            )

        # --- History Saving ---
        if self.config.include_history and storage_manager:
            if session_id:  # Only save if session_id is provided
                try:
                    # Convert conversation history to a serializable format first
                    serializable_history = []
                    for message in conversation_history:  # Indent this loop correctly
                        # Ensure message is a dict before processing
                        if isinstance(message, dict):
                            raw_content = message.get("content")
                        # Serialize complex blocks first
                        serializable_content = _serialize_content_blocks(raw_content)

                        # Ensure simple string content is also wrapped in the standard format for consistency
                        if isinstance(serializable_content, str):
                            serializable_content = [
                                {"type": "text", "text": serializable_content}
                            ]
                        elif not isinstance(serializable_content, list):
                            # If serialization resulted in something unexpected (not list or str), log and wrap as error
                            logger.warning(
                                f"Unexpected serialized content type {type(serializable_content)} for agent '{self.config.name}'. Wrapping as error."
                            )
                            serializable_content = [
                                {
                                    "type": "text",
                                    "text": f"[Serialization Error: {str(serializable_content)}]",
                                }
                            ]

                        serializable_history.append(
                            {
                                "role": message.get("role"),
                                "content": serializable_content,  # Use the potentially wrapped content
                            }
                        )
                    else:
                        # Log if a message isn't in the expected format
                        logger.warning(
                            f"Skipping non-dict message in history for agent '{self.config.name}': {type(message)}"
                        )

                    # Save the SERIALIZED conversation history (save_full_history is sync)
                    storage_manager.save_full_history(
                        agent_name=self.config.name,
                        session_id=session_id,  # Pass session_id
                        conversation=serializable_history,  # Pass the serialized version
                    )
                    logger.info(
                        f"Saved {len(serializable_history)} history turns for agent '{self.config.name}', session '{session_id}'."
                    )
                except Exception as e:
                    # Log error but don't fail the overall execution result
                    logger.error(
                        f"Failed to save history for agent '{self.config.name}', session '{session_id}': {e}",
                        exc_info=True,
                    )
                    # Log error but don't fail the overall execution result # Removed redundant comment
            else:  # This else corresponds to 'if session_id:'
                logger.warning(
                    f"History enabled for agent '{self.config.name}' but no session_id provided. History will not be saved."
                )

        # Return Results - Renumbered step
        logger.info(f"Agent '{self.config.name or 'Unnamed'}' execution finished.")
        # Return the final LLM response object directly if available
        final_llm_response: Optional[Message] = final_response

        return {
            "conversation": conversation_history,  # Return the tracked history
            "final_response": final_llm_response,
            "tool_uses": tool_uses_in_last_turn,
            "error": None,  # Explicitly return None for error on success
        }
