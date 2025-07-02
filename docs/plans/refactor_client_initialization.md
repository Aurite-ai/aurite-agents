# Implementation Plan: Resilient Client Initialization

**Version:** 1.0
**Date:** 2025-06-30
**Author(s):** Gemini
**Related Design Document (Optional):** N/A

## 1. Goals
*   Re-architect the client initialization process in `MCPHost` to be resilient to individual client connection failures.
*   Ensure that a failure to connect to one MCP server does not prevent other servers from initializing.
*   Ensure the application logs the error for the failed client but starts up successfully with the available clients.
*   Decouple the failure-prone connection logic from the long-term session lifecycle management.

## 2. Scope
*   **In Scope:**
    *   `src/aurite/host/host.py`: Major changes to `initialize` and `_initialize_client` methods.
    *   `src/aurite/host/foundation/clients.py`: Significant refactoring of `manage_client_lifecycle` into separate connection and monitoring functions.
*   **Out of Scope:**
    *   Changing the fundamental transport logic (e.g., how `stdio_client` works).
    *   Modifying any other part of the framework beyond the host's client management.

## 3. Implementation Steps

The core idea is to separate the connection attempt from the long-running monitoring task. The connection will be attempted directly in the main initialization loop, where exceptions can be caught cleanly. Only upon a successful connection will a background monitoring task be started.

---

**Phase 1: Refactor `ClientManager` (`src/aurite/host/foundation/clients.py`)**

1.  **Step 1.1: Create `connect_to_client` function**
    *   **File(s):** `src/aurite/host/foundation/clients.py`
    *   **Action:**
        *   Create a new `async` method in `ClientManager` called `connect_to_client`.
        *   This method will take `client_config: ClientConfig` and `security_manager: SecurityManager` as arguments.
        *   It will contain *only* the logic for establishing a transport context and creating a `ClientSession`.
        *   It will be responsible for resolving environment variables and secrets.
        *   Crucially, it will use an `AsyncExitStack` to manage the transport and session contexts. When the function returns, it will pass the `AsyncExitStack` and the `ClientSession` back to the caller. This transfers ownership of the lifecycle management to the caller.
        *   It will **not** use `task_status` or `anyio.sleep_forever()`.
        *   It will return a tuple: `(ClientSession, AsyncExitStack)`.
    *   **Verification:** This is a structural change. Verification will happen when testing the integrated `MCPHost`.

2.  **Step 1.2: Create `monitor_client_session` function**
    *   **File(s):** `src/aurite/host/foundation/clients.py`
    *   **Action:**
        *   Create a new `async` method in `ClientManager` called `monitor_client_session`.
        *   This method will take `client_id: str`, `session: ClientSession`, and `exit_stack: AsyncExitStack` as arguments.
        *   Its entire body will be a `try...finally` block.
        *   The `try` block will contain `await anyio.sleep_forever()`.
        *   The `finally` block will log the shutdown and call `await exit_stack.aclose()`, which will cleanly close the session and transport. It will also remove the client from `self.active_clients`.
    *   **Verification:** This is a structural change. Verification will happen when testing the integrated `MCPHost`.

3.  **Step 1.3: Remove `manage_client_lifecycle`**
    *   **File(s):** `src/aurite/host/foundation/clients.py`
    *   **Action:** Delete the old `manage_client_lifecycle` method entirely.
    *   **Verification:** The code should still lint correctly.

---

**Phase 2: Refactor `MCPHost` (`src/aurite/host/host.py`)**

1.  **Step 2.1: Modify `_initialize_client`**
    *   **File(s):** `src/aurite/host/host.py`
    *   **Action:**
        *   Remove the `tg.start()` call.
        *   Directly `await self.client_manager.connect_to_client(...)`. This call will be inside the `try...except` block that already exists in the `initialize` loop.
        *   If the connection is successful, `connect_to_client` will return a `session` and an `exit_stack`.
        *   Store the session in `self.client_manager.active_clients`.
        *   Proceed with the existing registration logic (sending `initialize` request, registering components, etc.).
        *   After successful registration, use `self._client_runners_task_group.start_soon()` to call `self.client_manager.monitor_client_session`, passing it the `client_id`, `session`, and `exit_stack`.
    *   **Verification:** The logic flow should match the new architecture.

2.  **Step 2.2: Adjust `initialize` loop**
    *   **File(s):** `src/aurite/host/host.py`
    *   **Action:**
        *   The `try...except (Exception, ExceptionGroup)` block around the `await self._initialize_client(client_config)` call is now the primary mechanism for catching connection errors.
        *   Ensure the logging within this `except` block is clear that a specific client failed but the host is continuing.
    *   **Verification:** The loop should no longer be interrupted by a single client failure.

3.  **Step 2.3: Adjust `shutdown` logic**
    *   **File(s):** `src/aurite/host/host.py`
    *   **Action:**
        *   The `shutdown` and `client_shutdown` methods will now work by cancelling the `monitor_client_session` tasks via their cancel scopes. The `finally` block within `monitor_client_session` will handle the actual resource cleanup by closing the `AsyncExitStack`.
        *   Review `shutdown` and `shutdown_all_clients` to ensure they correctly cancel the new monitoring tasks. The current logic of cancelling the task group should be sufficient.
    *   **Verification:** Shutting down the host should cleanly close all active client connections.

---

## 4. Testing Strategy
*   **Unit Tests:**
    *   The primary verification will be through the existing integration tests for the host, which were previously failing.
    *   Modify `tests/host/test_host_lifecycle.py` to include a test case with one valid client and one invalid client (e.g., with a bad `http_endpoint`).
*   **Manual Verification:**
    *   Run the application with the problematic `aurite_config.json` that has the broken `stock_analysis` client.
    *   **Expected Outcome:** The application should log an error for the `stock_analysis` client but start successfully. Other clients should be available and usable.
*   **Key Scenarios to Cover:**
    *   Host starts successfully when all clients are valid.
    *   Host starts successfully when one or more clients are invalid.
    *   Host correctly shuts down all active clients.

## 5. Final Documentation Review
*   When the implementation is complete and all tests are passing, review `.clinerules/documentation_guide.md` to identify all documents that require updates, read them, and then propose the necessary changes. The most likely candidates for updates are `docs/layers/3_host.md` and `docs/layers/2_orchestration.md` to reflect the new client lifecycle management process.
