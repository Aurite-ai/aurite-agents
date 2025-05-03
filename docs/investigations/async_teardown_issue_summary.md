# Investigation Summary: Async Teardown RuntimeError in Pytest

**Objective:** Resolve the `RuntimeError: Attempted to exit cancel scope in a different task than it was entered in` occurring during pytest teardown for tests involving `HostManager` and `MCPHost`.

**Problem Description:**

Tests using the `host_manager` fixture consistently fail during teardown (or sometimes setup, depending on the approach) with an `anyio` `RuntimeError`. This error indicates that an `anyio.CancelScope` (used internally by `mcp.client.stdio.stdio_client` and `mcp.ClientSession`) is being exited in a different asyncio task than the one it was created in.

Debugging logs confirmed a task mismatch:
*   Fixture setup code (entering the async contexts via `AsyncExitStack`) runs in one task (e.g., `Task-1`).
*   Teardown code (calling `AsyncExitStack.aclose()`, attempting to exit the contexts) runs in a different task (e.g., `Task-14` or `Task-15`).

**Attempted Solutions & Why They Failed:**

1.  **Initial State / Test `finally` Block (Plan v3):**
    *   **Change:** Moved `host_manager.shutdown()` into a `try...finally` block within the test function itself. The fixture only performed setup.
    *   **Reasoning:** Hoped the `finally` block would execute in the same task as the main test body and fixture setup.
    *   **Outcome:** Failed. Logs showed the `finally` block still executed in a separate task (`Task-14`) from the fixture setup (`Task-1`), triggering the `RuntimeError` during `shutdown()`.

2.  **Fixture Teardown (Function Scope) (Plan v1):**
    *   **Change:** Used `@pytest_asyncio.fixture(scope="function")` with `yield manager` and placed `await manager.shutdown()` after the `yield`. Removed explicit shutdown from tests.
    *   **Reasoning:** Standard pattern for fixture setup/teardown.
    *   **Outcome:** Failed. Logs showed fixture setup ran in `Task-1` and fixture teardown ran in `Task-15`, triggering the `RuntimeError` during teardown.

3.  **Fixture Teardown (Class Scope) (Plan v2):**
    *   **Change:** Changed fixture scope to `@pytest_asyncio.fixture(scope="class")`, keeping teardown logic after `yield`.
    *   **Reasoning:** Hoped class scope might maintain a single task context for setup and teardown across the class.
    *   **Outcome:** Failed. Logs still showed setup in `Task-1` and teardown in `Task-15`, triggering the `RuntimeError`. Fixture scope did not solve the task mismatch for teardown.

4.  **Refactor Host/Fixture (Local `AsyncExitStack` in Fixture) (Plan v4/v5):**
    *   **Change:** Refactored `MCPHost` to decouple client connection lifecycle. Modified the fixture to:
        *   Initialize `HostManager` and `MCPHost` core managers.
        *   Use a *local* `AsyncExitStack` (`async with AsyncExitStack() as local_stack:`) within the fixture setup phase to manage `stdio_client` and `ClientSession` contexts.
        *   `yield manager` after the `local_stack` block.
        *   Call `manager.shutdown()` (for host managers) in the fixture teardown after `yield`.
    *   **Reasoning:** Aligned with the working pattern from GitHub issue #79, keeping the client connection `AsyncExitStack` lifecycle contained.
    *   **Outcome:** Failed. The `RuntimeError` shifted and occurred *during setup* when the `async with local_stack:` block exited. This implies task switching occurred even *within* the fixture setup loop, between entering contexts and the stack implicitly closing.

**Root Cause Analysis:**

The core issue appears to be a fundamental incompatibility between:
*   `pytest-asyncio`'s management of tasks across fixture setup, test execution, and fixture teardown phases.
*   `anyio`'s strict requirement that `CancelScope` entry and exit occur within the *exact same task*.
*   The use of `anyio`-based async context managers (`stdio_client`, `ClientSession`) whose lifecycle needs to span across these different phases/tasks when managed by fixtures or long-lived objects like `MCPHost`.

**Supporting Evidence:**

*   [GitHub Issue mcp-py#79](https://github.com/modelcontextprotocol/mcp-py/issues/79): Describes the identical problem and confirms the cause is calling `AsyncExitStack.aclose()` in a different task. The suggested workaround involves managing the stack within a single scope.