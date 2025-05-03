# Implementation Plan: HostManager Execution Refactor

**Date:** 2025-05-03
**Version:** 1.0

## 1. Overview

This plan details the steps to refactor the execution logic for Agents, Simple Workflows, and Custom Workflows out of the `HostManager` and into dedicated executor classes. This refactoring aims to:

1.  **Decouple Execution:** Separate the responsibility of executing agentic components from the `HostManager`'s orchestration and lifecycle duties.
2.  **Enable Composition:** Allow `CustomWorkflow`s to execute other `Agent`s, `SimpleWorkflow`s, and `CustomWorkflow`s by providing a unified execution interface.
3.  **Improve Modularity & Testability:** Create more focused, testable units for execution logic.

The chosen approach is the **Executor Pattern with an Execution Facade**:

*   Dedicated classes (`Agent`, `SimpleWorkflowExecutor`, `CustomWorkflowExecutor`) will handle the specific execution logic for each component type.
*   An `ExecutionFacade` will provide a single, unified interface (`run_agent`, `run_simple_workflow`, `run_custom_workflow`) for initiating execution.
*   `CustomWorkflow`s will interact with the `ExecutionFacade` instead of directly with the `HostManager` or `MCPHost` for triggering other components.
*   `HostManager` will retain ownership of configurations and handle registration, passing config references to the facade.
*   `MCPHost` will continue to perform low-level MCP interactions and filtering, receiving necessary `AgentConfig` details during execution calls.

## 2. Implementation Steps (Combined Phases)

**Goal:** Refactor execution logic into dedicated Executors and a unified Facade, enabling component composition.

**Actual Implementation Steps Taken:**

1.  **Created Directories:**
    *   Created `src/workflows/`.
    *   Created `src/execution/`.
2.  **Implemented `SimpleWorkflowExecutor`:**
    *   Created `src/workflows/simple_workflow.py`.
    *   Defined class `SimpleWorkflowExecutor`.
    *   Constructor accepts `WorkflowConfig`, `Dict[str, AgentConfig]`, and `MCPHost`.
    *   `execute` method implements sequential agent execution logic, adapted from `HostManager`.
3.  **Implemented `CustomWorkflowExecutor`:**
    *   Created `src/workflows/custom_workflow.py`.
    *   Defined class `CustomWorkflowExecutor`.
    *   **Constructor (`__init__`)**: Initially accepted `CustomWorkflowConfig` and `MCPHost`, later refactored to accept only `CustomWorkflowConfig`.
    *   **Execution Method (`async def execute(...)`)**:
        *   Accepts `initial_input: Any` and `executor: ExecutionFacade`.
        *   Handles dynamic import and instantiation of the custom workflow class.
        *   Calls the custom workflow's `execute_workflow` method, passing the `ExecutionFacade` instance.
4.  **Implemented `ExecutionFacade`:**
    *   Created `src/execution/facade.py`.
    *   Defined class `ExecutionFacade`.
    *   **Constructor (`__init__`)**: Accepts `host_manager: HostManager`. Stores references to the manager and its host (`self._manager`, `self._host`).
    *   **Method (`async def run_agent(...)`)**: Implemented logic to look up config, instantiate `Agent`, and call `agent.execute_agent`.
    *   **Method (`async def run_simple_workflow(...)`)**: Implemented logic to look up config, instantiate `SimpleWorkflowExecutor`, and call `executor.execute`.
    *   **Method (`async def run_custom_workflow(...)`)**: Implemented logic to look up config, instantiate `CustomWorkflowExecutor`, and call `executor.execute`, passing `self` (the facade).
5.  **Refactored `HostManager`:**
    *   In `src/host_manager.py`:
        *   Imported `ExecutionFacade`.
        *   Added `self.execution: Optional[ExecutionFacade] = None` attribute.
        *   Instantiated `ExecutionFacade` in `initialize` after host initialization, passing `self`.
        *   Removed the old `execute_agent`, `execute_workflow`, `execute_custom_workflow` methods.
        *   Removed `workflow_configs` from the `MCPHost` constructor call.
6.  **Refactored `MCPHost` (Minor):**
    *   In `src/host/host.py`:
        *   Removed `workflow_configs` and `custom_workflow_configs` parameters from `__init__`.
        *   Removed `self._workflow_configs` and `self._custom_workflow_configs` attributes.
        *   Removed the `get_workflow_config` method.
7.  **Updated `CustomWorkflow` Interface:**
    *   Updated `tests/fixtures/custom_workflows/example_workflow.py` to accept `executor: ExecutionFacade` in `execute_workflow` and use it to call `executor.run_agent`.
8.  **Updated Entrypoints (Placeholders):**
    *   Added `TODO (Refactor): ...` comments in `src/bin/api.py`, `src/bin/cli.py`, and `src/bin/worker.py` where execution calls need to be updated to use `host_manager.execution.run_...`.
9.  **Testing & Verification:**
    *   Created integration tests for `SimpleWorkflowExecutor` and `CustomWorkflowExecutor` in `tests/workflows/`.
    *   Addressed and resolved `pytest-asyncio` / `anyio` event loop errors by:
        *   Using module-level `pytestmark = pytest.mark.anyio`.
        *   Removing function-level `@pytest.mark.asyncio` decorators.
        *   Setting `host_manager` fixture scope back to `function`.
        *   Suppressing the remaining `RuntimeError: Event loop is closed` in the `host_manager` fixture teardown.
    *   Skipped outdated execution tests in `tests/host/test_host_manager.py`.
    *   Fixed assertion errors in `tests/host/test_host_manager.py` related to config loading counts.
    *   Ensured all tests in `tests/workflows/` and `tests/host/` pass (excluding skipped tests).

### Phase C: Integrate ExecutionFacade into Entrypoints, Test, and Document

**Goal:** Modify API, Worker, and CLI entrypoints to use the `ExecutionFacade` for execution requests, add facade-specific tests, verify changes using API/CLI tests, and update documentation.

**Detailed Steps:**

1.  **Refactor API (`src/bin/api.py`):**
    *   **1.1.** Modify the `/agents/{agent_name}/execute` endpoint:
        *   Replace the call `manager.execute_agent(...)` with `manager.execution.run_agent(...)`.
        *   Verify the arguments passed (`agent_name`, `user_message`, `system_prompt`) match the `run_agent` signature.
        *   Ensure error handling (e.g., `KeyError` for missing agent) remains appropriate or is adapted for potential errors from the facade.
    *   **1.2.** Modify the `/workflows/{workflow_name}/execute` endpoint:
        *   Replace the call `manager.execute_workflow(...)` with `manager.execution.run_simple_workflow(...)`.
        *   Verify the arguments passed (`workflow_name`, `initial_user_message`) match the `run_simple_workflow` signature.
        *   Ensure the response model (`ExecuteWorkflowResponse`) still aligns with the facade's return structure.
        *   Adapt error handling for potential errors from the facade.
    *   **1.3.** Modify the `/custom_workflows/{workflow_name}/execute` endpoint:
        *   Replace the call `manager.execute_custom_workflow(...)` with `manager.execution.run_custom_workflow(...)`.
        *   Verify the arguments passed (`workflow_name`, `initial_input`) match the `run_custom_workflow` signature.
        *   Ensure the response model (`ExecuteCustomWorkflowResponse`) still aligns with the facade's return structure.
        *   Adapt error handling for potential errors from the facade (including setup errors vs. runtime errors within the custom workflow).
2.  **Refactor Worker (`src/bin/worker.py`):**
    *   **2.1.** Identify the section in `worker.py` that handles execution tasks (if it currently calls the old `manager.execute_...` methods).
    *   **2.2.** Update the task processing logic to call the corresponding `manager.execution.run_...` methods based on the task type (`agent`, `simple_workflow`, `custom_workflow`).
    *   **2.3.** Adjust argument passing and result handling as needed.
    *   *(Self-Correction: Need to verify if `worker.py` actually performs execution or just registration. If only registration, this step might be unnecessary or simpler).*
3.  **Verify CLI (`src/bin/cli.py`):**
    *   **3.1.** Confirm that the `execute agent`, `execute workflow`, and `execute custom-workflow` subcommands in `cli.py` solely rely on making requests to the API endpoints modified in Step 1.
    *   **3.2.** If the CLI *does* interact directly with `HostManager` (which seems unlikely based on the current `cli.py` structure), update those interactions to use `manager.execution.run_...`. Otherwise, no direct code changes are needed in the CLI for execution logic, but testing is crucial.
4.  **Add Facade Integration Tests:**
    *   **4.1.** Create the test file `tests/execution/test_facade_integration.py`.
    *   **4.2.** Add a test `test_facade_run_agent` that uses the `host_manager` fixture, calls `manager.execution.run_agent`, and verifies the result structure and basic content (similar to agent execution tests, but invoked via the facade).
    *   **4.3.** Add a test `test_facade_run_simple_workflow` that calls `manager.execution.run_simple_workflow` and verifies the result (similar to simple workflow executor tests).
    *   **4.4.** Add a test `test_facade_run_custom_workflow` that calls `manager.execution.run_custom_workflow` and verifies the result, ensuring the facade is passed correctly (similar to custom workflow executor tests).
    *   **4.5.** Add tests for error conditions (e.g., `test_facade_run_agent_not_found`, `test_facade_run_workflow_not_found`).
5.  **API Testing (Postman/Newman):**
    *   **5.1.** Review the existing Postman collection (`tests/api/main_server.postman_collection.json`).
    *   **5.2.** Ensure the tests for the `/execute` endpoints (`Execute Agent`, `Execute Simple Workflow`, `Execute Custom Workflow`) are still valid after the API refactoring in Step 1. Adjust request bodies or assertions if necessary.
    *   **5.3.** Run the Postman collection using Newman (with the environment file `tests/api/main_server.postman_environment.json`) against the locally running API server (`python -m src.bin.api`).
    *   **5.4.** Debug and fix any issues identified in the API implementation (Step 1) based on test failures.
6.  **CLI Testing:**
    *   **6.1.** Once API tests (Step 5) are passing, test the corresponding CLI `execute` commands:
        *   `python -m src.bin.cli execute agent ...`
        *   `python -m src.bin.cli execute workflow ...`
        *   `python -m src.bin.cli execute custom-workflow ...`
    *   **6.2.** Verify that the CLI commands produce the expected output by successfully calling the refactored API endpoints.
    *   **6.3.** Debug and fix any issues identified in the API implementation or CLI argument parsing.
7.  **Update Documentation:**
    *   **7.1.** Update `README.md`: Modify the architecture diagram/description if needed to clearly show the `ExecutionFacade` between `HostManager` and the Executors/Agent. Update usage examples if affected.
    *   **7.2.** Update `docs/architecture_overview.md`: Reflect the new `ExecutionFacade` layer and its role.
    *   **7.3.** Update `docs/framework_overview.md` or other relevant developer guides: Explain the facade, the executor pattern, and the updated custom workflow signature (`execute_workflow` receiving the facade).
    *   **7.4.** Review `docs/plans/manager_refactor_plan.md` itself and mark Phase C as complete or update its status.

## 3. Completion Criteria (Current Task)

*   Execution logic resides in `Agent`, `SimpleWorkflowExecutor`, or `CustomWorkflowExecutor`.
*   `ExecutionFacade` provides a unified interface (`run_agent`, `run_simple_workflow`, `run_custom_workflow`).
*   `CustomWorkflowExecutor` accepts the `ExecutionFacade` and passes it to the custom workflow's `execute_workflow` method.
*   Example custom workflow (`tests/fixtures/.../example_workflow.py`) updated to the new signature and successfully calls `executor.run_agent`.
*   `HostManager` uses the `ExecutionFacade` internally.
*   Relevant integration tests for executors pass.
*   Outdated tests in `test_host_manager.py` are skipped.
*   Test environment issues (event loop errors) are resolved/suppressed.

## 4. Next Steps

*   Implement Phase C: Update Entrypoints & Documentation (as detailed above).
*   Add comprehensive unit tests for the facade and executors where needed.
*   Consider refactoring configuration loading (`get_server_config`) shared between `api.py`, `cli.py`, and `worker.py`.
