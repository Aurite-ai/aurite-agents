# AI Agent Framework Overview

## 1. Introduction & Summary

This document provides an overview of the AI Agent Framework developed internally. The framework facilitates the creation, orchestration, and deployment of AI agents that can interact with various tools and data sources to accomplish complex tasks. It is built upon the Model Context Protocol (MCP) standard and provides layers of abstraction for managing external capabilities, agent logic, and different execution entrypoints.

The core goal is to provide a robust, extensible platform for building sophisticated AI-driven applications and workflows, ranging from simple sequential tasks to more dynamic, autonomous agents.

## 2. Core Concepts

*   **Model Context Protocol (MCP):** The foundation of the framework's interaction layer. MCP standardizes communication between AI models (like LLMs) and external systems providing tools (functions the AI can call), prompts (pre-defined instructions), and resources (data sources). We leverage MCP servers to encapsulate external capabilities (e.g., weather lookups, planning tools).
*   **Agents:** The primary actors within the framework. An Agent (`src/agents/agent.py`) typically involves an LLM that uses available MCP tools/prompts/resources to fulfill a user request or achieve a goal. Agents can be configured with specific system prompts, LLM parameters, and access controls (filtering) defining which MCP capabilities they can use.
*   **Workflows (Simple):** Sequences of pre-defined Agents executed one after another, where the output of one agent becomes the input for the next. This allows for building multi-step processes declaratively using JSON configuration.
*   **Custom Workflows:** Python classes that allow for maximum flexibility in orchestrating agents, tools, and custom logic. They receive access to the framework's core components (like the MCP Host) to leverage its capabilities within bespoke execution flows.

## 3. Architecture Layers

The framework follows a layered architecture (visualized at the bottom of this document):

### Layer 4: External Capabilities (MCP Servers)
*   **Description:** Standalone servers implementing the MCP protocol. They expose specific functionalities as tools, prompts, or resources.
*   **Examples:** `src/packaged_servers/weather_mcp_server.py`, `planning_server.py`.
*   **Configuration:** Defined via `ClientConfig` models (`src/host/models.py`), specifying server path, capabilities, security (optional GCP Secrets), and global component exclusions.
*   **Technology:** Python, `mcp.py` library.

### Layer 3: Host Infrastructure (MCP Host System)
*   **Description:** The core orchestration engine (`src/host/host.py`). Manages connections to MCP servers (clients) and coordinates access to their capabilities.
*   **Key Components:**
    *   `MCPHost`: Central class managing client lifecycles and orchestrating internal managers.
    *   Foundation Managers (`src/host/foundation/`): Handle security, root access, and message routing (`MessageRouter`).
    *   Resource Managers (`src/host/resources/`): Manage tools (`ToolManager`), prompts (`PromptManager`), and resources (`ResourceManager`) across connected clients.
    *   `FilteringManager` (`src/host/filtering.py`): Centralizes logic for filtering MCP components based on `ClientConfig` (global exclusions) and `AgentConfig` (client selection and specific component exclusions).
*   **Features:** Component Discovery (finding capabilities across clients), Filtering (controlling agent access).
*   **Technology:** Python, `mcp.py` library, Pydantic.

### Layer 2: Orchestration (Host Manager)
*   **Description:** Manages the `MCPHost` instance and orchestrates the registration and execution of Agents, Simple Workflows, and Custom Workflows (`src/host_manager.py`).
*   **Key Features:**
    *   Loads framework configuration (Host, Clients, Agents, Workflows) from JSON files (e.g., `config/testing_config.json`) using `src/config.py`.
    *   Initializes and shuts down the `MCPHost`.
    *   Provides methods to execute agents (`execute_agent`), simple workflows (`execute_workflow`), and custom workflows (`execute_custom_workflow`) by name.
    *   Supports dynamic registration of components (clients, agents, workflows).
*   **Technology:** Python.

### Layer 1: Entrypoints
*   **Description:** Provides various ways to interact with the framework via the `HostManager`.
*   **Components (`src/bin/`):**
    *   `api.py`: FastAPI server providing HTTP endpoints to register/execute agents and workflows.
    *   `worker.py`: Listens to a Redis stream for tasks (register/execute) to be processed.
    *   `cli.py`: Command-line interface for development/testing (interacts with the API).
*   **Testing:** The testing infrastructure (`tests/`) also acts as an entrypoint, using `pytest` fixtures to initialize a `HostManager` (often with `config/testing_config.json`) for running unit, integration, and end-to-end tests, including a prompt validation system.
*   **Technology:** Python, FastAPI, Redis (`redis-py`), Pytest.

## 4. Packaged MCP Servers

Beyond the core framework, several pre-built MCP servers are available to provide common capabilities:

### Storage Servers
*   **SQL Server:** Interacts with PostgreSQL and MySQL databases.
*   **Mem0 Server:** Manages memory creation, storage, and retrieval for agents.
*   **GCS Server:** Interfaces with Google Cloud Storage for object storage.

### Data Processing Servers
*   **Image Processing Server:** Handles image manipulation and analysis tasks.
*   **Audio Processing Server:** Provides tools for audio transcription, analysis, or synthesis.

### Utility Servers
*   **Planning Server:** Allows agents to create, save, and retrieve structured plans.
*   **Search Server:** Offers web search capabilities via Brave Search and potentially browser automation via Puppeteer.
*   **(Weather Server):** (Included in examples) Provides weather lookup and time zone information.

These servers can be configured and connected to the `MCPHost` via the standard `ClientConfig` mechanism.

## 5. Technology Stack

The Framework is built entirely on MCP, making the stack relatively simple:
*   **Core Language:** Python 3.x
*   **MCP Implementation:** `mcp.py` (Anthropic's Python library)
*   **Web API:** FastAPI
*   **Configuration/Validation:** Pydantic
*   **LLM Interaction:** `anthropic` Python SDK (currently configured for Claude models)
*   **Asynchronous Operations:** `asyncio`, `anyio`
*   **Testing:** Pytest, pytest-asyncio
*   **Worker Queue (Optional):** Redis
*   **Secrets Management (Optional):** Google Cloud Secret Manager integration

## 6. Work Completed So Far (v1)

*   **Core MCP Host System:** Implementation of the layered host system (`MCPHost` and associated managers) for managing MCP client connections and capabilities.
*   **Agent Implementation:** Core `Agent` class capable of interacting with LLMs and using tools provided by the `MCPHost`.
*   **Workflow Implementation:** Support for both declarative "Simple Workflows" (sequences of agents defined in JSON) and flexible "Custom Workflows" (Python classes).
*   **Configuration Loading:** Robust JSON-based configuration loading (`src/config.py`) for defining the entire framework setup (clients, agents, workflows).
*   **Entrypoints:** Functional API (FastAPI), Redis Worker, and CLI entrypoints.
*   **Component Filtering:** Implemented multi-level filtering:
    *   Global client component exclusion (`ClientConfig.exclude`).
    *   Agent-specific client selection (`AgentConfig.client_ids`).
    *   Agent-specific component exclusion (`AgentConfig.exclude_components`) - *Recently completed*.
*   **Testing Infrastructure:** Comprehensive test suite using `pytest`, including fixtures, mocks, E2E tests, and a prompt validation system.
*   **Security:** Basic API key authentication and optional GCP Secret Manager integration for client environment variables.

## 7. Potential Next Steps

Based on the current state and potential future needs:

*   **Develop More Examples:** Create more concrete examples of agents and workflows for specific use cases.
*   **Monitoring & Observability:** Add structured logging, tracing, and metrics collection for better monitoring of agent and host performance.
*   **UI/Frontend:** Develop a user interface for interacting with the API, managing configurations, and visualizing agent execution.
*   **Expand Tooling:** Create more MCP servers for common enterprise tools and data sources.

This framework provides a solid foundation for building and deploying powerful AI agents within the organization.

# Framework Diagram
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
| | - Init/Shutdown MCP Host                                    | |
| | - Register/Execute Agents, Simple/Custom Workflows          | |
| | - Dynamic Registration                                      | |
| +-------------------------------------------------------------+ |
|                       |                                         |
|                       v                                         |
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
| | MCP Servers (e.g., src/servers/, external)                  | |
| |-------------------------------------------------------------| |
| | Purpose:                                                    | |
| | - Implement MCP Protocol                                    | |
| | - Provide Tools, Prompts, Resources                         | |
| | - Handle Discovery (ListTools, etc.)                        | |
| +-------------------------------------------------------------+ |
+-----------------------------------------------------------------+
```
