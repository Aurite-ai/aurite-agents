# Implementation Plan: Refactor MCPHost to use ClientSessionGroup

**Version:** 1.0
**Date:** 2025-07-01
**Author(s):** Ryan, Gemini
**Related Design Document (Optional):** N/A

## 1. Goals
    *   Refactor the `MCPHost` to use the `mcp.client.ClientSessionGroup` for all MCP client lifecycle management.
    *   Eliminate the custom `ClientManager` and all manual `anyio` task group management from the Host Layer.
    *   Simplify the `MCPHost` into a lightweight orchestrator that delegates to the `ClientSessionGroup`.
    *   Create a simple, stable, and maintainable integration test for the `MCPHost`.

## 2. Scope
    *   **In Scope:**
        *   `src/aurite/host/host.py`
        *   `src/aurite/host/foundation/clients.py` (to be deleted)
        *   `src/aurite/host/foundation/factory.py` (to be deleted)
        *   `tests/integration/host/test_mcp_host.py`
        *   `src/aurite/config/config_models.py` (minor changes to support transport parameters)
    *   **Out of Scope:**
        *   Any changes to the `HostManager` or other layers above the `MCPHost`.
        *   Changes to other component managers (`PromptManager`, `ResourceManager`, etc.).

## 3. Implementation Steps

### Phase 1: Core Refactoring

1.  **Step 1.1: Delete Obsolete Foundation Files**
    *   **File(s):**
        *   `src/aurite/host/foundation/clients.py`
        *   `src/aurite/host/foundation/factory.py`
    *   **Action:** Delete these two files. Their functionality will be entirely replaced by `mcp.client.ClientSessionGroup`.
    *   **Verification:** The files are deleted.

2.  **Step 1.2: Update `MCPHost` to Use `ClientSessionGroup`**
    *   **File(s):** `src/aurite/host/host.py`
    *   **Action:**
        *   Import `ClientSessionGroup` and `ServerParameters` from `mcp.client.session_group`.
        *   Remove the `ClientManager` import and instance variable.
        *   In `MCPHost.__init__`, initialize `self._session_group: ClientSessionGroup = ClientSessionGroup()` and `self._exit_stack: contextlib.AsyncExitStack = contextlib.AsyncExitStack()`.
        *   Refactor `MCPHost.initialize()`:
            *   It should become an `async` context manager itself (`async with self`).
            *   The `__aenter__` should enter the `self._exit_stack`.
            *   Inside the `with` block, it will enter the `self._session_group` context.
            *   Loop through `self._config.mcp_servers` and call `self._session_group.connect_to_server()` for each, converting our `ClientConfig` to the required `ServerParameters` type.
        *   Refactor `MCPHost.shutdown()`:
            *   This method will call `await self._exit_stack.aclose()`.
        *   Update the `tools`, `prompts`, and `resources` properties to be simple pass-throughs to the `_session_group` properties (e.g., `return self._session_group.tools`).
        *   Update `call_tool` to delegate directly to `self._session_group.call_tool()`.
    *   **Verification:** The `MCPHost` class is updated, and the application should still run, although tests will be broken.

3.  **Step 1.3: Adapt `ClientConfig` to `ServerParameters`**
    *   **File(s):** `src/aurite/config/config_models.py` and `src/aurite/host/host.py`
    *   **Action:**
        *   The `mcp` library's `ServerParameters` types (`StdioServerParameters`, `SseServerParameters`, etc.) are Pydantic models. Our `ClientConfig` needs to be adapted to provide the necessary fields.
        *   Create a helper function within `MCPHost` (e.g., `_get_server_params(config: ClientConfig) -> ServerParameters`) that maps our `ClientConfig` to the correct `mcp` `ServerParameters` model based on the `transport_type`.
        *   This may require adding optional fields to our `ClientConfig` to capture things like `sse_read_timeout` if we want to support them. For now, we will stick to the basics.
    *   **Verification:** The helper function correctly transforms the config objects.

### Phase 2: Testing

1.  **Step 2.1: Refactor `test_mcp_host.py`**
    *   **File(s):** `tests/integration/host/test_mcp_host.py`
    *   **Action:**
        *   Rewrite the tests to be simpler.
        *   The primary test `test_mcp_host_initialize_shutdown` will now be much cleaner.
        *   Use `mocker.patch` to mock `mcp.client.session_group.ClientSessionGroup`.
        *   The test will:
            1.  Instantiate `MCPHost` with a test config.
            2.  Use `async with host:` to trigger initialization and shutdown.
            3.  Assert that the mocked `ClientSessionGroup`'s `connect_to_server` method was called for each server in the config.
            4.  Assert that the `__aenter__` and `__aexit__` methods of the mock were called.
    *   **Verification:** All tests in `test_mcp_host.py` pass.

## 4. Testing Strategy
    *   **Unit Tests:** The refactoring removes the need for complex unit tests for `ClientManager`. The new unit tests will be focused on `MCPHost` and will be significantly simpler due to the ability to mock `ClientSessionGroup`.
    *   **Integration Tests:** The primary integration test (`test_mcp_host.py`) will validate the correct orchestration behavior of `MCPHost` by asserting its interactions with the mocked `ClientSessionGroup`.

## 5. Final Documentation Review
    *   When the implementation is complete and all tests are passing, review `.clinerules/documentation_guide.md` to identify all documents that require updates, read them, and then propose the necessary changes. The most likely candidates for updates are `docs/layers/3_host.md` and `docs/layers/framework_overview.md`.
