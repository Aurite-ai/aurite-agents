# Layer 1: Entrypoints

**Version:** 1.0
**Date:** 2025-05-05

## 1. Overview

Layer 1 provides the external interfaces for interacting with the Aurite Agents framework. It exposes the core functionalities managed by the Orchestration Layer (Layer 2) through various access points, allowing users and external systems to register and execute agentic components (Agents, Simple Workflows, Custom Workflows).

This layer consists of:
*   A **FastAPI Server (`api.py`)**: Offers a RESTful API for programmatic interaction, suitable for UIs and other services.
*   A **Redis Worker (`worker.py`)**: Listens to a Redis stream for asynchronous task processing (registration/execution).
*   A **Command-Line Interface (`cli.py`)**: Provides convenient terminal-based access to the API for development and scripting.

All entrypoints primarily interact with the `HostManager` (Layer 2) to access configuration, registration methods, and the `ExecutionFacade` for running components.

## 2. Relevant Files

| File Path             | Primary Class(es)/Modules | Core Responsibility                                                                 |
| :-------------------- | :------------------------ | :---------------------------------------------------------------------------------- |
| `src/bin/api.py`      | `FastAPI`, `uvicorn`      | Provides HTTP endpoints for registration and execution, manages API lifecycle.      |
| `src/bin/worker.py`   | `redis.asyncio`, `asyncio`| Listens to Redis stream, parses tasks, delegates registration/execution to HostManager. |
| `src/bin/cli.py`      | `typer`, `httpx`          | Provides CLI commands that interact with the running API server via HTTP requests.  |
| `src/host_manager.py` | `HostManager`             | (Layer 2) Central class used by `api.py` and `worker.py` for orchestration.       |

## 3. Functionality

Describes how the entrypoints provide access to the framework's capabilities.

**3.1. Multi-File Interactions & Core Flows:**

*   **Initialization:**
    *   `api.py`: Uses a FastAPI `lifespan` context manager to instantiate `HostManager`, call `HostManager.initialize()`, and store the instance in `app.state`. It also handles `HostManager.shutdown()` on exit.
    *   `worker.py`: Instantiates `HostManager` and calls `HostManager.initialize()` at the start of its `main()` function. Calls `HostManager.shutdown()` during graceful shutdown.
    *   `cli.py`: Does *not* directly initialize `HostManager`. It relies on a running API server instance.
*   **Configuration & Dependencies:**
    *   `api.py` & `worker.py`: Use `src/config.py` (`ServerConfig`, `get_server_config`) to load environment variables (API Key, Redis details, Host Config Path, DB settings, etc.).
    *   `api.py`: Uses FastAPI dependency injection (`Depends`, `Security`) to provide `HostManager`, `ServerConfig`, and validate the API key (`X-API-Key` header) for protected endpoints.
*   **Registration Flow (API/Worker):**
    1.  Entrypoint receives registration request (HTTP POST for API, Redis message for Worker) containing component configuration (e.g., `ClientConfig`, `AgentConfig`).
    2.  Entrypoint validates the input data (FastAPI handles Pydantic validation automatically; Worker does basic checks and JSON parsing).
    3.  Entrypoint calls the corresponding `HostManager.register_*` method (e.g., `register_client`, `register_agent`).
    4.  `HostManager` updates its internal state and optionally syncs with the database (via `StorageManager`).
    5.  Entrypoint returns success/error response (HTTP for API, logging for Worker).
*   **Execution Flow (API/Worker):**
    1.  Entrypoint receives execution request (HTTP POST for API, Redis message for Worker) specifying component name and input data (e.g., user message, initial input).
    2.  Entrypoint validates the input.
    3.  Entrypoint retrieves the `ExecutionFacade` via the `HostManager` instance (`manager.execution`).
    4.  Entrypoint calls the appropriate `ExecutionFacade.run_*` method (e.g., `run_agent`, `run_simple_workflow`).
    5.  `ExecutionFacade` handles the execution logic, interacting with `HostManager`, `MCPHost`, and potentially `StorageManager`.
    6.  Entrypoint receives the result from the Facade.
    7.  Entrypoint returns the result (HTTP response for API, logging/optional Redis publish for Worker).
*   **CLI Interaction Flow:**
    1.  User runs a `cli.py` command (e.g., `python -m src.bin.cli execute agent ...`).
    2.  `typer` parses arguments and options (API URL, API Key, command-specific args).
    3.  The corresponding command function uses `httpx` to make an HTTP request to the configured API server endpoint (e.g., `/agents/{agent_name}/execute`).
    4.  The API server handles the request as described in the "Execution Flow (API/Worker)".
    5.  `cli.py` receives the HTTP response, prints it to the console, and handles potential errors (`httpx` exceptions, non-2xx status codes).

**3.2. Individual File Functionality:**

*   **`api.py` (`FastAPI` App):**
    *   **Lifecycle:** Manages `HostManager` init/shutdown via `lifespan`.
    *   **Dependencies:** Provides `HostManager`, `ServerConfig`, and API key validation via dependency injection.
    *   **Middleware:** Includes CORS and request logging middleware.
    *   **Exception Handling:** Defines custom handlers for `KeyError`, `ValueError`, `FileNotFoundError`, `AttributeError`, `ImportError`, `RuntimeError`, and generic `Exception` to return appropriate HTTP status codes and JSON error details.
    *   **Static Files:** Serves static files (HTML, CSS, JS) from the `static/` directory.
    *   **Endpoints:**
        *   `/` (GET): Serves `index.html`.
        *   `/health` (GET): Simple health check.
        *   `/status` (GET, Auth): Returns initialization status.
        *   `/agents/{agent_name}/execute` (POST, Auth): Executes an agent.
        *   `/workflows/{workflow_name}/execute` (POST, Auth): Executes a simple workflow.
        *   `/custom_workflows/{workflow_name}/execute` (POST, Auth): Executes a custom workflow.
        *   `/clients/register` (POST, Auth): Registers a client.
        *   `/agents/register` (POST, Auth): Registers an agent.
        *   `/workflows/register` (POST, Auth): Registers a simple workflow.
*   **`worker.py`:**
    *   **Configuration:** Loads `ServerConfig` via `get_server_config`.
    *   **Initialization:** Initializes `HostManager` in `main()`.
    *   **Redis Connection:** Connects to Redis using `redis.asyncio`.
    *   **Signal Handling:** Sets up `SIGINT`, `SIGTERM` handlers for graceful shutdown using `asyncio.Event`.
    *   **Main Loop (`worker_loop`):** Continuously reads messages from the configured Redis stream (`XREAD` with `BLOCK 0`).
    *   **Message Processing (`process_message`):**
        *   Parses JSON data from the `task_data` field of the Redis message.
        *   Determines `action` (register/execute) and `component_type`.
        *   Calls appropriate `HostManager.register_*` or `HostManager.execution.run_*` methods based on the task.
        *   Handles potential errors during parsing or processing (validation, value errors, file not found, etc.).
    *   **Shutdown:** Closes Redis connection and shuts down `HostManager`.
*   **`cli.py` (`typer` App):**
    *   **Configuration:** Uses `typer.Option` to get API URL and API Key (from args or `API_KEY` env var).
    *   **Async Execution:** Uses `httpx.AsyncClient` to make API calls. Wraps async logic in synchronous `typer` commands using `asyncio.run` and a helper (`run_async_with_cli_error_handling`) for standardized error handling and reporting.
    *   **Commands:** Provides subcommands under `register` and `execute`:
        *   `execute agent <name> <message>`
        *   `execute workflow <name> <message>`
        *   `execute custom-workflow <name> <json_input>`
        *   `register client <json_config>` (Placeholder)
        *   `register agent <json_config>` (Placeholder)
        *   `register workflow <json_config>` (Placeholder)
    *   **Output:** Prints JSON responses from the API to standard output.

## 4. Testing

**4.A. Testing Overview:**

*   **Execution:** Testing for Layer 1 involves a mix of methods:
    *   **API:** Tested via integration tests using `pytest` and FastAPI's `TestClient`. These tests are marked with `api_integration` and run via `pytest -m api_integration`. Manual testing is also possible using the Postman collection (`tests/api/main_server.postman_collection.json`) against a running API server (`python -m src.bin.api`).
    *   **CLI:** Tested manually by running `python -m src.bin.cli` commands against a running API server. Automated tests are planned.
    *   **Worker:** Tested implicitly through API/CLI actions if they trigger background tasks, or potentially via direct Redis message publishing (manual). Automated tests are planned.
*   **Location:**
    *   API `pytest` tests: `tests/api/test_api_integration.py`
    *   Postman collection: `tests/api/main_server.postman_collection.json`
    *   Postman environment: `tests/api/main_server.postman_environment.json`
*   **Approach:** Current automated testing focuses on API integration tests that validate the API endpoints, their interaction with the `HostManager`/`ExecutionFacade`, request/response schemas, and error handling. These tests use `TestClient` which handles the app lifecycle and `monkeypatch` to manage environment variables for configuration. Manual testing covers CLI and basic Worker flows.

**4.B. Testing Infrastructure:**

*   **`pytest`:** The core testing framework.
*   **`fastapi.testclient.TestClient`:** Used in `tests/api/test_api_integration.py` to make requests to the FastAPI application within the test process, handling app startup/shutdown.
*   **`pytest.monkeypatch`:** Used extensively in API tests to set environment variables (`API_KEY`, `HOST_CONFIG_PATH`, `AURITE_ENABLE_DB`, `ANTHROPIC_API_KEY`) for specific test contexts and clear `lru_cache` for configuration loading.
*   **Postman:** Collection and environment files define requests and expected responses for manual API testing or Newman execution.
*   **`httpx`:** Used within `cli.py` to make HTTP requests; could be leveraged in future `pytest` CLI tests.
*   **`redis.asyncio`:** Used by `worker.py`; could be mocked or used with a test Redis instance for future worker integration tests.
*   **`typer.testing.CliRunner`:** Could be used for future CLI integration tests.
*   **Markers:** `api_integration`, `anyio`.

**4.C. Testing Coverage:**

| Functionality                      | Relevant File(s)   | Test Method(s) / Status                                                                 |
| :--------------------------------- | :----------------- | :-------------------------------------------------------------------------------------- |
| API: Health Endpoint               | `api.py`           | `test_api_health_check` / Good (via pytest)                                             |
| API: Status Endpoint (Auth/Unauth) | `api.py`           | `test_api_status_unauthorized`, `test_api_status_authorized` / Good (via pytest)        |
| API: Agent Execution Endpoint      | `api.py`           | `test_execute_agent_success` / Good (via pytest, covers handled internal error)         |
| API: Simple Workflow Execution     | `api.py`           | `test_execute_simple_workflow_success` / Good (via pytest, covers handled internal error)|
| API: Custom Workflow Execution     | `api.py`           | `test_execute_custom_workflow_success` / Good (via pytest, covers handled internal error)|
| API: Client Registration Endpoint  | `api.py`           | `test_register_client_success`, `test_register_client_duplicate` / Good (via pytest)    |
| API: Agent Registration Endpoint   | `api.py`           | `test_register_agent_success`, `test_register_agent_duplicate_name`, `test_register_agent_invalid_client_id` / Good (via pytest) |
| API: Workflow Registration Endpoint| `api.py`           | `test_register_workflow_success`, `test_register_workflow_duplicate_name`, `test_register_workflow_invalid_agent_name` / Good (via pytest) |
| API: Error Handling (4xx, 5xx)     | `api.py`           | Covered implicitly by registration/auth tests / Good (via pytest for tested cases)      |
| API: Static File Serving           | `api.py`           | Manual Browser Access / Manual                                                          |
| Worker: Task Processing (Register) | `worker.py`        | Manual (via API/CLI registration) or Direct Redis Publish / Manual/Missing              |
| Worker: Task Processing (Execute)  | `worker.py`        | Manual (via API/CLI execution) or Direct Redis Publish / Manual/Missing                 |
| Worker: Redis Connection/Error     | `worker.py`        | Manual (Stopping/Starting Redis) / Manual/Missing                                       |
| CLI: Execute Agent Command         | `cli.py`           | Manual CLI Execution / Manual                                                           |
| CLI: Execute Workflow Command      | `cli.py`           | Manual CLI Execution / Manual                                                           |
| CLI: Execute Custom Workflow Cmd   | `cli.py`           | Manual CLI Execution / Manual                                                           |
| CLI: Register Commands             | `cli.py`           | Not Implemented / Missing                                                               |
| CLI: API Connection/Auth Errors    | `cli.py`           | Manual CLI Execution (Bad URL/Key) / Manual                                             |

**4.D. Remaining Testing Steps:**

*   **Worker Integration Tests (`pytest`):**
    1.  Implement integration tests for the worker.
    2.  Requires a strategy for Redis:
        *   Mock `redis.asyncio`.
        *   Use a real Redis instance (e.g., via Docker container managed by `pytest-docker`).
    3.  Publish test messages to the Redis stream.
    4.  Verify that the worker processes messages correctly by checking:
        *   Logs emitted by the worker.
        *   State changes in a mocked or real `HostManager` (e.g., checking `manager.agent_configs` after a register task).
        *   (Optional) Results published back to another Redis key/stream.
    5.  Test error handling for invalid message formats or processing errors.
*   **CLI Integration Tests (`pytest`):**
    1.  Implement integration tests for the CLI commands using Typer's `CliRunner` or `subprocess`.
    2.  Requires a running API server instance during the test (or mocking `httpx`).
    3.  Invoke CLI commands with various arguments (valid and invalid).
    4.  Assert on the standard output/error streams.
    5.  Verify that the expected API calls were made (potentially by mocking `httpx` or checking server logs/state if running a real server).
    6.  Implement the placeholder `register` commands in `cli.py` and add tests for them.
*   **API Static File Serving Test:** Add a simple `pytest` test to verify the `/` endpoint returns the `index.html` content.
