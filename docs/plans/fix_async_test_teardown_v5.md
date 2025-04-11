# Plan: Fix Async Test Teardown RuntimeError (v5 - Corrected Fixture Logic)

**Objective:** Resolve the `RuntimeError: Attempted to exit cancel scope in a different task than it was entered in` and the subsequent `AttributeError: 'NoneType' object has no attribute 'initialize'`.

**Background:**
Plan v4 failed because the test fixture (`host_manager`) tried to use `manager.host` before `manager.initialize()` was called, which is the method that actually creates the `MCPHost` instance.

**Revised Plan:**
Correct the order of operations in the `host_manager` fixture. Ensure `HostManager.initialize()` is called first to create the `MCPHost` instance, then proceed with client connection setup using a local `AsyncExitStack`.

1.  **Refactor `host_manager` Fixture (`tests/fixtures/host_fixtures.py`):**
    *   Instantiate `manager = HostManager(...)`.
    *   Call `await manager.initialize()` **first**. This loads configs, creates `manager.host`, and initializes the host's core managers.
    *   Get the valid `host = manager.host`. Add an assertion or check to ensure `host` is not `None`.
    *   Use `async with AsyncExitStack() as local_stack:`:
        *   Inside the `with` block, iterate through `host._config.clients`.
        *   Prepare connection params using `host._prepare_client_connection_params`.
        *   Establish connection (`stdio_client`, `ClientSession`) using `local_stack.enter_async_context`.
        *   Initialize the `session` (MCP handshake: `initialize` request/notification).
        *   Register components using `host._register_client_components(session, config)`.
    *   `yield manager` *after* the `async with local_stack:` block. The local stack ensures client connections established within it are closed upon exiting the `with` block.
    *   Teardown (after `yield`): Call `await manager.shutdown()` to shut down the host's core managers.
2.  **Update Plan Document:** This document serves as the update.
3.  **Run Test & Analyze:** Execute tests. Verify both the `AttributeError` and the original `RuntimeError` are resolved.
