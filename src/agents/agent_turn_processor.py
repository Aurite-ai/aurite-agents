"""
Helper class for processing a single turn in an Agent's conversation loop.
"""

import logging
from typing import (
    List,
    Optional,
    Tuple,
    Dict,
    Any,
    TYPE_CHECKING,
    AsyncGenerator,
)  # Added AsyncGenerator

import json
from jsonschema import validate, ValidationError as JsonSchemaValidationError

# Import necessary types
from anthropic.types import MessageParam, ToolResultBlockParam
from typing import cast  # Added for casting
from .agent_models import AgentOutputMessage
from ..host.host import MCPHost
from ..config.config_models import (
    AgentConfig,
    LLMConfig,
)  # Updated import path, added LLMConfig
# Import specific exceptions if needed for error handling

if TYPE_CHECKING:
    from ..llm.base_client import BaseLLM

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
        llm_client: "BaseLLM",
        host_instance: MCPHost,
        current_messages: List[MessageParam],
        tools_data: Optional[List[Dict[str, Any]]],
        effective_system_prompt: Optional[str],
        llm_config_for_override: Optional[LLMConfig] = None,  # New parameter
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
            llm_config_for_override: Optional LLMConfig to pass to the LLM client.
        """
        self.config = config
        self.llm = llm_client
        self.host = host_instance
        self.messages = current_messages
        self.tools = tools_data
        self.system_prompt = effective_system_prompt
        self.llm_config_for_override = llm_config_for_override  # Store new parameter
        self._last_llm_response: Optional[AgentOutputMessage] = (
            None  # Store the raw response
        )
        self._tool_uses_this_turn: List[Dict[str, Any]] = []  # Store tool uses
        logger.debug("AgentTurnProcessor initialized.")

    def get_last_llm_response(self) -> Optional[AgentOutputMessage]:
        """Returns the last raw response received from the LLM for this turn."""
        return self._last_llm_response

    def get_tool_uses_this_turn(self) -> List[Dict[str, Any]]:
        """Returns the details of tools used in this turn."""
        return self._tool_uses_this_turn

    async def process_turn(
        self,
    ) -> Tuple[Optional[AgentOutputMessage], Optional[List[MessageParam]], bool]:
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
                messages=self.messages,  # type: ignore[arg-type]
                tools=self.tools,
                system_prompt_override=self.system_prompt,
                schema=self.config.config_validation_schema,  # Use renamed field
                llm_config_override=self.llm_config_for_override,  # Pass stored override
            )
        except Exception as e:
            # Handle or re-raise LLM call errors appropriately
            logger.error(f"LLM call failed within turn processor: {e}", exc_info=True)
            # Decide error handling strategy - maybe return an error state?
            # For now, re-raise to be caught by Agent.execute_agent
            raise

        self._last_llm_response = llm_response  # Store the response

        # 2. Process LLM Response
        final_assistant_response: Optional[AgentOutputMessage] = None
        tool_results_for_next_turn: Optional[List[MessageParam]] = None
        is_final_turn = False  # Default to False, set True only on valid final response

        if llm_response.stop_reason == "tool_use":
            # Process tool calls if requested
            tool_results_for_next_turn = await self._process_tool_calls(llm_response)
            # _process_tool_calls also populates self._tool_uses_this_turn
            # is_final_turn remains False
            final_assistant_response = None  # No final response this turn
            logger.debug("Processed tool use request.")

        else:
            # Stop reason is likely 'end_turn' or similar - handle as potential final response
            logger.debug(
                f"Processing potential final response (stop_reason: {llm_response.stop_reason})."
            )
            # Handle final response, including schema validation
            validated_response = self._handle_final_response(llm_response)

            if validated_response is not None:
                # Schema validation passed (or no schema) - this IS the final turn
                final_assistant_response = validated_response
                is_final_turn = True
                logger.debug("Valid final response received.")
            else:
                # Schema validation failed - not the final turn, signal retry needed
                final_assistant_response = None  # No valid final response
                is_final_turn = False
                logger.warning("Schema validation failed. Signaling retry.")
                # ConversationManager loop will handle sending correction message

        logger.debug(f"Turn processed. Is final turn: {is_final_turn}")
        return final_assistant_response, tool_results_for_next_turn, is_final_turn

    async def stream_turn_response(
        self,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Processes a single conversation turn by streaming events from the LLM,
        handling tool calls inline, and yielding standardized event dictionaries.

        Yields:
            Dict[str, Any]: Standardized event dictionaries for SSE.
                            Includes text_delta, tool_use_start, tool_use_input_delta,
                            tool_use_end, tool_result, tool_execution_error, stream_end.
        """
        logger.debug("Streaming conversation turn...")
        self._tool_uses_this_turn = []  # Reset for this turn

        # --- Refactor for Frontend SSE Index (V2.1 Plan) ---
        frontend_sse_index_allocator = 0
        # Maps LLM's original block index to the frontend index *first assigned* to that LLM block instance.
        llm_block_original_idx_to_frontend_idx: Dict[int, int] = {}
        # Maps a tool_id to its assigned frontend_sse_index.
        tool_id_to_frontend_idx: Dict[str, int] = {}
        # Tracks the frontend index for the *currently open conceptual text block*.
        active_frontend_idx_for_current_text_stream: Optional[int] = None
        # --- End Refactor ---

        active_tool_calls: Dict[
            int, Dict[str, Any]
        ] = {}  # To store info about tools being called, indexed by content_block_index

        try:
            async for llm_event in self.llm.stream_message(
                messages=self.messages,  # type: ignore[arg-type]
                tools=self.tools,
                system_prompt_override=self.system_prompt,
                schema=self.config.config_validation_schema,  # Though schema less used in streaming
                llm_config_override=self.llm_config_for_override,
            ):
                event_type = llm_event.get("event_type")
                event_data = llm_event.get("data", {}).copy() # Use a copy for modification
                llm_event_original_index = event_data.get("index") # LLM's original index

                # --- Frontend SSE Index Assignment (V2.1 Plan) ---
                final_frontend_idx_to_yield: Optional[int] = None
                # Get LLM's original index from the original data, before event_data (the copy) is modified.
                # Note: llm_event_original_index was already defined above as event_data.get("index")
                # which is fine as event_data is a copy of llm_event.get("data", {}) at this point.
                # To be explicit with V2 plan, let's use a clear variable from original data if needed,
                # but current llm_event_original_index is effectively from original data at this stage.

                if event_type == "text_block_start":
                    assigned_frontend_idx = frontend_sse_index_allocator
                    frontend_sse_index_allocator += 1
                    active_frontend_idx_for_current_text_stream = assigned_frontend_idx
                    final_frontend_idx_to_yield = assigned_frontend_idx
                    if llm_event_original_index is not None:
                        llm_block_original_idx_to_frontend_idx[llm_event_original_index] = assigned_frontend_idx
                    logger.debug(f"text_block_start: llm_idx={llm_event_original_index}, assigned_fidx={assigned_frontend_idx}, active_text_fidx={active_frontend_idx_for_current_text_stream}")

                elif event_type == "tool_use_start":
                    assigned_frontend_idx = frontend_sse_index_allocator
                    frontend_sse_index_allocator += 1
                    final_frontend_idx_to_yield = assigned_frontend_idx
                    active_frontend_idx_for_current_text_stream = None # Tool use is not a text stream

                    tool_id = event_data.get("tool_id") # event_data is still original here for tool_id
                    if tool_id:
                        tool_id_to_frontend_idx[tool_id] = assigned_frontend_idx
                    else:
                        logger.error(f"Tool_use_start event missing 'tool_id'. Cannot map to frontend index. Data: {event_data}")

                    if llm_event_original_index is not None:
                        llm_block_original_idx_to_frontend_idx[llm_event_original_index] = assigned_frontend_idx
                    logger.debug(f"tool_use_start: llm_idx={llm_event_original_index}, tool_id={tool_id}, assigned_fidx={assigned_frontend_idx}")

                elif event_type == "text_delta":
                    # 1. Try to use mapping if llm_event_original_index is present and mapped
                    if llm_event_original_index is not None and llm_event_original_index in llm_block_original_idx_to_frontend_idx:
                        final_frontend_idx_to_yield = llm_block_original_idx_to_frontend_idx[llm_event_original_index]
                        # Ensure active_frontend_idx_for_current_text_stream is aligned
                        if active_frontend_idx_for_current_text_stream != final_frontend_idx_to_yield:
                            logger.debug(f"text_delta for llm_idx {llm_event_original_index} (mapped to fidx {final_frontend_idx_to_yield}) aligns active_text_fidx from {active_frontend_idx_for_current_text_stream}.")
                            active_frontend_idx_for_current_text_stream = final_frontend_idx_to_yield
                    # 2. Else, if a text stream is already active, continue it
                    elif active_frontend_idx_for_current_text_stream is not None:
                        final_frontend_idx_to_yield = active_frontend_idx_for_current_text_stream
                    # 3. Else, this delta starts a new conceptual block
                    else:
                        assigned_frontend_idx = frontend_sse_index_allocator
                        frontend_sse_index_allocator += 1
                        active_frontend_idx_for_current_text_stream = assigned_frontend_idx
                        final_frontend_idx_to_yield = assigned_frontend_idx
                        if llm_event_original_index is not None: # If this new block's delta has an original LLM index, map it.
                            llm_block_original_idx_to_frontend_idx[llm_event_original_index] = assigned_frontend_idx
                        logger.info(
                            f"text_delta initiating new conceptual block (active_text_fidx was None and llm_idx {llm_event_original_index} not mapped). "
                            f"Assigned_fidx={assigned_frontend_idx}"
                        )
                    logger.debug(f"text_delta: llm_idx={llm_event_original_index}, using_fidx={final_frontend_idx_to_yield}, active_text_fidx={active_frontend_idx_for_current_text_stream}")

                elif event_type == "tool_use_input_delta":
                    # This event is part of a tool_use block, which should have its llm_event_original_index mapped.
                    if llm_event_original_index is not None and llm_event_original_index in llm_block_original_idx_to_frontend_idx:
                        final_frontend_idx_to_yield = llm_block_original_idx_to_frontend_idx[llm_event_original_index]
                    else:
                        logger.error(f"tool_use_input_delta for unmapped or None llm_idx={llm_event_original_index}. Critical error if tool relies on this. Fallback to last allocated or 0.")
                        final_frontend_idx_to_yield = frontend_sse_index_allocator - 1 if frontend_sse_index_allocator > 0 else 0
                    logger.debug(f"tool_use_input_delta: llm_idx={llm_event_original_index}, using_fidx={final_frontend_idx_to_yield}")

                elif event_type == "content_block_stop":
                    # This event refers to an LLM block index that should have been previously mapped.
                    fidx_of_stopped_block = None
                    if llm_event_original_index is not None:
                        fidx_of_stopped_block = llm_block_original_idx_to_frontend_idx.get(llm_event_original_index)

                    final_frontend_idx_to_yield = fidx_of_stopped_block

                    if fidx_of_stopped_block is not None:
                        # If this stop event corresponds to the currently active text stream, clear it.
                        if fidx_of_stopped_block == active_frontend_idx_for_current_text_stream:
                            active_frontend_idx_for_current_text_stream = None
                            logger.debug(f"content_block_stop for llm_idx={llm_event_original_index}: Matched active_text_fidx {fidx_of_stopped_block}. Cleared active_text_fidx.")
                        # If it's stopping a tool_use block, active_frontend_idx_for_current_text_stream would be None already.
                        # If it's stopping an older text block (not the current active one), that's also fine.
                    elif active_frontend_idx_for_current_text_stream is not None and event_data.get("content_type") != "tool_use": # Check if it's not a tool_use stop without an index
                        # Fallback: LLM index was None or not in map, but a text stream was active. Assume this stop event is for it.
                        logger.warning(f"content_block_stop for unmapped/None LLM index {llm_event_original_index} (type: {event_data.get('content_type')}). Assuming it stops current text stream with fidx {active_frontend_idx_for_current_text_stream}.")
                        final_frontend_idx_to_yield = active_frontend_idx_for_current_text_stream
                        active_frontend_idx_for_current_text_stream = None
                    else:
                        # If llm_event_original_index is None or not mapped, and no active text stream,
                        # or if it's a tool_use stop without a mapped index (which shouldn't happen if tool_use_start worked).
                        logger.error(f"content_block_stop for unmapped/None LLM index {llm_event_original_index} (type: {event_data.get('content_type')}) and no active text stream or unhandled tool. Cannot determine frontend index reliably. Fallback.")
                        final_frontend_idx_to_yield = frontend_sse_index_allocator - 1 if frontend_sse_index_allocator > 0 else 0
                    logger.debug(f"content_block_stop: llm_idx={llm_event_original_index}, using_fidx={final_frontend_idx_to_yield}, active_text_fidx={active_frontend_idx_for_current_text_stream}")

                # For other event types like message_start, message_delta (message level), llm_call_completed, ping, error from LLM
                # final_frontend_idx_to_yield will remain None by default, so their original index (if any) from event_data is preserved.

                if final_frontend_idx_to_yield is not None:
                    event_data["index"] = final_frontend_idx_to_yield
                # --- End Frontend SSE Index Assignment (V2.1 Plan) ---


                if event_type == "message_start":
                    # Forward message_start if needed, or just log
                    logger.info(f"Stream started: {event_data}")
                    # message_start usually doesn't have an index related to content blocks
                    yield {"event_type": event_type, "data": event_data}

                elif event_type == "text_block_start":
                    # Useful for frontend to know a text block is beginning
                    yield {"event_type": event_type, "data": event_data}

                elif event_type == "text_delta":
                    yield {"event_type": event_type, "data": event_data} # Forward text chunks

                elif event_type == "tool_use_start":
                    if llm_event_original_index is not None: # Check if original index exists
                        active_tool_calls[llm_event_original_index] = { # Use original index for map key
                            "id": event_data.get("tool_id"), # Get from potentially modified event_data
                            "name": event_data.get("tool_name"),
                            "input_str": "",  # Initialize buffer for input JSON
                            # No longer storing frontend_index here, will use tool_id_to_frontend_idx
                        }
                    else:
                        # This was already logged above if llm_event_original_index is None for tool_use_start
                        # but specifically for active_tool_calls, it's critical.
                        logger.error(f"Tool_use_start event is missing 'llm_event_original_index'. Cannot track in active_tool_calls. Data: {event_data}")
                    yield {"event_type": event_type, "data": event_data}  # Forward to frontend

                elif event_type == "tool_use_input_delta":
                    logger.debug(
                        f"ATP: Received tool_use_input_delta event. Full event_data: {event_data}"
                    )
                    # Use llm_event_original_index to find the tool call in active_tool_calls
                    if llm_event_original_index is not None and llm_event_original_index in active_tool_calls:
                        json_chunk_data = event_data.get("json_chunk")
                        # Ensure chunk_to_add is a string
                        chunk_to_add = (
                            str(json_chunk_data) if json_chunk_data is not None else ""
                        )

                        logger.debug(
                            f"ATP: Tool input delta for index {llm_event_original_index}. Current input_str: '{active_tool_calls[llm_event_original_index]['input_str']}'. Chunk to add (type {type(chunk_to_add)}): '{chunk_to_add}'"
                        )
                        active_tool_calls[llm_event_original_index]["input_str"] += chunk_to_add
                        logger.debug(
                            f"ATP: Tool input delta for index {llm_event_original_index}. New input_str: '{active_tool_calls[llm_event_original_index]['input_str']}'"
                        )
                    else:
                        logger.warning(
                            f"ATP: Received tool_use_input_delta for index {llm_event_original_index} (from event_data: {event_data.get('index')}) but not found in active_tool_calls ({list(active_tool_calls.keys())}) or index is None."
                        )
                    yield {"event_type": event_type, "data": event_data}  # Forward to frontend

                elif event_type == "content_block_stop":
                    # No need to add to stopped_llm_indices anymore
                    yield {"event_type": event_type, "data": event_data}  # Forward to frontend

                    # Use llm_event_original_index to find the tool call in active_tool_calls
                    if llm_event_original_index is not None and llm_event_original_index in active_tool_calls:
                        # This signifies the LLM is done specifying this tool call
                        tool_call_info = active_tool_calls.pop(
                            llm_event_original_index # Use original index
                        )  # Process this tool call
                        tool_id = tool_call_info.get("id")
                        tool_name = tool_call_info.get("name")
                        tool_input_str = tool_call_info.get("input_str", "")

                        # V2 Plan: Retrieve frontend_idx using tool_id
                        retrieved_tool_frontend_idx = None
                        if tool_id:
                            retrieved_tool_frontend_idx = tool_id_to_frontend_idx.get(tool_id)

                        if retrieved_tool_frontend_idx is None:
                            logger.error(f"Could not find frontend SSE index for tool_id '{tool_id}'. Using block's assigned index {event_data.get('index')} as fallback.")
                            # Fallback to the index assigned to the content_block_stop event itself if tool-specific one not found
                            retrieved_tool_frontend_idx = event_data.get("index", 0)


                        logger.info(
                            f"Executing tool '{tool_name}' (ID: {tool_id}) from stream with input: {tool_input_str}, frontend_index: {retrieved_tool_frontend_idx}"
                        )
                        logger.debug(
                            f"ATP: Attempting to parse tool_input_str (repr): {repr(tool_input_str)}"
                        )

                        # Store tool use details (already done in non-streaming, ensure consistency if needed)
                        # self._tool_uses_this_turn.append(...)

                        try:
                            # Strip whitespace just in case, though json.loads usually handles it.
                            cleaned_tool_input_str = (
                                tool_input_str.strip() if tool_input_str else ""
                            )
                            # Aggressively remove potential null bytes or other non-printable ASCII that might break json.loads
                            sanitized_tool_input_str = "".join(
                                c
                                for c in cleaned_tool_input_str
                                if 31 < ord(c) < 127 or c in ("\n", "\r", "\t")
                            )  # Allow common whitespace
                            if (
                                not sanitized_tool_input_str and cleaned_tool_input_str
                            ):  # If stripping all made it empty, it was likely bad
                                logger.warning(
                                    f"ATP: tool_input_str became empty after sanitization. Original: {repr(cleaned_tool_input_str)}"
                                )
                                # Decide: raise error or try to parse original? For now, try original if sanitization empties it.
                                # Or, more safely, if sanitization changes the string, log both and parse sanitized.
                                if sanitized_tool_input_str != cleaned_tool_input_str:
                                    logger.debug(
                                        f"ATP: Sanitized tool_input_str for parsing: {repr(sanitized_tool_input_str)}. Original cleaned: {repr(cleaned_tool_input_str)}"
                                    )
                                # Use the sanitized string for parsing if it's not empty, otherwise use cleaned if that wasn't empty.
                                string_to_parse = (
                                    sanitized_tool_input_str
                                    if sanitized_tool_input_str
                                    else cleaned_tool_input_str
                                )
                            else:
                                string_to_parse = cleaned_tool_input_str  # Default to cleaned if sanitization didn't change or wasn't needed

                            logger.debug(
                                f"ATP: Final string for json.loads: {repr(string_to_parse)}"
                            )
                            parsed_input = (
                                json.loads(string_to_parse) if string_to_parse else {}
                            )

                            # Yield an event indicating the tool input is finalized
                            # Ensure this event also uses the correct frontend_index
                            tool_input_complete_data = {
                                "index": retrieved_tool_frontend_idx, # Use the frontend index for this tool
                                "tool_id": tool_id,
                                "input": parsed_input,
                            }
                            yield {
                                "event_type": "tool_use_input_complete",
                                "data": tool_input_complete_data
                            }

                            # Tool execution logic
                            tool_result_content = await self.host.execute_tool(
                                tool_name=tool_name,
                                arguments=parsed_input,
                                agent_config=self.config,
                            )
                            logger.debug(
                                f"Tool '{tool_name}' executed successfully via stream."
                            )

                            # Ensure tool_result_content is JSON serializable
                            serializable_output: Any
                            if isinstance(tool_result_content, str):
                                serializable_output = tool_result_content
                            elif isinstance(tool_result_content, (list, tuple)):
                                serializable_output = []
                                for item in tool_result_content:
                                    if hasattr(item, "model_dump"):
                                        # Ensure exclude_none=True for nested models
                                        item_dump = item.model_dump(
                                            mode="json", exclude_none=True
                                        )
                                        # Anthropic expects tool result content text blocks to NOT have 'id' or 'name'
                                        if item_dump.get("type") == "text":
                                            item_dump = {
                                                "type": "text",
                                                "text": item_dump.get("text", ""),
                                            }  # Keep only type and text
                                        serializable_output.append(item_dump)
                                    else:
                                        serializable_output.append(str(item))
                            elif hasattr(
                                tool_result_content, "model_dump"
                            ):  # Pydantic model
                                serializable_output = tool_result_content.model_dump(
                                    mode="json", exclude_none=True
                                )
                                # If the top-level result is a single text block, ensure it's clean
                                if serializable_output.get("type") == "text":
                                    serializable_output = {
                                        "type": "text",
                                        "text": serializable_output.get("text", ""),
                                    }
                            elif (
                                isinstance(
                                    tool_result_content, (dict, int, float, bool)
                                )
                                or tool_result_content is None
                            ):
                                serializable_output = tool_result_content
                            else:
                                logger.warning(
                                    f"Tool result output for '{tool_name}' is of complex type {type(tool_result_content)}. Converting to string."
                                )
                                serializable_output = str(tool_result_content)

                            tool_result_data = {
                                "index": retrieved_tool_frontend_idx,  # Use the frontend index for this tool
                                "tool_use_id": tool_id,
                                "tool_name": tool_name,
                                "status": "success",
                                "output": serializable_output,
                                "is_error": False,
                            }
                            yield {
                                "event_type": "tool_result",
                                "data": tool_result_data,
                            }
                        except json.JSONDecodeError as json_err: # Dedented
                            logger.error(
                                f"Failed to parse tool input JSON for tool '{tool_name}': {json_err}"
                            )
                            tool_error_data = {
                                "index": retrieved_tool_frontend_idx,  # Use the frontend index
                                "tool_use_id": tool_id,
                                "tool_name": tool_name,
                                "error_message": f"Invalid JSON input for tool: {str(json_err)}",
                            }
                            yield {
                                "event_type": "tool_execution_error",
                                "data": tool_error_data,
                            }
                        except Exception as e: # Dedented
                            logger.error(
                                f"Error executing tool {tool_name} via stream: {e}",
                                exc_info=True,
                            )
                            tool_error_data = {
                                "index": retrieved_tool_frontend_idx,  # Use the frontend index
                                "tool_use_id": tool_id,
                                "tool_name": tool_name,
                                "error_message": str(e),
                            }
                            yield {
                                "event_type": "tool_execution_error",
                                "data": tool_error_data,
                            }
                    elif llm_event_original_index is None:
                        logger.warning(f"Content_block_stop event missing 'index', cannot process associated tool call if any. Data: {event_data}")


                elif event_type == "message_delta":
                    # Contains stop_reason, usage. Could be part of stream_end or separate.
                    # For now, let Agent handle the final stop_reason from message_stop.
                    # This event type usually doesn't have a block-specific index.
                    yield {"event_type": event_type, "data": event_data}

                elif (
                    event_type
                    == "stream_end"  # This event now comes from anthropic_client with stop_reason
                ):
                    llm_call_stop_reason = event_data.get("stop_reason")
                    logger.info(
                        f"LLM stream call processing finished by ATP. LLM Stop Reason: {llm_call_stop_reason}"
                    )

                    # This event signifies the end of the current LLM call from the LLM's perspective.
                    # AgentTurnProcessor's role for *this specific LLM call* is complete.
                    # It needs to inform the Agent class about the outcome of this LLM call.
                    # If tools were used, the Agent class will decide to loop.
                    # If it was 'end_turn', the Agent class will decide to stop.
                    # AgentTurnProcessor itself does not yield the *final* stream_end to the client.
                    # It yields an event indicating this LLM part of the turn is done.
                    yield {
                        "event_type": "llm_call_completed",  # New, specific event for Agent class
                        "data": { # Ensure this data is also a copy if modified
                            "stop_reason": llm_call_stop_reason,
                            "original_event_data": event_data, # This is already a copy
                        },
                    }
                    break  # Stop processing events from this specific LLM stream call; ATP's job for this LLM call is done.

                elif (
                    event_type == "ping"
                    or event_type == "error" # General LLM error, not tool execution error
                    or event_type == "unknown"
                ):
                    # These events usually don't have a block-specific index or don't need it modified.
                    yield {"event_type": event_type, "data": event_data}

        except Exception as e:
            logger.error(f"Error during agent turn streaming: {e}", exc_info=True)
            yield {
                "event_type": "error",  # A general error for the stream processing itself
                "data": {"message": f"Agent turn processing error: {str(e)}"},
            }
        finally:
            logger.debug("Finished streaming conversation turn.")
            # Ensure a final stream_end is yielded if not already by LLM, though LLM should handle it.
            # This might be redundant if LLM always sends message_stop.
            # For safety, one could add a check here if a stream_end wasn't the last thing yielded.

    async def _process_tool_calls(
        self, llm_response: AgentOutputMessage
    ) -> List[MessageParam]:
        """Handles tool execution based on LLM response."""
        logger.debug("Processing tool calls...")
        tool_results_for_next_turn: List[MessageParam] = []
        self._tool_uses_this_turn = []  # Reset for this turn
        has_tool_calls = False

        if not llm_response.content:
            logger.warning(
                "LLM response has stop_reason 'tool_use' but no content blocks."
            )
            return []  # Return empty list, Agent loop should handle this unexpected state

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
                    logger.info(
                        f"Executing tool '{block.name}' via host (ID: {block.id})"
                    )
                    try:
                        # Execute the tool via the host instance
                        tool_result_content = await self.host.execute_tool(
                            tool_name=block.name,
                            arguments=block.input,
                            agent_config=self.config,  # Pass agent config for filtering
                        )
                        logger.debug(f"Tool '{block.name}' executed successfully.")
                        # Create a result block using the host's tool manager helper
                        tool_result_block_data: Dict[str, Any] = (
                            self.host.tools.create_tool_result_blocks(
                                tool_use_id=block.id, tool_result=tool_result_content
                            )
                        )
                        message_with_tool_result: MessageParam = {
                            "role": "user",
                            "content": [
                                cast(ToolResultBlockParam, tool_result_block_data)
                            ],
                        }
                        tool_results_for_next_turn.append(message_with_tool_result)
                    except Exception as e:
                        # Handle tool execution errors
                        logger.error(
                            f"Error executing tool {block.name}: {e}", exc_info=True
                        )
                        error_content = f"Error executing tool '{block.name}': {str(e)}"
                        # Create an error result block
                        error_tool_result_block_data: Dict[str, Any] = (
                            self.host.tools.create_tool_result_blocks(
                                tool_use_id=block.id, tool_result=error_content
                            )
                        )
                        message_with_tool_error_result: MessageParam = {
                            "role": "user",
                            "content": [
                                cast(ToolResultBlockParam, error_tool_result_block_data)
                            ],
                        }
                        tool_results_for_next_turn.append(
                            message_with_tool_error_result
                        )
                else:
                    # Log if a tool_use block is missing required fields
                    logger.warning(
                        f"Skipping tool_use block with missing fields: {block.model_dump_json()}"
                    )

        if not has_tool_calls:
            # This case should ideally not be reached if stop_reason was 'tool_use',
            # but log it if it occurs.
            logger.warning(
                "LLM stop_reason was 'tool_use' but no valid tool_use blocks found in content."
            )

        logger.debug(
            f"Processed {len(self._tool_uses_this_turn)} tool calls, generated {len(tool_results_for_next_turn)} result blocks."
        )
        return tool_results_for_next_turn

    def _handle_final_response(
        self, llm_response: AgentOutputMessage
    ) -> Optional[AgentOutputMessage]:
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
                (
                    block.text
                    for block in llm_response.content
                    if block.type == "text" and block.text is not None
                ),
                None,
            )

        # If no text content, return the response as is (might be an error or unusual case)
        if not text_content:
            logger.warning("No text content found in final LLM response.")
            return llm_response

        # Perform schema validation if a schema is configured
        if self.config.config_validation_schema:  # Use renamed field
            logger.debug("Schema validation required.")
            try:
                json_content = json.loads(text_content)
                validate(
                    instance=json_content, schema=self.config.config_validation_schema
                )  # Use renamed field
                logger.debug("Response validated successfully against schema.")
                return (
                    llm_response  # Schema is valid, return the original response object
                )
            except json.JSONDecodeError:
                logger.warning(
                    "Final response was not valid JSON, schema validation failed."
                )
                return None  # Signal failure (Agent needs to send correction)
            except JsonSchemaValidationError as e:
                logger.warning(f"Schema validation failed: {e.message}")
                return None  # Signal failure (Agent needs to send correction)
            except Exception as e:
                logger.error(
                    f"Unexpected error during schema validation: {e}", exc_info=True
                )
                return None  # Signal failure on unexpected validation errors
        else:
            # No schema defined, response is considered final and valid
            logger.debug("No schema defined, skipping validation.")
            return llm_response
