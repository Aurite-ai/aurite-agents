# Agent Framework Update (April 9, 2025): New Entrypoints & Dynamic Registration :rocket:

This update introduces significant enhancements to the Aurite Agents framework, focusing on flexibility, usability, and different operational modes.

**Key Additions:**

*   **Multiple Entrypoints:** The framework now offers API, CLI, and Worker entrypoints in `src/bin/`.
*   **Dynamic Registration:** Clients, Agents, and Simple Workflows can now be registered at runtime via any entrypoint.
*   **Developer QoL:** Added `pyproject.toml` scripts for easier execution and testing, plus a new `usage_guide.md`.

## Core Concepts Recap

*   **MCP Host (`src/host/host.py`):** Manages connections to MCP servers ("clients") and provides access to their tools, prompts, and resources.
*   **Host Manager (`src/host_manager.py`):** Orchestrates the `MCPHost` lifecycle, component execution (agents, workflows), and dynamic registration.
*   **Agent Framework (`src/agents/agent.py`):** Enables LLM-driven agents to interact with the `HostManager` to utilize MCP capabilities.

## Configuration

*   **`.env` File:** Stores environment-specific settings like API keys, `HOST_CONFIG_PATH`, logging level, and Redis connection details.
*   **Host JSON Config (`HOST_CONFIG_PATH`):** Defines the initial set of `clients` (MCP Servers), `agents`, `workflows` (simple JSON-based), and `custom_workflows` (Python-based) for the `HostManager` to load on startup. Paths within this file are relative to the project root.

## Running the Framework (New Entrypoints & Scripts)

Install dependencies and scripts first: `pip install -e .`

1.  **API Server (`src/bin/api.py`):**
    *   Provides HTTP endpoints for execution and dynamic registration.
    *   Run with: `start-api`
    *   Requires `.env` configured (esp. `HOST_CONFIG_PATH`, `API_KEY`).
    *   Interact via HTTP client (Postman, curl) using `X-API-Key` header. See `usage_guide.md` or `tests/api/main_server.postman_collection.json`.

2.  **Command-Line Interface (CLI) (`src/bin/cli.py`):**
    *   Allows terminal-based interaction.
    *   Run with: `run-cli` (requires manual addition of args)
    *   **Requires `-c <config_path>` for every command.**
    *   Example: `run-cli -c config/agents/testing_config.json execute agent "Agent Name" "Message"`
    *   Supports `register` and `execute` subcommands for all component types. Use `run-cli -c <config> --help` for details.
    *   *Note:* Currently exhibits async shutdown errors during tool execution, though registration and basic execution work.

3.  **Redis Worker (`src/bin/worker.py`):**
    *   Listens on a Redis stream for asynchronous tasks.
    *   Run with: `start-worker`
    *   Requires Redis server running and `.env` configured (`HOST_CONFIG_PATH`, Redis vars if not default).
    *   Processes JSON messages from the `REDIS_STREAM_NAME` stream (default: `aurite:tasks`) containing `action`, `component_type`, and `data`. See `usage_guide.md` for message format.

4.  **API Tests (`test-api`):**
    *   Runs the Postman collection via Newman against a running API server.
    *   Run with: `test-api`
    *   Requires `newman` installed globally.

*(See the new `usage_guide.md` for detailed examples of running each entrypoint).*

## Dynamic Registration

*   **What:** Clients, Agents, and Simple Workflows can be added *after* startup.
*   **How:**
    *   **API:** `POST /clients/register`, `/agents/register`, `/workflows/register` with JSON body.
    *   **CLI:** `run-cli -c <config> register <client|agent|workflow> '{...JSON...}'`
    *   **Worker:** Send Redis message with `action: "register"`, `component_type`, and `data: {...JSON...}`.
*   **Paths:** Paths in JSON (`server_path`, `module_path`) must be relative to the project root.
*   **Persistence:** Dynamically registered components are **in-memory only** and lost on restart.

## Building Components (Recap)

*   **MCP Servers:** Implement the MCP protocol in Python (see `src/servers/`). Register in host JSON `clients`.
*   **Agents:** Define in host JSON `agents` section (name, system prompt, LLM params, allowed `client_ids`). Logic is in `src/agents/agent.py`.
*   **Simple Workflows:** Define sequences of agent names in host JSON `workflows` section. I/O is passed between steps.
*   **Custom Workflows:** Define Python class with `async execute_workflow(self, initial_input, host_instance)` method. Register `module_path` and `class_name` in host JSON `custom_workflows`.

## Granular Control (Existing Feature)

*   The `exclude` list within a `ClientConfig` in the host JSON still allows preventing specific tools, prompts, or resources from a given MCP server from being registered by the `MCPHost`.

## Next Steps (From Draft)

*   Add `include`/`exclude` options to `AgentConfig` for finer-grained component control per agent.
*   Package the framework for easier distribution/installation.
*   Implement production security features (e.g., GCP Secrets Manager).
*   Dockerize and test in a production-like environment.
