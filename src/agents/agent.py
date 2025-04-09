"""
Core Agent implementation for interacting with MCP Hosts and executing tasks.
"""

import os
import logging
import anthropic
from anthropic.types import MessageParam, ToolUseBlock
from typing import Dict, Any, Optional, List

from ..host.models import AgentConfig
from ..host.host import MCPHost  # Import MCPHost for type hinting

logger = logging.getLogger(__name__)


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
            self.anthropic_client = anthropic.Anthropic(api_key=api_key)
            logger.info("Anthropic client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            # Re-raise critical initialization error
            raise ValueError(f"Failed to initialize Anthropic client: {e}")

        logger.info(f"Agent '{self.config.name or 'Unnamed'}' initialized.")

    async def _make_llm_call(
        self,
        # client: anthropic.Anthropic, # Removed client parameter
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
            # Construct arguments, omitting None values for system and tools
            api_args = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }
            if system_prompt:
                api_args["system"] = system_prompt
            if tools:
                api_args["tools"] = tools

            # Use the client initialized in __init__
            response = self.anthropic_client.messages.create(**api_args)
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
        filter_client_ids: Optional[List[str]] = None,  # Added filter parameter
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
                           resources, and tools.
            filter_client_ids: Optional list of client IDs to restrict tool usage to.
                               If None, all tools from the host are available.

        Returns:
            A dictionary containing the conversation history and final response.

        Raises:
            ValueError: If host_instance is not provided.
            TypeError: If host_instance is not an instance of MCPHost.
            # ValueError: If Anthropic API key is not found. # Removed as key checked in __init__
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

        # API Key retrieval and client initialization moved to __init__

        # Determine LLM Parameters (AgentConfig -> Defaults) - Renumbered step
        model = self.config.model or "claude-3-opus-20240229"
        temperature = self.config.temperature or 0.7
        max_tokens = self.config.max_tokens or 4096
        system_prompt = self.config.system_prompt or "You are a helpful assistant."
        include_history = (
            self.config.include_history or False
        )  # Default to not including history unless specified

        logger.debug(
            f"Using LLM parameters: model={model}, temp={temperature}, max_tokens={max_tokens}"
        )
        logger.debug(
            f"Using system prompt: '{system_prompt[:100]}...'"
        )  # Log truncated prompt

        # Prepare Tools (Using Host's ToolManager, potentially filtered) - Renumbered step
        # TODO: Enhance format_tools_for_llm to accept filter_client_ids if needed,
        #       or rely on execute_tool filtering. For now, format all tools known to host.
        #       The filtering primarily happens during *execution*.
        all_tools_data = host_instance.tools.format_tools_for_llm()
        # Filter tools presented to LLM based on filter_client_ids?
        # This is complex as format_tools_for_llm doesn't know client source.
        # Let's rely on execute_tool filtering for now and present all tools.
        tools_data = all_tools_data  # Use all tools for now
        logger.debug(f"Formatted tools for LLM: {[t['name'] for t in tools_data]}")
        if filter_client_ids:
            logger.debug(
                f"Agent execution will filter tool calls to clients: {filter_client_ids}"
            )

        # Initialize Message History - Renumbered step
        # TODO: Implement history loading/management if include_history is True
        messages: List[MessageParam] = [{"role": "user", "content": user_message}]
        conversation_history = []  # Store full request/response cycles

        # Execute Conversation Loop - Renumbered step
        final_response = None
        tool_uses_in_last_turn = []  # Track tool uses specifically for the return value
        # Use max_iterations from config or default to 10
        max_iterations = self.config.max_iterations or 10
        logger.debug(f"Conversation loop max iterations set to: {max_iterations}")
        current_iteration = 0

        while current_iteration < max_iterations:
            current_iteration += 1
            logger.debug(f"Conversation loop iteration {current_iteration}")

            # Make API call using the helper method
            try:
                response = await self._make_llm_call(
                    # client=client, # Removed, uses self.anthropic_client now
                    messages=messages,
                    system_prompt=system_prompt,
                    tools=tools_data,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                # Logger message for success is now inside _make_llm_call
            except Exception as e:
                # Logger message for failure is now inside _make_llm_call
                # Decide how to handle API errors - re-raise, return error message?
                # For now, let's return an error structure.
                return {
                    "conversation": conversation_history,
                    "final_response": None,
                    "error": f"Anthropic API call failed: {str(e)}",
                    "tool_uses": [],
                }

            # Store assistant response in history
            # Ensure content is serializable if needed later
            conversation_history.append(
                {"role": "assistant", "content": response.content}
            )
            # NOTE: Don't add assistant response to messages here unconditionally.
            # It's only needed for the *next* turn if there are tool calls.

            # Check for tool use
            tool_results_for_next_turn = []
            tool_uses_in_this_turn = []  # Track for this specific turn
            has_tool_calls = False

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
                        # ToolManager.execute_tool is async
                        # Pass the filter_client_ids down to the host's execute_tool method
                        tool_result_content = await host_instance.execute_tool(
                            tool_name=tool_use.name,
                            arguments=tool_use.input,
                            filter_client_ids=filter_client_ids,  # Pass filter
                        )
                        logger.info(
                            f"Tool '{tool_use.name}' executed successfully (within filter)."
                        )

                        # Use ToolManager to format the tool result block
                        tool_result_block = (
                            host_instance.tools.create_tool_result_blocks(
                                tool_use.id, tool_result_content
                            )
                        )
                        tool_results_for_next_turn.append(tool_result_block)

                    except Exception as e:
                        logger.error(f"Error executing tool {tool_use.name}: {e}")
                        # Create an error result block using the same format
                        error_content = (
                            f"Error executing tool '{tool_use.name}': {str(e)}"
                        )
                        # Format error message using the standard method (no is_error flag)
                        tool_result_block = (
                            host_instance.tools.create_tool_result_blocks(
                                tool_use.id, error_content
                            )
                        )
                        tool_results_for_next_turn.append(tool_result_block)

            # If no tool calls in this turn, the conversation might be finished
            if not has_tool_calls:
                final_response = response  # The last assistant message is the final one
                logger.debug("No tool calls in the last response. Ending loop.")
                break

            # If there were tool calls, add the assistant's response (requesting the tools)
            # and the user's response (tool results) to the messages for the next API call.
            if has_tool_calls and tool_results_for_next_turn:
                # Add assistant message with tool calls
                messages.append({"role": "assistant", "content": response.content})
                # Add user message with combined tool results
                messages.append({"role": "user", "content": tool_results_for_next_turn})
                # Also log the user turn in history
                conversation_history.append(
                    {"role": "user", "content": tool_results_for_next_turn}
                )  # Also log this turn
                tool_uses_in_last_turn = tool_uses_in_this_turn  # Update last tool uses
                logger.debug(
                    f"Added {len(tool_results_for_next_turn)} tool result(s) for next turn."
                )
            else:
                # Should not happen if has_tool_calls is True, but log just in case
                logger.warning("Tool calls detected, but no results generated.")

        if current_iteration >= max_iterations:
            logger.warning(f"Reached max iterations ({max_iterations}). Aborting loop.")
            # Potentially return an error or the last response? Return last response for now.
            final_response = response

        # Return Results - Renumbered step
        logger.info(f"Agent '{self.config.name or 'Unnamed'}' execution finished.")
        return {
            "conversation": conversation_history,
            "final_response": final_response,  # Could be None if loop aborted early or error
            "tool_uses": tool_uses_in_last_turn,  # Return tool uses from the *last* assistant turn that had them
        }
        # --- End of Step 3 Implementation ---
