"""
Helper class for processing a single turn in an Agent's conversation loop.
"""
import logging
from typing import List, Optional, Tuple, Dict, Any, TYPE_CHECKING

import json
from jsonschema import validate, ValidationError as JsonSchemaValidationError

# Import necessary types
from anthropic.types import MessageParam
from .models import AgentOutputMessage
from ..host.host import MCPHost
from ..host.models import AgentConfig
# Import specific exceptions if needed for error handling

if TYPE_CHECKING:
    from ..llm.client import BaseLLM

logger = logging.getLogger(__name__)

class ConversationTurnProcessor:
    """
    Handles the logic for a single turn of interaction within the Agent's
    execution loop, including LLM calls, response parsing, schema validation,
    and tool execution coordination.
    """

    def __init__(
        self,
        config: AgentConfig,
        llm_client: "BaseLLM",
        host_instance: MCPHost,
        current_messages: List[MessageParam],
        tools_data: Optional[List[Dict[str, Any]]],
        effective_system_prompt: Optional[str],
    ):
        """
        Initializes the turn processor.

        Args:
            config: The AgentConfig for the current agent.
            llm_client: The initialized LLM client instance.
            host_instance: The MCPHost instance.
            current_messages: The current list of messages to be sent to the LLM.
            tools_data: Formatted tool definitions for the LLM.
            effective_system_prompt: The system prompt to use for this turn.
        """
        self.config = config
        self.llm = llm_client
        self.host = host_instance
        self.messages = current_messages
        self.tools = tools_data
        self.system_prompt = effective_system_prompt
        self._last_llm_response: Optional[AgentOutputMessage] = None # Store the raw response
        self._tool_uses_this_turn: List[Dict[str, Any]] = [] # Store tool uses
        logger.debug("ConversationTurnProcessor initialized.")

    def get_last_llm_response(self) -> Optional[AgentOutputMessage]:
        """Returns the last raw response received from the LLM for this turn."""
        return self._last_llm_response

    def get_tool_uses_this_turn(self) -> List[Dict[str, Any]]:
        """Returns the details of tools used in this turn."""
        return self._tool_uses_this_turn

    async def process_turn(self) -> Tuple[Optional[AgentOutputMessage], Optional[List[MessageParam]], bool]:
        """
        Processes a single conversation turn.

        1. Makes the LLM call.
        2. Parses the response (AgentOutputMessage).
        3. Handles stop reason (tool use or final response).
        4. Performs schema validation if needed.
        5. Executes tools if requested.
        6. Prepares tool results for the next turn if applicable.

        Returns:
            A tuple containing:
            - The final assistant response (AgentOutputMessage) if the turn ended without tool use, else None.
            - A list of tool result messages (List[MessageParam]) to be added for the next turn, or None.
            - A boolean indicating if this turn resulted in the final response (True) or if the loop should continue (False).
        """
        logger.debug("Processing conversation turn...")
        # --- Placeholder for logic to be moved from Agent.execute_agent ---

        # 1. Make LLM call
        try:
            llm_response: AgentOutputMessage = await self.llm.create_message(
                messages=self.messages,
                tools=self.tools,
                system_prompt_override=self.system_prompt,
                schema=self.config.schema
            )
        except Exception as e:
            # Handle or re-raise LLM call errors appropriately
            logger.error(f"LLM call failed within turn processor: {e}", exc_info=True)
            # Decide error handling strategy - maybe return an error state?
            # For now, re-raise to be caught by Agent.execute_agent
            raise

        self._last_llm_response = llm_response # Store the response

        # 2. Process LLM Response
        final_assistant_response: Optional[AgentOutputMessage] = None
        tool_results_for_next_turn: Optional[List[MessageParam]] = None
        is_final_turn = True # Assume final unless tool use occurs

        if llm_response.stop_reason == "tool_use":
            is_final_turn = False
            tool_results_for_next_turn = await self._process_tool_calls(llm_response)
            # _process_tool_calls also populates self._tool_uses_this_turn
        else:
            # Handle final response, including schema validation
            # This might return the original response, or None if validation fails and needs retry
            final_assistant_response = self._handle_final_response(llm_response)
            if final_assistant_response is None:
                 # Indicate that the loop should continue for schema correction
                 is_final_turn = False
                 # We need a way to signal the Agent to send a correction message.
                 # For now, returning None, None, False might be interpretable by the Agent.
                 # Or, this method could return a specific "retry_needed" state.
                 # Let's refine this: _handle_final_response should return the message to send next if retry needed.
                 # For simplicity now, let's assume _handle_final_response returns the validated response or raises an error handled by Agent.
                 # Let's stick to the original plan: _handle_final_response returns the validated response or None if retry needed by Agent.
                 # The Agent loop will need modification to handle the None case by sending a correction message.
                 logger.warning("Schema validation failed. Agent needs to handle retry.")


        logger.debug(f"Turn processed. Is final turn: {is_final_turn}")
        return final_assistant_response, tool_results_for_next_turn, is_final_turn


    async def _process_tool_calls(self, llm_response: AgentOutputMessage) -> List[MessageParam]:
        """Handles tool execution based on LLM response."""
        logger.debug("Processing tool calls...")
        tool_results_for_next_turn: List[MessageParam] = []
        self._tool_uses_this_turn = [] # Reset for this turn
        has_tool_calls = False

        if not llm_response.content:
             logger.warning("LLM response has stop_reason 'tool_use' but no content blocks.")
             return [] # Return empty list, Agent loop should handle this unexpected state

        for block in llm_response.content:
            if block.type == "tool_use":
                has_tool_calls = True
                if block.id and block.name and block.input is not None:
                    # Record the tool use attempt
                    self._tool_uses_this_turn.append(
                        {
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }
                    )
                    logger.info(f"Executing tool '{block.name}' via host (ID: {block.id})")
                    try:
                        # Execute the tool via the host instance
                        tool_result_content = await self.host.execute_tool(
                            tool_name=block.name,
                            arguments=block.input,
                            agent_config=self.config, # Pass agent config for filtering
                        )
                        logger.debug(f"Tool '{block.name}' executed successfully.")
                        # Create a result block using the host's tool manager helper
                        tool_result_block_param = self.host.tools.create_tool_result_blocks(
                            tool_use_id=block.id, # Corrected kwarg name
                            content=tool_result_content,
                            is_error=False
                        )
                        tool_results_for_next_turn.append(tool_result_block_param)
                    except Exception as e:
                        # Handle tool execution errors
                        logger.error(f"Error executing tool {block.name}: {e}", exc_info=True)
                        error_content = f"Error executing tool '{block.name}': {str(e)}"
                        # Create an error result block
                        tool_result_block_param = self.host.tools.create_tool_result_blocks(
                            tool_use_id=block.id, # Corrected kwarg name
                            content=error_content,
                            is_error=True
                        )
                        tool_results_for_next_turn.append(tool_result_block_param)
                else:
                    # Log if a tool_use block is missing required fields
                    logger.warning(f"Skipping tool_use block with missing fields: {block.model_dump_json()}")

        if not has_tool_calls:
            # This case should ideally not be reached if stop_reason was 'tool_use',
            # but log it if it occurs.
            logger.warning("LLM stop_reason was 'tool_use' but no valid tool_use blocks found in content.")

        logger.debug(f"Processed {len(self._tool_uses_this_turn)} tool calls, generated {len(tool_results_for_next_turn)} result blocks.")
        return tool_results_for_next_turn


    def _handle_final_response(self, llm_response: AgentOutputMessage) -> Optional[AgentOutputMessage]:
        """
        Handles the final response, including schema validation.
        Returns the validated response if successful, or None if schema validation fails,
        signaling the need for a retry/correction message.
        """
        logger.debug("Handling final response...")

        # Extract text content
        text_content = None
        if llm_response.content:
            text_content = next(
                (block.text for block in llm_response.content if block.type == "text" and block.text is not None),
                None,
            )

        # If no text content, return the response as is (might be an error or unusual case)
        if not text_content:
            logger.warning("No text content found in final LLM response.")
            return llm_response

        # Perform schema validation if a schema is configured
        if self.config.schema:
            logger.debug("Schema validation required.")
            try:
                json_content = json.loads(text_content)
                validate(instance=json_content, schema=self.config.schema)
                logger.debug("Response validated successfully against schema.")
                return llm_response # Schema is valid, return the original response object
            except json.JSONDecodeError:
                logger.warning("Final response was not valid JSON, schema validation failed.")
                return None # Signal failure (Agent needs to send correction)
            except JsonSchemaValidationError as e:
                logger.warning(f"Schema validation failed: {e.message}")
                return None # Signal failure (Agent needs to send correction)
            except Exception as e:
                 logger.error(f"Unexpected error during schema validation: {e}", exc_info=True)
                 return None # Signal failure on unexpected validation errors
        else:
            # No schema defined, response is considered final and valid
            logger.debug("No schema defined, skipping validation.")
            return llm_response


    async def _process_tool_calls(self, llm_response: AgentOutputMessage) -> List[MessageParam]:
        """Handles tool execution based on LLM response."""
        logger.debug("Processing tool calls...")
        tool_results_for_next_turn: List[MessageParam] = []
        self._tool_uses_this_turn = [] # Reset for this turn
        has_tool_calls = False

        if not llm_response.content:
             logger.warning("LLM response has stop_reason 'tool_use' but no content blocks.")
             return [] # Return empty list, Agent loop should handle this unexpected state

        for block in llm_response.content:
            if block.type == "tool_use":
                has_tool_calls = True
                if block.id and block.name and block.input is not None:
                    self._tool_uses_this_turn.append(
                        {
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }
                    )
                    logger.info(f"Executing tool '{block.name}' via host (ID: {block.id})")
                    try:
                        tool_result_content = await self.host.execute_tool(
                            tool_name=block.name,
                            arguments=block.input,
                            agent_config=self.config, # Pass agent config for filtering
                        )
                        logger.debug(f"Tool '{block.name}' executed successfully.")
                        tool_result_block_param = self.host.tools.create_tool_result_blocks(
                            block.id, tool_result_content
                        )
                        tool_results_for_next_turn.append(tool_result_block_param)
                    except Exception as e:
                        logger.error(f"Error executing tool {block.name}: {e}", exc_info=True)
                        error_content = f"Error executing tool '{block.name}': {str(e)}"
                        tool_result_block_param = self.host.tools.create_tool_result_blocks(
                            block.id, error_content, is_error=True # Assuming create_tool_result_blocks handles is_error
                        )
                        tool_results_for_next_turn.append(tool_result_block_param)
                else:
                    logger.warning(f"Skipping tool_use block with missing fields: {block.model_dump_json()}")

        if not has_tool_calls:
            logger.warning("LLM stop_reason was 'tool_use' but no valid tool_use blocks found in content.")
            # Decide how Agent should handle this - maybe treat as final response?
            # For now, return empty results.

        logger.debug(f"Processed {len(self._tool_uses_this_turn)} tool calls, generated {len(tool_results_for_next_turn)} result blocks.")
        return tool_results_for_next_turn


    def _handle_final_response(self, llm_response: AgentOutputMessage) -> Optional[AgentOutputMessage]:
        """Handles the final response, including schema validation."""
        logger.debug("Handling final response...")

        text_content = None
        if llm_response.content:
            text_content = next(
                (block.text for block in llm_response.content if block.type == "text" and block.text is not None),
                None,
            )

        if not text_content:
            logger.warning("No text content found in final LLM response.")
            # What should happen here? Maybe return the response as is? Or signal error?
            # Let's return the response as is for now.
            return llm_response

        if self.config.schema:
            logger.debug("Schema validation required.")
            try:
                json_content = json.loads(text_content)
                validate(instance=json_content, schema=self.config.schema)
                logger.debug("Response validated successfully against schema.")
                return llm_response # Return original response if valid
            except json.JSONDecodeError:
                logger.warning("Final response was not valid JSON, schema validation failed.")
                # Signal to Agent that retry is needed
                return None
            except JsonSchemaValidationError as e:
                logger.warning(f"Schema validation failed: {e.message}")
                # Signal to Agent that retry is needed
                return None
            except Exception as e:
                 logger.error(f"Unexpected error during schema validation: {e}", exc_info=True)
                 # Signal to Agent that retry is needed (treat unexpected validation errors as failure)
                 return None
        else:
            # No schema defined, response is considered final
            logger.debug("No schema defined, skipping validation.")
            return llm_response
