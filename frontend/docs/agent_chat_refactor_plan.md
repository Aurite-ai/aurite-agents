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

## 3. Proposed Solution

The core of the solution is to modify how `tool_result` and `tool_execution_error` events are handled within the `updateStreamingMessageBlocks` function in `AgentChatView.tsx`. Instead of appending these blocks, they will be inserted directly after their corresponding `tool_use` block.

### 3.1. Key Changes in `AgentChatView.tsx`

1.  **`content_block_stop` Event Handler (Revised Logic):**
    *   This is the most critical change. When a `content_block_stop` event is received for a text block at a given `index`:
        *   The handler will parse the accumulated text content of `contentBlocks[index]`.
        *   It will attempt to extract `<thinking>...</thinking>` tags (`extractedThinkingText`) and the remaining text (`textForJsonParsing`).
        *   It will attempt to parse `textForJsonParsing` as JSON (`parsedJsonData`).
        *   **Scenario 1: Both `extractedThinkingText` and valid `parsedJsonData` are found within the same original text block:**
            *   The block at `contentBlocks[index]` will be updated to become a `text` block containing *only* the `extractedThinkingText`.
            *   A *new* `AgentOutputContentBlock` of `type: 'final_response_data'` will be created for `parsedJsonData`.
            *   This new `final_response_data` block will be **pushed** to the end of the `contentBlocks` array. This ensures it appears after any tool calls that might have their own `index` values.
        *   **Scenario 2: Only valid `parsedJsonData` is found (no `extractedThinkingText` in this specific block):**
            *   The block at `contentBlocks[index]` will be converted into a `type: 'final_response_data'` block, preserving its original `index`.
        *   **Scenario 3: Only `extractedThinkingText` is found (the rest is not valid JSON):**
            *   The block at `contentBlocks[index]` will be updated to a `text` block containing the `extractedThinkingText` (and any non-JSON remainder).
        *   **Scenario 4: Plain text (no thinking, not JSON):**
            *   The block remains as `type: 'text'`; no specific change needed by `content_block_stop` beyond what `text_delta` accumulated.

2.  **`tool_result` Event Handler (Logic remains as previously planned):**
    *   When a `tool_result` event is received:
        *   Identify the `tool_use_id`.
        *   Find the `tool_use` block in `contentBlocks` by its `id`.
        *   Create the new `tool_result` block.
        *   Use `Array.prototype.splice(toolCallBlockIndex + 1, 0, newToolResultBlock)` to insert it immediately after the found `tool_use` block.
        *   Fallback to appending if the `tool_use` block is not found (with a warning).

3.  **`tool_execution_error` Event Handler (Logic remains as previously planned):**
    *   Apply the same `findIndex` and `splice` logic as for `tool_result` to insert the error block (typed as `tool_result` with `is_error: true`) after its corresponding `tool_use` block.

### 3.2. Expected Chronological Order

With these changes, the display order should be:
1.  Agent's initial text/thinking (at its original `index`).
2.  Tool Call (at its original, subsequent `index`).
3.  Tool Result (spliced in immediately after its Tool Call).
4.  Agent's final structured response (pushed to the end of all blocks for that turn, if it was separated from thinking text that shared its original `index`).

### 3.3. Compatibility Confirmation

*   **`src/components/common/StreamingMessageContentView.tsx`:** This component renders blocks in the order they are present in the `blocks` prop. The proposed changes will ensure the `blocks` array is correctly ordered, so `StreamingMessageContentView` will render them chronologically without needing modification.
*   **`src/types/projectManagement.ts` (`AgentOutputContentBlock`):** The existing type definitions for `AgentOutputContentBlock` (including `id` for `tool_use` and `tool_use_id` for `tool_result`) are sufficient and support this refactoring. No changes to types are anticipated.

## 4. Implementation Steps

1.  **Modify `content_block_stop` event listener in `AgentChatView.tsx`:**
    *   Locate the `eventSource.addEventListener('content_block_stop', ...)` block.
    *   Inside the `updateStreamingMessageBlocks` callback, specifically within the `else if (currentBlock.type === 'text' && currentBlock.text)` condition:
        *   Implement the logic to extract `extractedThinkingText` and `textForJsonParsing`.
        *   Attempt to parse `textForJsonParsing` into `parsedJsonData`.
        *   Based on whether `extractedThinkingText` and `parsedJsonData` exist:
            *   If both exist: Update `newBlocks[index]` to be a `text` block with only thinking. Create a new `final_response_data` block for the JSON and `newBlocks.push()` it.
            *   If only JSON exists: Convert `newBlocks[index]` to `final_response_data`.
            *   If only thinking exists: Update `newBlocks[index]` to be a `text` block with thinking (and any non-JSON remainder).
            *   Ensure unique IDs are generated for any newly created blocks.

2.  **Verify/Confirm `tool_result` event listener in `AgentChatView.tsx`:**
    *   Ensure the logic implemented in the previous iteration (using `findIndex` and `splice`) is correctly in place as per section 3.1.2.

3.  **Verify/Confirm `tool_execution_error` event listener in `AgentChatView.tsx`:**
    *   Ensure the logic implemented in the previous iteration (using `findIndex` and `splice`) is correctly in place as per section 3.1.3.

4.  **Testing:**
    *   Manually test the chat view with an agent that:
        *   Outputs thinking, then a tool call, then its result, then a final JSON response.
        *   Outputs thinking and a final JSON response in the same text stream (without an intermediate tool call).
        *   Outputs only thinking.
        *   Outputs only a final JSON response.
        *   Outputs plain text.
    *   Verify the chronological order in all scenarios.
    *   Check browser console for any new warnings or errors.

## 5. Anticipated Issues/Risks

*   **Complexity in `content_block_stop`:** The logic for handling combined thinking/JSON text streams adds complexity. Careful implementation is needed.
*   **Off-by-one errors with `splice` (for tool results):** Still relevant, ensure `toolCallBlockIndex + 1` is correct.
*   **Backend `index` assumptions:** The plan relies on the backend providing consistent `index` values for distinct "operations" (initial text, tool call). If a final JSON response (that was *not* part of an initial text stream with thinking) is sent with an `index` by the backend, the current "push" logic for separated JSON might need refinement to respect that `index` if it's intended to be placed before other later-indexed items. For now, pushing ensures it comes after earlier indexed tool calls.
*   **Performance:** Still expected to be negligible.

## 6. Future Considerations

*   This more robust refactor should significantly improve the chronological accuracy and lay a better foundation for the "simple workflow UI".
*   Further clarification on the backend's SSE `index` strategy for different content block types could help simplify frontend logic in the long term.
