# Implementation Plan: Refactor Client Management for AnyIO Shutdown Issue

**Version:** 1.0
**Date:** 2025-05-12
**Author(s):** Ryan, Gemini

## 1. Goals

*   Refactor `MCPHost` and `ClientManager` to use `anyio`'s structured concurrency (TaskGroups and CancelScopes) for managing the lifecycle of individual MCP client connections.
*   Resolve the "Event loop is closed" / "Cannot run shutdown() while loop is stopping" errors encountered during test teardown when clients are shut down.
*   Ensure robust and clean startup and shutdown of client processes and sessions.

## 2. Scope

This plan primarily involves changes to:
*   `src/host/host.py` (MCPHost)
*   `src/host/foundation/clients.py` (ClientManager)
*   Related test files, particularly integration tests involving host/client lifecycle.

The core refactoring from `docs/plans/layer3_refactoring_plan.md` (Async GCP, Root Validation, Component Unregistration) is considered prerequisite and already completed. This plan focuses specifically on the client lifecycle management with `anyio`.

## 3. Implementation Steps

**Phase 1: Modify `ClientManager`**

1.  **Add `manage_client_lifecycle` method to `ClientManager`:**
    *   **File:** `src/host/foundation/clients.py`
    *   **Action:**
        *   Define a new `async def manage_client_lifecycle(self, client_config: ClientConfig, security_manager: SecurityManager, client_cancel_scope: anyio.CancelScope, *, task_status: anyio.abc.TaskStatus[ClientSession])`.
        *   This method will encapsulate the `async with stdio_client(...)` and `async with ClientSession(...)` blocks.
        *   Inside the `ClientSession` block, it will:
            *   Store the `session` in `self.active_clients[client_id]`.
            *   Call `task_status.started(session)` to signal readiness and pass the session back to the caller (`MCPHost`).
            *   Call `await anyio.sleep_forever()` to keep the client task alive until its `client_cancel_scope` is cancelled.
        *   Wrap the core logic in `with client_cancel_scope:` to make the task responsive to cancellation.
        *   Include `try...except anyio.get_cancelled_exc_class()...finally` blocks for robust logging and cleanup (removing from `self.active_clients`).
    *   **Note:** The `ClientManager`'s `exit_stack` will no longer be used by this method for `stdio_client` or `ClientSession`.
    *   **Verification:** No direct tests for this method yet; it will be tested via `MCPHost` integration.

2.  **Remove `start_client`, `shutdown_client`, `shutdown_all_clients` from `ClientManager`:**
    *   **File:** `src/host/foundation/clients.py`
    *   **Action:** Delete these methods. Their responsibilities will be absorbed by `manage_client_lifecycle` and the controlling logic in `MCPHost`.
    *   **Verification:** Ensure no direct calls to these old methods remain (they shouldn't if `MCPHost` is updated correctly).

3.  **Update `ClientManager.__init__`:**
    *   **File:** `src/host/foundation/clients.py`
    *   **Action:** Remove the `exit_stack` parameter and `self.exit_stack` attribute. The `client_processes` attribute can also be removed as process management is handled by `stdio_client` and `anyio.Process`.
    *   **Verification:** Update `MCPHost.__init__` where `ClientManager` is instantiated.

**Phase 2: Modify `MCPHost`**

1.  **Update `MCPHost.__init__`:**
    *   **File:** `src/host/host.py`
    *   **Action:**
        *   Remove `self._exit_stack = AsyncExitStack()`.
        *   Add `self._client_runners_task_group: Optional[anyio.TaskGroup] = None`.
        *   Add `self._client_cancel_scopes: Dict[str, anyio.CancelScope] = {}`.
        *   Update `ClientManager` instantiation: `self.client_manager = ClientManager()`.
    *   **Verification:** Basic instantiation tests if any, otherwise covered by integration.

2.  **Update `MCPHost.initialize`:**
    *   **File:** `src/host/host.py`
    *   **Action:**
        *   Before the loop that calls `_initialize_client`, create and enter the main task group:
            ```python
            # Ensure anyio is imported
            import anyio
            # ...
            self._main_exit_stack = AsyncExitStack() # MCPHost still needs an exit stack for its own resources if any, and for the TG
            self._client_runners_task_group = await self._main_exit_stack.enter_async_context(anyio.create_task_group())
            ```
        *   The rest of the client initialization loop will use this task group.
    *   **Verification:** Integration tests for host initialization.

3.  **Update `MCPHost._initialize_client`:**
    *   **File:** `src/host/host.py`
    *   **Action:**
        *   Remove the direct usage of `self.client_manager.start_client`.
        *   Create an `anyio.CancelScope()` for the client: `client_scope = anyio.CancelScope()`.
        *   Store it: `self._client_cancel_scopes[config.client_id] = client_scope`.
        *   Start the client lifecycle task using the main task group and wait for the session:
            ```python
            session = await self._client_runners_task_group.start(
                self.client_manager.manage_client_lifecycle,
                config, # client_config
                self._security_manager,
                client_scope
            )
            ```
        *   The existing logic for MCP handshake, root registration, component discovery using the `session` object remains largely the same.
        *   `ToolManager.register_client(config.client_id, session)` will still be needed.
    *   **Verification:** Integration tests for host initialization and client registration.

4.  **Update `MCPHost.client_shutdown` (method in `MCPHost` to stop a specific client):**
    *   **File:** `src/host/host.py`
    *   **Action:**
        *   The component unregistration logic (calling `unregister_client_tools`, etc.) should remain *before* cancelling the client's task.
        *   Retrieve the `client_scope` from `self._client_cancel_scopes.pop(client_id, None)`.
        *   If the scope exists, call `client_scope.cancel()`.
        *   The `_client_runners_task_group` will automatically await the completion of the cancelled task (which includes its cleanup via `manage_client_lifecycle`'s `finally` block and the `async with` exits).
        *   Remove the direct call to `self.client_manager.shutdown_client(client_id)` as this method will be deleted from `ClientManager`.
    *   **Verification:** Update/run `test_dynamic_client_registration_and_unregistration`.

5.  **Update `MCPHost.shutdown_all_clients` (method in `MCPHost`):**
    *   **File:** `src/host/host.py`
    *   **Action:**
        *   Iterate through `list(self._client_cancel_scopes.keys())` to get client IDs.
        *   For each `client_id`, call the component unregistration methods (e.g., `self._tool_manager.unregister_client_tools(client_id)`).
        *   After unregistering components for a client, retrieve its scope `self._client_cancel_scopes.pop(client_id, None)` and call `scope.cancel()`.
        *   This method no longer needs to call `self.client_manager.shutdown_all_clients()`. The main task group cancellation in `MCPHost.shutdown` will handle waiting for all client tasks.
    *   **Verification:** Integration tests for full host shutdown.

6.  **Update `MCPHost.shutdown`:**
    *   **File:** `src/host/host.py`
    *   **Action:**
        *   The calls to manager shutdowns (`_prompt_manager.shutdown()`, etc.) remain.
        *   The call to `await self.shutdown_all_clients()` should still be made to ensure individual client scopes are cancelled and components unregistered *before* the main task group is cancelled.
        *   After `shutdown_all_clients`, if `self._client_runners_task_group` exists, cancel its scope: `self._client_runners_task_group.cancel_scope.cancel()`.
        *   Finally, `await self._main_exit_stack.aclose()`. This will wait for the `_client_runners_task_group` to exit (which waits for all its tasks) and any other resources managed by `_main_exit_stack`.
    *   **Verification:** Integration tests for full host shutdown.

**Phase 3: Testing**

1.  **Review and Update Unit Tests:**
    *   `tests/host/foundation/test_client_manager.py`: These tests will need significant updates or replacement as `ClientManager`'s public API changes. New tests might focus on `manage_client_lifecycle` if it can be tested in isolation (might be hard due to `task_status`).
    *   Other unit tests should largely remain valid if their mocked dependencies are still appropriate.
2.  **Focus on Integration Tests:**
    *   `tests/host/test_host_dynamic_registration.py`: The `test_dynamic_client_registration_and_unregistration` will be critical. It should now pass without the `xfail` if the refactoring is successful.
    *   `tests/host/test_host_lifecycle.py`: Verify full host startup and shutdown.
    *   `tests/host/test_host_integration.py` (if it exists and is relevant).
3.  **Observe Teardown:** The primary goal is to eliminate the `anyio` errors during test teardown.

## 4. Potential Challenges

*   **Synchronization of Session Availability:** Ensuring `MCPHost._initialize_client` correctly receives the `ClientSession` object from the task started by `_client_runners_task_group.start()` via `task_status` is critical.
*   **Error Propagation:** Errors occurring within `ClientManager.manage_client_lifecycle` (e.g., `stdio_client` or `ClientSession` failing to start) need to propagate correctly to `MCPHost` so it can handle failed client initializations. `task_group.start()` should handle this if `task_status.started()` is not called and an exception occurs.
*   **Cancellation Semantics:** Ensuring that cancelling `client_scope` correctly and fully cleans up the `stdio_client` (including its internal task group and process) and `ClientSession`.
