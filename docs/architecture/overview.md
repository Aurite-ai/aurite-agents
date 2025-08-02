# Framework Overview

This document provides a detailed overview of the Aurite Agents framework architecture.

## Architecture

The framework follows a layered architecture:

![Aurite Agents Framework Architecture](../images/architecture_diagram.svg)

*   **Layer 0: Frontends:** This layer provides the user-facing interfaces for interacting with the framework. It currently includes a developer-focused web UI built with React. This UI is served as a static application by the API Entrypoint and communicates with it to manage and execute components.

*   **Layer 1: Entrypoints:** This layer provides the external interfaces for interacting with the Aurite Agents framework. It includes:
    *   A **FastAPI Server** (`src/aurite/bin/api/api.py`): Offers a RESTful API for programmatic interaction.
    *   A **Command-Line Interface (CLI)** (`src/aurite/bin/cli/main.py`): A self-contained tool for scripting and launching other entrypoints.
    *   **Terminal UIs (TUI)**: Rich interactive applications for chat (`src/aurite/bin/tui/chat.py`) and configuration editing (`src/aurite/bin/tui/edit.py`).
    All entrypoints interact with the `Aurite` class in Layer 2.

*   **Layer 2: Orchestration & Configuration:** This layer is the central nervous system, responsible for lifecycle and configuration management.
    *   **`ConfigManager`** (`src/aurite/config/config_manager.py`): Implements a sophisticated, priority-based configuration system. It discovers the project/workspace context and builds a unified index of all available components.
    *   **`Aurite` / `AuriteKernel`** (`src/aurite/host_manager.py`): Manages the lifecycle of all core services, ensuring they are initialized on-demand and shut down gracefully. It provides the main public API for the entrypoint layers.

*   **Layer 2.5: Execution:** This sub-layer is responsible for the actual execution of agentic components.
    *   The **`ExecutionFacade`** (`src/aurite/execution/facade.py`) provides a unified interface (`run_agent`, `stream_agent_run`, etc.) for all execution requests. It handles Just-in-Time (JIT) registration of required MCP servers and manages conversation history.
    *   It instantiates and delegates tasks to specific **Executors**:
        *   **`Agent`** (`src/aurite/components/agents/agent.py`): Manages the multi-turn conversation loop, including tool use and history.
        *   **`LinearWorkflowExecutor`** (`src/aurite/components/workflows/linear_workflow.py`): Executes a defined sequence of agents.
        *   **`CustomWorkflowExecutor`** (`src/aurite/components/workflows/custom_workflow.py`): Dynamically loads and executes user-defined Python classes.

*   **Layer 3: Host Infrastructure:** The `MCPHost` (`src/aurite/host/host.py`) is the core infrastructure layer responsible for direct interaction with external MCP servers.
    *   **Client Management:** It manages connections and sessions with all MCP servers.
    *   **Component Discovery & Registration:** It discovers tools, prompts, and resources offered by connected clients.
    *   **Filtering and Routing:** It applies filtering rules and routes requests to the appropriate client.
    *   **Security and Access Control:** It handles credential encryption and access control.
    *   It provides the direct interface (`call_tool`, `get_formatted_tools`) used by the `Agent` in Layer 2.5.

*   **Layer 4: External Capabilities:** This layer consists of the external MCP Servers themselves. These are separate processes that provide tools, prompts, or resources according to the Model Context Protocol.
