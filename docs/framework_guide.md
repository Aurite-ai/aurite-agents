# Aurite Agents Framework Guide

This guide provides a comprehensive overview of the Aurite Agents framework, explaining its core concepts, configuration, and how to use its different entrypoints.

## 1. Introduction

The Aurite Agents framework is designed to build AI agents capable of complex interactions using the Model Context Protocol (MCP). It allows agents, typically powered by Large Language Models (LLMs), to leverage external tools, prompts, and resources provided by MCP servers.

**Core Components:**

*   **MCP Host (`src/host/host.py`):** The central infrastructure piece that connects to and manages MCP servers (referred to as "clients"). It handles component discovery, registration, routing, and provides a unified interface for agents to interact with MCP capabilities.
*   **Host Manager (`src/host_manager.py`):** Orchestrates the lifecycle of the `MCPHost` and provides methods for executing configured agents, simple workflows (sequences of agents defined in JSON), and custom Python workflows. It also handles dynamic registration of components.
*   **Agent (`src/agents/agent.py`):** A base class for LLM-driven agents. It uses the `HostManager` (via the `MCPHost` instance it holds) to interact with MCP tools based on the LLM's requests during a conversation.
*   **Entrypoints (`src/bin/`):** Scripts providing different ways to run and interact with the framework:
    *   `api.py`: Runs a FastAPI server with HTTP endpoints.
    *   `cli.py`: Provides a command-line interface.
    *   `worker.py`: Listens to a Redis stream for tasks.

```mermaid
graph TD
    subgraph sg_entrypoints [Layer 1: Entrypoints (src/bin)]
        CLI[CLI - cli.py]
        API[API Server - api.py]
        Worker[Worker - worker.py]
    end

    subgraph sg_orchestration [Layer 2: Orchestration]
        HM[Host Manager - host_manager.py\nHandles Config, Init/Shutdown, Execution, Registration]
    end

    subgraph sg_host [Layer 3: Host Infrastructure (MCP Host System)]
        Host[MCP Host - host.py\nManages Clients, Security, Component Execution/Discovery]
    end

    subgraph sg_external [Layer 4: External Capabilities]
        Servers[MCP Servers\nProvide Tools, Prompts, Resources via MCP]
    end

    CLI --> HM
    API --> HM
    Worker --> HM
    HM --> Host
    Host --> Servers

    classDef layer1 fill:#e6f3ff,stroke:#333,stroke-width:2px;
    classDef layer2 fill:#d4f0c4,stroke:#333,stroke-width:2px;
    classDef layer3 fill:#fff2e6,stroke:#333,stroke-width:2px;
    classDef layer4 fill:#f9f9f9,stroke:#333,stroke-width:2px;

    class CLI,API,Worker layer1;
    class HM layer2;
    class Host layer3;
    class Servers layer4;
```

## 2. Configuration

The framework relies on several configuration sources:

### 2.1. Environment Variables (`.env`)

Sensitive keys, paths, and server settings are typically loaded from a `.env` file in the project root. Key variables include:

*   `HOST_CONFIG_PATH`: **Required.** Absolute path to the main JSON host configuration file.
*   `API_KEY`: **Required for API/CLI.** Secret key for authenticating API/CLI requests.
*   `ANTHROPIC_API_KEY`: **Required for Agents.** API key for the Anthropic (Claude) LLM.
*   `LOG_LEVEL`: Logging level (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`). Defaults to `INFO`.
*   `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_STREAM_NAME`: Configuration for the Redis worker. Defaults are provided.
*   `AURITE_MCP_ENCRYPTION_KEY` (Optional): Encryption key for the host's `SecurityManager`.
*   *(Other keys specific to MCP servers, like database credentials)*

These are loaded by `src/config.py` using `pydantic-settings`.

### 2.2. Host Configuration JSON (`HOST_CONFIG_PATH`)

This JSON file (e.g., `config/agents/testing_config.json`) defines the initial setup for the `HostManager`. It contains lists of:

*   **`clients`**: Defines MCP servers the host should connect to on startup. Each client object specifies:
    *   `client_id`: A unique identifier for the server.
    *   `server_path`: Path (relative to project root) to the server's executable script.
    *   `capabilities`: List of capabilities the server provides (e.g., `tools`, `prompts`, `resources`).
    *   `roots` (Optional): List of resource URI roots the client is allowed to access.
    *   `timeout` (Optional): Connection timeout.
    *   `routing_weight` (Optional): Weight for tool routing decisions.
    *   `exclude` (Optional): List of tool/prompt/resource names *not* to register from this client.
    *   `gcp_secrets` (Optional): List of GCP secrets to resolve and inject into the server's environment.
*   **`agents`**: Defines pre-configured agents. Each agent object specifies:
    *   `name`: Unique name for the agent.
    *   `client_ids` (Optional): List of `client_id`s this agent is allowed to use (client-level filtering). If omitted, the agent can use any client.
    *   `exclude_components` (Optional): List of specific tool/prompt/resource names this agent *cannot* use, even if provided by allowed clients (component-level filtering).
    *   `system_prompt` (Optional): The system prompt for the LLM.
    *   `model`, `temperature`, `max_tokens`, `max_iterations`, `include_history` (Optional): LLM parameters.
*   **`workflows`**: Defines simple, sequential workflows. Each workflow object specifies:
    *   `name`: Unique name for the workflow.
    *   `steps`: A list of agent `name`s to execute in order.
    *   `description` (Optional): A description of the workflow.
*   **`custom_workflows`**: Defines custom Python workflows. Each object specifies:
    *   `name`: Unique name for the custom workflow.
    *   `module_path`: Path (relative to project root) to the Python file containing the workflow class.
    *   `class_name`: The name of the class implementing the workflow logic (must have an `async execute_workflow` method).
    *   `description` (Optional): A description.

**Path Resolution:** Paths like `server_path` (for clients) and `module_path` (for custom workflows) specified in the JSON config are resolved relative to the project's root directory (`aurite-agents/`).

## 3. Running the Framework (Entrypoints)

Choose the entrypoint that best suits your needs. Ensure dependencies are installed (`pip install -e .`) and the virtual environment is active.

### 3.1. API Server (`src/bin/api.py`)

This is ideal for web-based interactions or integration with other services.

*   **Setup:** Ensure `.env` file is configured, especially `HOST_CONFIG_PATH` and `API_KEY`.
*   **Run:**
    ```bash
    python -m src.bin.api
    ```
*   **Interaction:** Use an HTTP client (like `curl` or Postman) to send requests to the endpoints (default: `http://localhost:8000`). Requires the `X-API-Key` header for authentication.
    *   `/health`: Basic health check.
    *   `/status`: Check HostManager status.
    *   `/agents/{agent_name}/execute` (POST): Execute an agent. Body: `{"user_message": "..."}`.
    *   `/workflows/{workflow_name}/execute` (POST): Execute a simple workflow. Body: `{"initial_user_message": "..."}`.
    *   `/custom_workflows/{workflow_name}/execute` (POST): Execute a custom workflow. Body: `{"initial_input": ...}`.
    *   `/clients/register` (POST): Dynamically register a client. Body: `ClientConfig` JSON.
    *   `/agents/register` (POST): Dynamically register an agent. Body: `AgentConfig` JSON.
    *   `/workflows/register` (POST): Dynamically register a simple workflow. Body: `WorkflowConfig` JSON.

### 3.2. Command-Line Interface (`src/bin/cli.py`)

Useful for direct interaction, scripting, and testing from the terminal.

*   **Setup:** Requires the path to the host configuration JSON via the `-c` or `--config` option for every command. Ensure relevant environment variables (like `ANTHROPIC_API_KEY`) are set.
*   **Run:**
    ```bash
    # General Help
    python -m src.bin.cli --help

    # Specify config and get help for subcommands
    python -m src.bin.cli -c config/agents/testing_config.json --help
    python -m src.bin.cli -c config/agents/testing_config.json register --help
    python -m src.bin.cli -c config/agents/testing_config.json execute --help

    # Example: Execute Agent
    python -m src.bin.cli -c config/agents/testing_config.json execute agent "Weather Agent" --message "Is it raining in Paris?"

    # Example: Register Agent (JSON as single argument)
    python -m src.bin.cli -c config/agents/testing_config.json register agent \
      '{"name": "CLI Agent", "system_prompt": "Test agent.", "client_ids": ["weather_server"]}'

    # Example: Execute Workflow
    python -m src.bin.cli -c config/agents/testing_config.json execute workflow "Example workflow using weather and planning servers" --message "Start the workflow"
    ```
*   **Note:** When providing JSON configuration strings for registration commands, ensure they are valid JSON and properly quoted for your shell. Paths within the JSON (like `server_path`) should still be relative to the project root.

### 3.3. Redis Worker (`src/bin/worker.py`)

Designed for asynchronous task processing via a Redis message queue.

*   **Setup:**
    *   Install and run a Redis server.
    *   Configure Redis connection details in `.env` (or rely on defaults: `localhost:6379`, db 0).
    *   Ensure `HOST_CONFIG_PATH` and any necessary API keys are set in `.env`.
*   **Run:**
    ```bash
    python -m src.bin.worker
    ```
*   **Interaction:** Publish messages to the configured Redis stream (default: `aurite:tasks`). Each message should have a field named `task_data` containing a JSON string with the following structure:
    *   `action`: `"register"` or `"execute"`.
    *   `component_type`: `"client"`, `"agent"`, `"workflow"`, or `"custom_workflow"`.
    *   `data`:
        *   For `register`: The JSON configuration object (`ClientConfig`, `AgentConfig`, `WorkflowConfig`). Paths should be relative to the project root.
        *   For `execute`: A JSON object containing execution parameters (e.g., `{"name": "AgentName", "user_message": "..."}` or `{"name": "WorkflowName", "initial_input": ...}`).
*   **Example Redis Command (using `redis-cli`):**
    ```bash
    # Register a client
    XADD aurite:tasks * task_data '{"action": "register", "component_type": "client", "data": {"client_id": "redis_client", "server_path": "tests/fixtures/servers/weather_mcp_server.py", "capabilities": ["tools"], "roots": []}}'

    # Execute an agent
    XADD aurite:tasks * task_data '{"action": "execute", "component_type": "agent", "data": {"name": "Weather Agent", "user_message": "Hello from Redis!"}}'
    ```
*   The worker logs processing information to standard output. Results are not currently published back to Redis but could be added.

## 4. Dynamic Registration

All three entrypoints (API, CLI, Worker) support dynamic registration of clients, agents, and simple workflows after the initial startup.

*   **API:** Use the `POST /clients/register`, `POST /agents/register`, `POST /workflows/register` endpoints.
*   **CLI:** Use the `register client`, `register agent`, `register workflow` commands, providing the configuration as a JSON string.
*   **Worker:** Send a message to the Redis stream with `action: "register"` and the appropriate `component_type` and `data` (configuration JSON).

**Important Considerations:**

*   **Duplicate Names/IDs:** Attempting to register a component with a name/ID that already exists will result in an error (e.g., 409 Conflict in API, error message in CLI/Worker).
*   **Dependencies:** When registering agents or workflows, ensure any referenced clients (for agents) or agents (for workflows) already exist (either from initial config or previously registered dynamically). Otherwise, registration will fail.
*   **Path Resolution:** Paths (`server_path`, `module_path`) provided during dynamic registration (via API, CLI, or Worker message) must be specified relative to the project root directory, just like in the initial JSON configuration file. The framework resolves these relative paths.
*   **Persistence:** Dynamically registered components exist only in memory for the current runtime of the application instance (API server, CLI command, Worker process). They are **not** persisted to the original configuration file and will be lost upon restart unless re-registered.

## 5. Development & Testing

*   See `tests/README.md` for instructions on running the `pytest` test suite, which includes unit, integration, and E2E tests.
*   Refer to `docs/testing_strategy.md` for a detailed overview of the testing approach, including the prompt validation system.
*   Use the Postman collection (`tests/api/main_server.postman_collection.json`) with its environment file (`tests/api/main_server.postman_environment.json`) for API testing.
