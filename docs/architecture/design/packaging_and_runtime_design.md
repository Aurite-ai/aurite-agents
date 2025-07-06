# Design Document: Packaging and Runtime Behavior

**Version:** 1.3
**Date:** 2025-07-03
**Author(s):** Gemini, Ryan
**Status:** Final Draft

## 1. Overview

This document outlines the definitive design for the `aurite` package's user experience. It defines a dynamic, multi-level context system based on a single, unified anchor file (`.aurite`). This approach, inspired by version control systems like Git, provides a flexible and extensible hierarchy for managing projects and shared configurations. The design covers the anchor file's structure, runtime path resolution, hierarchical configuration loading, and the command-line interface (CLI).

## 2. Guiding Principles

*   **Dynamic Hierarchy:** Support for an arbitrary number of configuration levels (Project, Workspace, Super-Workspace, etc.) to provide maximum flexibility.
*   **Clarity and Convention:** The use of a single `.aurite` anchor file is simple, clear, and follows established conventions.
*   **Predictable Resolution:** Configuration and component loading must follow a strict, clearly defined order of precedence to ensure behavior is always predictable.
*   **User-Friendly CLI:** The command-line interface must be explicit and guide the user through the setup process.

## 3. The Unified Anchor Model

### 3.1. The `.aurite` Anchor File

The `.aurite` file is the single source of truth for defining the framework's context. It is a TOML file that lives at the root of any directory acting as a Project or Workspace.

*   **Discovery:** The framework discovers the context hierarchy by searching upwards from the current working directory for all instances of the `.aurite` file.
*   **Hierarchy:**
    *   The **first** `.aurite` file found defines the **Project Root**.
    *   The **second** file found defines the **Workspace Root**.
    *   The **third** file found defines a **Super-Workspace Root**, and so on.

### 3.2. Structure of the `.aurite` File

The file consists of two main tables: `[aurite]` for core settings and `[env]` for environment variables.

```toml
# --- Example .aurite File ---

# [aurite] is the main table for all Aurite-specific settings.
[aurite]
# Defines the role of this anchor. Can be "project" or "workspace". Required.
type = "workspace"

# For workspaces, lists relative paths to the projects it manages.
# The order of this list is CRITICAL for configuration loading priority.
projects = ["./project-alpha", "./project-bravo"]

# A list of additional directories to search for component JSON configurations.
# Paths are relative to this .aurite file's location.
include_configs = ["./shared_configs"]

# A list of directories where custom Python modules can be found.
custom_workflow_paths = ["./shared_workflows"]
mcp_server_paths = ["./shared_mcp_servers"]

# The [env] table defines environment variables to be set for this context.
[env]
LOG_LEVEL = "INFO"
DEFAULT_MODEL = "claude-3-sonnet-20240229"
```

## 4. Context Resolution and Configuration Loading

### 4.1. Hierarchical Merging Rules

Settings from all discovered `.aurite` files are merged to form the final runtime configuration.

*   **`type`, `projects`:** These are unique to each file and are not merged. They define the structure of their specific level.
*   **Path Lists (`include_configs`, `custom_workflow_paths`, etc.):** These lists are **concatenated**. The paths from the most specific level (the Project) are added first, ensuring they are searched first.
*   **`[env]` Variables:** The dictionaries are **merged**. If a variable exists at multiple levels, the value from the most specific level (the Project) **wins**.

### 4.2. The Configuration Loading Priority Order

The `ConfigManager` loads component configurations (e.g., agents, LLMs) from all sources in a strict, well-defined order. When searching for a component, the framework searches these locations in order and **stops as soon as it finds the first match.**

The priority is as follows:

1.  **Current Project:** The `config/` and `include_configs` directories of the first `.aurite` file found (Project Root).
2.  **Workspace Defaults:** The `config/` and `include_configs` of the second `.aurite` file found (Workspace Root).
3.  **Peer Projects:** The `config/` directories of each project listed in the Workspace's `projects` array, **in the exact order they are listed.**
4.  **Higher-Level Contexts:** This pattern repeats for any further `.aurite` files found.
5.  **Global Config:** `~/.aurite/config/` is checked last as the ultimate fallback.

## 5. The `aurite` Command-Line Interface (CLI)

The CLI is fully context-aware based on the unified anchor model.

### `aurite init`
*   **Action:** A command group for scaffolding projects and workspaces.
*   **Subcommands:**
    *   `aurite init project [NAME]`
    *   `aurite init workspace [NAME]`

### `aurite api`, `aurite run`, `aurite list`
*   These commands (`api`, `run`, `list`) and their subcommands operate on the fully resolved context, using the `ConfigManager` to find and load the correct components based on the strict priority order.
