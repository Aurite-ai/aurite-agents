# Plan: Fix Async Test Teardown RuntimeError

**Objective:** Resolve the `RuntimeError: Attempted to exit cancel scope in a different task than it was entered in` occurring during pytest teardown for tests using the `host_manager` fixture.

**Background:**
The error stems from `anyio`'s requirement that `CancelScope` entry and exit must happen in the same asyncio task. The `host_manager` fixture setup (which enters async contexts via `MCPHost._exit_stack`) runs in one task, while the teardown (which calls `_exit_stack.aclose()`) appears to run in a different task when triggered either by fixture teardown or a test's `finally` block.

**Plan:**

1.  **Modify Test File (`tests/host/test_host_manager.py`):**
    *   Remove explicit `try...finally` blocks calling `await host_manager.shutdown()` from tests using the `host_manager` fixture. Rely solely on the fixture's built-in teardown.
2.  **Modify Fixture File (`tests/fixtures/host_fixtures.py`):**
    *   Ensure `await manager.shutdown()` is called within the `host_manager` fixture's teardown phase (after `yield`).
    *   Add `logging.debug(f"Task Info: {asyncio.current_task()}")` statements immediately before `await manager.initialize()` (setup) and `await manager.shutdown()` (teardown) to verify task identity.
3.  **Run Test & Analyze:** Execute the failing test (`TestHostManagerInitialization::test_host_manager_initialization_success`). Check logs for task IDs and whether the error persists.
4.  **Iterate:** If the issue remains, further investigation into `pytest-asyncio` behavior or alternative fixture/task management strategies will be required.
