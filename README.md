# Aurite Agents Framework

**Aurite Agents** is a Python framework for building AI agents that leverage the Model Context Protocol (MCP) for interacting with tools, prompts, and resources provided by external MCP servers.

It provides three core components:

1.  **MCP Host (`src/host/host.py`)**: The core infrastructure layer. Manages connections to MCP servers (clients), handles component registration (tools, prompts, resources), enforces security/access boundaries, and provides a unified interface for interaction via specialized managers.
2.  **Host Manager (`src/host_manager.py`)**: The orchestration layer. Manages the lifecycle of the `MCPHost`, loads configurations from JSON, and handles the registration and execution of Agents, Simple Workflows, and Custom Workflows.
3.  **Agent Framework (`src/agents/agent.py`)**: Provides the `Agent` class for implementing LLM interaction logic. Agents use an injected `MCPHost` instance (managed by the `HostManager`) to access tools and accomplish tasks.

## Key Concepts

*   **MCP (Model Context Protocol):** A standardized way for AI models/agents to interact with external tools, prompts, and resources. See `docs/official-mcp/` for protocol details.
*   **MCP Host:** The infrastructure layer connecting to and managing MCP servers.
*   **Host Manager:** The orchestration layer managing the Host, Agents, and Workflows.
*   **MCP Server/Client:** An external process implementing the MCP protocol to provide specific capabilities (e.g., a weather tool server, a planning tool server). The Host connects to these servers, referring to them as clients.
*   **Agent:** An AI entity (powered by an LLM) configured via `AgentConfig` that uses the `MCPHost` to access tools and information. Can optionally persist conversation history using the Storage Manager (requires `session_id` during execution).
*   **Simple Workflow:** A sequence of Agents defined in `WorkflowConfig`, executed sequentially via the `ExecutionFacade`. (Note: Session history is not automatically propagated to agents within a simple workflow currently).
*   **Custom Workflow:** A Python class defined in `CustomWorkflowConfig`, allowing flexible orchestration logic. Its `execute_workflow` method receives an `ExecutionFacade` instance and an optional `session_id`. If calling agents that use history, the `session_id` must be passed along.
*   **Storage Manager (`src/storage/db_manager.py`):** Handles database interactions, including persisting agent configurations and conversation history (keyed by `agent_name` and `session_id`) if enabled.

## Architecture

The framework follows a layered architecture:

```text
+-----------------------------------------------------------------+
| Layer 1: Entrypoints (src/bin)                                  |
| +--------------+   +----------------+   +---------------------+ |
| | CLI          |   | API Server     |   | Worker              | |
| | (cli.py)     |   | (api.py)       |   | (worker.py)         | |
| +--------------+   +----------------+   +---------------------+ |
|        |                 |                  |                   |
|        +-------+---------+--------+---------+                   |
|                v                  v                             |
+----------------|------------------|-----------------------------+
                 |                  |
                 v                  v
+----------------+------------------+-----------------------------+
| Layer 2: Orchestration                                          |
| +-------------------------------------------------------------+ |
| | Host Manager (host_manager.py)                              | |
| |-------------------------------------------------------------| |
| | Purpose:                                                    | |
| | - Load Host JSON Config                                     | |
| | - Init/Shutdown MCP Host & Storage Manager (optional)       | |
| | - Holds Agent/Workflow Configs                              | |
| | - Dynamic Registration & DB Sync (optional)                 | |
| | - Owns ExecutionFacade                                      | |
| +-------------------------------------------------------------+ |
|                       |                                         |
|                       v                                         |
+-----------------------+-----------------------------------------+
                        |
                        v
+-----------------------+-----------------------------------------+
| Layer 2.5: Execution Facade & Executors                       |
| +-------------------------------------------------------------+ |
| | ExecutionFacade (execution/facade.py)                       | |
| |-------------------------------------------------------------| |
| | Purpose: Unified interface (run_agent, run_simple_workflow, | |
| |          run_custom_workflow) for execution.                | |
| | Delegates to specific Executors.                            | |
| | Passes Storage Manager to Agent execution if available.     | |
| +-------------------------------------------------------------+ |
| | Agent (agents/agent.py) - Executes itself                   | |
| | SimpleWorkflowExecutor (workflows/simple_workflow.py)       | |
| | CustomWorkflowExecutor (workflows/custom_workflow.py)       | |
| +-------------------------------------------------------------+ |
|                       |                                         |
|                       v (Uses MCP Host & Storage Manager)       |
+-----------------------+-----------------------------------------+
                        |
                        v
+-----------------------+-----------------------------------------+
| Layer 3: Host Infrastructure (MCP Host System)                  |
| +-------------------------------------------------------------+ |
| | MCP Host (host.py)                                          | |
| |-------------------------------------------------------------| |
| | Purpose:                                                    | |
| | - Manage Client Connections                                 | |
| | - Handle Roots/Security                                     | |
| | - Register/Execute Tools, Prompts, Resources                | |
| | - Component Discovery/Filtering                             | |
| +-------------------------------------------------------------+ |
|                       |                                         |
|                       v                                         |
+-----------------------+-----------------------------------------+
                        |
                        v
+-----------------------+-----------------------------------------+
| Layer 4: External Capabilities                                  |
| +-------------------------------------------------------------+ |
| | MCP Servers (e.g., src/packaged_servers/, external)         | |
| |-------------------------------------------------------------| |
| | Purpose:                                                    | |
| | - Implement MCP Protocol                                    | |
| | - Provide Tools, Prompts, Resources                         | |
| | - Handle Discovery (ListTools, etc.)                        | |
| +-------------------------------------------------------------+ |
+-----------------------------------------------------------------+
```

*   **Layer 4: External Capabilities:** MCP Servers providing tools/prompts/resources.
*   **Layer 3: Host Infrastructure:** The `MCPHost` manages connections and low-level MCP interactions.
*   **Layer 2.5: Execution Facade & Executors:** The `ExecutionFacade` provides a unified interface for running components, delegating to specific executors (`Agent`, `SimpleWorkflowExecutor`, `CustomWorkflowExecutor`). It also passes the `StorageManager` instance (if available) to the `Agent` during execution.
*   **Layer 2: Orchestration:** The `HostManager` loads configuration, manages the `MCPHost` and optional `StorageManager` lifecycle, handles dynamic registration (syncing to DB if enabled), and owns the `ExecutionFacade`.
*   **Layer 1: Entrypoints:** API, CLI, and Worker interfaces interact with the `HostManager` (and through it, the `ExecutionFacade`).

For more details, see `docs/architecture_overview.md` and `docs/framework_overview.md`.

## Configuration

The framework uses Pydantic models for configuration (`src/host/models.py`):

*   **`HostConfig`**: Defines the host name and a list of `ClientConfig` objects.
*   **`ClientConfig`**: Defines settings for connecting to a specific MCP server, including its path, capabilities, roots, optional GCP secrets, and global component exclusions (`exclude`).
*   **`AgentConfig`**: Defines settings for an `Agent` instance, including LLM parameters (model, temperature, etc.), filtering rules (`client_ids`, `exclude_components`), and an optional `include_history` flag (boolean) to enable conversation history persistence via the database.
*   **`WorkflowConfig`**: Defines a simple workflow as a named sequence of agent names (`steps`).
*   **`CustomWorkflowConfig`**: Defines a custom workflow by pointing to its Python module path and class name.

Configuration for the entire system (Host, Clients, Agents, Workflows) is loaded from a single JSON file specified by the `HOST_CONFIG_PATH` environment variable. The `HostManager` uses `src/config.py` to parse this file during initialization. See `config/testing_config.json` for an example structure.

Database persistence for agent configurations and conversation history can be enabled by setting the `AURITE_ENABLE_DB=true` environment variable and configuring the database connection via other `AURITE_DB_*` variables (see `src/storage/db_connection.py`).

## Installation

1.  **Prerequisites:** Python >= 3.12, `pip`, `redis-server` (for worker).
2.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd aurite-agents
    ```
3.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate # On Windows use `.venv\Scripts\activate`
    ```
4.  **Install dependencies:**
    ```bash
    pip install -e .
    ```
    This installs the package in editable mode along with all dependencies listed in `pyproject.toml`.

## Usage

The framework now provides multiple entrypoints located in `src/bin/`:

### 1. API Server (`src/bin/api.py`)

Runs a FastAPI application providing HTTP endpoints for executing and dynamically registering components.

1.  **Set Environment Variables:** Create a `.env` file in the project root and define required variables, especially:
    *   `API_KEY`: An API key for securing the FastAPI endpoints.
    *   `HOST_CONFIG_PATH`: Path to the desired host configuration JSON file (e.g., `config/agents/testing_config.json`).
    *   `ANTHROPIC_API_KEY`: Required by the `Agent` class for LLM calls.
    *   `AURITE_MCP_ENCRYPTION_KEY` (Optional): For the `SecurityManager`. If not set, a temporary one will be generated.
    *   `AURITE_ENABLE_DB` (Optional): Set to `true` to enable database persistence. Defaults to `false`.
    *   `AURITE_DB_URL` (Required if DB enabled): Full database connection URL (e.g., `postgresql+psycopg2://user:pass@host:port/dbname`).
    *   Other `AURITE_DB_*` variables (Optional): For specific database connection parameters if not using `AURITE_DB_URL`.
2.  **Run the server:**
    ```bash
    python -m src.bin.api
    ```
    The server will start (default: `http://0.0.0.0:8000`). You can interact with it using tools like Postman (see `tests/api/main_server.postman_collection.json`) or `curl`.

### 2. Command-Line Interface (`src/bin/cli.py`)

Provides commands to interact with the framework from the terminal.

1.  **Set Environment Variables:** Ensure `ANTHROPIC_API_KEY` is set if executing agents/workflows that use it.
2.  **Run commands:** Requires specifying the host configuration file (`-c` or `--config`).
    ```bash
    # Example: Execute an agent
    python -m src.bin.cli -c config/agents/testing_config.json execute agent "Weather Agent" --message "Weather in London?"

    # Example: Register a client (pass config as JSON string)
    python -m src.bin.cli -c config/agents/testing_config.json register client \
      '{"client_id": "cli_client", "server_path": "tests/fixtures/servers/weather_mcp_server.py", "capabilities": ["tools"], "roots": []}'

    # Example: List commands
    python -m src.bin.cli --help
    python -m src.bin.cli register --help
    python -m src.bin.cli execute --help
    ```

### 3. Redis Worker (`src/bin/worker.py`)

Listens to a Redis stream for tasks (registration or execution requests).

1.  **Prerequisites:** Ensure Redis server is running and accessible.
2.  **Set Environment Variables:**
    *   `HOST_CONFIG_PATH`: Path to the host configuration JSON file.
    *   `ANTHROPIC_API_KEY` (if needed by components).
    *   `AURITE_ENABLE_DB` and `AURITE_DB_*` variables (if database persistence is desired).
    *   `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_STREAM_NAME` (defaults are provided in `src/config.py` but can be overridden via `.env`).
3.  **Run the worker:**
    ```bash
    python -m src.bin.worker
    ```
    The worker will connect to Redis and wait for messages on the configured stream (default: `aurite:tasks`). Messages should be JSON strings in a field named `task_data`, specifying `action`, `component_type`, and `data`.

## Testing

The project uses `pytest` for testing, with tests categorized into unit, integration, and end-to-end (E2E). A prompt validation system is also included for testing agent outputs against rubrics.

See `docs/testing_strategy.md` and `tests/README.md` for detailed instructions on running tests and understanding the testing structure.

## Directory Structure

*   **`src/`**: Contains the core source code.
    *   `src/host/`: Implementation of the MCP Host system (`host.py`) and its managers.
    *   `src/agents/`: Implementation of the Agent framework (`agent.py`).
    *   `src/host_manager.py`: Orchestration layer managing Host, Agents, and Workflows.
    *   `src/storage/`: Database connection, models, and management (`db_connection.py`, `db_models.py`, `db_manager.py`).
    *   `src/packaged_servers/`: Example and pre-built MCP server implementations.
    *   `src/config.py`: Configuration loading utilities.
    *   `src/bin/`: Entrypoint scripts (API, CLI, Worker).
*   **`tests/`**: Contains all automated tests (unit, integration, e2e).
    *   `tests/fixtures/`: Reusable pytest fixtures and mock servers.
    *   `tests/mocks/`: Mock objects for external services (e.g., Anthropic API).
*   **`config/`**: Contains JSON configuration files defining hosts, clients, agents, and workflows.
*   **`docs/`**: Project documentation, including architecture, guides, and plans.

## Contributing

Contributions are welcome. Please follow standard fork/pull request workflows. Ensure tests pass and documentation is updated for any changes.
