# Plan: Fix Async Test Teardown RuntimeError (v4 - Local ExitStack in Fixture)

**Objective:** Resolve the `RuntimeError: Attempted to exit cancel scope in a different task than it was entered in` by aligning with the working pattern identified in MCP GitHub issue #79.

**Background:**
Previous attempts failed because the `AsyncExitStack` managing client connections (`stdio_client`, `ClientSession`) was instance-level in `MCPHost` and closed in a different task context during test teardown. The working pattern uses a locally scoped `AsyncExitStack`.

**Revised Plan:**
Refactor `MCPHost` to decouple client connection lifecycle management from its instance-level `_exit_stack`. Move the responsibility of managing the `stdio_client` and `ClientSession` contexts (using a local `AsyncExitStack`) into the `host_manager` test fixture.

1.  **Refactor `MCPHost` (`src/host/host.py`):**
    *   Modify `_initialize_client`:
        *   Remove usage of `self._exit_stack.enter_async_context` for `stdio_client` and `ClientSession`.
        *   Perform initial setup (e.g., creating `StdioServerParameters`, resolving env vars).
        *   Return necessary components (e.g., `StdioServerParameters`, `ClientConfig`) for the caller to manage the connection.
        *   Separate the component registration logic (tools, prompts, resources) into a new method like `_register_client_components(client_id, session, config)` that takes an active `session`.
    *   Modify `MCPHost.shutdown`: Remove the closing of client connections via `self._exit_stack.aclose()`. The stack might become unused for clients.
    *   Adjust `self._clients` if needed (e.g., store config initially, update with session later).
2.  **Refactor `host_manager` Fixture (`tests/fixtures/host_fixtures.py`):**
    *   Use `scope="function"`.
    *   Inside the fixture function:
        *   Use `async with AsyncExitStack() as local_stack:` to create a local stack.
        *   Instantiate `HostManager`.
        *   Call `await manager.initialize()` (initializes host managers, not client connections).
        *   Iterate through `ClientConfig`s from `manager.config.clients`.
        *   For each `client_config`:
            *   Call the refactored `host._initialize_client` setup part.
            *   Use `local_stack.enter_async_context(stdio_client(...))` to get `read`, `write`.
            *   Use `local_stack.enter_async_context(ClientSession(read, write))` to get `session`.
            *   `await session.initialize()`.
            *   Store the active `session` (e.g., `manager.host._clients[client_config.client_id] = session`).
            *   Call `await host._register_client_components(client_id, session, client_config)`.
        *   `yield manager` *inside* the `async with local_stack:` block.
    *   The `local_stack` automatically handles `aclose()` upon exiting the `with` block after the test yields.
3.  **Modify Test File (`tests/host/test_host_manager.py`):**
    *   Ensure all `try...finally` blocks calling `shutdown()` are removed from the tests.
4.  **Run Test & Analyze:** Execute tests. Verify the `RuntimeError` is resolved.
