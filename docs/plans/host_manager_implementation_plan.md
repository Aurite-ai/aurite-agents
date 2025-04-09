# Host Manager Implementation Plan

**Objective:** Introduce a `HostManager` class (`src/host_manager.py`) to encapsulate configuration loading, `MCPHost` initialization/shutdown, and the execution logic for agents, simple workflows, and custom workflows. Refactor `main.py` and test fixtures to use this manager, aiming to simplify the architecture and improve async stability during testing.

**Owner:** Ryan Wilcox (assisted by Gemini)

**Status:** Approved

**Related Docs:**
*   [Architecture Overview](docs/architecture_overview.md) (To be updated after implementation)
*   [Host Implementation](docs/host/host_implementation.md) (No changes expected)

**Background:**
Currently, `MCPHost` manages MCP server connections, `CustomWorkflowManager` handles custom Python workflows, and `main.py` orchestrates initialization and contains the logic for executing agents and simple (JSON-defined) workflows. This distribution of responsibilities adds complexity to the application lifecycle and testing, particularly concerning async resource management. This plan centralizes these responsibilities into a new `HostManager` class.

**High-Level Plan:**

1.  Create the `HostManager` class responsible for lifecycle and execution orchestration.
2.  Implement methods within `HostManager` to handle initialization, shutdown, agent execution, simple workflow execution, and custom workflow execution.
3.  Refactor `main.py` to use `HostManager` via the application lifespan and dependency injection.
4.  Refactor test fixtures (`host_fixtures.py`) to provide a `HostManager` instance for testing.
5.  Update relevant tests to use the new manager and fixtures.
6.  Remove the now-redundant `CustomWorkflowManager` (`src/workflows/manager.py`).

**Impacted Files:**

*   `src/host_manager.py` (New file)
*   `src/main.py` (Refactor lifespan, dependencies, API endpoints)
*   `tests/fixtures/host_fixtures.py` (Update/add fixtures)
*   `tests/workflows/test_custom_workflow_api.py` (Update tests, especially E2E)
*   `tests/workflows/test_workflow_api.py` (Update tests)
*   `src/workflows/manager.py` (To be deleted)
*   `src/config.py` (Minor review, likely no changes needed)
*   `src/host/host.py` (No changes expected)

**Detailed Implementation Steps:**

1.  **Create `HostManager` Class (`src/host_manager.py`):**
    *   Define `HostManager` class.
    *   Implement `__init__(self, config_path: Path)`: Store `config_path`. Initialize internal state: `self.host = None`, `self.agent_configs = {}`, `self.workflow_configs = {}`, `self.custom_workflow_configs = {}`.

2.  **Implement `HostManager.initialize()`:**
    *   Make it `async`.
    *   Call `load_host_config_from_json(self.config_path)` to get all four configuration types.
    *   Store `agent_configs_dict`, `workflow_configs_dict`, `custom_workflow_configs_dict` in `self`.
    *   Instantiate `MCPHost` using loaded `HostConfig`, `AgentConfig`, `WorkflowConfig`. Store as `self.host`. (Note: `MCPHost` itself still takes agent/workflow configs for its internal `get_..._config` methods).
    *   Call `await self.host.initialize()`.
    *   Log successful initialization.

3.  **Implement `HostManager.shutdown()`:**
    *   Make it `async`.
    *   Check if `self.host` exists and call `await self.host.shutdown()`.
    *   Clear internal state (`self.host = None`, clear config dicts).
    *   Log shutdown completion.

4.  **Implement `HostManager.execute_agent()`:**
    *   Make it `async`.
    *   Accept `agent_name: str`, `user_message: str`.
    *   Retrieve `AgentConfig` from `self.agent_configs` (handle `KeyError`).
    *   Instantiate `Agent(config=agent_config)`.
    *   Call `await agent.execute_agent(user_message=user_message, host_instance=self.host, filter_client_ids=agent_config.client_ids)`.
    *   Return the result. Include logging.

5.  **Implement `HostManager.execute_workflow()`:**
    *   Make it `async`.
    *   Accept `workflow_name: str`, `initial_user_message: str`.
    *   Retrieve `WorkflowConfig` from `self.workflow_configs` (handle `KeyError`).
    *   Implement the step-by-step execution logic (similar to current `main.py::execute_workflow_endpoint`):
        *   Loop through `workflow_config.steps`.
        *   For each step (agent name), call `await self.execute_agent(...)` with the current message.
        *   Handle agent execution errors.
        *   Extract the text output from the agent's response to use as input for the next step.
        *   Handle output extraction errors.
    *   Return the final status, message, and any error. Include logging.

6.  **Implement `HostManager.execute_custom_workflow()`:**
    *   Make it `async`.
    *   Accept `workflow_name: str`, `initial_input: Any`.
    *   Retrieve `CustomWorkflowConfig` from `self.custom_workflow_configs` (handle `KeyError`).
    *   Implement the dynamic loading logic (moved from `CustomWorkflowManager`):
        *   Path validation (within project root).
        *   `importlib.util.spec_from_file_location`, `importlib.util.module_from_spec`, `spec.loader.exec_module`.
        *   Get class using `getattr`.
        *   Instantiate the workflow class.
        *   Check for `execute_workflow` method (callable, async).
        *   Call `await workflow_instance.execute_workflow(initial_input=initial_input, host_instance=self.host)`.
    *   Return the result. Include robust error handling (FileNotFound, ImportError, AttributeError, PermissionError, TypeError, internal workflow exceptions) similar to the original manager. Include logging.

7.  **Delete `src/workflows/manager.py`:**
    *   Remove the file `src/workflows/manager.py`.
    *   Remove any imports referencing `CustomWorkflowManager` (e.g., in `main.py`, `host_fixtures.py`).

8.  **Refactor `src/main.py`:**
    *   Update `lifespan` context manager:
        *   Import `HostManager`.
        *   Instantiate `HostManager(config_path=server_config.HOST_CONFIG_PATH)`.
        *   Call `await manager.initialize()`.
        *   Store the `manager` instance in `app.state.host_manager`.
        *   Remove `app.state.mcp_host` and `app.state.workflow_manager`.
        *   In the `finally` block, retrieve `manager` from `app.state` and call `await manager.shutdown()`.
    *   Create a new dependency `get_host_manager(request: Request) -> HostManager`.
    *   Remove the old `get_mcp_host` and `get_workflow_manager` dependencies.
    *   Update API endpoints (`/agents/{agent_name}/execute`, `/workflows/{workflow_name}/execute`, `/custom_workflows/{workflow_name}/execute`):
        *   Change dependency to `manager: HostManager = Depends(get_host_manager)`.
        *   Modify endpoint logic to call the corresponding methods on the `manager` instance (e.g., `await manager.execute_agent(...)`).
        *   Remove the simple workflow execution loop from the `/workflows/...` endpoint body.

9.  **Refactor `tests/fixtures/host_fixtures.py`:**
    *   Import `HostManager`.
    *   Create a new async fixture `host_manager` (scope="function").
        *   Instantiate `HostManager` using `config/agents/testing_config.json`.
        *   Call `await manager.initialize()`.
        *   `yield manager`.
        *   In the teardown part (after `yield`), call `await manager.shutdown()`.
    *   Remove the `real_host_and_manager` fixture.
    *   Review `mock_mcp_host` fixture for continued relevance in unit tests.
    *   **Address pytest-asyncio warning:** Ensure `pytest.ini` or `pyproject.toml` has `asyncio_mode = auto` (or `strict`) and `asyncio_default_fixture_loop_scope = function`.

10. **Update Tests (`tests/workflows/test_custom_workflow_api.py`, `tests/workflows/test_workflow_api.py`):**
    *   Modify E2E tests to use the `host_manager` fixture where a real host is needed.
    *   Update unit/integration tests that previously mocked `MCPHost` or `CustomWorkflowManager` to potentially mock `HostManager` methods or use the real `host_manager` fixture.
    *   Ensure tests for simple workflows (`test_workflow_api.py`) correctly interact with the refactored endpoint and manager.

11. **Testing & Debugging:**
    *   Run all tests, paying close attention to workflow and custom workflow tests (`pytest -v tests/workflows/`).
    *   Analyze output for async errors, hangs, or unexpected behavior during execution or teardown.

**Async Handling Strategy:**
The `HostManager` becomes the single owner of the `MCPHost` instance and its associated async resources (`AsyncExitStack`, client connections).
*   In `main.py`, the FastAPI `lifespan` manages the `HostManager`'s `initialize` and `shutdown`.
*   In tests, the `host_manager` fixture manages the `HostManager`'s `initialize` and `shutdown` within the scope of the test function, ensuring isolation and proper cleanup.

**Diagram:**

```mermaid
graph TD
    subgraph FastAPI App (main.py)
        A[Lifespan Start] --> B(Instantiate HostManager);
        B --> C(await manager.initialize());
        C --> D(Store manager in app.state);
        D --> E[Yield (Server Runs)];
        E --> F(Retrieve manager from app.state);
        F --> G(await manager.shutdown());
        G --> H[Lifespan End];

        I[API Endpoint] -- Depends --> J(get_host_manager);
        J -- Reads --> D;
        I -- Calls --> K{HostManager Methods};
    end

    subgraph HostManager (host_manager.py)
        K --> L[execute_agent];
        K --> M[execute_workflow];
        K --> N[execute_custom_workflow];

        L --> O(Instantiate Agent);
        O --> P(agent.execute_agent);
        P -- Uses --> Q([MCPHost Instance]);

        M -- Calls --> L;

        N -- Contains Logic From --> R([Former CustomWorkflowManager]);
        N -- Uses --> Q;

        C --> S(Load All Configs);
        C --> T(Instantiate MCPHost);
        T -- Uses --> S;
        C --> U(await host.initialize());
        G --> V(await host.shutdown());
    end

    subgraph MCPHost (host.py)
        U --> W(Initialize Managers);
        U --> X(Initialize Clients via AsyncExitStack);
        V --> Y(Shutdown Managers);
        V --> Z(Close Clients via AsyncExitStack);
    end

    subgraph Test Fixture (host_fixtures.py)
        AA[Fixture Setup] --> AB(Instantiate HostManager);
        AB --> AC(await manager.initialize());
        AC --> AD[Yield manager];
        AD --> AE(await manager.shutdown());
        AE --> AF[Fixture Teardown];
    end

    style K fill:#f9f,stroke:#333,stroke-width:2px
    style Q fill:#ccf,stroke:#333,stroke-width:2px
    style R fill:#eee,stroke:#999,stroke-width:1px,stroke-dasharray: 5 5
