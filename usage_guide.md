# Aurite Agents Usage Guide

This guide helps developers get started with using the Aurite Agents framework, including running the different entrypoints and understanding how to define agents and workflows.

**Prerequisites:**
*   Python >= 3.12
*   `pip`
*   Git
*   Redis Server (for the worker entrypoint)
*   `newman` (if running Postman tests via `test-api` script)

## 1. Installation & Setup

1.  **Clone:** `git clone <repository-url> && cd aurite-agents`
2.  **Virtual Env (Recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate # Linux/macOS
    # .venv\Scripts\activate # Windows
    ```
3.  **Install Dependencies & Scripts:**
    ```bash
    pip install -e .
    ```
    This installs the framework in editable mode and makes the scripts defined in `pyproject.toml` available (e.g., `start-api`, `run-cli`).
4.  **Environment Variables (`.env`):**
    Create a `.env` file in the project root. Essential variables:
    *   `HOST_CONFIG_PATH`: **Required.** Absolute path to your main host JSON config (e.g., `/home/user/aurite-agents/config/agents/testing_config.json`).
    *   `API_KEY`: **Required for API/CLI.** A secret key for authentication. Generate one securely.
    *   `ANTHROPIC_API_KEY`: **Required for Agents.** Your Anthropic API key.
    *   `REDIS_HOST`, `REDIS_PORT`, etc. (Optional): Override defaults for the worker if needed.
    *   `LOG_LEVEL` (Optional): Set to `DEBUG` for more verbose logs.

## 2. Understanding Configuration (`HOST_CONFIG_PATH` JSON)

The JSON file specified by `HOST_CONFIG_PATH` is central to the framework's initial setup. See `docs/framework_guide.md` (Section 2.2) or `README.md` for a detailed breakdown of the `clients`, `agents`, `workflows`, and `custom_workflows` sections.

**Key Points:**
*   **Paths:** `server_path` (for clients) and `module_path` (for custom workflows) are relative to the project root.
*   **Dependencies:** Workflows depend on agents being defined; agents depend on clients being defined (if `client_ids` is specified).

## 3. Running the Entrypoints (Using Scripts)

After installation (`pip install -e .`), you can use the following scripts:

### 3.1. API Server

*   **Purpose:** Runs the FastAPI web server.
*   **Script:** `start-api`
*   **Usage:**
    ```bash
    start-api
    ```
    (Ensure `.env` is configured correctly). The API will be available at `http://localhost:8000` by default. Use Postman or `curl` with the `X-API-Key` header to interact.

### 3.2. Worker

*   **Purpose:** Listens to Redis for asynchronous tasks.
*   **Prerequisites:** Redis server running.
*   **Script:** `start-worker`
*   **Usage:**
    ```bash
    start-worker
    ```
    (Ensure `.env` is configured). It connects to Redis and listens on the `REDIS_STREAM_NAME` stream.

### 3.3. Command-Line Interface (CLI)

*   **Purpose:** Direct interaction via terminal commands.
*   **Script:** `run-cli` (Note: This makes the base command available; you add arguments manually).
*   **Usage:** Requires specifying the config file (`-c`) for *every* command.
    ```bash
    # Get Help
    run-cli --help
    run-cli -c path/to/config.json --help
    run-cli -c path/to/config.json register --help
    run-cli -c path/to/config.json execute --help

    # Execute Agent
    run-cli -c config/agents/testing_config.json execute agent "Agent Name" "Your message here"

    # Register Client (JSON string as argument)
    run-cli -c config/agents/testing_config.json register client \
      '{"client_id": "my-cli-client", "server_path": "path/to/server.py", "capabilities": ["tools"], "roots": []}'

    # Register Agent
    run-cli -c config/agents/testing_config.json register agent \
      '{"name": "My CLI Agent", "system_prompt": "...", "client_ids": ["my-cli-client"]}'

    # Register Workflow
    run-cli -c config/agents/testing_config.json register workflow \
      '{"name": "My CLI Workflow", "steps": ["My CLI Agent"]}'
    ```

### 3.4. API Tests (Newman)

*   **Purpose:** Runs the Postman collection tests against a running API server.
*   **Prerequisites:** `newman` installed (`npm install -g newman`), API server running.
*   **Script:** `test-api`
*   **Usage:**
    ```bash
    test-api
    ```
    (Ensure `tests/api/main_server.postman_environment.json` has the correct `base_url` and `api_key`).

## 4. Defining Components

### 4.1. MCP Servers (Clients)

*   These are separate Python processes implementing the MCP protocol.
*   See `src/servers/` for examples (e.g., `weather_mcp_server.py`, `planning_server.py`).
*   Define the tools, prompts, or resources the server provides.
*   Register the server in the `clients` section of your host JSON config, specifying its `client_id` and the relative `server_path` to its script.

### 4.2. Agents

*   Defined in the `agents` section of the host JSON config.
*   Specify `name`, LLM parameters (`model`, `temperature`, etc.), `system_prompt`, and optionally `client_ids` to restrict which MCP servers the agent can use.
*   The agent logic (`src/agents/agent.py`) handles the LLM interaction loop and calling tools via the host based on the LLM's requests.

### 4.3. Simple Workflows (JSON)

*   Defined in the `workflows` section of the host JSON config.
*   Specify `name` and a `steps` list containing the `name`s of agents (defined in the same config) to run sequentially.
*   The output of one agent step (the first text block) becomes the input message for the next.

### 4.4. Custom Workflows (Python)

*   Defined in the `custom_workflows` section of the host JSON config.
*   Specify `name`, the relative `module_path` to the Python file, and the `class_name` within that file.
*   The Python class must implement an `async def execute_workflow(self, initial_input: Any, host_instance: MCPHost) -> Any:` method.
*   This method receives the `initial_input` (from the API/CLI/Worker request) and the initialized `MCPHost` instance, allowing full programmatic control over using host capabilities (tools, prompts, resources) and orchestrating complex logic.
*   See `tests/fixtures/custom_workflows/example_workflow.py` for an example.

## 5. Dynamic Registration

*   Components (clients, agents, simple workflows) can be added *after* an entrypoint (API, CLI, Worker) has started.
*   Use the respective registration commands/endpoints.
*   Provide the full configuration object (e.g., `ClientConfig`, `AgentConfig`) as JSON.
*   **Paths** in dynamically registered configs must still be relative to the project root.
*   **Persistence:** Dynamically registered components are **not** saved to the config file and are lost on restart.

This guide provides a starting point. Refer to the source code, other documentation files (`README.md`, `docs/`), and specific examples for more details.
