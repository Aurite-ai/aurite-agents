# Design Document: Aurite Agents Packaged Version Strategy

**Version:** 1.0
**Date:** 2025-05-16
**Author(s):** Ryan, Gemini

## 1. Introduction & Goals

*   **Overview:** This document outlines the strategy for packaging the `aurite-agents` framework as a pip-installable Python package for open-source distribution via PyPI.
*   **Primary Objectives:**
    1.  Enable users to easily install and use `aurite-agents` in their own Python projects.
    2.  Provide a robust and intuitive solution for managing dynamic file paths for:
        *   Component configurations (LLMs, Clients, Agents, Workflows).
        *   MCP server executable paths.
        *   User-created custom workflow module paths.
    3.  Ensure a smooth user experience for project setup and configuration.
*   **Scope:**
    *   **In Scope:** Changes to configuration loading, path resolution, package structure for PyPI, and introduction of a project initialization CLI command.
    *   **Out of Scope (for this specific design):** Detailed implementation of every MCP server or custom workflow example, major changes to the core agent execution logic unrelated to pathing.

## 2. Current State

*   The `aurite-agents` framework currently operates primarily as a standalone project cloned from a Git repository.
*   Path resolution for component configurations (e.g., `config/agents/`, `config/llms/`) relies on a `PROJECT_ROOT_DIR` variable, typically derived from the `src.config` module's location within the development environment. This assumes a fixed relative path to a `config/` directory at the project root.
*   Paths within configuration files (e.g., `server_path` for MCP servers, `module_path` for custom workflows) are also resolved relative to this `PROJECT_ROOT_DIR`.
*   This approach is not suitable for a packaged version where the framework code resides in `site-packages` and user projects are external.

## 3. Proposed Design: "Hybrid Project-Centric" Strategy

This strategy combines package-internal defaults with project-local user configurations, making the location of the user's main project configuration file central to path resolution.

### 3.1. Package-Internal Default/Example Components

*   **Location:** A new top-level directory, `src/aurite/packaged/`, will be created within the `aurite-agents` package source. This directory will contain subdirectories for different types of bundled resources:
    *   `component_configs/`: For all component JSON definition files.
        *   `agents/`
        *   `clients/`
        *   `llms/`
        *   `workflows/` (for simple workflow JSONs)
        *   `custom_workflows/` (for custom workflow JSONs)
    *   `example_mcp_servers/`: For example MCP server Python script files.
    *   `example_custom_workflow_src/`: For example custom workflow Python module files.
*   **Content:** These directories will house a curated set of default/example component JSON configurations, example MCP server scripts, and example custom workflow Python modules.
*   **Access & Loading:**
    *   The `ComponentManager` will use `importlib.resources.files('aurite.packaged')` as the base. For example, to access agent JSON configurations, it would use `.joinpath('component_configs/agents')`.
    *   These components serve as a read-only baseline, providing out-of-the-box functionality and examples.
    *   They are loaded first by the `ComponentManager`.

### 3.2. User Project Structure & Configuration

*   **User Project Root (`current_project_root`):**
    *   When a user utilizes `aurite-agents` for their application, they will typically work within a dedicated project directory (e.g., `/path/to/my_ai_app/`).
    *   The **root of this user project (`current_project_root`)** is defined as the directory containing their main project configuration JSON file.
*   **Main Project Configuration File:**
    *   The framework will identify this main project configuration file. This can be specified via:
        1.  The existing `PROJECT_CONFIG_PATH` environment variable.
        2.  A CLI argument when running framA I see. component definitions within the main project JSON file are resolved last and can override both package-internal and user-project file-based components if IDs conflict.

### 3.4. Path Resolution for MCP Servers, Custom Workflows, etc.

*   Paths specified within configuration files (e.g., `server_path` in `ClientConfig`, `module_path` in `CustomWorkflowConfig`) will be interpreted as **relative to the `current_project_root`**.
*   The `resolve_path_fields` and `relativize_path_fields` utility functions in `src/config/config_utils.py` will be updated to accept the `current_project_root` as a parameter for path resolution, instead of relying on a static, package-level `PROJECT_ROOT_DIR`.

### 3.5. CLI Command: `aurite-agents init`

*   A new CLI command, `aurite-agents init <project_directory_name>`, will be introduced.
*   **Functionality:**
    1.  Creates the specified `<project_directory_name>`.
    2.  Scaffolds a basic main project configuration JSON file within this directory (e.g., `aurite_config.json` or `project.json`).
    3.  Creates recommended subdirectories, such as:
        *   `config/agents/`
        *   `config/llms/`
        *   `config/clients/`
        *   `config/workflows/`
        *   `config/custom_workflows/`
        *   `mcp_servers/` (for user-managed MCP server scripts)
        *   `custom_workflow_src/` (for user's custom workflow Python modules)
    4.  Optionally, copies a few example files (e.g., a sample MCP server script, a basic custom workflow Python file) into these directories to guide the user.
    5.  Prints a message guiding the user on next steps (e.g., "Set PROJECT_CONFIG_PATH to your new project.json").

### 3.6. Core Module Modifications

*   **`src.config.PROJECT_ROOT_DIR`:** This static variable, and its usage for locating the `config/` subdirectories, will be removed or refactored.
*   **`ComponentManager` (`src/config/component_manager.py`):**
    *   The constructor (`__init__`) will load package-internal default component JSONs from `src/aurite/packaged/component_configs/` using `importlib.resources`.
    *   A new method, e.g., `load_project_components(self, project_root_path: Path)`, will be added. This method will scan for user-defined component JSON files in subdirectories (e.g., `project_root_path / 'config' / 'agents'`) relative to the provided `project_root_path`.
    *   The `COMPONENT_TYPES_DIRS` dictionary will be adapted to define sub-paths (e.g., `config/agents` for user projects, and `component_configs/agents` relative to the `src/aurite/packaged/` base for internal defaults).
    *   File CRUD operations (`save_component_config`, `delete_component_config`, etc.) will operate on paths relative to the `project_root_path` passed to them (likely via `ProjectManager`).
*   **`ProjectManager` (`src/config/project_manager.py`):**
    *   When `load_project(project_config_file_path)` is called, `project_config_file_path.parent` will be stored as the `current_project_root`.
    *   This `current_project_root` will be passed to `ComponentManager.load_project_components()`.
    *   This `current_project_root` will also be passed to `resolve_path_fields` (from `config_utils`) when parsing the project file itself and its inline component definitions.
*   **`config_utils.py`:**
    *   Functions like `resolve_path_fields` and `relativize_path_fields` will be modified to accept a `base_path: Path` argument (which will be the `current_project_root`) instead of using the static `PROJECT_ROOT_DIR`.

## 4. Design Considerations & Trade-offs

*   **Simplicity vs. Flexibility for Project Root:** Using the main project config file's directory as the `current_project_root` is simple and covers most use cases for a packaged library. It might be slightly less flexible if a user has many disparate project config files in one directory all pointing to different sets of relative resources, but this is considered an edge case for the initial packaged version.
*   **User Experience:** The `aurite-agents init` command aims to significantly lower the barrier to entry for new users.
*   **Configuration Overriding:** The defined loading order (package -> project files -> inline project defs) provides a clear and predictable way for users to customize and override default configurations.
*   **Version Control:** This project-centric approach allows users to easily version control their specific configurations, custom workflow code, and MCP server scripts alongside their main application code.
*   **No Global User Directory Pollution:** Core project configurations and files are kept within the user's project directory, avoiding the need to manage files in global user-specific directories (like `~/.config/`) for primary operation, which is cleaner. (Global dirs could still be used for truly global settings like API keys if desired in the future, perhaps via `appdirs`).

## 5. Open Questions & Discussion Points

*   (None at this time, user has expressed agreement with the overall strategy.)

## 6. PyPI Packaging Details (High-Level)

*   **`pyproject.toml`:** Will be updated with all necessary metadata for PyPI (name, version, author, description, classifiers, dependencies).
*   **Package Data:** The `src/aurite/packaged/` directory and all its contents (including subdirectories like `component_configs`, `example_mcp_servers`, `example_custom_workflow_src`) must be included in the built distributions (sdist and wheel). This will be configured in `pyproject.toml` (e.g., via `setuptools` `package_data` or `include_package_data` and `MANIFEST.in`).
*   **Entry Points:** CLI entry points for `aurite-agents init` (and potentially other future commands) will be defined in `pyproject.toml`.
*   **Build Process:** Standard `python -m build` will be used.
*   **Publishing:** `twine` will be used for uploading to TestPyPI and then PyPI.
