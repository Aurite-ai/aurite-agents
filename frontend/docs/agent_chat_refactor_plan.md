# Implementation Plan: Agent Chat View Chronological Ordering Refactor

**Date:** 2025-05-11
**Author:** Gemini (AI Assistant)
**Reviewer:** Ryan

## 1. Objective

To refactor the `src/features/execute/views/AgentChatView.tsx` component to ensure that agent output, including thinking, tool calls, tool results, and final responses, are displayed in strict chronological order. This will improve the user experience and make the chat flow easier to understand. This change will also support future reusability of chat components for simple workflow UIs.

## 2. Background

Currently, the `AgentChatView.tsx` component processes Server-Sent Events (SSE) to display an agent's turn. While most content blocks (text, tool use initiation) are placed using an `index` from the backend, `tool_result` and `tool_execution_error` events append new blocks to the `contentBlocks` array. This can lead to tool results appearing after the agent's subsequent final response, breaking the chronological flow.

For example, the observed incorrect order is:
1.  Agent's final text/response (e.g., from `text_delta` and `content_block_stop` at `index: 0`)
2.  Tool Call (e.g., from `tool_use_start` at `index: 1`)
3.  Tool Result (pushed to the end of the `contentBlocks` array)

The desired order is:
1.  Agent's initial text/thinking
2.  Tool Call
3.  Tool Result
4.  Agent's final text/response (if any, after the tool interaction)

## 3. Proposed Solution (Revised Strategy)

To address persistent ordering and styling issues, the strategy involves introducing new content block types for intermediate streaming states and refining the logic in both `text_delta` and `content_block_stop` event handlers in `AgentChatView.tsx`.

### 3.1. New/Updated Content Block Types

The following types will be added/clarified in `src/types/projectManagement.ts` for `AgentOutputContentBlock.type`:
*   `'text'`: Will continue to be used for plain text, and as an initial state for text being streamed by `text_delta` that might become thinking.
*   `'thinking_finalized'`: A new type for a block that contains only finalized thinking text. This allows specific styling.
*   `'json_stream'`: A new type for a block that is actively accumulating the text of a (potential) final JSON response. This block will be created and pushed to the end of `contentBlocks` as soon as JSON streaming is detected following thinking text within the same backend-indexed stream.
*   `'final_response_data'`: Remains for finalized JSON data.
*   `'tool_use'`, `'tool_result'`: Remain unchanged.

### 3.2. Key Changes in `AgentChatView.tsx` (Further Refined)

1.  **`text_delta` Event Handler (Refined Logic):**
    *   When a `text_chunk` arrives for a given `index`:
        *   Initialize `newBlocks[index]` as `type: 'text'` if it doesn't exist or is a placeholder. Let this be `blockAtIndex`.
        *   **If `blockAtIndex.text` already contains a complete `</thinking>` tag:**
            *   This means `blockAtIndex` has finished its thinking phase. The current `text_chunk` must belong to the associated `json_stream`.
            *   Find or create a single `json_stream` block (associated with `_originalIndex: index`) at the end of `newBlocks`.
            *   Append `text_chunk` to this `json_stream` block.
        *   **Else (text is for `blockAtIndex`):**
            *   Append `text_chunk` to `blockAtIndex.text`.
            *   **If `text_chunk` itself contained `</thinking>` (thus completing the thinking part now):**
                *   Split `blockAtIndex.text` into the thinking part (up to and including `</thinking>`) and the `beyondThinkingPart`.
                *   Update `blockAtIndex.text` to only contain the thinking part.
                *   If `beyondThinkingPart` is not empty, find or create the `json_stream` block (as above) and append `beyondThinkingPart` to it.
    *   This ensures that as soon as `</thinking>` is processed for an indexed block, all subsequent text (even if part of the same `text_chunk` or later chunks for the same backend `index`) is immediately routed to the correct, separate `json_stream` block.

2.  **`content_block_stop` Event Handler (Refined Logic):**
    *   When `content_block_stop` arrives for `index`:
        *   Let `blockToFinalize = newBlocks[index]`.
        *   **If `blockToFinalize.type === 'text'`:**
            *   Match for `<thinking>content</thinking>`.
            *   If a match is found, change `blockToFinalize.type` to `'thinking_finalized'` and set `blockToFinalize.text` to *only* the extracted `content` (without the tags).
            *   The `text_delta` handler is now solely responsible for splitting off any text that appeared *after* `</thinking>` into a `json_stream` block. `content_block_stop` no longer deals with this split.
            *   If no thinking tags are found, the block remains `type: 'text'`.
        *   This handler does NOT attempt to parse JSON from the indexed block.

3.  **`stream_end` Event Handler (Primary JSON Finalization):**
    *   This handler is now the primary place where `json_stream` blocks are converted.
    *   Iterate through all `contentBlocks`. If a block is `type: 'json_stream'`:
        *   Attempt to parse its `text`.
        *   If successful, convert it to `type: 'final_response_data'` with the `parsedJson`.
        *   If unsuccessful, convert it to `type: 'text'` (e.g., with an error message or the raw unparseable text).

4.  **`tool_use_start` Event Handler:** (No change)
5.  **`tool_result` and `tool_execution_error` Event Handlers:** (No change from previous correct logic)

### 3.3. Expected Chronological Order & Behavior (Reaffirmed)

*   Thinking text streams into its indexed block (initially `type: 'text'`).
*   If JSON text follows thinking (even in the same `text_chunk` that contains `</thinking>`), `text_delta` immediately splits the post-thinking part and routes it to a *new* `json_stream` block (pushed to the end). The indexed block's text is truncated to only include the thinking part.
*   `content_block_stop` for the original index finalizes the thinking block from `type: 'text'` to `type: 'thinking_finalized'`, using the (now purely thinking) text.
*   The `json_stream` block (at the end) continues to accumulate its JSON content from subsequent `text_delta` calls (if any).
*   `stream_end` finalizes any `json_stream` blocks into `final_response_data`.
*   Tool calls and results are handled as before.
*   This should prevent JSON mangling and ensure correct styling and ordering.

### 3.4. Compatibility Confirmation

*   **`src/types/projectManagement.ts`:** Needs updates for `thinking_finalized`, `json_stream`.
*   **`src/components/common/StreamingMessageContentView.tsx`:** Needs to be updated to handle rendering for `thinking_finalized` (with specific styling) and `json_stream` (as raw streaming text).

## 4. Implementation Steps (Order of file changes adjusted for clarity)

1.  **Verify `src/types/projectManagement.ts`:**
    *   Ensure `'thinking_finalized'`, `'json_stream'`, and optional `_originalIndex?: number` are correctly defined in `AgentOutputContentBlock.type`. (Done in previous iteration).

2.  **Verify `src/components/common/StreamingMessageContentView.tsx`:**
    *   Ensure rendering cases for `'thinking_finalized'` (with styling) and `'json_stream'` (raw text) are correct.
    *   Ensure `final_response_data` does not use `thinkingText`. (Done in previous iteration).

3.  **Refactor `text_delta` event listener in `AgentChatView.tsx`:**
    *   Implement the refined logic from section 3.2.1 to handle the split between thinking text (in the indexed block) and subsequent JSON text (in a pushed `json_stream` block), including immediate splitting if `</thinking>` is in the current `text_chunk`.

4.  **Refactor `content_block_stop` event listener in `AgentChatView.tsx`:**
    *   Implement the simplified logic from section 3.2.2: only convert `text` blocks with thinking content to `thinking_finalized` (storing only inner thinking text). No JSON parsing here.

5.  **Verify `stream_end` event listener in `AgentChatView.tsx`:**
    *   Ensure it correctly iterates `contentBlocks` and finalizes any `json_stream` blocks to `final_response_data` or `text`. (Logic from previous iteration should be mostly correct).

6.  **Verify `tool_result` and `tool_execution_error` listeners:** (No change expected).

7.  **Testing (Comprehensive):**
    *   Scenario: Thinking followed immediately by JSON in the same backend stream. Verify JSON streams into its own block at the end from the start.
    *   Scenario: Only thinking. Verify it's styled correctly.
    *   Scenario: Thinking, then tool call, then tool result, then final JSON (that was part of the initial stream with thinking).
    *   Verify no "jump" of the final JSON response.
    *   Verify thinking text styling is consistently applied.

## 5. Anticipated Issues/Risks

*   **Complexity in `text_delta` and `content_block_stop`:** The logic to differentiate and route text streams is intricate.
*   **State management for `json_stream`:** Ensuring only one active `json_stream` is appended per assistant message if multiple `text_delta` chunks trigger the post-thinking logic. A simple flag or checking the last block's type might be needed.
*   **Finalization of `json_stream`:** Relying on `stream_end` for `json_stream` blocks is a good catch-all.

## 6. Future Considerations

*   This comprehensive approach should yield the correct visual behavior and robustly handle various streaming sequences.
