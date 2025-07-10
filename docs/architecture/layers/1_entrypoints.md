# Layer 1: Entrypoints

**Version:** 2.0
**Date:** 2025-07-09

## 1. Overview

Layer 1 provides the external interfaces for interacting with the Aurite Agents framework. It exposes the core functionalities managed by the Orchestration Layer (Layer 2) through various access points, allowing users to configure, manage, and execute agentic components.

This layer consists of three primary types of entrypoints:
*   A **FastAPI Server**: Offers a comprehensive RESTful API for programmatic interaction, serving as the backend for UIs and other services.
*   **Terminal UIs (TUI)**: Rich, interactive terminal applications built with `textual` for an enhanced user experience directly in the console.
    *   **Chat TUI**: For real-time, streaming conversations with agents.
    *   **Edit TUI**: For interactively creating and modifying component configurations.
*   A **Command-Line Interface (CLI)**: A standard command-line tool built with `typer` for scripting, automation, and quick interactions.

All entrypoints primarily interact with the `Aurite` class (Layer 2) to access configuration, registration, and execution capabilities.

## 2. Relevant Files

| File Path                               | Primary Class(es)/Modules | Core Responsibility                                                                 |
| :-------------------------------------- | :------------------------ | :---------------------------------------------------------------------------------- |
| `src/aurite/bin/api/api.py`             | `FastAPI`                 | Main FastAPI application. Manages lifecycle, includes routers, and serves the API.  |
| `src/aurite/bin/api/routes/*`           | `APIRouter`               | Modularized routers for different API functionalities (config, execution, etc.).    |
| `src/aurite/bin/cli/main.py`            | `typer.Typer`             | The main CLI application, providing commands to run agents, list configs, and launch other entrypoints. |
| `src/aurite/bin/tui/chat.py`            | `TextualChatApp`          | A Textual-based TUI for interactive, streaming conversations with an agent.         |
| `src/aurite/bin/tui/edit.py`            | `AuriteEditTUI`           | A Textual-based TUI for browsing and editing all component configurations.          |
| `src/aurite/host_manager.py`            | `Aurite`                  | (Layer 2) The central class used by all entrypoints for orchestration.              |

## 3. Functionality

### 3.1. API Server (`api.py`)

The FastAPI server is the most comprehensive entrypoint, providing a full suite of programmatic controls.

*   **Lifecycle Management:** It uses FastAPI's `lifespan` context manager to instantiate and manage the `Aurite` instance, ensuring all services are started and stopped gracefully with the server.
*   **Modular Routers:** The API is organized into logical groups using `APIRouter`. Each router in `src/aurite/bin/api/routes/` handles a specific domain (e.g., `facade_routes.py` for execution, `config_manager_routes.py` for configuration).
*   **Dependency Injection:** It heavily uses FastAPI's dependency injection system (`Depends`) via `src/aurite/bin/dependencies.py` to provide authenticated access to the shared `Aurite` instance and its underlying managers.
*   **Primary Use Case:** Serves as the backend for the web frontend (Layer 0) and enables any third-party service to integrate with the framework.

### 3.2. Command-Line Interface (`cli/main.py`)

The CLI provides a powerful and scriptable way to interact with the framework directly from the terminal.

*   **Direct Instantiation:** Unlike older versions that were HTTP clients, the new CLI directly instantiates the `Aurite` class. This makes it a self-contained entrypoint that does not require the API server to be running.
*   **Core Commands:**
    *   `aurite run <agent_name>`: Executes an agent and streams its response to the console.
    *   `aurite list <component_type>`: Lists all available components of a given type (e.g., `agents`, `llms`).
    *   `aurite show <component_name>`: Displays the configuration for a specific component.
    *   `aurite init`: Interactively initializes a new project or workspace.
*   **Launching Other Entrypoints:** The CLI also acts as a launcher for the other entrypoints:
    *   `aurite api`: Starts the FastAPI server.
    *   `aurite edit`: Launches the configuration editor TUI.

### 3.3. Terminal UIs (TUI)

The TUIs offer a rich, app-like experience within the terminal.

*   **Chat TUI (`tui/chat.py`):**
    *   Launched via `aurite run <agent_name>` (or can be run directly).
    *   Provides a real-time, interactive chat window.
    *   It instantiates the `Aurite` class and uses the `stream_agent` method to receive and display events (like text deltas and tool calls) as they happen, providing a responsive user experience.

*   **Edit TUI (`tui/edit.py`):**
    *   Launched via `aurite edit`.
    *   Provides a two-pane interface for browsing component types and names in a tree/table view on the left, and editing the selected component's configuration in a form on the right.
    *   It uses the `ConfigManager` (via the `Aurite` instance) to read all component configurations and the `upsert_component` method to save changes back to the original source files.
