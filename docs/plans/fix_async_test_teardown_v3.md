# Plan: Fix Async Test Teardown RuntimeError (v3 - Test Finally Block)

**Objective:** Resolve the `RuntimeError: Attempted to exit cancel scope in a different task than it was entered in` occurring during pytest teardown for tests using the `host_manager` fixture.

**Background:**
Previous attempts using fixture teardown (both `function` and `class` scope) failed because the teardown code executed in a different asyncio task (`Task-15`) than the setup code (`Task-1`), violating `anyio`'s `CancelScope` rules.

**Revised Plan:**
Return to handling shutdown within the test function itself using a `try...finally` block, but add explicit task logging to verify if the `finally` block executes in the same task context as the fixture setup.

1.  **Revert Fixture (`tests/fixtures/host_fixtures.py`):**
    *   Change the `host_manager` fixture scope back to `@pytest_asyncio.fixture(scope="function")`.
    *   Remove the teardown logic (`await manager.shutdown()` etc.) from after the `yield manager` statement. The fixture will only perform setup.
2.  **Modify Test File (`tests/host/test_host_manager.py`):**
    *   In relevant test methods (starting with `test_host_manager_initialization_success`), re-introduce the `try...finally` structure.
    *   Inside the `finally` block, add `logging.debug(f"Test Finally Block - Task Info: {asyncio.current_task()}")` immediately before the `await host_manager.shutdown()` call.
3.  **Run Test & Analyze:** Execute the test (`TestHostManagerInitialization::test_host_manager_initialization_success`). Compare the task ID logged during fixture setup with the task ID logged in the test's `finally` block. Check if the `RuntimeError` persists.
4.  **Iterate:**
    *   If tasks match and error persists: Investigate deeper interactions between `AsyncExitStack`, `anyio`, and `pytest-asyncio`.
    *   If tasks mismatch: Confirm that `pytest-asyncio` switches tasks even for the test's `finally` block. Explore alternative solutions like manual task group management or potentially patching/wrapping the problematic `anyio` scope exit during testing.
