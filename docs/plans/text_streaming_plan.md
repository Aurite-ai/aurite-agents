# Implementation Plan: Agent Response Streaming & Tool Call Display

**Date:** 2025-05-10
**Author:** Gemini (AI Assistant for Ryan)
**Status:** Proposed

## 1. Goals

1.  **Display Agent Tool Calls:** Enhance the frontend chat UI to display tool calls made by an agent and their corresponding results as distinct messages or parts of messages within the conversation flow.
2.  **Implement Text Streaming:** Introduce Server-Sent Events (SSE) to stream agent responses (including text chunks, tool call information, and tool results) to the frontend, allowing users to see the agent's activity and response generation in real-time.
3.  **Maintain Existing Functionality:** Ensure the current non-streaming agent execution pathway remains functional.

## 2. Background & Context

Currently, the agent execution endpoint returns the full `AgentExecutionResult` after the entire agent run is complete. This includes the final response and the complete conversation history. The frontend displays the final response and has recently been styled.

The new requirements are to:
*   Make intermediate steps (tool calls and results) visible in the UI.
*   Stream the agent's thought process and final response token by token, or chunk by chunk.

Anthropic's streaming API for Messages provides a detailed event flow (`message_start`, `content_block_start`, `content_block_delta` for text and tool input JSON, `content_block_stop`, `message_delta`, `message_stop`) which will be leveraged.

## 3. Proposed Phased Implementation

### Phase 0: Pre-requisite - Backend Data Confirmation

*   **Task:** Verify that the current non-streaming agent execution endpoint (`/api/agents/{agent_name}/execute`) in `src/bin/api/routes/components_api.py` returns the *complete* `conversation` array within the `AgentExecutionResult`. This array should include all `tool_use` blocks from the assistant and subsequent `user` role messages containing `tool_result` blocks.
*   **Verification:** Test with an agent that uses tools. Log the full response in the frontend or use an API client.
*   **Contingency:** If not, modify the endpoint and underlying logic (`Agent._prepare_agent_result`) to include the full conversation.

### Phase 1: Backend - LLM Streaming Foundation

*   **Objective:** Enable streaming at the LLM client level.
*   **Tasks:**
    1.  **Modify `src/llm/base_client.py`:**
        *   Define a new abstract async generator method `stream_message` in `BaseLLM`.
        *   This method should be designed to `yield` dictionaries representing distinct events (e.g., `{"event_type": "text_delta", "data": ...}`, `{"event_type": "tool_use_start", "data": ...}`).
            ```python
            from typing import AsyncGenerator, Union, Dict, List, Optional, Any # Ensure all are imported
            from ...config.config_models import LLMConfig # Relative import for LLMConfig

            @abstractmethod
            async def stream_message(
                self,
                messages: List[Dict[str, Any]],
                tools: Optional[List[Dict[str, Any]]],
                system_prompt_override: Optional[str] = None,
                schema: Optional[Dict[str, Any]] = None,
                llm_config_override: Optional[LLMConfig] = None,
            ) -> AsyncGenerator[Dict[str, Any], None]:
                raise NotImplementedError
                yield {} # Placeholder for linter
            ```
    2.  **Modify `src/llm/providers/anthropic_client.py`:**
        *   Implement the `stream_message` method in `AnthropicLLM`.
        *   Utilize `self.anthropic_sdk_client.messages.stream(...)`.
        *   Iterate through the SSE events from Anthropic (`message_start`, `content_block_start`, `content_block_delta`, etc.).
        *   Translate these Anthropic events into our standardized dictionary format to be yielded. Example translations:
            *   `content_block_delta` with `delta.type == "text_delta"` -> `yield {"event_type": "text_delta", "index": event.index, "text_chunk": event.delta.text}`
            *   `content_block_start` with `content_block.type == "tool_use"` -> `yield {"event_type": "tool_use_start", "index": event.index, "tool_name": event.content_block.name, "tool_id": event.content_block.id, "input_so_far": ""}` (Initialize `input_so_far`)
            *   `content_block_delta` with `delta.type == "input_json_delta"` -> `yield {"event_type": "tool_use_input_delta", "index": event.index, "json_chunk": event.delta.partial_json}`
            *   `content_block_stop` for a `tool_use` block -> `yield {"event_type": "tool_use_end", "index": event.index}`
            *   `message_stop` -> `yield {"event_type": "stream_end", "reason": event.message.stop_reason, "usage": event.message.usage.model_dump_json() if event.message.usage else None}`
        *   Handle `ping` and `error` events from the Anthropic stream appropriately.

### Phase 2: Backend - Propagate Streaming Logic Upwards

*   **Objective:** Create new streaming methods in the agent execution pipeline.
*   **Tasks:**
    1.  **`src/agents/agent_turn_processor.py` (`AgentTurnProcessor`):**
        *   Add new async generator method `stream_turn_response`.
        *   Calls `self.llm.stream_message()`.
        *   Yields text chunks directly.
        *   **Tool Handling within Stream:**
            *   When `tool_use_start` is yielded by the LLM, the processor notes it.
            *   Accumulates `tool_use_input_delta` chunks.
            *   On `tool_use_end`, parses the complete JSON input.
            *   Calls `self.host.execute_tool(...)`.
            *   Yields a `{"event_type": "tool_result", "tool_name": ..., "tool_id": ..., "output": ...}` event.
            *   This requires careful state management within the generator.
    2.  **`src/agents/agent.py` (`Agent`):**
        *   Add new async generator method `stream_conversation`.
        *   Manages the conversation loop, calling `turn_processor.stream_turn_response()` in each iteration.
        *   Yields events from the turn processor.
        *   Handles appending tool results (received from `stream_turn_response`) to the message history for subsequent LLM interactions within the same streaming session.
    3.  **`src/execution/facade.py` (`ExecutionFacade`):**
        *   Add new async generator method `stream_agent_run`.
        *   Instantiates the `Agent` with necessary configs and initial messages.
        *   Calls `agent_instance.stream_conversation()` and yields its events.
    4.  **`src/host_manager.py` (`HostManager`):**
        *   Add new async generator method that calls `self.execution.stream_agent_run()`.
    5.  **`src/bin/api/routes/components_api.py`:**
        *   Create new FastAPI endpoint: `/agents/{agent_name}/execute-stream` (e.g., using `GET` with query params for user message, or `POST` if request body is complex and supported by SSE clients).
        *   Use FastAPI's `StreamingResponse(media_type="text/event-stream")`.
        *   The generator for `StreamingResponse` will:
            *   Call the `HostManager`'s streaming method.
            *   Iterate through the yielded event dictionaries.
            *   Format each dictionary into an SSE string: `event: <event_type>\ndata: <json_string_of_data>\n\n`.
            *   Yield these SSE formatted strings.

### Phase 3: Frontend - Display Full Conversation (Non-Streaming First)

*   **Objective:** Ensure UI components exist for all message types, using the current non-streaming API.
*   **Tasks (`frontend/src/features/execute/views/AgentChatView.tsx`):**
    1.  Modify `handleSend` to process the *entire* `executionResult.conversation` array (assuming Phase 0 confirmed data availability).
    2.  Iterate through each message in `conversation`.
    3.  For assistant messages, iterate through their `content` blocks.
    4.  Create and use new React components:
        *   `ToolCallView.tsx`: Displays `tool_use` blocks (name, input).
        *   `ToolResultView.tsx`: Displays `tool_result` blocks (result content, status).
    5.  Style these new components to be distinct and readable.

### Phase 4: Frontend - Integrate Streaming Functionality

*   **Objective:** Adapt the frontend to consume the new streaming SSE endpoint.
*   **Tasks (`frontend/src/features/execute/views/AgentChatView.tsx`):**
    1.  **EventSource:**
        *   On message send, instantiate `new EventSource(\`/api/agents/${agentName}/execute-stream?user_message=${encodedMessage}&system_prompt=...\`)`. (Adjust URL and parameter passing as needed).
    2.  **State Management for Streaming:**
        *   Maintain a "current_assistant_message_parts" state variable (e.g., an array of content blocks being built).
        *   When a message stream starts, add a new placeholder assistant message to the `messages` array.
        *   Update this placeholder message in-place as new parts arrive.
    3.  **Event Listeners:**
        *   `eventSource.addEventListener('text_delta', event => ...)`: Append text to the last text block in `current_assistant_message_parts`.
        *   `eventSource.addEventListener('tool_use_start', event => ...)`: Add a new tool_call object (with name, id) to `current_assistant_message_parts`. Render `ToolCallView` in a pending/loading state.
        *   `eventSource.addEventListener('tool_use_input_delta', event => ...)`: Append `partial_json` to the input string of the current tool_call object.
        *   `eventSource.addEventListener('tool_use_end', event => ...)`: Mark the current tool_call input as complete. Parse the accumulated JSON.
        *   `eventSource.addEventListener('tool_result', event => ...)`: Add a tool_result object to `current_assistant_message_parts`. Render `ToolResultView`.
        *   `eventSource.addEventListener('stream_end', event => ...)`: Finalize the current assistant message. `eventSource.close()`.
        *   `eventSource.onerror = error => ...`: Handle errors, display an error message, `eventSource.close()`.
    4.  **Rendering:** The `messages.map(...)` logic will render based on the structure of these incrementally built message objects and their content parts.

## 4. Key Considerations & Challenges

*   **Error Handling:** Robust error handling is needed at each stage of the stream, both backend and frontend.
*   **Tool Execution in Stream:** The `AgentTurnProcessor`'s `stream_turn_response` will be complex. It needs to pause LLM output streaming, execute a tool (which might be async), get the result, yield the tool result as an event, and then potentially resume LLM streaming or instruct the `Agent` class to make a new LLM call with the tool result.
*   **State Management (Frontend):** Managing the incremental updates to the UI and the state of partially constructed messages will be challenging.
*   **Backpressure/Flow Control:** Not typically an issue with SSE for text, but good to be aware of if data chunks are very large or rapid.
*   **Anthropic Event Granularity:** The `input_json_delta` for tool use means the frontend (or backend stream processor) will need to accumulate these partial JSON strings and parse them upon `content_block_stop` for that tool.
*   **Transactionality of History:** If streaming, when and how is conversation history (including partial thoughts or tool calls) saved? The current plan saves full history after the non-streaming `run_agent` completes. For streaming, this might need to be adapted (e.g., save on `stream_end`).

## 5. Testing Strategy

*   **Unit Tests:** For new methods in LLM clients, turn processor, agent, facade.
*   **Integration Tests (Backend):** Test the full streaming pipeline from API endpoint to LLM client, mocking tool execution.
*   **Manual Frontend Testing:** Thoroughly test UI rendering for text chunks, tool calls (pending, input accumulation, final), tool results, and error states. Test with various agents and tool interactions.
*   **API Level Testing:** Use `curl` or an API client to directly test the SSE endpoint and inspect the raw event stream.

This plan provides a structured approach to these complex but valuable features.
