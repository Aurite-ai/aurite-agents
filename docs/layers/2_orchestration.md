# Layer 2: Orchestration Layer

**Version:** 1.0
**Date:** 2025-05-04

## 1. Overview

The Orchestration Layer serves as the central coordination hub of the Aurite MCP framework. Its primary purpose is to manage the lifecycle and configuration of agentic components (Agents, Simple Workflows, Custom Workflows) and provide a unified interface for their execution. It bridges the high-level application entrypoints (API, CLI, Worker) with the lower-level MCP Host (Layer 3) and the optional Storage Layer.

Key responsibilities include:
*   Loading and managing configurations for the host, clients, agents, and workflows from files.
*   Initializing and managing the lifecycle of the underlying `MCPHost` and the optional `StorageManager`.
*   Handling dynamic registration of clients, agents, and workflows, optionally syncing these configurations to a database via the `StorageManager`.
*   Providing a consistent facade (`ExecutionFacade`) for triggering the execution of any configured agentic component.
*   Instantiating and managing the execution flow within different component types (`Agent`, `SimpleWorkflowExecutor`, `CustomWorkflowExecutor`), which act as an intermediate layer (sometimes informally called Layer 2.5) translating Facade requests into interactions with the `MCPHost` (Layer 3) and passing the `StorageManager` to Agents for history persistence.

## 2. Relevant Files

| File Path                          | Primary Class(es)        | Core Responsibility                                            | Notes                                                                 |
| :--------------------------------- | :----------------------- | :------------------------------------------------------------- | :-------------------------------------------------------------------- |
| `src/host_manager.py`              | `HostManager`            | Overall lifecycle, config mgmt, registration, DB sync (opt.) | Orchestrates Host, Storage (opt.), Facade                             |
| `src/config.py`                    | `ServerConfig`, utils    | Server config loading, Host/Agent/Workflow config parsing      | Handles JSON loading and path resolution                              |
| `src/host/models.py`               | Config Models            | Pydantic models for all configurations                         | Defines structure for JSON configs                                    |
| `src/execution/facade.py`          | `ExecutionFacade`        | Unified execution interface for components                     | Delegates to executors, passes StorageManager to Agent                |
| `src/agents/agent.py`              | `Agent`                  | Core LLM interaction loop, tool use, filtering, history (opt.) | Interacts with Host and Storage (opt.)                                |
| `src/workflows/simple_workflow.py` | `SimpleWorkflowExecutor` | Executes sequential agent steps                                | Uses Facade/Agent instances                                           |
| `src/workflows/custom_workflow.py` | `CustomWorkflowExecutor` | Dynamically loads and executes custom Python workflows         | Uses Facade instance                                                  |
| `src/storage/db_manager.py`        | `StorageManager`         | Handles DB interactions (config sync, history load/save)       | Optional component, initialized by HostManager                        |
| `src/storage/db_connection.py`     | utils                    | Creates SQLAlchemy engine based on env vars                    | Used by HostManager to create engine for StorageManager               |
| `src/storage/db_models.py`         | SQLAlchemy Models        | Defines database table structures                              | Used by StorageManager and Alembic (for migrations, not shown here) |

## 3. Functionality

This layer orchestrates the core agentic capabilities of the framework.

**3.1. Multi-File Interactions & Core Flows:**

*   **Initialization:** The `HostManager` is instantiated by an entrypoint. During `initialize()`:
    *   It optionally creates a database engine (`db_connection.py`) and initializes the `StorageManager` (`db_manager.py`) if `AURITE_ENABLE_DB=true`.
    *   It loads configurations (`config.py`, `models.py`).
    *   It initializes the database schema via `StorageManager` if enabled.
    *   It initializes the `MCPHost` (Layer 3).
    *   It optionally syncs loaded configurations to the database via `StorageManager`.
    *   It initializes the `ExecutionFacade`, passing itself and the optional `StorageManager`.
*   **Registration:** The `HostManager` provides methods (`register_client`, `register_agent`, etc., `register_config_file`) for dynamic registration. These update in-memory configs and optionally sync changes to the database via `StorageManager`.
*   **Execution:** Entrypoints use `HostManager.execution` (`ExecutionFacade`).
    *   `ExecutionFacade` looks up configs from `HostManager`.
    *   It instantiates the appropriate executor (`Agent`, `SimpleWorkflowExecutor`, `CustomWorkflowExecutor`).
    *   It calls the execution method (`execute_agent`, `execute`).
    *   Crucially, when calling `Agent.execute_agent`, the `ExecutionFacade` passes the `StorageManager` instance (if available) from the `HostManager`.
    *   The `Agent` checks its `include_history` config flag and uses the passed `StorageManager` to load/save conversation history if both are true/available.
*   **Configuration Loading:** `config.py` handles parsing/validation of JSON configs into Pydantic models (`models.py`), resolving paths.
*   **Shutdown:** `HostManager.shutdown` shuts down the `MCPHost` and disposes of the database engine if it was created.

**3.2. Individual File Functionality:**

*   **`host_manager.py` (`HostManager`):**
    *   Manages the lifecycle (`initialize`, `shutdown`) of `MCPHost` and optional `StorageManager`.
    *   Initializes `StorageManager` based on `AURITE_ENABLE_DB` env var.
    *   Holds in-memory dictionaries of loaded/registered configurations.
    *   Provides public methods for dynamic registration, optionally syncing to DB via `StorageManager`.
    *   Instantiates and holds the `ExecutionFacade`.
*   **`config.py`:**
    *   `ServerConfig`: Loads server-level settings.
    *   `load_host_config_from_json`: Parses main JSON config, validates structure, resolves paths.
*   **`host/models.py`:**
    *   Defines Pydantic models for all configurations, including `AgentConfig.include_history`.
*   **`execution/facade.py` (`ExecutionFacade`):**
    *   Provides unified API (`run_agent`, `run_simple_workflow`, `run_custom_workflow`).
    *   References `HostManager` for configs, `MCPHost`, and `StorageManager`.
    *   Instantiates appropriate executors.
    *   Passes `StorageManager` instance to `Agent.execute_agent`.
*   **`agents/agent.py` (`Agent`):**
    *   Manages core LLM interaction loop.
    *   Handles `tool_use` via `MCPHost`.
    *   Applies filtering via `MCPHost`.
    *   If `config.include_history` is true and a `StorageManager` is provided during `execute_agent`, loads previous history before the first LLM call and saves the full history after execution completes.
*   **`workflows/simple_workflow.py` (`SimpleWorkflowExecutor`):**
    *   Executes a sequence of agents defined in `WorkflowConfig`.
    *   Uses `ExecutionFacade` (indirectly via `Agent` instantiation) to run each agent step.
*   **`workflows/custom_workflow.py` (`CustomWorkflowExecutor`):**
    *   Dynamically loads and executes a Python class defined in `CustomWorkflowConfig`.
    *   Passes the `ExecutionFacade` instance to the custom workflow's `execute_workflow` method.
*   **`storage/db_manager.py` (`StorageManager`):**
    *   Provides methods to interact with the database (sync configs, load/save history).
    *   Uses SQLAlchemy sessions managed internally.
*   **`storage/db_connection.py`:**
    *   `create_db_engine`: Factory function to create a SQLAlchemy engine based on `AURITE_DB_*` environment variables.
*   **`storage/db_models.py`:**
    *   Defines SQLAlchemy ORM models mapping to database tables (e.g., `AgentConfigDB`, `ConversationHistoryDB`).

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
    *   `host_manager`: Integration fixture initializing `HostManager` with `testing_config.json`, including `MCPHost` and dummy servers. **Note:** This fixture likely needs updating if tests require the DB to be enabled/disabled explicitly, potentially by parameterizing it or creating separate fixtures. Currently, it relies on the environment state (`AURITE_ENABLE_DB`).
    *   `mock_mcp_host`: Mock `MCPHost` for unit tests.
*   **`tests/fixtures/agent_fixtures.py`:** Provides various `AgentConfig` instances.
*   **`tests/fixtures/custom_workflows/example_workflow.py`:** Example custom workflow for integration tests.
*   **`tests/fixtures/servers/`:** Dummy MCP servers for integration tests.
*   **`tests/storage/conftest.py` (or similar):** Likely contains fixtures like `db_session` for managing test database sessions (if following standard patterns).
*   **`pytestmark = pytest.mark.anyio`:** Used in relevant test modules for async testing.

**4.C. Testing Coverage (Updated Assessment):**

| Functionality                                      | Relevant File(s)                                      | Existing Test File(s) / Status                                                                                                                                                                                                                         |
| :------------------------------------------------- | :---------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **HostManager: Initialization (No DB)**            | `host_manager.py`                                     | `tests/orchestration/test_host_manager_unit.py` (Unit). Integration covered by `host_manager` fixture (when DB disabled). **Coverage: Good.** |
| **HostManager: Initialization (With DB)**          | `host_manager.py`, `db_manager.py`, `db_connection.py` | `tests/orchestration/test_host_manager.py` (Integration - implicitly tests DB init if env var set). Needs specific unit tests mocking DB (`test_host_manager_unit.py`). **Coverage: Needs Improvement (Unit).** |
| **HostManager: Dynamic Registration (No DB)**      | `host_manager.py`                                     | `tests/orchestration/test_host_manager_unit.py` (Unit). **Coverage: Sufficient.** |
| **HostManager: Dynamic Registration (With DB)**    | `host_manager.py`, `db_manager.py`                    | `tests/orchestration/test_host_manager.py` (Integration - implicitly tests DB sync if env var set). Needs specific unit tests mocking DB (`test_host_manager_unit.py`). **Coverage: Needs Improvement (Unit).** |
| **HostManager: `register_config_file` (With DB)**  | `host_manager.py`, `db_manager.py`                    | `tests/orchestration/test_host_manager.py` (Integration - implicitly tests DB sync if env var set). Needs specific unit tests mocking DB (`test_host_manager_unit.py`). **Coverage: Needs Improvement (Unit).** |
| **ExecutionFacade: `run_agent` (No History)**      | `facade.py`, `agent.py`                               | `tests/orchestration/facade/test_facade_integration.py` (Integration), `tests/orchestration/facade/test_facade_unit.py` (Unit). **Coverage: Good.** |
| **ExecutionFacade: `run_agent` (With History)**    | `facade.py`, `agent.py`, `db_manager.py`              | `tests/orchestration/facade/test_facade_integration.py` (Integration - implicitly tests if DB enabled). Needs specific unit tests mocking DB (`test_facade_unit.py`). **Coverage: Needs Improvement (Unit).** |
| **ExecutionFacade: `run_simple_workflow`**         | `facade.py`, `simple_workflow.py`, `agent.py`         | `tests/orchestration/facade/test_facade_integration.py` (Integration), `tests/orchestration/facade/test_facade_unit.py` (Unit). **Coverage: Good.** |
| **ExecutionFacade: `run_custom_workflow`**         | `facade.py`, `custom_workflow.py`                     | `tests/orchestration/facade/test_facade_integration.py` (Integration), `tests/orchestration/facade/test_facade_unit.py` (Unit). **Coverage: Good.** |
| **ExecutionFacade: Error Handling**                | `facade.py`                                           | `tests/orchestration/facade/test_facade_integration.py` (Integration - Not Found), `tests/orchestration/facade/test_facade_unit.py` (Unit - Not Found, Setup Error, Exec Error). **Coverage: Good.** |
| **Agent: Execution Loop & Tool Use**               | `agent.py`                                            | `tests/orchestration/agent/test_agent.py` (E2E), `tests/orchestration/agent/test_agent_unit.py` (Unit - mocks LLM/Host). **Coverage: Good.** |
| **Agent: History Load/Save**                       | `agent.py`, `db_manager.py`                           | `tests/orchestration/agent/test_agent_unit.py` (Unit - mocks StorageManager). **Coverage: Good (Unit).** Integration depends on Facade tests. |
| **Agent: Filtering (`client_ids`, `exclude`)**     | `agent.py`, `host.py` (filtering logic)               | `tests/orchestration/agent/test_agent_unit.py` (Unit - mocks Host). **Coverage: Good (Unit).** Integration depends on Facade/E2E tests. |
| **SimpleWorkflowExecutor: Sequential Execution**   | `simple_workflow.py`                                  | `tests/orchestration/workflow/test_simple_workflow_executor_integration.py` (Integration), `tests/orchestration/workflow/test_simple_workflow_executor_unit.py` (Unit). **Coverage: Good.** |
| **CustomWorkflowExecutor: Dynamic Loading/Exec**   | `custom_workflow.py`                                  | `tests/orchestration/workflow/test_custom_workflow_executor_integration.py` (Integration), `tests/orchestration/workflow/test_custom_workflow_executor_unit.py` (Unit). **Coverage: Good.** |
| **Config Loading & Validation**                    | `config.py`, `models.py`                              | `tests/orchestration/config/test_config_loading.py`. **Coverage: Good.** |
| **StorageManager: DB Init & Sync**                 | `db_manager.py`, `db_connection.py`, `db_models.py`   | `tests/storage/test_db_manager.py`. **Coverage: Good (Unit).** Integration tested implicitly via HostManager tests. |
| **StorageManager: History Load/Save**              | `db_manager.py`, `db_connection.py`, `db_models.py`   | `tests/storage/test_db_manager.py`. **Coverage: Good (Unit).** Integration tested implicitly via Agent/Facade tests. |

**4.D. Remaining Testing Steps:**

1.  **Enhance HostManager Unit Tests (`tests/orchestration/test_host_manager_unit.py`):**
    *   Add specific tests for initialization and registration logic when `StorageManager` is mocked (both enabled and disabled scenarios). Verify `sync_*` methods are called appropriately.
2.  **Enhance ExecutionFacade Unit Tests (`tests/orchestration/facade/test_facade_unit.py`):**
    *   Add tests verifying that the `StorageManager` instance is correctly passed to `Agent.execute_agent` when the facade is initialized with one.
3.  **Review Integration Tests:**
    *   Ensure `tests/orchestration/test_host_manager.py` and `tests/orchestration/facade/test_facade_integration.py` adequately cover scenarios where the database *is* enabled (requires setting `AURITE_ENABLE_DB=true` in the test environment or parameterizing fixtures). This implicitly tests the integration between `HostManager`, `Facade`, `Agent`, and `StorageManager`.
