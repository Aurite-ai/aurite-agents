# Implementation Plan: Backend SSE Index Refinement (V2)

**Date:** 2025-05-11
**Author:** Gemini (AI Assistant)
**Reviewer:** Ryan
**Status:** Proposed

## 1. Objective

To refine the backend `AgentTurnProcessor.stream_turn_response` method in `src/agents/agent_turn_processor.py`. The goal is to ensure that unique, sequential `index` values are emitted in Server-Sent Events (SSE) for each distinct conceptual content block intended for the frontend. This change is critical for resolving persistent UI issues in `AgentChatView.tsx` related to content ordering, styling, and duplication.

## 2. Problem Analysis: Why Previous Frontend Fixes Were Insufficient

Despite multiple iterations on the frontend `AgentChatView.tsx` logic, issues with duplicated thinking text, mangled JSON responses, and incorrect styling persisted. Log analysis revealed the root cause:

*   **Backend Index Reuse:** The underlying LLM client (e.g., Anthropic SDK) may reuse its internal `index` for different conceptual blocks within a single turn. For example, thinking text might be streamed with `index: 0`, followed by a `content_block_stop` for `index: 0`. Subsequently, the final JSON response might also be streamed with `text_delta` events using the same `index: 0`, followed by another `content_block_stop` for `index: 0`.
*   **Frontend Misinterpretation:** The frontend was attempting to manage this reused index.
    *   Initially, this led to new content (JSON) overwriting or merging with previously finalized content (thinking text) at the same array slot in `contentBlocks`.
    *   Attempts to make the frontend "smarter" by pushing follow-up streams for reused indices (`_isFollowUpForIndex` or `streamSourceIndex` concepts) became overly complex and still didn't perfectly solve the ordering and state management, as the `content_block_stop` event still only carried the original reused `index`, making it hard to target the correct pushed block.
*   **Conclusion:** The most robust solution is for the backend to take responsibility for providing a clean, unambiguous sequence of indexed blocks to the frontend. Each conceptually separate piece of content (thinking, a specific tool call's invocation, a final JSON response) should have its own unique, sequential index in the SSE stream sent to the client.

## 3. Proposed Backend Solution: Unique Frontend SSE Index Generation

The `AgentTurnProcessor.stream_turn_response` method will be modified to manage and emit its own set of indices for SSE events, ensuring uniqueness and sequentiality for frontend consumption.

### 3.1. Core Logic Changes in `AgentTurnProcessor.stream_turn_response`:

1.  **Initialize a Frontend SSE Index Counter:**
    *   At the beginning of the `stream_turn_response` method, introduce a counter:
        ```python
        frontend_sse_index_allocator = 0
        # This will be incremented for each new conceptual block sent to the frontend.
        ```

2.  **Maintain a Mapping for LLM Block Instances to Frontend SSE Indices:**
    *   A dictionary will map a unique identifier from an LLM's block instance (e.g., the `index` field from an Anthropic `content_block_start` or `tool_use_start` event, which is unique *per block instance within that message from the LLM*) to the `frontend_sse_index` we assign to it.
        ```python
        # Key: LLM's original block index (from content_block_start/tool_use_start)
        # Value: The unique frontend_sse_index assigned to this block
        llm_block_original_idx_to_frontend_idx: Dict[int, int] = {}
        ```
    *   For tool calls, since a `tool_use_id` is unique per call, we also need to map `tool_use_id` to its assigned `frontend_sse_index` to correctly index tool results.
        ```python
        tool_id_to_frontend_idx: Dict[str, int] = {}
        ```

3.  **Assigning and Using the Frontend SSE Index:**
    *   Iterate through events from `self.llm.stream_message(...)`.
    *   For each `llm_event`, make a `sse_event_data = llm_event.get("data", {}).copy()`.
    *   Let `llm_original_idx = original_event_data.get("index")`.

    *   **On `text_block_start` or `tool_use_start` from LLM:**
        *   These events signify a new conceptual block.
        *   If `llm_original_idx` is not None:
            *   `assigned_frontend_idx = frontend_sse_index_allocator`
            *   `llm_internal_index_to_frontend_sse_index[llm_original_idx] = assigned_frontend_idx`
            *   If it's a `tool_use_start`, also map its `tool_id`:
                `tool_id_from_event = original_event_data.get("tool_id")`
                `if tool_id_from_event: tool_id_to_frontend_idx[tool_id_from_event] = assigned_frontend_idx`
            *   `sse_event_data["index"] = assigned_frontend_idx`
            *   `frontend_sse_index_allocator += 1`
        *   Yield the modified event: `yield {"event_type": event_type, "data": sse_event_data}`.

    *   **On `text_delta`, `content_block_stop` (for a text block), `tool_use_input_delta`:**
        *   If `llm_original_idx` is not None and is in `llm_internal_index_to_frontend_sse_index`:
            *   `sse_event_data["index"] = llm_internal_index_to_frontend_sse_index[llm_original_idx]`
        *   Else (should ideally not happen if start event was processed):
            *   Log a warning. Fallback to `frontend_sse_index_allocator - 1` or handle as an error.
        *   Yield the modified event.

    *   **On `content_block_stop` (for a `tool_use` block that is now complete and tool execution will follow):**
        *   Retrieve `assigned_frontend_idx = llm_internal_index_to_frontend_sse_index.get(llm_original_idx)`.
        *   Yield the `content_block_stop` with this `assigned_frontend_idx`.
        *   When executing the tool and yielding `tool_use_input_complete`, `tool_result`, or `tool_execution_error`:
            *   Use the `assigned_frontend_idx` (retrieved via `tool_id_to_frontend_idx` using the `tool_use_id`) in the `index` field of these SSE events.

    *   **For events not tied to a specific block `index` (e.g., `message_start`, `message_delta`, `llm_call_completed`, `stream_end` from ATP, `ping`):**
        *   These can be yielded without modifying their `index` (as they usually don't have one or it's not block-specific).

### 3.2. Example Scenario Flow:

1.  LLM: `text_block_start` (LLM index 0, thinking)
    *   Backend: `frontend_sse_index_allocator` is 0. Maps LLM idx 0 to frontend idx 0. Increments counter to 1.
    *   SSE to Frontend: `text_block_start` (data.index = 0)
2.  LLM: `text_delta` (LLM index 0)
    *   Backend: Looks up mapping for LLM idx 0, gets frontend idx 0.
    *   SSE to Frontend: `text_delta` (data.index = 0)
3.  LLM: `content_block_stop` (LLM index 0, for thinking)
    *   Backend: Looks up mapping for LLM idx 0, gets frontend idx 0.
    *   SSE to Frontend: `content_block_stop` (data.index = 0)
4.  LLM: `tool_use_start` (LLM index 1, tool_id="T1")
    *   Backend: `frontend_sse_index_allocator` is 1. Maps LLM idx 1 to frontend idx 1. Maps tool_id "T1" to frontend idx 1. Increments counter to 2.
    *   SSE to Frontend: `tool_use_start` (data.index = 1, tool_id="T1")
5.  LLM: `content_block_stop` (LLM index 1, for tool use)
    *   Backend: Looks up mapping for LLM idx 1, gets frontend idx 1.
    *   SSE to Frontend: `content_block_stop` (data.index = 1)
    *   (Tool executes)
    *   Backend: For tool result of "T1", retrieves mapped frontend_idx 1.
    *   SSE to Frontend: `tool_result` (data.index = 1, tool_use_id="T1")
6.  LLM: `text_block_start` (LLM index 0 again, for final JSON)
    *   Backend: `frontend_sse_index_allocator` is 2. **Recognizes this is a new block start.** Maps LLM idx 0 (for this *new instance* of content at LLM idx 0) to frontend idx 2. Increments counter to 3.
    *   SSE to Frontend: `text_block_start` (data.index = 2)
7.  LLM: `text_delta` (LLM index 0)
    *   Backend: Looks up mapping for current LLM idx 0 context (which is frontend idx 2).
    *   SSE to Frontend: `text_delta` (data.index = 2)
8.  LLM: `content_block_stop` (LLM index 0, for JSON)
    *   Backend: Looks up mapping for current LLM idx 0 context (frontend idx 2).
    *   SSE to Frontend: `content_block_stop` (data.index = 2)

This ensures the frontend receives `index: 0` for thinking, `index: 1` for the tool, and `index: 2` for the final JSON.

## 4. Required Code Changes in `src/agents/agent_turn_processor.py`

*   Add `frontend_sse_index_allocator` and `llm_internal_index_to_frontend_sse_index` (and potentially `tool_id_to_frontend_idx`) to `stream_turn_response`.
*   Implement the logic to assign and use these frontend-specific indices when preparing the `data` payload for `yield`ed SSE events. Pay close attention to correctly identifying the start of new conceptual blocks from the LLM's stream to know when to increment `frontend_sse_index_allocator` and create a new mapping.

## 5. Expected Frontend State (Post-Backend Change)

*   The frontend `AgentChatView.tsx` can rely on the `index` from SSE events being unique and sequential for distinct blocks.
*   The simplified `text_delta` handler (immutable append to `contentBlocks[index]`) will work correctly.
*   The `content_block_stop` handler (using `flatMap` to process `contentBlocks[index]`) will work correctly.
*   The `json_stream` type and `_originalIndex` (or `streamSourceIndex`) property will no longer be needed on the frontend.

This backend refactor is the most direct and robust way to solve the observed frontend issues.
