# Layer 1: Entrypoints

**Version:** 1.0
**Date:** 2025-05-05

## 1. Overview

Layer 1 provides the external interfaces for interacting with the Aurite Agents framework. It exposes the core functionalities managed by the Orchestration Layer (Layer 2) through various access points, allowing users and external systems to register and execute agentic components (Agents, Simple Workflows, Custom Workflows).

This layer consists of:
*   A **FastAPI Server**: Offers a RESTful API for programmatic interaction, suitable for UIs and other services. The main application logic, lifecycle management, middleware, router inclusions, and global exception handling reside in `src/bin/api/api.py`. Specific endpoint groups for configuration, components, projects, and evaluation are modularized into separate route files within `src/bin/api/routes/`. Shared FastAPI dependencies are managed in `src/bin/dependencies.py`.
*   A **Redis Worker (`worker.py`)**: Listens to a Redis stream for asynchronous task processing (registration/execution).
*   A **Command-Line Interface (`cli.py`)**: Provides convenient terminal-based access to the API for development and scripting.

All entrypoints primarily interact with the `HostManager` (Layer 2) to access configuration, registration methods, and the `ExecutionFacade` for running components.

## 2. Relevant Files

| File Path                                 | Primary Class(es)/Modules                                  | Core Responsibility                                                                                                                               |
| :---------------------------------------- | :--------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/bin/api/api.py`                      | `FastAPI`, `uvicorn`                                       | Main FastAPI application. Manages lifecycle (HostManager init/shutdown), includes routers, global middleware, exception handlers, static file serving. |
| `src/bin/api/routes/config_routes.py`     | `APIRouter`                                                | Provides HTTP endpoints for CRUD operations on component JSON configuration files (agents, clients, LLMs, workflows).                               |
| `src/bin/api/routes/components_routes.py` | `APIRouter`                                                | Provides HTTP endpoints for registering and executing components (agents, simple/custom workflows, LLM configs), and listing registered components. |
| `src/bin/api/routes/project_routes.py`    | `APIRouter`                                                | Provides HTTP endpoints for managing project configurations (loading, creating, listing, viewing active config, editing project files).             |
| `src/bin/api/routes/evaluation_api.py`    | `APIRouter`                                                | Provides HTTP endpoints for evaluation-related workflows (e.g., prompt validation). (Note: Intern to refactor/test this file).                  |
| `src/bin/dependencies.py`                 | `Depends`, `Security`, `ServerConfig`, `HostManager`, etc. | Defines and provides shared FastAPI dependencies (e.g., `get_host_manager`, `get_api_key`, `get_component_manager`, `get_project_manager`).      |
| `src/bin/worker.py`                       | `redis.asyncio`, `asyncio`                                 | Listens to Redis stream, parses tasks, delegates registration/execution to HostManager.                                                             |
| `src/bin/cli.py`                          | `typer`, `httpx`                                           | Provides CLI commands that interact with the running API server via HTTP requests.                                                                  |
| `src/host_manager.py`                     | `HostManager`                                              | (Layer 2) Central class used by API routes (via dependencies) and `worker.py` for orchestration.                                                  |

## 3. Functionality

Describes how the entrypoints provide access to the framework's capabilities.

**3.1. Multi-File Interactions & Core Flows:**

*   **Initialization:**
    *   `src/bin/api/api.py`: Uses a FastAPI `lifespan` context manager to instantiate `HostManager`, call `HostManager.initialize()`, and store the instance in `app.state`. It also handles `HostManager.shutdown()` on exit.
    *   `src/bin/worker.py`: Instantiates `HostManager` and calls `HostManager.initialize()` at the start of its `main()` function. Calls `HostManager.shutdown()` during graceful shutdown.
    *   `src/bin/cli.py`: Does *not* directly initialize `HostManager`. It relies on a running API server instance.
*   **Configuration & Dependencies:**
    *   The main `ServerConfig` (API Key, Redis details, Host Config Path, DB settings, etc.) is loaded via `get_server_config()` from `src/bin/dependencies.py`. This function is used by `api.py` (indirectly via other dependencies) and `worker.py`.
    *   API route files (in `src/bin/api/routes/`) use FastAPI dependency injection (`Depends`, `Security`) provided by `src/bin/dependencies.py` to get instances of `HostManager`, `ComponentManager`, `ProjectManager`, `ServerConfig`, and to validate the API key (`X-API-Key` header or `api_key` query parameter).
*   **Registration Flow (API):**
    1.  API receives registration request (HTTP POST).
        *   For component registration (agents, workflows, clients, LLM configs): Requests are typically routed to `src/bin/api/routes/components_routes.py`.
        *   For direct JSON configuration file creation/update: Requests are routed to `src/bin/api/routes/config_routes.py`.
    2.  Input data is validated (FastAPI handles Pydantic validation automatically).
    3.  The relevant route function calls the corresponding method on `HostManager` (e.g., `register_agent`, `register_client`) or `ComponentManager` (e.g., `create_component_file`, `save_component_config`).
    4.  The manager updates its internal state and optionally syncs with the database (via `StorageManager` if DB is enabled and the operation involves it).
    5.  API returns success/error HTTP response.
*   **Registration Flow (Worker):**
    1.  Worker receives Redis message containing component configuration.
    2.  Worker validates input data (basic checks, JSON parsing).
    3.  Worker calls the corresponding `HostManager.register_*` method.
    4.  `HostManager` updates its internal state and optionally syncs with the database.
    5.  Worker logs success/error.
*   **Execution Flow (API):**
    1.  API receives execution request (HTTP POST to `src/bin/api/routes/components_routes.py` or `src/bin/api/routes/evaluation_api.py`) specifying component name and input data.
    2.  Input is validated.
    3.  The route function retrieves the `ExecutionFacade` via the `HostManager` instance (`manager.execution`) obtained from `src/bin/dependencies.py`.
    4.  The route function calls the appropriate `ExecutionFacade.run_*` method (e.g., `run_agent`, `run_simple_workflow`, `run_custom_workflow`).
    5.  `ExecutionFacade` handles the execution logic.
    6.  API route receives the result from the Facade.
    7.  API returns the result as an HTTP response (including streaming for agent execution if requested).
*   **Execution Flow (Worker):**
    1.  Worker receives Redis message specifying component name and input data.
    2.  Worker validates input.
    3.  Worker retrieves the `ExecutionFacade` via its `HostManager` instance.
    4.  Worker calls the appropriate `ExecutionFacade.run_*` method.
    5.  `ExecutionFacade` handles the execution logic.
    6.  Worker receives the result from the Facade.
    7.  Worker logs the result/optional Redis publish.
*   **Project Management Flow (API):**
    1.  API receives project management request (e.g., load project, create project file, get active config) via HTTP to `src/bin/api/routes/project_routes.py`.
    2.  Input is validated.
    3.  The route function retrieves the `ProjectManager` via the `HostManager` instance (`manager.project_manager`) obtained from `src/bin/dependencies.py`.
    4.  The route function calls the appropriate `ProjectManager` method (e.g., `change_project`, `create_project_file`, `get_active_project_config`).
    5.  API returns success/error HTTP response.
*   **CLI Interaction Flow:**
    1.  User runs a `cli.py` command (e.g., `python -m src.bin.cli execute agent ...`).
    2.  `typer` parses arguments and options.
    3.  The corresponding command function uses `httpx` to make an HTTP request to the configured API server endpoint (e.g., `/agents/{agent_name}/execute` now handled by `components_routes.py`).
    4.  The API server (specifically the relevant route file) handles the request as described in the API flows above.
    5.  `cli.py` receives the HTTP response, prints it, and handles errors. (Note: Planned CLI expansions and automated tests were deferred).

**3.2. Individual File Functionality:**

*   **`src/bin/api/api.py` (`FastAPI` App):**
    *   **Lifecycle:** Manages `HostManager` initialization and shutdown via FastAPI's `lifespan` event handler.
    *   **Router Inclusion:** Includes APIRouters from `src/bin/api/routes/` (e.g., `config_routes`, `components_routes`, `project_routes`, `evaluation_api`).
    *   **Middleware:** Configures and includes CORS and request logging middleware.
    *   **Global Exception Handling:** Defines custom global exception handlers for common errors (e.g., `KeyError`, `ValueError`, `FileNotFoundError`) to return standardized JSON error responses.
    *   **Static Files & Frontend Serving:** Mounts the `/assets` directory for frontend static assets and includes a catch-all route to serve `index.html` from `frontend/dist/` for client-side routing.
    *   **Basic Endpoints:** Defines minimal root-level endpoints like `/health`.
*   **`src/bin/api/routes/config_routes.py`:**
    *   **Purpose:** Provides HTTP endpoints for CRUD (Create, Read, Update, Delete) operations on individual component JSON configuration files.
    *   **Dependencies:** Uses `get_api_key` for authentication and `get_component_manager` (from `dependencies.py`) to interact with the `ComponentManager`.
    *   **Endpoints:**
        *   `GET /configs/{component_type}`: Lists available JSON configuration filenames for a component type.
        *   `GET /configs/{component_type}/id/{component_id_or_name}`: Retrieves a specific parsed component configuration model by its ID or name.
        *   `GET /configs/{component_type}/{filename}`: Retrieves the raw parsed JSON content of a specific configuration file.
        *   `POST /configs/{component_type}/{filename}`: Creates a new component JSON configuration file. Supports single object or list of objects in the request body.
        *   `PUT /configs/{component_type}/{filename}`: Updates (or creates if not existing) a specific component JSON configuration file. Supports single object or list of objects.
        *   `DELETE /configs/{component_type}/{filename}`: Deletes a specific component JSON configuration file.
*   **`src/bin/api/routes/components_routes.py`:**
    *   **Purpose:** Provides HTTP endpoints for registering and executing components (agents, workflows, etc.) and listing currently registered/active components.
    *   **Dependencies:** Uses `get_api_key` for authentication and `get_host_manager` (from `dependencies.py`) to interact with `HostManager` and its `ExecutionFacade`.
    *   **Execution Endpoints:**
        *   `POST /agents/{agent_name}/execute`: Executes a named agent.
        *   `GET /agents/{agent_name}/execute-stream`: Executes a named agent and streams Server-Sent Events (SSE).
        *   `POST /workflows/{workflow_name}/execute`: Executes a named simple workflow.
        *   `POST /custom_workflows/{workflow_name}/execute`: Executes a named custom workflow.
    *   **Registration Endpoints:**
        *   `POST /clients/register`: Registers a new MCP client.
        *   `POST /agents/register`: Registers a new agent.
        *   `POST /workflows/register`: Registers a new simple workflow.
        *   `POST /custom_workflows/register`: Registers a new custom workflow.
        *   `POST /llm-configs/register`: Registers a new LLM configuration.
    *   **Listing Endpoints:**
        *   `GET /components/agents`: Lists names of registered agents from the active project.
        *   `GET /components/workflows`: Lists names of registered simple workflows from the active project.
        *   `GET /components/custom_workflows`: Lists names of registered custom workflows from the active project.
        *   `GET /components/clients`: Lists client IDs of registered clients from the active project.
        *   `GET /components/llm-configs`: Lists LLM IDs of registered LLM configurations from the active project.
*   **`src/bin/api/routes/project_routes.py`:**
    *   **Purpose:** Provides HTTP endpoints for managing project configurations.
    *   **Dependencies:** Uses `get_api_key` for authentication and `get_host_manager` (from `dependencies.py`) to access the `ProjectManager`.
    *   **Endpoints:**
        *   `GET /projects/active/component/{project_component_type}/{component_name}`: Retrieves a specific component's configuration from the active project.
        *   `POST /projects/change`: Changes the active project by loading a new project configuration file.
        *   `POST /projects/create_file`: Creates a new, minimal project JSON file.
        *   `POST /projects/load_components`: Loads components from a specified project file into the active configuration.
        *   `GET /projects/list_files`: Lists all project JSON files in the `config/projects/` directory.
        *   `GET /projects/get_active_project_config`: Retrieves the full configuration of the currently active project.
        *   `GET /projects/file/{filename}`: Retrieves the raw JSON content of a specific project file.
        *   `PUT /projects/file/{filename}`: Updates the content of a specific project file.
*   **`src/bin/api/routes/evaluation_api.py`:**
    *   **Purpose:** Provides HTTP endpoints specifically for evaluation-related workflows, currently focused on prompt validation. (Note: This file is slated for further refactoring and testing by an intern).
    *   **Dependencies:** Uses `get_api_key` and `get_host_manager`.
    *   **Endpoints:**
        *   `POST /evaluation/prompt_validation/file`: Executes the prompt validation workflow using a configuration file.
        *   `POST /evaluation/prompt_validation/simple`: Executes the prompt validation workflow with direct inputs (agent name, user input, testing prompt).
*   **`src/bin/dependencies.py`:**
    *   **Purpose:** Centralizes the definition and provision of shared dependencies for the FastAPI application, promoting cleaner route files and easier dependency management.
    *   **Key Provided Dependencies:**
        *   `get_server_config()`: Loads and caches `ServerConfig`.
        *   `get_api_key()`: Validates API key from header or query parameter.
        *   `get_host_manager()`: Retrieves the `HostManager` instance from `app.state`.
        *   `get_component_manager()`: Retrieves the `ComponentManager` from the `HostManager`.
        *   `get_project_manager()`: Retrieves the `ProjectManager` from the `HostManager`.
    *   **Constants:** Defines `PROJECT_ROOT` for path calculations.
*   **`src/bin/worker.py`:**
    *   **Configuration:** Loads `ServerConfig` via `get_server_config` (from `dependencies.py`).
    *   **Initialization:** Initializes `HostManager` in `main()`.
    *   **Redis Connection:** Connects to Redis using `redis.asyncio`.
    *   **Signal Handling:** Sets up `SIGINT`, `SIGTERM` handlers for graceful shutdown.
    *   **Main Loop (`worker_loop`):** Continuously reads messages from the configured Redis stream.
    *   **Message Processing (`process_message`):** Parses JSON task data, determines action/component type, and calls appropriate `HostManager` methods for registration or execution.
    *   **Shutdown:** Closes Redis connection and shuts down `HostManager`. (Note: Planned automated tests were deferred).
*   **`src/bin/cli.py` (`typer` App):**
    *   **Configuration:** Uses `typer.Option` for API URL and API Key.
    *   **Async Execution:** Uses `httpx.AsyncClient` for API calls, wrapped for synchronous Typer commands.
    *   **Commands:** Provides `register` and `execute` subcommands. (Note: Placeholder `register` commands were implemented, but further CLI expansion and automated tests were deferred).
    *   **Output:** Prints JSON responses from the API.

## 4. Testing

**4.A. Testing Overview:**

*   **Execution:** Testing for Layer 1 involves a mix of methods:
    *   **API:** Comprehensively tested via integration tests using `pytest` and FastAPI's `TestClient`. These tests cover the main `src/bin/api/api.py` application setup (lifecycle, static files) and all route modules in `src/bin/api/routes/`. Tests are generally marked with `api_integration` and run via `pytest -m api_integration`. Manual testing is also possible using the Postman collection (`tests/api/main_server.postman_collection.json`) against a running API server (`python -m src.bin.api`).
    *   **CLI:** Tested manually by running `python -m src.bin.cli` commands against a running API server. Planned expansions and automated tests for the CLI were deferred for this iteration.
    *   **Worker:** Tested manually by triggering tasks via API/CLI and observing logs/behavior, or potentially via direct Redis message publishing. Planned automated tests for the Worker were deferred for this iteration.
*   **Location:**
    *   API `pytest` tests: `tests/api/test_api_integration.py` (for `api.py` specifics) and `tests/api/routes/` (e.g., `test_config_routes.py`, `test_components_api.py`, `test_project_api.py` - note: test filenames might need alignment with source file renames like `test_components_routes.py`).
    *   Postman collection: `tests/api/main_server.postman_collection.json`
    *   Postman environment: `tests/api/main_server.postman_environment.json`
*   **Approach:** Automated testing for the API focuses on integration tests that validate endpoint functionality, request/response schemas, error handling, and interactions with `HostManager`, `ComponentManager`, `ProjectManager`, and `ExecutionFacade` (often via mocked dependencies or controlled test configurations). `TestClient` handles the app lifecycle, and `pytest.monkeypatch` is used for environment variable management. Manual testing covers current CLI and Worker flows.

**4.B. Testing Infrastructure:**

*   **`pytest`:** The core testing framework.
*   **`fastapi.testclient.TestClient`:** Used extensively in `tests/api/` to make requests to the FastAPI application within the test process, handling app startup/shutdown. This is the primary tool for testing all API routes.
*   **`pytest.monkeypatch`:** Used in API tests to set environment variables for specific test contexts and manage cached configurations.
*   **Postman:** Collection and environment files for manual API testing or Newman execution.
*   **`httpx`:** Used within `cli.py` for HTTP requests; could be leveraged in future CLI tests.
*   **`redis.asyncio`:** Used by `worker.py`; would be mocked or used with a test Redis instance for future worker tests.
*   **`typer.testing.CliRunner`:** Could be used for future CLI tests.
*   **Markers:** `api_integration`, `anyio`.

**4.C. Testing Coverage:**

| Functionality                                     | Relevant File(s)                                     | Test Method(s) / Status                                                                    |
| :------------------------------------------------ | :--------------------------------------------------- | :----------------------------------------------------------------------------------------- |
| **API: Main Application (`api.py`)**              |                                                      |                                                                                            |
| API: Health Endpoint                              | `api.py`                                             | `test_api_health_check` / Good (via pytest)                                                |
| API: Status Endpoint (Auth/Unauth)                | `api.py`                                             | `test_api_status_unauthorized`, `test_api_status_authorized` / Good (via pytest)           |
| API: Static File Serving (Frontend Assets & Index)| `api.py`                                             | `test_serve_static_assets`, `test_serve_index_html_catch_all` / Good (via pytest)          |
| API: Global Exception Handlers                    | `api.py`                                             | Implicitly tested by various route tests triggering errors / Good (via pytest)             |
| **API: Config Routes (`config_routes.py`)**       |                                                      |                                                                                            |
| API: List Config Files                            | `routes/config_routes.py`                            | Comprehensive tests for various component types / Good (via pytest)                        |
| API: Get Specific Config (by ID/Name)             | `routes/config_routes.py`                            | Comprehensive tests for various component types, found/not found / Good (via pytest)       |
| API: Get Raw Config File Content                  | `routes/config_routes.py`                            | Tests for found/not found, valid/invalid JSON (latter is 500) / Good (via pytest)          |
| API: Create Config File (Single/List)             | `routes/config_routes.py`                            | Tests for creation, conflict, invalid data / Good (via pytest)                             |
| API: Update Config File (Single/List)             | `routes/config_routes.py`                            | Tests for update, creation if not exists, invalid data / Good (via pytest)                 |
| API: Delete Config File                           | `routes/config_routes.py`                            | Tests for successful deletion, not found / Good (via pytest)                               |
| **API: Components Routes (`components_routes.py`)**|                                                      |                                                                                            |
| API: Agent Execution                              | `routes/components_routes.py`                        | `test_execute_agent_success`, error cases / Good (via pytest)                              |
| API: Agent Execution Stream                       | `routes/components_routes.py`                        | Tests for SSE format, event sequence, errors / Good (via pytest)                           |
| API: Simple Workflow Execution                    | `routes/components_routes.py`                        | `test_execute_simple_workflow_success`, error cases / Good (via pytest)                    |
| API: Custom Workflow Execution                    | `routes/components_routes.py`                        | `test_execute_custom_workflow_success`, error cases / Good (via pytest)                    |
| API: Client Registration                          | `routes/components_routes.py`                        | `test_register_client_success`, duplicate / Good (via pytest)                              |
| API: Agent Registration                           | `routes/components_routes.py`                        | `test_register_agent_success`, duplicate, invalid refs / Good (via pytest)                 |
| API: Simple Workflow Registration                 | `routes/components_routes.py`                        | `test_register_workflow_success`, duplicate, invalid refs / Good (via pytest)              |
| API: Custom Workflow Registration                 | `routes/components_routes.py`                        | Tests for success, duplicate / Good (via pytest)                                           |
| API: LLM Config Registration                      | `routes/components_routes.py`                        | Tests for success, duplicate / Good (via pytest)                                           |
| API: List Registered Components (All types)       | `routes/components_routes.py`                        | Tests for listing agents, workflows, clients, LLMs / Good (via pytest)                     |
| **API: Project Routes (`project_routes.py`)**     |                                                      |                                                                                            |
| API: Get Active Project Component Config          | `routes/project_routes.py`                           | Tests for various component types, found/not found / Good (via pytest)                     |
| API: Change Active Project                        | `routes/project_routes.py`                           | Tests for successful change, file not found, errors / Good (via pytest)                    |
| API: Create Project File                          | `routes/project_routes.py`                           | Tests for creation, conflict, invalid data / Good (via pytest)                             |
| API: Load Components from Project File            | `routes/project_routes.py`                           | Tests for successful load, file not found, errors / Good (via pytest)                      |
| API: List Project Files                           | `routes/project_routes.py`                           | Tests for listing files, empty directory / Good (via pytest)                               |
| API: Get Active Project Config                    | `routes/project_routes.py`                           | Tests for active project, no active project / Good (via pytest)                            |
| API: Get Project File Content                     | `routes/project_routes.py`                           | Tests for found/not found, valid/invalid JSON / Good (via pytest)                          |
| API: Update Project File Content                  | `routes/project_routes.py`                           | Tests for successful update, validation errors, IO errors / Good (via pytest)              |
| **API: Evaluation Routes (`evaluation_api.py`)**  |                                                      |                                                                                            |
| API: Prompt Validation (File/Simple)              | `routes/evaluation_api.py`                           | Manual / Out of scope for current automated testing                                        |
| **Worker (`worker.py`)**                          |                                                      |                                                                                            |
| Worker: Task Processing (Register/Execute)        | `worker.py`                                          | Manual testing / Automated tests skipped                                                   |
| Worker: Redis Connection/Error Handling           | `worker.py`                                          | Manual testing / Automated tests skipped                                                   |
| **CLI (`cli.py`)**                                |                                                      |                                                                                            |
| CLI: Execute Commands (Agent, Workflow)           | `cli.py`                                             | Manual testing / Automated tests skipped                                                   |
| CLI: Register Commands (Client, Agent, Workflow)  | `cli.py`                                             | Manual testing (basic placeholders) / Automated tests skipped                              |
| CLI: API Connection/Auth Errors                   | `cli.py`                                             | Manual testing / Automated tests skipped                                                   |

**4.D. Remaining Testing Steps:**

Automated `pytest` tests for `src/bin/cli.py` and `src/bin/worker.py` were deferred in the current task. Manual testing is performed for these components. The API static file serving test has been implemented and is passing.
