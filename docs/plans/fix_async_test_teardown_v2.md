# Plan: Fix Async Test Teardown RuntimeError (v2 - Class Scope)

**Objective:** Resolve the `RuntimeError: Attempted to exit cancel scope in a different task than it was entered in` occurring during pytest teardown for tests using the `host_manager` fixture.

**Background:**
Initial attempts confirmed the error stems from `anyio`'s requirement that `CancelScope` entry/exit happen in the same task. The `host_manager` fixture setup (entering async contexts) ran in `Task-1`, while the fixture teardown (exiting contexts via `shutdown()`) ran in `Task-15` under the default `function` scope, causing the error.

**Revised Plan:**
Leverage `pytest-asyncio`'s `class` scope for the fixture, aiming to keep the setup and teardown operations within the same task context for the duration of the test class execution.

1.  **Modify Fixture Scope (`tests/fixtures/host_fixtures.py`):**
    *   Change the `host_manager` fixture decorator from `@pytest_asyncio.fixture(scope="function")` to `@pytest_asyncio.fixture(scope="class")`.
    *   Maintain the existing fixture structure:
        *   Setup logic (`manager.initialize()`) before `yield`.
        *   `yield manager`.
        *   Teardown logic (`await manager.shutdown()`) after `yield`.
    *   Keep the task logging statements before initialization and shutdown.
2.  **Run Test & Analyze:** Execute the test (`TestHostManagerInitialization::test_host_manager_initialization_success`). Check logs for task IDs during setup and teardown. Verify if the `RuntimeError` is resolved.
3.  **Iterate:** If the issue persists even with class scope, further investigation into `pytest-asyncio` internals or the interaction with `mcp-py`/`anyio` task groups will be necessary. Potential next steps could involve looking at `anyio`'s task group propagation or specific `pytest-asyncio` configurations.
