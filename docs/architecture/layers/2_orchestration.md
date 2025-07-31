# Layer 2: Orchestration & Configuration

**Version:** 2.0
**Date:** 2025-07-09

## 1. Overview

The Orchestration & Configuration Layer serves as the primary entrypoint and lifecycle manager for the Aurite framework. It is responsible for understanding the user's workspace and project structure, loading all relevant configurations, and initializing the core services required for execution.

This layer is defined by two primary classes:

- **`ConfigManager`**: The intelligent configuration loader. It scans the file system from the current directory, identifies the project and workspace context, and builds a prioritized index of all available components (agents, LLMs, servers, etc.).
- **`Aurite` / `AuriteKernel`**: The main entrypoint and lifecycle manager. The public `Aurite` class is a user-friendly wrapper around the internal `AuriteKernel`, which holds the state of all core services (`ConfigManager`, `MCPHost`, `ExecutionFacade`, `StorageManager`). It ensures that services are initialized lazily (on first use) and shut down gracefully.

This layer's core responsibility is to prepare the ground for the Execution Layer (2.5) by providing it with a fully configured environment.

## 2. Relevant Files

| File Path                             | Primary Class(es)        | Core Responsibility                                                                                                    |
| :------------------------------------ | :----------------------- | :--------------------------------------------------------------------------------------------------------------------- |
| `src/aurite/aurite.py`                | `Aurite`, `AuriteKernel` | Manages the lifecycle of core services (`MCPHost`, `ExecutionFacade`, `StorageManager`). Provides the main public API. |
| `src/aurite/config/config_manager.py` | `ConfigManager`          | Discovers and loads all component configurations from the hierarchical context (project, workspace, user).             |
| `src/aurite/config/config_utils.py`   | utils                    | Helper functions for finding anchor files (`.aurite`) to establish context.                                            |
| `src/aurite/config/file_manager.py`   | `FileManager`            | Handles CRUD operations for configuration files, used by `ConfigManager`.                                              |
| `src/aurite/config/config_models.py`  | Pydantic Models          | Defines the data structures for all configuration types.                                                               |

## 3. Functionality

### 3.1. Configuration Loading (`ConfigManager`)

The `ConfigManager` is the first component to be initialized and is the foundation of the framework's context awareness.

- **Context Discovery:**
  1.  It starts from the current working directory and searches upwards for `.aurite` anchor files.
  2.  It identifies the current **Project** and **Workspace** based on these files.
  3.  It establishes a priority order for loading configurations: **Current Project > Workspace > Other Workspace Projects > Global User Config**.
- **Component Indexing:**
  1.  It recursively scans the `config` directories specified in each `.aurite` file.
  2.  It parses all `.json` and `.yaml` files, expecting them to contain lists of component definitions.
  3.  It builds an in-memory index of all components, where components from higher-priority sources (like the current project) override those from lower-priority sources (like the user's global config).
- **Path Resolution:** When a component's configuration is requested (e.g., via `get_config`), the `ConfigManager` resolves any relative paths (like `server_path` in an MCP Server config) relative to the location of the file where the component was defined.

### 3.2. Framework Lifecycle (`AuriteKernel`)

The `AuriteKernel` is the internal engine that owns and manages the state of the running framework.

- **Initialization (`AuriteKernel.initialize`):**
  - This method is called lazily by the public `Aurite` class on the first execution request (e.g., `run_agent`).
  - It initializes the `MCPHost` (Layer 3) by calling its `__aenter__` method, which connects to all statically defined MCP servers.
  - If database persistence is enabled (`AURITE_ENABLE_DB=true`), it initializes the `StorageManager`.
  - It instantiates the `ExecutionFacade` (Layer 2.5), providing it with the `ConfigManager`, the active `MCPHost`, and the optional `StorageManager`.
- **Shutdown (`AuriteKernel.shutdown`):**
  - This method is called when the `Aurite` context manager exits or when the program terminates.
  - It gracefully shuts down the `MCPHost` (closing all MCP server connections) and disposes of the database engine.

### 3.3. Public Interface (`Aurite`)

The `Aurite` class provides a clean, high-level API for users to interact with the framework without needing to manage the internal state.

- **Execution Delegation:** Methods like `run_agent`, `run_linear_workflow`, and `stream_agent` are the primary user-facing functions. They perform a single critical task: they ensure the `AuriteKernel` is initialized and then delegate the actual execution logic to the `ExecutionFacade` (Layer 2.5).
- **Lazy Initialization:** The `_ensure_initialized` method allows users to instantiate the `Aurite` class cheaply without kicking off all the underlying services until they are actually needed.
- **Context Management:** It can be used as an `async` context manager (`async with Aurite() as aurite:`) to guarantee that the `shutdown` sequence is called, which is the recommended pattern for applications.
