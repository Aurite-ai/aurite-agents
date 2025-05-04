# Layer 2: Orchestration Layer

**Version:** 1.0
**Date:** 2025-05-04

## 1. Overview

The Orchestration Layer serves as the central coordination hub of the Aurite MCP framework. Its primary purpose is to manage the lifecycle and configuration of agentic components (Agents, Simple Workflows, Custom Workflows) and provide a unified interface for their execution. It bridges the high-level application entrypoints (API, CLI, Worker) with the lower-level MCP Host (Layer 3) interactions.

Key responsibilities include:
*   Loading and managing configurations for the host, clients, agents, and workflows.
*   Initializing and managing the lifecycle of the underlying `MCPHost`.
*   Handling dynamic registration of clients, agents, and workflows.
*   Providing a consistent facade (`ExecutionFacade`) for triggering the execution of any configured agentic component.
*   Orchestrating the execution flow within different component types (e.g., sequential steps in Simple Workflows, dynamic loading in Custom Workflows).

## 2. Relevant Files

| File Path                          | Primary Class(es)        | Core Responsibility                                       |
| :--------------------------------- | :----------------------- | :-------------------------------------------------------- |
| `src/host_manager.py`              | `HostManager`            | Overall lifecycle, configuration management, registration |
| `src/config.py`                    | `ServerConfig`, utils    | Server config loading, Host/Agent/Workflow config parsing |
| `src/host/models.py`               | Config Models            | Pydantic models for all configurations                    |
| `src/execution/facade.py`          | `ExecutionFacade`        | Unified execution interface for components                |
| `src/agents/agent.py`              | `Agent`                  | Core LLM interaction loop, tool use, filtering            |
| `src/workflows/simple_workflow.py` | `SimpleWorkflowExecutor` | Executes sequential agent steps                           |
| `src/workflows/custom_workflow.py` | `CustomWorkflowExecutor` | Dynamically loads and executes custom Python workflows    |

## 3. Functionality

This layer orchestrates the core agentic capabilities of the framework.

**3.1. Multi-File Interactions & Core Flows:**

*   **Initialization:** The `HostManager` is typically instantiated by an entrypoint (like `api.py`). During its `initialize()` method, it uses `config.py`'s `load_host_config_from_json` to parse configurations (`models.py`) from a file. It then initializes the `MCPHost` (Layer 3) and subsequently the `ExecutionFacade`.
*   **Registration:** The `HostManager` provides methods (`register_client`, `register_agent`, etc., and `register_config_file`) to dynamically add new configurations after initialization. These methods update the manager's internal dictionaries (`agent_configs`, etc.).
*   **Execution:** Entrypoints interact with the `HostManager.execution` attribute (which holds the `ExecutionFacade` instance). The `ExecutionFacade` provides `run_agent`, `run_simple_workflow`, and `run_custom_workflow` methods.
    *   The `ExecutionFacade` looks up the relevant configuration from the `HostManager`'s dictionaries.
    *   It then instantiates the appropriate executor (`Agent`, `SimpleWorkflowExecutor`, `CustomWorkflowExecutor`).
    *   It calls the `execute` (or `execute_agent`) method on the instantiated object.
    *   For `CustomWorkflowExecutor`, the facade passes *itself* (`self`) to the custom workflow's `execute_workflow` method, enabling composition.
    *   For `SimpleWorkflowExecutor`, the facade passes the necessary `AgentConfig` dictionary and the `MCPHost` instance.
    *   For `Agent`, the facade passes the `MCPHost` instance and execution parameters.
*   **Configuration Loading:** `config.py` handles the parsing and validation of JSON configuration files into Pydantic models defined in `models.py`, resolving relative paths for servers and custom workflows.

**3.2. Individual File Functionality:**

*   **`host_manager.py` (`HostManager`):**
    *   Manages the lifecycle (`initialize`, `shutdown`) of the `MCPHost`.
    *   Holds dictionaries of loaded/registered configurations (`agent_configs`, `workflow_configs`, `custom_workflow_configs`).
    *   Provides public methods for dynamic registration of components.
    *   Instantiates and holds the `ExecutionFacade`.
*   **`config.py`:**
    *   `ServerConfig`: Loads server-level settings (port, API key, etc.) from environment variables.
    *   `load_host_config_from_json`: Parses the main JSON config, validates structure using models from `models.py`, resolves paths relative to the project root, and returns structured config objects/dictionaries.
*   **`host/models.py`:**
    *   Defines Pydantic models (`HostConfig`, `ClientConfig`, `AgentConfig`, `WorkflowConfig`, `CustomWorkflowConfig`, etc.) ensuring type safety and validation for all configuration structures.
*   **`execution/facade.py` (`ExecutionFacade`):**
    *   Provides a clean, unified API (`run_agent`, `run_simple_workflow`, `run_custom_workflow`) abstracting away the specific executor details.
    *   References the `HostManager` to access current configurations and the `MCPHost`.
    *   Handles the instantiation of the correct executor/agent based on the requested component type.
    *   Contains shared logic (`_execute_component`) for the execution flow (config lookup, instantiation, execution call, error handling).
*   **`agents/agent.py` (`Agent`):**
    *   Manages the core interaction loop with the LLM (Anthropic API).
    *   Handles `tool_use` requests from the LLM by calling `MCPHost.execute_tool`.
    *   Applies agent-specific filtering (`client_ids`, `exclude_components`) when requesting tools from the `MCPHost`.
    *   Configures LLM parameters (model, temperature, system prompt).
*   **`workflows/simple_workflow.py` (`SimpleWorkflowExecutor`):**
    *   Takes a `WorkflowConfig` and executes the defined sequence of agents.
    *   Retrieves `AgentConfig` for each step.
    *   Instantiates and executes each `Agent` sequentially, passing the output of one step as the input to the next.
*   **`workflows/custom_workflow.py` (`CustomWorkflowExecutor`):**
    *   Takes a `CustomWorkflowConfig`.
    *   Dynamically imports the Python module specified in the config.
    *   Instantiates the specified class from the module.
    *   Calls the required `async def execute_workflow(self, initial_input: Any, executor: ExecutionFacade)` method on the instance, passing the `ExecutionFacade` to enable further component calls.

## 4. Testing

**4.A. Testing Overview:**

*   **Execution:** Tests for this layer are run using the `orchestration` marker: `pytest -m orchestration`
*   **Location:** Tests reside within the `tests/orchestration/` directory (to be created). Existing relevant tests from `tests/execution/`, `tests/workflows/`, and `tests/host/` will be moved and marked.
*   **Approach:** Testing focuses on verifying the core responsibilities of this layer through a combination of:
    *   **Unit Tests:** Isolating and testing specific methods within `HostManager`, `ExecutionFacade`, and the individual Executors/Agent (potentially using mocks for dependencies like `MCPHost` or LLM calls).
    *   **Integration Tests:** Verifying the interactions *between* components within this layer (e.g., `HostManager` -> `ExecutionFacade` -> `SimpleWorkflowExecutor` -> `Agent`) and their interaction with a *real* (but potentially locally running) `MCPHost` using the `host_manager` fixture. These tests validate the end-to-end flow for registration and execution initiation.

**4.B. Testing Infrastructure:**

*   **`tests/conftest.py`:**
    *   Contains global pytest configuration: registers custom markers (`unit`, `integration`, `e2e`), adds `--config` CLI option.
    *   Sets the `anyio_backend` fixture to `"asyncio"` globally. Note: While most tests use `pytestmark = pytest.mark.anyio` at the module level, this global setting might be relevant for potential future tests or fixtures.
    *   Provides a `parse_json_result` utility fixture.
*   **`tests/fixtures/host_fixtures.py`:**
    *   `host_manager`: A crucial **function-scoped** integration fixture. It initializes a `HostManager` instance using `config/testing_config.json`, which in turn initializes a real `MCPHost` and connects to the dummy MCP servers defined in that config (`weather_server`, `planning_server`, `address_server`). It handles setup and teardown, including suppressing known `RuntimeError: Event loop is closed` errors during teardown (a workaround for `anyio`/`asyncio` interaction issues with `AsyncExitStack`). Provides a realistic environment for testing orchestration logic.
    *   `mock_mcp_host`: Provides a `unittest.mock.Mock` object mimicking `MCPHost`, useful for unit tests needing isolation from real host interactions.
    *   `mock_host_config`: Provides a basic `HostConfig` mock.
*   **`tests/fixtures/agent_fixtures.py`:** Provides various `AgentConfig` instances for testing different agent setups (minimal, filtered, specific LLM params).
*   **`tests/fixtures/custom_workflows/example_workflow.py`:** A simple custom workflow implementation used for testing the `CustomWorkflowExecutor` and facade integration via the `host_manager` fixture.
*   **`tests/fixtures/servers/`:** Contains dummy MCP server implementations (like `weather_mcp_server.py`, `planning_server.py`) used by the `host_manager` fixture during integration tests.
*   **`pytestmark = pytest.mark.anyio`:** Used at the module level in relevant test files (`test_host_manager.py`, `test_simple_workflow_executor_integration.py`, etc.) to ensure tests run correctly with the async fixtures and `anyio`.

**4.C. Testing Coverage (Updated Assessment):**

| Functionality                                      | Relevant File(s)                              | Existing Test File(s) / Status                                                                                                                                                                                                                         |
| :------------------------------------------------- | :-------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **HostManager: Initialization**                    | `host_manager.py`                             | `tests/host/test_host_manager.py::TestHostManagerInitialization::test_host_manager_initialization_success` (Integration via `host_manager` fixture). Checks counts based on `testing_config.json` + `prompt_validation_config.json`. Needs unit tests. |
| **HostManager: Dynamic Registration (Individual)** | `host_manager.py`                             | No dedicated tests calling `register_client/agent/workflow` directly. Partially covered by API tests.                                                                                                                                                  |
| **HostManager: `register_config_file`**            | `host_manager.py`                             | `tests/host/test_host_manager.py::TestHostManagerDynamicRegistration::test_register_config_file_success` (Integration via `host_manager` fixture, uses `testing_dynamic_config.json`). Checks counts and handles duplicates.                           |
| **ExecutionFacade: `run_agent`**                   | `facade.py`, `agent.py`                       | `tests/execution/test_facade_integration.py::test_facade_run_agent` (Integration via `host_manager`). Needs unit tests for facade logic.                                                                                                               |
| **ExecutionFacade: `run_simple_workflow`**         | `facade.py`, `simple_workflow.py`, `agent.py` | `tests/execution/test_facade_integration.py::test_facade_run_simple_workflow` (Integration via `host_manager`). Needs unit tests for facade logic.                                                                                                     |
| **ExecutionFacade: `run_custom_workflow`**         | `facade.py`, `custom_workflow.py`             | `tests/execution/test_facade_integration.py::test_facade_run_custom_workflow` (Integration via `host_manager`). Needs unit tests for facade logic.                                                                                                     |
| **ExecutionFacade: Error Handling**                | `facade.py`                                   | `tests/execution/test_facade_integration.py` (Tests `_not_found` errors). Coverage of `_execute_component` helper needs verification/addition.                                                                                                         |
| **Agent: Execution Loop & Tool Use**               | `agent.py`                                    | `tests/agents/test_agent.py::TestAgentE2E::test_agent_e2e_basic_execution_real_llm` (E2E, requires API key). Implicitly tested via Facade/Workflow tests. Needs unit tests mocking LLM/tools.                                                          |
| **Agent: Filtering (`client_ids`, `exclude`)**     | `agent.py`, `host.py` (filtering logic)       | `tests/host/test_filtering.py`, `tests/host/test_tool_filtering.py`. Good coverage exists, needs marking/moving. `test_agent.py` is outdated for filtering.                                                                                            |
| **SimpleWorkflowExecutor: Sequential Execution**   | `simple_workflow.py`                          | `tests/workflows/test_simple_workflow_executor_integration.py` (Integration tests: init, basic exec, agent not found via `host_manager`). Needs unit tests.                                                                                            |
| **CustomWorkflowExecutor: Dynamic Loading/Exec**   | `custom_workflow.py`                          | `tests/workflows/test_custom_workflow_executor_integration.py` (Integration tests: init, basic exec via `host_manager`). Needs unit tests (mocking `importlib`, etc.).                                                                                 |
| **Config Loading & Validation**                    | `config.py`, `models.py`                      | `tests/config/test_config_loading.py`. Good coverage exists, needs marking/moving.                                                                                                                                                                     |

**4.D. Next Steps for Testing (Updated):**

1.  **Create Directory & Marker:** Create `tests/orchestration/`. Define `@pytest.mark.orchestration` in `tests/conftest.py` (if not already present - it should be added).
2.  **Refactor Existing Tests:**
    *   **Status:** In Progress
    *   **Moved & Marked:**
        *   `tests/orchestration/test_config_loading.py`
        *   `tests/orchestration/test_facade_integration.py`
        *   `tests/orchestration/test_simple_workflow_executor_integration.py`
        *   `tests/orchestration/test_custom_workflow_executor_integration.py`
        *   `tests/orchestration/test_host_manager.py`
        *   `tests/orchestration/test_filtering.py`
    *   **To Move & Mark:**
        *   `tests/host/test_tool_filtering.py` -> `tests/orchestration/test_tool_filtering.py`
        *   `tests/agents/test_agent.py` -> `tests/orchestration/test_agent.py`
    *   **Next Action:** Apply marker to remaining moved files, then move `test_agent.py` and mark it. Finally, run `pytest -m orchestration` and ensure all refactored tests pass (expect `test_agent.py` might need adjustments or skipping initially).
3.  **Implement Missing Unit Tests:**
    *   `HostManager`: Unit test `register_agent`, `register_workflow`, `register_custom_workflow` methods (mocking `self.host` and checking internal dictionaries). Unit test `_register_*_from_config` helpers.
    *   `ExecutionFacade`: Unit test `_execute_component` helper logic (mocking dependencies like `config_lookup`, `executor_setup`, `execution_func`).
    *   `Agent`: Unit test `execute_agent` loop logic, mocking `_make_llm_call` and `host_instance.execute_tool` to simulate different LLM responses (tool use, no tool use, errors). **Crucially, add unit tests specifically verifying the `client_ids` and `exclude_components` filtering logic when `host_instance.get_formatted_tools` is called.**
    *   `SimpleWorkflowExecutor`: Unit test `execute` method logic, mocking `Agent` instantiation and `execute_agent` calls. Test edge cases (empty steps, agent errors).
    *   `CustomWorkflowExecutor`: Unit test `execute` method, mocking `importlib`, file system interactions (`Path.exists`), and the dynamically loaded class/method. Test error conditions (file not found, class not found, method not async, etc.).
4.  **Implement Missing Integration Tests:**
    *   `HostManager`: Add integration tests for individual dynamic registration methods (`register_client`, `register_agent`, etc.) using the `host_manager` fixture to verify state changes.
5.  **Update & Enhance Existing Tests:**
    *   Update `tests/orchestration/test_agent.py` (formerly `tests/agents/test_agent.py`) to correctly test agent execution *with* the current filtering mechanisms, potentially adding new test cases using the `agent_config_filtered` fixture.
    *   Review integration tests (`test_facade_integration`, `test_*_workflow_executor_integration`, `test_host_manager`) to ensure they cover key success and failure paths in the orchestration flow.
