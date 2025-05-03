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

## 2. Implementation Phases

### Phase A: Implement Agentic Component Executors

**Goal:** Create the `SimpleWorkflowExecutor` and `CustomWorkflowExecutor` classes, move execution logic into them, and remove the old execution methods from `HostManager`.

**Steps:**

1.  **Create Directory:**
    *   Create `src/workflows/`.
2.  **Implement `SimpleWorkflowExecutor`:**
    *   Create `src/workflows/simple_workflow.py`.
    *   Define class `SimpleWorkflowExecutor`.
    *   **Constructor (`__init__`)**: Accepts `WorkflowConfig`, `Dict[str, AgentConfig]` (all agent configs), and `MCPHost`.
    *   **Execution Method (`async def execute(...)`)**:
        *   Accepts `initial_input: str`.
        *   Retrieves agent names from `WorkflowConfig.steps`.
        *   Iterates through steps:
            *   Looks up the `AgentConfig` for the current step's agent name from the provided dictionary.
            *   Instantiates `src.agents.agent.Agent` with the retrieved `AgentConfig`.
            *   Calls `agent_instance.execute_agent(user_message=current_message, host_instance=self.host)`.
            *   Handles output/error from the agent call, updating `current_message` for the next step or breaking on error.
        *   Returns a result dictionary (e.g., `{"status": "completed" | "failed", "final_message": ..., "error": ...}`).
    *   **Reference Logic:** Adapt logic currently in `HostManager.execute_workflow`.
3.  **Implement `CustomWorkflowExecutor`:**
    *   Create `src/workflows/custom_workflow.py`.
    *   Define class `CustomWorkflowExecutor`.
    *   **Constructor (`__init__`)**: Accepts `CustomWorkflowConfig` and `MCPHost`. (Note: It doesn't need all configs, just the specific one it's executing).
    *   **Execution Method (`async def execute(...)`)**:
        *   Accepts `initial_input: Any` and `executor: ExecutionFacade` (this is the *new* signature the custom workflow itself will expect).
        *   Retrieves `module_path` and `class_name` from `CustomWorkflowConfig`.
        *   Performs dynamic import of the module.
        *   Instantiates the workflow class.
        *   Validates the existence and signature of the `execute_workflow` method within the instantiated class.
        *   Calls `workflow_instance.execute_workflow(initial_input=initial_input, executor=executor)`. **Crucially, it passes the `ExecutionFacade` instance it received.**
        *   Returns the result from the custom workflow's method.
    *   **Reference Logic:** Adapt logic currently in `HostManager.execute_custom_workflow`, but modify the call signature as described.
4.  **Refactor `HostManager`:**
    *   In `src/host_manager.py`:
        *   Remove the methods: `execute_agent`, `execute_workflow`, `execute_custom_workflow`.
5.  **Refactor `MCPHost` (Minor):**
    *   In `src/host/host.py`:
        *   The `__init__` method no longer needs `workflow_configs` or `custom_workflow_configs` passed to it, as it doesn't store or use them directly anymore. Update the `__init__` signature and remove `self._workflow_configs` and `self._custom_workflow_configs`.
        *   Remove the `get_workflow_config` method.
        *   Ensure `get_agent_config` remains as it's still used for filtering lookups initiated by `execute_tool`/`get_prompt`.

**Testing (Phase A):**

*   **Strategy:** Integration tests first (no mocks for executors or host), followed by unit tests if complex internal logic warrants mocking. Test one case at a time.
*   **Files:**
    *   `tests/workflows/test_simple_workflow_executor_integration.py`
    *   `tests/workflows/test_simple_workflow_executor_unit.py`
    *   `tests/workflows/test_custom_workflow_executor_integration.py`
    *   `tests/workflows/test_custom_workflow_executor_unit.py`
*   **Integration Test Cases (Examples):**
    *   `test_simple_executor_init`: Ensure `SimpleWorkflowExecutor` initializes.
    *   `test_simple_executor_basic_execution`: Run a simple 2-step workflow using real agents and `MCPHost` (potentially with mock MCP *servers* via fixtures if needed, but not mocking the executor/host/agent classes). Verify final output.
    *   `test_simple_executor_agent_not_found`: Test failure when a step references a non-existent agent config.
    *   `test_custom_executor_init`: Ensure `CustomWorkflowExecutor` initializes.
    *   `test_custom_executor_basic_execution`: Run a simple custom workflow (that perhaps just returns input or calls one tool via the passed facade) using a real `MCPHost` and a placeholder facade. Verify output.
    *   `test_custom_executor_module_not_found`: Test failure for invalid module path.
    *   `test_custom_executor_class_not_found`: Test failure for invalid class name.
    *   `test_custom_executor_method_not_found`: Test failure if `execute_workflow` is missing.
    *   `test_custom_executor_method_signature_invalid`: Test failure if `execute_workflow` doesn't accept `(self, initial_input, executor)`.
*   **Unit Test Cases:** Add as needed to cover specific internal logic branches within the executors, potentially mocking `MCPHost` or `Agent` interactions if required for isolation.

### Phase B: Implement Execution Facade & Integrate

**Goal:** Create the `ExecutionFacade`, integrate it with `HostManager`, and update the `CustomWorkflow` interface.

**Steps:**

1.  **Create Directory:**
    *   Create `src/execution/`.
2.  **Implement `ExecutionFacade`:**
    *   Create `src/execution/facade.py`.
    *   Define class `ExecutionFacade`.
    *   **Constructor (`__init__`)**:
        *   Accepts `host_instance: MCPHost`.
        *   Accepts references to the configuration dictionaries: `agent_configs: Dict[str, AgentConfig]`, `workflow_configs: Dict[str, WorkflowConfig]`, `custom_workflow_configs: Dict[str, CustomWorkflowConfig]`.
        *   Stores these internally (e.g., `self._host`, `self._agent_configs`, etc.).
    *   **Method (`async def run_agent(...)`)**:
        *   Accepts `agent_name: str`, `user_message: str`, `system_prompt: Optional[str] = None`.
        *   Looks up `AgentConfig` from `self._agent_configs` using `agent_name`. Handle `KeyError`.
        *   Instantiates `src.agents.agent.Agent` with the config.
        *   Calls `agent_instance.execute_agent(user_message=user_message, host_instance=self._host, system_prompt=system_prompt)`.
        *   Returns the result.
    *   **Method (`async def run_simple_workflow(...)`)**:
        *   Accepts `workflow_name: str`, `initial_user_message: str`.
        *   Looks up `WorkflowConfig` from `self._workflow_configs`. Handle `KeyError`.
        *   Instantiates `src.workflows.simple_workflow.SimpleWorkflowExecutor` passing the specific `WorkflowConfig`, the *entire* `self._agent_configs` dictionary (needed for step lookups), and `self._host`.
        *   Calls `executor_instance.execute(initial_input=initial_user_message)`.
        *   Returns the result.
    *   **Method (`async def run_custom_workflow(...)`)**:
        *   Accepts `workflow_name: str`, `initial_input: Any`.
        *   Looks up `CustomWorkflowConfig` from `self._custom_workflow_configs`. Handle `KeyError`.
        *   Instantiates `src.workflows.custom_workflow.CustomWorkflowExecutor` passing the specific `CustomWorkflowConfig` and `self._host`.
        *   Calls `executor_instance.execute(initial_input=initial_input, executor=self)`. **Crucially, passes `self` (the facade instance) as the `executor` argument.**
        *   Returns the result.
3.  **Refactor `HostManager`:**
    *   In `src/host_manager.py`:
        *   Add `from src.execution.facade import ExecutionFacade`.
        *   Add `self.executor: Optional[ExecutionFacade] = None` attribute.
        *   In `initialize`:
            *   After `self.host = MCPHost(...)` and `await self.host.initialize()`, instantiate the facade:
              ```python
              self.executor = ExecutionFacade(
                  host_instance=self.host,
                  agent_configs=self.agent_configs,
                  workflow_configs=self.workflow_configs,
                  custom_workflow_configs=self.custom_workflow_configs
              )
              logger.info("ExecutionFacade initialized.")
              ```
        *   In `shutdown`: Set `self.executor = None`.
        *   Add method `get_executor(self) -> ExecutionFacade`:
            ```python
            if not self.executor:
                raise RuntimeError("HostManager is not initialized or facade is not available.")
            return self.executor
            ```
        *   **Dynamic Registration:** Verify that `register_agent`, `register_workflow`, `register_custom_workflow`, and `register_config_file` correctly update the `self.agent_configs`, `self.workflow_configs`, and `self.custom_workflow_configs` dictionaries. Since the facade holds references to these dictionaries, no explicit update to the facade is needed upon registration.
4.  **Update `CustomWorkflow` Interface:**
    *   Modify the required signature for the `execute_workflow` method in all custom workflow implementations (including examples/tests like `tests/fixtures/custom_workflows/example_workflow.py`):
        ```python
        # Change from:
        # async def execute_workflow(self, initial_input: Any, host_instance: MCPHost):
        # To:
        async def execute_workflow(self, initial_input: Any, executor: ExecutionFacade):
            # Use executor.run_agent(...), executor.run_simple_workflow(...), etc.
            # Access host capabilities via executor._host if absolutely necessary (discouraged)
            # Example: tools = executor._host.get_formatted_tools(agent_config=...)
        ```
    *   Update any custom workflows that previously accessed `host_instance` directly to now use the `executor` (primarily for calling other components, or accessing `executor._host` for direct host interactions if unavoidable).

**Testing (Phase B):**

*   **Strategy:** Integration tests first, focusing on the facade's ability to correctly orchestrate the underlying executors.
*   **Files:**
    *   `tests/execution/test_facade_integration.py`
    *   `tests/execution/test_facade_unit.py`
*   **Integration Test Cases (Examples):**
    *   `test_facade_init`: Ensure facade initializes correctly with a mock/real host and config dictionaries.
    *   `test_facade_run_agent`: Call `facade.run_agent` and verify it correctly executes the agent via `Agent.execute_agent`. Use a real `Agent` and `MCPHost`.
    *   `test_facade_run_simple_workflow`: Call `facade.run_simple_workflow` and verify it executes via `SimpleWorkflowExecutor`. Use real components.
    *   `test_facade_run_custom_workflow`: Call `facade.run_custom_workflow`. Verify it executes via `CustomWorkflowExecutor` and correctly passes the facade instance *back* to the custom workflow's method. Test a custom workflow that *uses* the passed executor to call another agent.
    *   `test_facade_dynamic_registration`: Register a new agent via `HostManager`, then execute it via the *same* facade instance to ensure the referenced config dictionary was updated.
    *   `test_facade_component_not_found`: Test `KeyError` handling when calling `run_...` for non-existent component names.
*   **Unit Test Cases:** Mock executors and host to test the facade's internal logic (config lookups, instantiation calls) in isolation if needed.

### Phase C: Update Entrypoints & Documentation

**Goal:** Modify API, Worker, and CLI entrypoints to use the `ExecutionFacade` for execution requests and update documentation.

**Steps:**

1.  **Refactor API (`src/bin/api.py`):**
    *   Identify all route handlers that perform execution (e.g., `/agents/{name}/execute`, `/workflows/{name}/execute`, `/custom_workflows/{name}/execute`).
    *   In each handler, replace calls like `host_manager.execute_agent(...)` with:
        ```python
        try:
            executor = host_manager.get_executor()
            result = await executor.run_agent(agent_name=name, user_message=payload.user_message) # Or run_workflow, etc.
            # Process result...
        except (KeyError, RuntimeError, ValueError) as e:
            # Handle errors (e.g., 404 Not Found, 500 Internal Server Error)
        ```
    *   Ensure registration endpoints (`/clients/register`, `/agents/register`, etc.) still call the `host_manager.register_...` methods directly.
2.  **Refactor Worker (`src/bin/worker.py`):**
    *   Modify the task processing logic. When an execution task is received:
        *   Get the facade: `executor = host_manager.get_executor()`.
        *   Call the appropriate `executor.run_...` method based on the task data.
        *   Handle results/errors.
    *   Registration tasks should still call `host_manager.register_...`.
3.  **Refactor CLI (`src/bin/cli.py`):**
    *   Update the `execute` command group.
    *   For `agent`, `workflow`, `custom-workflow` subcommands:
        *   Get the facade: `executor = host_manager.get_executor()`.
        *   Call the appropriate `executor.run_...` method.
        *   Print results/errors.
    *   Ensure `register` commands still call `host_manager.register_...`.
4.  **Update Documentation:**
    *   `README.md`: Update architecture diagram/description if necessary to show facade/executors. Update usage examples if CLI/API calls changed significantly.
    *   `docs/architecture_overview.md`: Detail the new execution flow involving the facade and executors. Explain the role of each component (`HostManager`, `ExecutionFacade`, Executors, `MCPHost`).
    *   `docs/framework_guide.md` (or similar developer guide): Document the new `CustomWorkflow` signature (`execute_workflow(self, initial_input, executor)`). Provide examples of how custom workflows can now call other components using the `executor`.
    *   Review other potentially relevant docs (`docs/host/host_implementation.md`, etc.) for necessary updates.

**Testing (Phase C):**

*   **Strategy:** End-to-end testing using API client (Postman/Newman) and CLI. Avoid pytest due to potential event loop complexities with entrypoint runners.
*   **Tools:**
    *   Postman Collection: `tests/api/main_server.postman_collection.json` (Update requests if necessary).
    *   Newman (for automated Postman runs).
    *   Manual CLI execution (`python -m src.bin.cli ...`).
*   **Test Cases:**
    *   **API/Newman:**
        *   Run existing "Execute Agent", "Execute Simple Workflow", "Execute Custom Workflow" requests. Verify they still work via the facade.
        *   Run existing "[Dynamic] Register ..." requests for Client, Agent, Workflow.
        *   Add a "[Dynamic] Register Custom Workflow" request.
        *   Add requests to *execute* the dynamically registered Agent, Simple Workflow, and Custom Workflow.
        *   Test execution of a Custom Workflow that *calls* another Agent or Workflow via the facade.
        *   Test error handling (e.g., 404 for non-existent components).
    *   **CLI:**
        *   Manually run `python -m src.bin.cli execute agent ...`, `... execute workflow ...`, `... execute custom-workflow ...` for existing and dynamically registered components.
        *   Manually run `python -m src.bin.cli register client ...`, `... register agent ...`, etc.
        *   Verify successful execution and correct error reporting.

## 3. Completion Criteria

*   All execution logic is removed from `HostManager` and resides in `Agent`, `SimpleWorkflowExecutor`, or `CustomWorkflowExecutor`.
*   `ExecutionFacade` provides a working, unified interface for `run_agent`, `run_simple_workflow`, `run_custom_workflow`.
*   `CustomWorkflow`s can successfully call other agents/workflows via the `ExecutionFacade` passed to their `execute_workflow` method.
*   Dynamic registration via `HostManager` correctly updates configurations used by the `ExecutionFacade`.
*   All tests defined in Phases A and B pass.
*   End-to-end testing via API (Newman) and CLI (manual) confirms execution and registration functionality for all component types (Phase C).
*   Relevant documentation (`README.md`, architecture, guides) is updated to reflect the changes.
