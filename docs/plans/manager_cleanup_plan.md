# Implementation Plan: Code Cleanup & Refactoring (Post-Manager Refactor)

**Date:** 2025-05-03
**Version:** 1.0

## 1. Overview

This plan outlines the steps for refactoring and cleaning up the codebase following the major `HostManager` execution refactor. The goal is to improve code quality, reduce redundancy, enhance readability, and refine logging based on the suggestions identified in `docs/plans/manager_refactor_plan.md`.

This plan is divided into phases, starting with refactoring error handling, HostManager registration, and the ExecutionFacade pattern. Subsequent phases will address MCPHost logic, executor/agent internals, and logging/typing consistency.

## 2. Phase A: Error Handling, HostManager Registration, Facade Pattern

**Goal:** Implement shared error handling, simplify HostManager registration logic, and refactor the ExecutionFacade for consistency.

**Detailed Steps:**

1.  **Refactor API Error Handling (`src/bin/api.py`):**
    *   **1.1.** Define custom FastAPI exception handlers for common error types encountered in endpoints (e.g., `KeyError`, `ValueError`, `FileNotFoundError`, `RuntimeError`, potentially mapping them to appropriate `HTTPException` statuses like 404, 400, 500, 503).
    *   **1.2.** Register these exception handlers with the FastAPI app instance.
    *   **1.3.** Simplify `try...except` blocks within the API endpoint functions (`execute_..._endpoint`, `register_..._endpoint`), allowing the registered handlers to catch and process the exceptions, returning standardized HTTP responses. Remove redundant logging within endpoint `except` blocks if the handlers cover it.

2.  **Refactor CLI Error Handling (`src/bin/cli.py`):**
    *   **2.1.** Create one or more helper functions or decorators within `cli.py`. These wrappers should encapsulate the `asyncio.run(...)` call for the async API logic functions (`_execute_..._async_logic`).
    *   **2.2.** Implement consistent error handling within these wrappers for common exceptions like `httpx.HTTPStatusError`, `httpx.ConnectError`, `ValueError` (e.g., for JSON parsing), and generic `Exception`. Ensure errors are logged clearly and consistently, and the CLI exits with an appropriate status code (e.g., `typer.Exit(code=1)`).
    *   **2.3.** Update the synchronous Typer command functions (`execute_..._via_api_sync`, `register_..._via_api_sync`) to use these new wrappers, removing repetitive `try...except` blocks from the command functions themselves.

3.  **Refactor HostManager Registration (`src/host_manager.py`):**
    *   **3.1.** In `HostManager`, create private helper methods:
        *   `async def _register_clients_from_config(self, clients: List[ClientConfig]) -> Tuple[int, int, List[str]]`
        *   `async def _register_agents_from_config(self, agents: Dict[str, AgentConfig]) -> Tuple[int, int, List[str]]`
        *   `async def _register_workflows_from_config(self, workflows: Dict[str, WorkflowConfig], available_agents: set) -> Tuple[int, int, List[str]]`
        *   `async def _register_custom_workflows_from_config(self, custom_workflows: Dict[str, CustomWorkflowConfig]) -> Tuple[int, int, List[str]]`
        *   (Each helper should return counts of registered/skipped items and any error messages for that category).
    *   **3.2.** Move the registration loops and associated error handling logic for each component type from `register_config_file` into the corresponding private helper method.
    *   **3.3.** Update `register_config_file` to:
        *   Call `load_host_config_from_json`.
        *   Call each private helper method sequentially, passing the relevant loaded config data.
        *   Aggregate the results (counts, errors) from the helpers for the final summary logging.
    *   **3.4.** *Optional:* Create a small private helper (e.g., `_ensure_host_initialized()`) to encapsulate the `if not self.host:` check and raise `ValueError`, and call this at the start of methods requiring an initialized host (`register_client`, `register_agent`, etc.).

4.  **Refactor ExecutionFacade Pattern (`src/execution/facade.py`):**
    *   **4.1.** Define a standardized dictionary structure for returning errors from facade methods (e.g., `{"status": "failed", "error": "message"}`).
    *   **4.2.** Create a private helper method, potentially a decorator or a method like `async def _execute_component(self, component_type: str, component_name: str, config_lookup: Callable, executor_setup: Callable, execution_func: Callable, initial_input: Any, **kwargs) -> Any:`. This helper should encapsulate:
        *   Looking up the configuration (using `config_lookup`).
        *   Instantiating the Agent/Executor (using `executor_setup`).
        *   Calling the execution method (using `execution_func`).
        *   Wrapping the execution call in a `try...except` block to catch common errors (`KeyError`, `FileNotFoundError`, `AttributeError`, `ImportError`, `TypeError`, `RuntimeError`, generic `Exception`).
        *   Returning the successful result or the standardized error dictionary.
    *   **4.3.** Refactor `run_agent`, `run_simple_workflow`, and `run_custom_workflow` to utilize this helper method/decorator, passing the specific functions/lambdas needed for config lookup, setup, and execution for each component type. Ensure they return results consistent with the standardized error structure when failures occur.

5.  **Testing (Phase A):**
    *   **5.1.** Run existing unit and integration tests (`pytest tests/`) to ensure no regressions were introduced by the refactoring. Pay close attention to tests covering API endpoints, CLI commands, HostManager registration, and Facade execution.
    *   **5.2.** Manually test CLI commands with invalid inputs or non-existent components to verify the improved error handling.
    *   **5.3.** Manually test API endpoints (e.g., via Postman or `curl`) with invalid requests to verify the FastAPI exception handlers.
    *   **5.4.** Add new tests if necessary to specifically cover the new helper methods/decorators and exception handlers.

## 3. Phase B: MCPHost Refactoring

**Goal:** Refactor common logic within `MCPHost` for client resolution/filtering and initialization.

**Relevant Suggestions:** 4, 5

**Detailed Steps:**

1.  **Implement `_resolve_target_client_and_check_access` Helper:**
    *   *(Details to be added after Phase A completion and discussion)*
2.  **Refactor `get_prompt`, `execute_tool`, `read_resource`:**
    *   *(Details to be added after Phase A completion and discussion)*
3.  **Break Down `_initialize_client`:**
    *   *(Details to be added after Phase A completion and discussion)*
4.  **Testing (Phase B):**
    *   *(Details to be added after Phase A completion and discussion)*

## 4. Phase C: Executor & Agent Internals Refactoring

**Goal:** Refactor internal loop complexities in Agent and Executors, and address the custom workflow signature check.

**Relevant Suggestions:** 6, 7, 8

**Detailed Steps:**

1.  **Refactor Agent Execution Loop (`src/agents/agent.py`):**
    *   *(Details to be added after Phase B completion and discussion)*
2.  **Refactor Simple Workflow Loop (`src/workflows/simple_workflow.py`):**
    *   *(Details to be added after Phase B completion and discussion)*
3.  **Address Custom Workflow Signature Check (`src/workflows/custom_workflow.py`):**
    *   *(Details to be added after Phase B completion and discussion)*
4.  **Testing (Phase C):**
    *   *(Details to be added after Phase B completion and discussion)*

## 5. Phase D: Logging and Typing Consistency Review

**Goal:** Improve logging clarity (reducing INFO noise) and ensure consistent type hinting across the reviewed codebase.

**Relevant Suggestions:** 9

**Detailed Steps:**

1.  **Review Logging Levels:**
    *   Analyze `INFO` level logs across key modules (`host_manager`, `host`, `facade`, `agent`, `executors`, `api`, `cli`).
    *   Identify logs that provide routine operational details rather than significant events.
    *   Change appropriate logs from `INFO` to `DEBUG`. Focus on making `INFO` represent key lifecycle events, start/end of major operations (like execution requests), and significant warnings/errors.
2.  **Standardize Log Messages:**
    *   Ensure consistent formatting and context in log messages (e.g., always including relevant IDs or names).
3.  **Review Type Hinting:**
    *   Check for missing or inaccurate type hints in function signatures and variable annotations within the refactored areas and related modules.
    *   Ensure consistency (e.g., using `Optional[X]` vs. `X | None`).
    *   Utilize `TYPE_CHECKING` blocks where necessary to avoid circular imports for type hints.
4.  **Testing (Phase D):**
    *   Run the application and tests, observing the log output to confirm that `INFO` level is less noisy and `DEBUG` level provides necessary detail for troubleshooting.
    *   Use static analysis tools (like `mypy`) if configured to verify type hint correctness.

## 6. Completion Criteria

*   Phase A refactoring implemented and tested.
*   Phase B refactoring implemented and tested.
*   Phase C refactoring implemented and tested.
*   Phase D logging/typing improvements implemented and verified.
*   All existing tests pass.
*   Code readability and maintainability are demonstrably improved in the refactored sections.
