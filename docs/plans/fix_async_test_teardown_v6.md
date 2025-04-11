# Plan: Fix Async Test Teardown RuntimeError (v6 - Manual Test Lifecycle)

**Objective:** Resolve the `RuntimeError: Attempted to exit cancel scope in a different task than it was entered in`.

**Background:**
Previous attempts using async fixtures (both generator and regular) with local `AsyncExitStack` failed, indicating task context switches even within the fixture setup/execution, likely due to interactions between `pytest-asyncio`, `yield`, and `anyio` internals used by `stdio_client`/`ClientSession`.

**Revised Plan:**
Simplify the fixture to be synchronous and only instantiate `HostManager`. Move all asynchronous initialization (host managers *and* client connections) and the associated `AsyncExitStack` management directly into the test function's scope.

1.  **Simplify `host_manager` Fixture (`tests/fixtures/host_fixtures.py`):**
    *   Change to a synchronous fixture: `@pytest.fixture(scope="function")`.
    *   Instantiate `manager = HostManager(config_path=...)`.
    *   Return the *uninitialized* `manager`.
    *   Remove all `async`/`await` and teardown logic from the fixture.
2.  **Refactor Test Function (`tests/host/test_host_manager.py::test_host_manager_initialization_success` and others):**
    *   Ensure test function is `async def`.
    *   Add a top-level `try...finally` block for host manager shutdown.
    *   Inside the `try` block:
        *   Use `async with AsyncExitStack() as stack:` to manage client connections.
        *   Inside the `with stack:` block:
            *   Call `await manager.initialize()` (initializes host's core managers).
            *   Get `host = manager.host`. Check it's not `None`.
            *   Loop through `host._config.clients`:
                *   `server_params = await host._prepare_client_connection_params(config)`.
                *   `read, write = await stack.enter_async_context(stdio_client(server_params))`.
                *   `session = await stack.enter_async_context(ClientSession(read, write))`.
                *   Send MCP `initialize` request and `initialized` notification to `session`.
                *   `await host._register_client_components(session, config)`.
            *   Perform actual test assertions on the fully initialized `manager`.
    *   Inside the `finally` block (outside the `async with stack:`):
        *   Call `await manager.shutdown()` (shuts down host's core managers).
3.  **Update Plan Document:** This document serves as the update.
4.  **Run Test & Analyze:** Execute tests. Verify the `RuntimeError` is resolved.
