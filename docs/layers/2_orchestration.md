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
*   Instantiating and managing the execution flow within different component types (`Agent`, `SimpleWorkflowExecutor`, `CustomWorkflowExecutor`), which act as an intermediate layer (sometimes informally called Layer 2.5) translating Facade requests into interactions with the `MCPHost` (Layer 3).

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
    *   Calls the required `async def execute_workflow(self, initial_input: Any, executor: "ExecutionFacade")` method on the instance, passing the `ExecutionFacade` instance (`executor`) to enable the custom workflow to call back into the facade for executing other agents or workflows if needed (composition).

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
| **HostManager: Initialization**                    | `host_manager.py`                             | `tests/orchestration/test_host_manager.py` (Integration), `tests/orchestration/test_host_manager_unit.py` (Unit). **Coverage: Good.** |
| **HostManager: Dynamic Registration (Individual)** | `host_manager.py`                             | `tests/orchestration/test_host_manager_unit.py` (Unit). Integration tests lower priority. **Coverage: Sufficient.** |
| **HostManager: `register_config_file`**            | `host_manager.py`                             | `tests/orchestration/test_host_manager.py` (Integration), `tests/orchestration/test_host_manager_unit.py` (Unit). **Coverage: Good.** |
| **ExecutionFacade: `run_agent`**                   | `facade.py`, `agent.py`                       | `tests/orchestration/facade/test_facade_integration.py` (Integration), `tests/orchestration/facade/test_facade_unit.py` (Unit). **Coverage: Good.** |
| **ExecutionFacade: `run_simple_workflow`**         | `facade.py`, `simple_workflow.py`, `agent.py` | `tests/orchestration/facade/test_facade_integration.py` (Integration), `tests/orchestration/facade/test_facade_unit.py` (Unit). **Coverage: Good.** |
| **ExecutionFacade: `run_custom_workflow`**         | `facade.py`, `custom_workflow.py`             | `tests/orchestration/facade/test_facade_integration.py` (Integration), `tests/orchestration/facade/test_facade_unit.py` (Unit). **Coverage: Good.** |
| **ExecutionFacade: Error Handling**                | `facade.py`                                   | `tests/orchestration/facade/test_facade_integration.py` (Integration - Not Found), `tests/orchestration/facade/test_facade_unit.py` (Unit - Not Found, Setup Error, Exec Error). **Coverage: Good.** |
| **Agent: Execution Loop & Tool Use**               | `agent.py`                                    | `tests/orchestration/agent/test_agent.py` (E2E, requires API key). Implicitly tested via Facade/Workflow tests. Needs unit tests mocking LLM/tools (`tests/orchestration/agent/test_agent_unit.py`). |
| **Agent: Filtering (`client_ids`, `exclude`)**     | `agent.py`, `host.py` (filtering logic)       | `tests/orchestration/test_filtering.py`, `tests/orchestration/test_tool_filtering.py`. Good coverage exists. Needs specific unit tests in `test_agent_unit.py`. |
| **SimpleWorkflowExecutor: Sequential Execution**   | `simple_workflow.py`                          | `tests/orchestration/workflow/test_simple_workflow_executor_integration.py` (Integration). Needs unit tests (`tests/orchestration/workflow/test_simple_workflow_executor_unit.py`). |
| **CustomWorkflowExecutor: Dynamic Loading/Exec**   | `custom_workflow.py`                          | `tests/orchestration/workflow/test_custom_workflow_executor_integration.py` (Integration). Needs unit tests (`tests/orchestration/workflow/test_custom_workflow_executor_unit.py`). |
| **Config Loading & Validation**                    | `config.py`, `models.py`                      | `tests/orchestration/config/test_config_loading.py`. **Coverage: Good.** |

**4.D. Remaining Testing Steps:**

1.  **Implement Agent Unit Tests (`tests/orchestration/agent/test_agent_unit.py`):**
    *   Focus on `execute_agent` loop logic.
    *   Mock `_make_llm_call` and `host_instance.execute_tool` (using `mock_mcp_host`) to simulate various LLM responses (tool use, no tool use, errors).
    *   **Crucially, add unit tests specifically verifying the `client_ids` and `exclude_components` filtering logic when `host_instance.get_formatted_tools` is called.**
2.  **Implement SimpleWorkflowExecutor Unit Tests (`tests/orchestration/workflow/test_simple_workflow_executor_unit.py`):**
    *   Focus on the `execute` method's sequential logic.
    *   Mock `Agent` instantiation and `execute_agent` calls.
    *   Test edge cases (empty steps, agent errors during a step).
3.  **Implement CustomWorkflowExecutor Unit Tests (`tests/orchestration/workflow/test_custom_workflow_executor_unit.py`):**
    *   Focus on the `execute` method's dynamic loading and execution.
    *   Mock `importlib`, file system interactions (`Path.exists`), and the dynamically loaded class/method (`execute_workflow`).
    *   Test error conditions (module not found, class not found, `execute_workflow` method missing or not async, errors within the custom workflow).
4.  **Enhance Existing Integration/E2E Tests:**
    *   Review `tests/orchestration/agent/test_agent.py` (E2E) to ensure it adequately covers agent execution with filtering, potentially adding cases using `agent_config_filtered`.
    *   Review integration tests (`test_facade_integration`, `test_*_workflow_executor_integration`, `test_host_manager`) to ensure they cover key success and failure paths in the *orchestrated* flow (interactions between Facade, Executors, and Host). Consider adding specific integration tests for Facade error handling if gaps are identified.
