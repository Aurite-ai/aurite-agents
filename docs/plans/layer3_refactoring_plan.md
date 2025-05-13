# Implementation Plan: Layer 3 Refactoring

**Version:** 1.0
**Date:** 2025-05-12
**Author(s):** Ryan, Gemini

## 1. Goals

*   Refactor Layer 3 (Host System) components based on code review and discussion.
*   Improve performance by addressing blocking I/O calls.
*   Enhance robustness by implementing component unregistration during client shutdown.
*   Implement basic root validation checks.

## 2. Scope

This plan covers refactoring within the following primary files:
*   `src/host/foundation/security.py`
*   `src/host/foundation/roots.py`
*   `src/host/host.py`
*   `src/host/resources/prompts.py`
*   `src/host/resources/resources.py`
*   `src/host/resources/tools.py`
*   `src/host/foundation/routing.py` (MessageRouter)

## 3. Implementation Steps

**Phase 1: Async GCP Secret Resolution**

1.  **Modify `SecurityManager.resolve_gcp_secrets`:**
    *   **File:** `src/host/foundation/security.py`
    *   **Action:** Import `anyio`. Wrap the blocking call `self._gcp_secret_client.access_secret_version(request=request)` within `await anyio.to_thread.run_sync()`. Ensure the surrounding async/await structure is correct.
    *   **Verification:** Run relevant unit tests for `SecurityManager` (e.g., `tests/host/foundation/test_security_manager.py`). Although the mock might not fully exercise the threading, ensure the code structure is valid and existing tests pass.

**Phase 2: Implement Root Validation Logic**

1.  **Update `RootManager.validate_access`:**
    *   **File:** `src/host/foundation/roots.py`
    *   **Action:** Change the method body to `return client_id in self._client_roots`. Keep the existing warning log if the client is not found.
    *   **Verification:** Run relevant unit tests for `RootManager` (e.g., `tests/host/foundation/test_root_manager.py`) and potentially integration tests involving tool execution to ensure no regressions.

**Phase 3: Implement Component Unregistration & Handle Shutdown**

1.  **Add `unregister_server` to `MessageRouter`:**
    *   **File:** `src/host/foundation/routing.py`
    *   **Action:** Implement an `async def unregister_server(self, server_id: str):` method. This method should perform the same logic currently in `remove_server`. Rename `remove_server` to `unregister_server`.
    *   **Verification:** Update any tests calling `remove_server` to call `unregister_server`. Ensure tests pass.
2.  **Add `unregister_client_prompts` to `PromptManager`:**
    *   **File:** `src/host/resources/prompts.py`
    *   **Action:** Implement `async def unregister_client_prompts(self, client_id: str):`. This method should remove the `client_id` entry from `self._prompts`. Log the action.
    *   **Verification:** Add a new unit test in `tests/host/resources/test_prompt_manager.py` to verify this unregistration logic.
3.  **Add `unregister_client_resources` to `ResourceManager`:**
    *   **File:** `src/host/resources/resources.py`
    *   **Action:** Implement `async def unregister_client_resources(self, client_id: str):`. This method should remove the `client_id` entry from `self._resources`. Log the action.
    *   **Verification:** Add a new unit test in `tests/host/resources/test_resource_manager.py` to verify this unregistration logic.
4.  **Add `unregister_client_tools` to `ToolManager`:**
    *   **File:** `src/host/resources/tools.py`
    *   **Action:** Implement `async def unregister_client_tools(self, client_id: str):`. This method needs to:
        *   Identify all tools currently registered *only* to this `client_id` (check `MessageRouter`).
        *   Remove those tools from `self._tools` and `self._tool_metadata`.
        *   Remove the `client_id` entry from `self._clients`.
        *   Log the action.
    *   **Verification:** Add a new unit test in `tests/host/resources/test_tool_manager.py` to verify this unregistration logic, including cases where a tool is provided by multiple clients.
5.  **Update `MCPHost.client_shutdown`:**
    *   **File:** `src/host/host.py`
    *   **Action:** Before calling `self.client_manager.shutdown_client(client_id)`, add calls to:
        *   `await self._tool_manager.unregister_client_tools(client_id)`
        *   `await self._prompt_manager.unregister_client_prompts(client_id)`
        *   `await self._resource_manager.unregister_client_resources(client_id)`
        *   `await self._message_router.unregister_server(client_id)`
    *   **Verification:** Run integration tests involving dynamic client registration and shutdown (e.g., `tests/host/test_host_dynamic_registration.py`). Expect potential `anyio` errors during teardown, but verify the host state reflects the unregistered client/components if possible before teardown. Mark tests with `xfail` if necessary due to the known shutdown issue.
6.  **Update `MCPHost.shutdown_all_clients`:**
    *   **File:** `src/host/host.py`
    *   **Action:** Before calling `self.client_manager.shutdown_all_clients()`, iterate through the known client IDs (e.g., `list(self.client_manager.active_clients.keys())`) and call the unregistration methods for each client ID as done in `client_shutdown`.
    *   **Verification:** Run integration tests involving full host shutdown (e.g., `tests/host/test_host_lifecycle.py`). Expect potential `anyio` errors during teardown. Mark tests with `xfail` if necessary.

## 4. Testing Strategy

*   **Unit Tests:** Verify individual method logic within each modified manager, especially the new unregistration methods.
*   **Integration Tests:** Use existing tests (like `test_host_dynamic_registration.py`, `test_host_lifecycle.py`) to verify the updated shutdown sequences in `MCPHost`.
*   **`xfail`:** Apply `@pytest.mark.xfail(reason="Known anyio shutdown issue")` to integration tests that fail *only* during teardown due to the known `anyio` task context issue after verifying the core test logic passes.
