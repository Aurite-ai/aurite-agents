# Layer 2: Orchestration Layer

**Version:** 1.1
**Date:** 2025-05-12

## 1. Overview

The Orchestration Layer serves as the central coordination hub of the Aurite MCP framework. Its primary purpose is to manage the lifecycle and configuration of agentic components (Agents, Simple Workflows, Custom Workflows) and provide a unified interface for their execution. It bridges the high-level application entrypoints (API, CLI, Worker) with the lower-level MCP Host (Layer 3) and the optional Storage Layer.

Key responsibilities include:
*   Loading and managing configurations for the host, clients, agents, and workflows from files via `ProjectManager` and `ComponentManager`.
*   Initializing and managing the lifecycle of the underlying `MCPHost`, `ExecutionFacade`, and the optional `StorageManager`.
*   Handling dynamic registration of clients, agents, and workflows, optionally syncing these configurations to a database via the `StorageManager`.
*   Providing a consistent facade (`ExecutionFacade`) for triggering the execution of any configured agentic component.
*   Instantiating and managing the execution flow within different component types (`Agent`, `SimpleWorkflowExecutor`, `CustomWorkflowExecutor`), which act as an intermediate layer translating Facade requests into interactions with the `MCPHost` (Layer 3) and passing the `StorageManager` to Agents for history persistence.
*   Managing LLM client instances, including caching and graceful shutdown, via the `ExecutionFacade`.

## 2. Relevant Files

| File Path                             | Primary Class(es)        | Core Responsibility                                                                 | Notes                                                                                                |
| :------------------------------------ | :----------------------- | :---------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------- |
| `src/host_manager.py`                 | `HostManager`            | Overall lifecycle, config mgmt via ProjectManager, registration, DB sync (opt.)     | Orchestrates Host, Storage (opt.), Facade                                                            |
| `src/config/project_manager.py`       | `ProjectManager`         | Manages loading of project configurations and active project state.                   | Uses ComponentManager.                                                                               |
| `src/config/component_manager.py`     | `ComponentManager`       | Manages loading/storage of default component configs (clients, agents, LLMs, etc.). | Used by ProjectManager.                                                                              |
| `src/config/config_models.py`         | Config Models            | Pydantic models for all configurations (Project, Client, Agent, LLM, Workflow etc.) | Defines structure for JSON configs (formerly `src/host/models.py`). `AgentConfig.config_validation_schema`. |
| `src/config/config_utils.py`          | utils                    | Configuration loading utilities.                                                    | Handles JSON loading, path resolution.                                                               |
| `src/execution/facade.py`             | `ExecutionFacade`        | Unified execution interface, LLM client caching & shutdown (`aclose`)               | Delegates to executors, passes StorageManager to Agent, manages LLM client lifecycle                 |
| `src/agents/agent.py`                 | `Agent`                  | Core LLM interaction loop, tool use, filtering, history (opt.)                      | Interacts with Host & Storage (opt.), stores full `AgentOutputMessage` for assistant turns.        |
| `src/workflows/simple_workflow.py`    | `SimpleWorkflowExecutor` | Executes sequential agent steps                                                     | Uses Facade/Agent instances                                                                          |
| `src/workflows/custom_workflow.py`    | `CustomWorkflowExecutor` | Dynamically loads and executes custom Python workflows                              | Uses Facade instance                                                                                 |
| `src/storage/db_manager.py`           | `StorageManager`         | Handles DB interactions (config sync, history load/save)                            | Optional component, initialized by HostManager                                                       |
| `src/storage/db_connection.py`        | utils                    | Creates SQLAlchemy engine based on env vars                                         | Used by HostManager to create engine for StorageManager                                              |
| `src/storage/db_models.py`            | SQLAlchemy Models        | Defines database table structures                                                   | Used by StorageManager and Alembic (for migrations, not shown here)                                |

## 3. Functionality

This layer orchestrates the core agentic capabilities of the framework.

**3.1. Multi-File Interactions & Core Flows:**

*   **Initialization:** The `HostManager` is instantiated by an entrypoint. During `initialize()`:
    *   It optionally creates a database engine (`db_connection.py`) and initializes the `StorageManager` (`db_manager.py`) if `AURITE_ENABLE_DB=true`.
    *   It uses `ProjectManager` to load the specified project configuration (e.g., from `testing_config.json`). `ProjectManager` uses `ComponentManager` to resolve references to default components. `ProjectConfig` in `config_models.py` expects `simple_workflows` and `custom_workflows` as direct dictionaries from the JSON.
    *   It initializes the database schema via `StorageManager` if enabled.
    *   It initializes the `MCPHost` (Layer 3) with clients defined in the active project.
    *   It optionally syncs loaded configurations to the database via `StorageManager`.
    *   It initializes the `ExecutionFacade`, passing the `MCPHost` instance, the active `ProjectConfig`, and the optional `StorageManager`.
*   **Registration:** The `HostManager` provides methods (`register_client`, `register_agent`, etc.) for dynamic registration. When a component like an Agent is registered, the `HostManager` will automatically perform Just-in-Time (JIT) registration for its dependencies (e.g., any `mcp_servers` listed in the `AgentConfig`). It looks up the dependency in the `ComponentManager`'s store of packaged components and registers it if it's not already active. This allows users to reference packaged components by name without needing a project file. These changes are then reflected in the active project config and optionally synced to the database.
*   **Execution:** Entrypoints use `HostManager.execution` (`ExecutionFacade`).
    *   `ExecutionFacade` looks up component configs from its `_current_project` attribute (the active `ProjectConfig`).
    *   It manages a cache of LLM clients (`_llm_client_cache`) to reuse instances based on `LLMConfig.llm_id`. All LLM clients are instances of `LiteLLMClient`. If an `AgentConfig` has no `llm_config_id`, a temporary, non-cached client is created using agent-specific LLM parameters or defaults.
    *   It instantiates the appropriate executor (`Agent`, `SimpleWorkflowExecutor`, `CustomWorkflowExecutor`).
    *   It calls the execution method (`run_conversation` for `Agent`, `execute` for workflows).
    *   Crucially, when instantiating `Agent`, the `ExecutionFacade` passes the resolved `LLMClient` and the `StorageManager` instance (if available).
    *   The `Agent` checks its `config.include_history` flag and uses the passed `StorageManager` to load/save conversation history.
*   **Configuration Loading:** `ProjectManager` and `ComponentManager` (in `src/config/`) handle parsing/validation of JSON configs into Pydantic models (`config_models.py`), resolving paths, and managing default vs. project-specific components.
*   **Shutdown:** `HostManager.shutdown` calls `ExecutionFacade.aclose()` to close cached LLM clients, then shuts down the `MCPHost` (which closes its MCP client sessions), and disposes of the database engine if it was created.

**3.2. Individual File Functionality:**

*   **`host_manager.py` (`HostManager`):**
    *   Manages the lifecycle (`initialize`, `shutdown`) of `MCPHost`, `ExecutionFacade`, and optional `StorageManager`.
    *   Uses `ProjectManager` to load and manage project configurations.
    *   Initializes `StorageManager` based on `AURITE_ENABLE_DB` env var.
    *   Provides public methods for dynamic registration, delegating to `ProjectManager` and optionally syncing to DB via `StorageManager`.
    *   Instantiates and holds the `ExecutionFacade`.
*   **`config/project_manager.py` (`ProjectManager`):**
    *   Loads a specific project configuration file.
    *   Manages the "active" project config.
    *   Uses `ComponentManager` to resolve component references (e.g., client names as strings) against default configurations.
*   **`config/component_manager.py` (`ComponentManager`):**
    *   Loads and stores default configurations for all component types (clients, LLMs, agents, simple workflows, custom workflows) from their respective JSON/YAML files in `config/`.
*   **`config/config_models.py`:**
    *   Defines Pydantic models for all configurations (e.g., `ProjectConfig`, `ClientConfig`, `AgentConfig`, `LLMConfig`, `WorkflowConfig`, `CustomWorkflowConfig`).
    *   `ProjectConfig` expects `simple_workflows` and `custom_workflows` as dictionaries.
    *   `AgentConfig` includes `include_history` and `config_validation_schema` fields.
*   **`config/config_utils.py`:**
    *   Provides utility functions for loading and processing configuration files.
*   **`execution/facade.py` (`ExecutionFacade`):**
    *   Provides unified API (`run_agent`, `run_simple_workflow`, `run_custom_workflow`, `stream_agent_run`).
    *   Holds references to `MCPHost`, the active `ProjectConfig`, and optional `StorageManager`.
    *   Manages a cache for `BaseLLM` clients (`_llm_client_cache`) identified by `LLMConfig.llm_id`. Creates temporary clients if no `llm_config_id` is provided in `AgentConfig`.
    *   Has an `aclose()` method to shut down all cached LLM clients.
    *   Instantiates appropriate executors.
    *   Passes `StorageManager` instance and resolved `LLMClient` to `Agent`.
*   **`agents/agent.py` (`Agent`):**
    *   Manages core LLM interaction loop.
    *   Stores full `AgentOutputMessage` objects for assistant turns in its `conversation_history` list to preserve all metadata (id, model, usage). Other message types (user, tool_result) are stored as `MessageParam` dicts.
    *   Handles `tool_use` via `MCPHost`.
    *   Applies filtering via `MCPHost`.
    *   If `config.include_history` is true and a `StorageManager` is provided, loads previous history and saves the full history after execution.
    *   **Streaming SSE Indexing:** When streaming agent responses, the `Agent` (via `AgentTurnProcessor`) now primarily passes through the LLM provider's original content block indices for Server-Sent Events. This simplifies backend logic compared to previous custom index mapping.
*   **`workflows/simple_workflow.py` (`SimpleWorkflowExecutor`):**
    *   Executes a sequence of agents defined in `WorkflowConfig`.
    *   Uses `ExecutionFacade` to run each agent step.
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
*   **Location:** Tests reside within the `tests/orchestration/` directory.
*   **Approach:** Testing focuses on verifying the core responsibilities of this layer through a combination of:
    *   **Unit Tests:** Isolating and testing specific methods within `HostManager`, `ExecutionFacade`, `ProjectManager`, `ComponentManager`, and the individual Executors/Agent (potentially using mocks for dependencies like `MCPHost` or LLM calls).
    *   **Integration Tests:** Verifying the interactions *between* components within this layer (e.g., `HostManager` -> `ExecutionFacade` -> `SimpleWorkflowExecutor` -> `Agent`) and their interaction with a *real* (but potentially locally running) `MCPHost` using the `host_manager` fixture. These tests validate the end-to-end flow for registration and execution initiation.

**4.B. Testing Infrastructure:**

*   **`tests/conftest.py`:**
    *   Contains global pytest configuration: registers custom markers (`unit`, `integration`, `e2e`, `orchestration`), adds `--config` CLI option.
    *   Sets the `anyio_backend` fixture to `"asyncio"` globally.
    *   Provides a `parse_json_result` utility fixture.
*   **`tests/fixtures/host_fixtures.py`:**
    *   `host_manager`: Integration fixture initializing `HostManager` with `testing_config.json`, including `MCPHost` and dummy servers. It now calls `ExecutionFacade.aclose()` during teardown.
    *   `mock_mcp_host`: Mock `MCPHost` for unit tests.
*   **`tests/fixtures/agent_fixtures.py`:** Provides various `AgentConfig` instances.
*   **`tests/fixtures/custom_workflows/example_workflow.py`:** Example custom workflow for integration tests.
*   **`tests/fixtures/servers/`:** Dummy MCP servers for integration tests.
*   **`pytestmark = pytest.mark.anyio`:** Used in relevant test modules for async testing.

**4.C. Testing Coverage (Updated Assessment):**

| Functionality                                      | Relevant File(s)                                                                 | Existing Test File(s) / Status                                                                                                                                                                                                                         |
| :------------------------------------------------- | :------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **HostManager: Initialization (No DB)**            | `host_manager.py`, `project_manager.py`, `component_manager.py`                  | `tests/orchestration/test_host_manager_unit.py` (Unit). Integration covered by `host_manager` fixture (when DB disabled). **Coverage: Good.** |
| **HostManager: Initialization (With DB)**          | `host_manager.py`, `db_manager.py`, `db_connection.py`, `project_manager.py`     | `tests/orchestration/test_host_manager.py` (Integration - implicitly tests DB init if env var set). Needs specific unit tests mocking DB (`test_host_manager_unit.py`). **Coverage: Needs Improvement (Unit).** |
| **HostManager: Dynamic Registration (No DB)**      | `host_manager.py`, `project_manager.py`                                          | `tests/orchestration/test_host_manager_registration_unit.py` (Unit). **Coverage: Good.** |
| **HostManager: Dynamic Registration (With DB)**    | `host_manager.py`, `db_manager.py`, `project_manager.py`                         | `tests/orchestration/test_host_manager_registration_unit.py` (Unit - needs DB mock). Integration tests implicitly if DB enabled. **Coverage: Needs Improvement (Unit).** |
| **HostManager: `register_config_file` (With DB)**  | `host_manager.py`, `db_manager.py`, `project_manager.py`                         | Needs specific unit tests mocking DB (`test_host_manager_unit.py`). Integration tests implicitly if DB enabled. **Coverage: Needs Improvement (Unit).** |
| **ExecutionFacade: `run_agent` (No History)**      | `facade.py`, `agent.py`                                                          | `tests/orchestration/facade/test_facade_integration.py` (Integration), `tests/orchestration/facade/test_facade_unit.py` (Unit). **Coverage: Good.** |
| **ExecutionFacade: `run_agent` (With History)**    | `facade.py`, `agent.py`, `db_manager.py`                                         | `tests/orchestration/facade/test_facade_integration.py` (Integration - implicitly tests if DB enabled). Needs specific unit tests mocking DB (`test_facade_unit.py`). **Coverage: Needs Improvement (Unit).** |
| **ExecutionFacade: LLM Client Caching/Shutdown**   | `facade.py`                                                                      | `tests/orchestration/facade/test_facade_unit.py` (Unit - `test_run_agent_success_and_caching`). `host_manager` fixture tests shutdown. **Coverage: Good.** |
| **ExecutionFacade: `run_simple_workflow`**         | `facade.py`, `simple_workflow.py`, `agent.py`                                    | `tests/orchestration/facade/test_facade_integration.py` (Integration), `tests/orchestration/facade/test_facade_unit.py` (Unit). **Coverage: Good.** |
| **ExecutionFacade: `run_custom_workflow`**         | `facade.py`, `custom_workflow.py`                                                | `tests/orchestration/facade/test_facade_integration.py` (Integration - xfail for event loop), `tests/orchestration/facade/test_facade_unit.py` (Unit). **Coverage: Good (Unit), Fair (Integration - xfail).** |
| **ExecutionFacade: Error Handling**                | `facade.py`                                                                      | `tests/orchestration/facade/test_facade_integration.py` (Integration - Not Found), `tests/orchestration/facade/test_facade_unit.py` (Unit - Not Found, Setup Error, Exec Error). **Coverage: Good.** |
| **Agent: Execution Loop & Tool Use**               | `agent.py`                                                                       | `tests/orchestration/agent/test_agent_unit.py` (Unit - mocks LLM/Host). **Coverage: Good.** |
| **Agent: History Storage (Full Messages)**         | `agent.py`                                                                       | `tests/orchestration/agent/test_agent_unit.py` (Unit - verifies history content). **Coverage: Good.** |
| **Agent: History Load/Save (DB)**                  | `agent.py`, `db_manager.py`                                                      | `tests/orchestration/agent/test_agent_unit.py` (Unit - mocks StorageManager). **Coverage: Good (Unit).** Integration depends on Facade tests. |
| **Agent: Filtering (`client_ids`, `exclude`)**     | `agent.py`, `host.py` (filtering logic)                                          | `tests/orchestration/agent/test_agent_unit.py` (Unit - mocks Host). **Coverage: Good (Unit).** Integration depends on Facade/E2E tests. |
| **SimpleWorkflowExecutor: Sequential Execution**   | `simple_workflow.py`                                                             | `tests/orchestration/workflow/test_simple_workflow_executor_unit.py` (Unit). Integration via Facade tests. **Coverage: Good.** |
| **CustomWorkflowExecutor: Dynamic Loading/Exec**   | `custom_workflow.py`                                                             | `tests/orchestration/workflow/test_custom_workflow_executor_unit.py` (Unit). Integration via Facade tests. **Coverage: Good.** |
| **Config Loading & Validation (Project/Component)**| `config_models.py`, `project_manager.py`, `component_manager.py`, `config_utils.py` | `tests/config/test_project_manager.py`, `tests/config/test_component_manager.py`. **Coverage: Good.** |
| **StorageManager: DB Init & Sync**                 | `db_manager.py`, `db_connection.py`, `db_models.py`                              | `tests/storage/test_db_manager.py`. **Coverage: Good (Unit).** Integration tested implicitly via HostManager tests. |
| **StorageManager: History Load/Save**              | `db_manager.py`, `db_connection.py`, `db_models.py`                              | `tests/storage/test_db_manager.py`. **Coverage: Good (Unit).** Integration tested implicitly via Agent/Facade tests. |

**4.D. Remaining Testing Steps:**

1.  **Enhance HostManager Unit Tests (`tests/orchestration/test_host_manager_unit.py`):**
    *   Add specific tests for initialization and registration logic when `StorageManager` is mocked (both enabled and disabled scenarios). Verify `sync_*` methods are called appropriately.
2.  **Enhance ExecutionFacade Unit Tests (`tests/orchestration/facade/test_facade_unit.py`):**
    *   Add tests verifying that the `StorageManager` instance is correctly passed to `Agent` constructor when the facade is initialized with one.
3.  **Review Integration Tests:**
    *   Ensure `tests/orchestration/test_host_manager.py` and `tests/orchestration/facade/test_facade_integration.py` adequately cover scenarios where the database *is* enabled (requires setting `AURITE_ENABLE_DB=true` in the test environment or parameterizing fixtures). This implicitly tests the integration between `HostManager`, `Facade`, `Agent`, and `StorageManager`.
    *   Investigate and resolve the "Event loop is closed" errors currently marked with `xfail` in `test_facade_integration.py` and `test_anthropic_client_unit.py` if they become consistent blockers.
