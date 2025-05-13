# Implementation Plan: Backend SSE Index Refactor for Agent Streaming

**Date:** 2025-05-11
**Author:** Gemini (AI Assistant)
**Reviewer:** Ryan

## 1. Objective

To refactor the backend `AgentTurnProcessor.stream_turn_response` method in `src/agents/agent_turn_processor.py` to ensure that unique, sequential indices are emitted in Server-Sent Events (SSE) for each distinct conceptual content block sent to the frontend. This will resolve issues on the frontend caused by the LLM client potentially reusing indices for different content blocks within the same turn (e.g., thinking text followed by a final JSON response both using the same LLM-provided index).

## 2. Background

The frontend (`AgentChatView.tsx`) has experienced significant difficulty in correctly ordering and styling streamed content because the `index` provided in SSE events (e.g., for `text_delta`, `content_block_stop`) can be reused by the underlying LLM client for different conceptual blocks within a single agent turn. For instance, thinking text might use `index: 0`, receive a `content_block_stop` for `index: 0`, and then the subsequent final JSON response might also be streamed with events using `index: 0`. This makes it challenging for the frontend to manage its display block array correctly, leading to overwritten content, lost styling, and incorrect ordering.

The current backend logic in `AgentTurnProcessor.stream_turn_response` largely forwards the `index` it receives from the LLM client's streaming events directly to the frontend.

## 3. Proposed Solution: Backend SSE Index Management

The solution is to introduce a new layer of index management within `AgentTurnProcessor.stream_turn_response` specifically for the SSE events yielded to the frontend. This "SSE index" will be unique and sequential for each new conceptual content block within an agent's turn, regardless of the index provided by the LLM client.

### 3.1. Key Changes in `src/agents/agent_turn_processor.py`

Inside the `AgentTurnProcessor.stream_turn_response` method:

1.  **Initialize SSE Index Counter:**
    *   At the beginning of the method, initialize a counter: `current_frontend_sse_index = 0`.
    *   Maintain a dictionary to map an LLM client's content block identifier (e.g., its `block.index` if available and consistent for a single conceptual block from the LLM, or a tuple of `(llm_event_index, content_type_or_sequence_id)`) to the `current_frontend_sse_index` that was assigned to it. Let's call this `llm_block_to_frontend_index_map = {}`. This map helps ensure that all deltas for a given conceptual block from the LLM use the same *frontend* SSE index.

2.  **Assigning Frontend SSE Index:**
    *   When an event from the LLM client signals the **start of a new conceptual content block** that will be streamed to the frontend (e.g., `text_block_start`, `tool_use_start`, or the first `text_delta` for a new piece of text if `text_block_start` isn't granular enough):
        *   Let `llm_event_index` be the index provided by the LLM client for this block.
        *   **Check if this `llm_event_index` (potentially combined with a content type if the LLM reuses indices for different types like text vs. tool_use at the same LLM index) represents a truly new conceptual block for the frontend.** This is the trickiest part. A simple heuristic: if this `llm_event_index` was associated with a block that has already received its `content_block_stop` from the LLM, then any new `text_block_start` or `tool_use_start` for that same `llm_event_index` should be treated as a new conceptual block for the frontend.
        *   If it's determined to be a new conceptual block for the frontend:
            *   The `frontend_index_to_emit = current_frontend_sse_index`.
            *   Update the mapping: `llm_block_to_frontend_index_map[<identifier_for_this_llm_block>] = frontend_index_to_emit`.
            *   Increment `current_frontend_sse_index += 1`.
        *   Else (it's a continuation of a known LLM block):
            *   `frontend_index_to_emit = llm_block_to_frontend_index_map[<identifier_for_this_llm_block>]`.

3.  **Modifying Yielded SSE Events:**
    *   For all relevant SSE events yielded to the frontend (`text_block_start`, `text_delta`, `content_block_stop`, `tool_use_start`, `tool_use_input_complete`, `tool_result`, `tool_execution_error`), ensure the `index` field in the `data` payload is set to the `frontend_index_to_emit` determined above.

    *Example for `text_delta` (conceptual):*
    ```python
    # Inside async for llm_event in self.llm.stream_message(...):
    #   llm_event_index = llm_event.get("data", {}).get("index")
    #
    #   # Determine if this llm_event_index + event_type signifies a new block start
    #   is_new_conceptual_block_for_frontend = determine_if_new_block(llm_event, llm_event_index, previously_stopped_llm_indices_map)
    #
    #   if is_new_conceptual_block_for_frontend:
    #       frontend_index_to_emit = self.current_frontend_sse_index
    #       # Map this specific instance of llm_event_index (perhaps combined with a unique block ID from LLM if available)
    #       # to frontend_index_to_emit
    #       self.llm_block_to_frontend_index_map[get_unique_llm_block_id(llm_event)] = frontend_index_to_emit
    #       self.current_frontend_sse_index += 1
    #   else:
    #       frontend_index_to_emit = self.llm_block_to_frontend_index_map.get(get_unique_llm_block_id(llm_event), self.current_frontend_sse_index -1) # Fallback to last used if not found (should be found)
    #
    #   event_data_for_frontend = llm_event.get("data", {}).copy()
    #   event_data_for_frontend["index"] = frontend_index_to_emit
    #   yield {"event_type": llm_event.get("event_type"), "data": event_data_for_frontend}
    ```
    The `determine_if_new_block` and `get_unique_llm_block_id` functions/logic would need careful implementation based on the specifics of the LLM client's event stream. A simpler approach might be to increment `current_frontend_sse_index` every time a `content_block_start` (or `tool_use_start`) is received from the LLM, and use that new `current_frontend_sse_index` for all subsequent deltas and the corresponding `content_block_stop`.

### 3.2. State Management within `AgentTurnProcessor`

*   The `AgentTurnProcessor` will need to maintain `current_frontend_sse_index` across the asynchronous generation of events for a single `stream_turn_response` call.
*   It might also need to track which LLM indices (and potentially content types at those indices) have already been "stopped" to correctly decide when to increment the `current_frontend_sse_index`.

## 4. Expected Outcome

*   The frontend will receive a stream of SSE events where the `index` field is always unique and sequential for each distinct conceptual block (thinking, tool use, final JSON response, etc.) within a single agent turn.
*   This will allow the frontend `AgentChatView.tsx` to use a much simpler logic for managing its `contentBlocks` array, directly using the received `index` to place or update blocks.
*   The issues of duplicated text, mangled JSON, and incorrect styling due to index reuse should be resolved.

## 5. Frontend Simplifications (Post-Backend Change)

Once the backend provides unique indices:
*   The frontend `text_delta` handler can revert to its simplest form: immutably append text to `contentBlocks[index]`.
*   The frontend `content_block_stop` handler will correctly process `contentBlocks[index]` using the `flatMap` logic to replace it with `thinking_finalized`, `final_response_data`, etc.
*   The `_originalIndex` property and `json_stream` type can be definitively removed from the frontend.

## 6. Testing (Backend)

*   Unit tests for `AgentTurnProcessor.stream_turn_response` simulating LLM event streams where indices are reused.
*   Verify that the yielded SSE events contain new, sequential `index` values for distinct conceptual blocks.
*   Test scenarios:
    *   Thinking only.
    *   Thinking -> Final JSON (LLM reuses index).
    *   Thinking -> Tool Use -> Final JSON (LLM reuses index for thinking and final JSON, tool use has its own LLM index).

This backend change is crucial for a robust and maintainable solution to the streaming UI issues.
