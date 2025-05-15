# Design Document: MCP Client Transport Handling

**Version:** 1.0
**Date:** 2025-05-15
**Author(s):** Ryan, Gemini

## 1. Introduction & Goals
    *   Document the current mechanisms for establishing and managing client connections in `MCPHost`.
    *   Clarify the roles of `ClientConfig`, `ClientManager`, `mcp-py` transport clients (`stdio_client`, `sse_client`), and `ClientSession`.
    *   Identify known issues, particularly around client task lifecycle management and shutdown (stalling).
    *   Propose potential improvements or areas for investigation.

## 2. Current Transport Mechanisms

    *   **2.1. Standard Input/Output (stdio)**
        *   **Configuration (`ClientConfig`):** `transport_type: "stdio"`, `server_path`.
        *   **Implementation (`ClientManager.manage_client_lifecycle`):**
            *   Uses `mcp.client.stdio.stdio_client` to launch a subprocess.
            *   Wraps reader/writer streams with `mcp.ClientSession`.
        *   **Pros:** Suitable for local Python MCP servers.
        *   **Cons/Issues:**
            *   Observed difficulties with clean subprocess shutdown when `MCPHost` initiates shutdown, potentially related to `anyio` task group ownership and cancellation propagation to subprocesses.

    *   **2.2. Server-Sent Events (SSE) - Current Implementation**
        *   **Configuration (`ClientConfig`):** `transport_type: "sse"`, `sse_url` (points to the GET endpoint for establishing the SSE stream).
        *   **Implementation (`ClientManager.manage_client_lifecycle`):**
            *   Uses `mcp.client.sse.sse_client` (from `mcp-py==1.6.0`).
            *   This client internally handles:
                *   GET request to `sse_url` to establish the event stream.
                *   Receiving an `event: endpoint` message specifying the URL for POSTing client messages.
                *   Managing separate tasks for reading SSE events and POSTing outgoing messages.
            *   Wraps reader/writer streams provided by `sse_client` with `mcp.ClientSession`.
        *   **Pros:** Enables connection to remote MCP servers that use this SSE pattern.
        *   **Cons/Issues:**
            *   Significant stalling issues observed during client shutdown (in `pytest` and API server). This appears to be due to `sse_client`'s internal tasks or underlying HTTP/SSE libraries not responding cleanly/promptly to `anyio` cancellation signals when initiated from `MCPHost`'s lifecycle management.
            *   The `mcp.client.sse.sse_client` seems to implement an older SSE pattern rather than the more unified "HTTP Stream Transport" described in some (possibly newer or JS-specific) MCP documentation.

    *   **2.3. HTTP Stream Transport (Not Currently Implemented/Available)**
        *   **Concept:** (Based on external MCP documentation) Unified HTTP endpoint, supports batch/stream responses, session headers.
        *   **`mcp-py==1.6.0` Status:** The `streamablehttp_client` mentioned in some examples is NOT found in the installed library version. This transport type is effectively unavailable with the current library.

## 3. Client Lifecycle Management in `MCPHost`

    *   **`MCPHost._client_runners_task_group`:** Main `anyio.TaskGroup` for all client lifecycle tasks.
    *   **`ClientManager.manage_client_lifecycle`:**
        *   Launched as a separate task for each client within `_client_runners_task_group`.
        *   Operates within its own `client_cancel_scope` passed from `MCPHost`.
        *   Responsible for:
            1.  Setting up the transport (`stdio_client` or `sse_client`) using an `async with` block.
            2.  Setting up `ClientSession` using another `async with` block, using streams from the transport.
            3.  Signaling `MCPHost` that the session is ready (via `task_status.started(session)`).
            4.  Waiting for cancellation (currently `await anyio.Event().wait()`).
    *   **Shutdown Process (`MCPHost.client_shutdown` or `MCPHost.shutdown_all_clients`):**
        1.  `MCPHost` cancels the specific `client_cancel_scope` for the client.
        2.  This *should* cause the `with client_cancel_scope:` block in `manage_client_lifecycle` to exit due to `anyio.get_cancelled_exc_class()`.
        3.  This *should* trigger the `__aexit__` methods of `ClientSession` and then the transport client (`stdio_client` or `sse_client`).
        4.  `ClientSession.__aexit__` closes its streams and cancels its internal handler task.
        5.  The transport client's `__aexit__` (e.g., `sse_client`) should cancel its internal tasks and close its resources (HTTP connections, subprocesses).
    *   **Observed Problem:** The propagation of cancellation or the cleanup within `sse_client` (and possibly `stdio_client` for subprocesses) seems incomplete or slow, preventing `manage_client_lifecycle` from exiting promptly, thus stalling `MCPHost` shutdown.

## 4. Message Routing (`MessageRouter`)
    *   Acts as a simple, in-memory registry.
    *   Maps component names (tools, prompts, resources) to lists of `client_id`s that provide them.
    *   Does not handle actual message sending or transport details.
    *   `MCPHost` uses it for discovery before selecting a `ClientSession` for actual communication.
    *   (This part seems to be working as intended and is largely independent of the transport stalling issues).

## 5. Analysis of Stalling Issue (Focus on SSE)

    *   The `debug_sse_client_stall.py` script demonstrated that `mcp.client.sse.sse_client` *can* shut down cleanly in a minimal, direct cancellation scenario.
    *   The issue in `MCPHost` is likely due to the interaction of multiple nested `anyio.CancelScope`s and `anyio.TaskGroup`s:
        *   `MCPHost`'s main task group and its per-client cancel scopes.
        *   `sse_client`'s internal task group.
    *   When `MCPHost` cancels a client's scope, the `manage_client_lifecycle` task receives the cancellation. The `async with sse_client(...)` block should then exit. `sse_client`'s `__aexit__` then cancels its *internal* task group. If tasks within that internal group (e.g., `sse_reader` waiting on `event_source.aiter_sse()`, or `post_writer` waiting on an `httpx` call or the `write_stream_reader`) don't respond to their cancellation quickly, `sse_client.__aexit__` blocks, and the stall propagates upwards.
    *   The `httpx-sse` library or `httpx` itself might not be fully compatible with `anyio`'s cancellation model in all edge cases, or `mcp.client.sse.py` might not be using their cancellation features correctly.

## 6. Proposed Next Steps & Potential Solutions (for investigation)

    *   **6.1. Deeper Dive into `mcp.client.sse.py` and `httpx-sse`:**
        *   Review how `httpx_sse.aconnect_sse` and `event_source.aiter_sse()` handle cancellation.
        *   Review how `httpx.AsyncClient` and its `post` calls handle cancellation, especially if a connection is active or a response is being awaited.
        *   Consider if explicit timeouts on `httpx` calls within `sse_client` might help, though cancellation should be the primary mechanism.

    *   **6.2. Modify `sse_example_server.py` for Robustness (Minor):**
        *   While likely not the root cause of the client-side stall, ensure the server handles client disconnects gracefully (FastAPI/Starlette usually do this well). The current pings are fine.

    *   **6.3. Investigate `MCPHost`'s Client Shutdown Logic:**
        *   Ensure the order of operations in `MCPHost.client_shutdown` and `MCPHost.shutdown` is optimal for allowing tasks to clean up.
        *   Could adding a small `anyio.sleep(0)` after requesting cancellation of `client_cancel_scope` give the event loop a chance to process the cancellation before `manage_client_lifecycle`'s `finally` block cleans up `active_clients`? (This is speculative).

    *   **6.4. Consider Alternatives if `mcp.client.sse.py` is problematic:**
        *   If `mcp.client.sse.py` proves too difficult to get working reliably with `anyio` cancellation, and given the "HTTP Stream Transport" is the future direction (even if not in `mcp-py 1.6.0`):
            *   Could we implement a *basic* HTTP stream client ourselves using `httpx` and `httpx-sse` directly within `manage_client_lifecycle`, giving us more direct control over its tasks and cancellation? This would be a significant undertaking.
            *   Check for newer versions of `mcp-py` that might have better HTTP/SSE support or have fixed these issues.

    *   **6.5. Address `stdio_client` Shutdown:**
        *   Separately investigate the `stdio_client` shutdown issues. This might involve ensuring the subprocess is explicitly terminated (`proc.terminate()`, `proc.kill()`) and its streams are closed in the correct order, potentially with timeouts. `anyio.Process` might offer more robust subprocess management if `mcp.client.stdio.stdio_client` is too opaque.

## 7. Open Questions
    *   What is the exact cancellation behavior of `event_source.aiter_sse()` from `httpx-sse` when its wrapping task/scope is cancelled?
    *   How does `httpx.AsyncClient.post()` behave if its surrounding task is cancelled mid-request?
    *   Is there any specific guidance from `mcp-py` or `anyio` maintainers on managing nested task groups and context managers that involve I/O resources like HTTP connections or subprocesses, especially regarding reliable cancellation?

