# Implementation Plan: Task D - Packaging & Distribution Strategy

**Version:** 1.0
**Date:** 2025-05-14
**Author(s):** Ryan, Gemini
**Related Design Document (Optional):** N/A (Referencing `docs/plans/overarching_open_source_plan.md`)

## 1. Goals
*   Define a robust strategy for packaging `aurite-agents` as a pip-installable Python package.
*   Develop solutions for managing dynamic file paths for user-provided MCP server scripts, configuration files, and custom workflow modules when the framework is installed as a package.
*   Ensure the `pyproject.toml` is correctly configured for building and distributing the package.
*   Outline the necessary documentation for users regarding installation, setup, and usage of the packaged framework.

## 2. Scope
*   **In Scope:**
    *   Investigation of path management strategies for user-defined components.
    *   Design of how users will provide paths for:
        *   STDIO-based MCP server executables.
        *   Project configuration files (e.g., `my_project_config.json`).
        *   Custom Python workflow modules.
    *   Review and necessary modifications to `pyproject.toml` to:
        *   Include necessary data files (e.g., default `packaged_servers`, example configurations if any).
        *   Define console script entry points (e.g., for a potential CLI tool).
    *   Defining a recommended project structure for users of the `aurite-agents` package.
    *   Outlining the build process for the Python package (e.g., using `python -m build`).
    *   Documenting the installation and usage of the packaged framework.
*   **Out of Scope (Optional but Recommended):**
    *   Actual publishing to PyPI.
    *   Creating extensive example projects beyond what's needed to demonstrate path management.
    *   Modifying the core framework logic extensively, unless directly required for path resolution.

## 3. Prerequisites (Optional)
*   Understanding of current path handling in `HostManager`, `ClientConfig`, `CustomWorkflowConfig`.
*   Familiarity with Python packaging concepts (`pyproject.toml`, `setuptools`, `pip`).

## 4. Implementation Steps

**Phase 1: Research & Strategy Definition (PLAN MODE)**

1.  **Step 1.1: Analyze Current Path Handling**
    *   **Action:** Review `ClientConfig` (for `server_path`), `CustomWorkflowConfig` (for `module_path`), and `HostManager` (for `config_path`). Understand how paths are currently resolved (relative to CWD, absolute, etc.).
    *   **Tooling:** `read_file` on `src/config/config_models.py`, `src/host_manager.py`.
    *   **Verification:** Clear understanding of current path mechanisms.

2.  **Step 1.2: Investigate Path Management Solutions for Packaged Applications**
    *   **Action:** Research common patterns for Python packages to handle user-provided files/scripts:
        *   **Absolute Paths:** Requiring users to provide absolute paths in their configs.
        *   **Paths Relative to a User Project Root:** Defining a "project root" concept for users, and resolving paths relative to that. How would this root be determined (e.g., CWD, an env var, a marker file)?
        *   **Environment Variables:** Using environment variables to point to directories or specific files.
        *   **Application Data Directories:** Using platform-specific app data dirs (e.g., via `appdirs` library) for storing user configs or discovering plugins (less likely for server scripts).
        *   **Entry Points/Plugins:** For custom workflows, could Python entry points be a more robust solution than file paths for discoverability if they are installed in the same environment?
        *   **CLI for Initialization/Configuration:** A CLI tool (e.g., `aurite-admin init`) that sets up a user project structure or config file with correct paths.
    *   **Verification:** A list of potential solutions with pros and cons for each type of dynamic path (STDIO servers, project configs, custom workflows).

3.  **Step 1.3: Define Path Strategy for Each Component Type**
    *   **Action:** Based on research, decide on the recommended strategy for:
        *   **STDIO MCP Servers (`server_path` in `ClientConfig`):**
            *   Likely: Absolute paths or paths relative to the *project configuration file's location*.
        *   **Project Configuration Files (e.g., `my_project_config.json` loaded by `HostManager`):**
            *   Likely: User provides a path (absolute or relative to CWD) to `HostManager` or via a CLI argument.
            *   Consider if the package should ship with a default/example config and how users copy/customize it.
        *   **Custom Workflow Modules (`module_path` in `CustomWorkflowConfig`):**
            *   Likely: Python importable paths (e.g., `my_workflows.my_module`) if the user's workflow code is in their `PYTHONPATH`.
            *   Alternatively, paths relative to the *project configuration file's location*.
    *   **Verification:** A clear, documented strategy for each path type.

4.  **Step 1.4: Design User Project Structure (Recommendation)**
    *   **Action:** Outline a recommended directory structure for users who want to create projects using `aurite-agents`. This helps in standardizing where they place their configs, server scripts, and workflow modules, making relative path strategies more predictable.
    *   Example:
        ```
        my-aurite-project/
        ├── project_config.json
        ├── mcp_servers/
        │   └── my_stdio_server.py
        └── custom_workflows/
            └── my_workflow_module.py
        ```
    *   **Verification:** A documented recommended project layout.

**Phase 2: `pyproject.toml` and Build Process (PLAN then ACT MODE)**

1.  **Step 2.1: Review `pyproject.toml` for Packaging**
    *   **Action:**
        *   Ensure `[project.scripts]` is correctly defined if we want a CLI tool (e.g., `aurite-agents = src.bin.cli:app`).
        *   Review `[tool.setuptools.package-data]` or `[tool.setuptools.packages.find]` (if using `include_package_data` in `setup.cfg` or equivalent in `pyproject.toml`) to ensure any default/example files shipped with the package (like `src/packaged_servers/`) are included.
        *   Confirm all dependencies are correctly listed.
    *   **Tooling:** `read_file` on `pyproject.toml`.
    *   **Verification:** `pyproject.toml` is ready for building a distributable package.

2.  **Step 2.2: Outline Package Build and Local Install Test Process**
    *   **Action:** Document the commands to build the package (e.g., `python -m build`) and install it locally for testing (e.g., `pip install dist/aurite_agents-*.whl`).
    *   **Verification:** Clear steps for building and testing the package installation.

**Phase 3: Implementation (Code Changes if Necessary - ACT MODE)**

1.  **Step 3.1: Implement Path Resolution Logic (If Changed)**
    *   **Action:** If the chosen path strategies require changes to how `HostManager`, `ClientConfig`, or `CustomWorkflowConfig` resolve paths, implement these changes.
    *   This might involve:
        *   Using `Path(config_file_path).parent / relative_path_from_config` for paths relative to the config file.
        *   Checking environment variables.
        *   Modifying `sys.path` carefully if using Python importable paths for workflows not in the standard path (generally discouraged if alternatives exist).
    *   **Tooling:** `replace_in_file` or `write_to_file` for `src/host_manager.py`, `src/config/config_models.py`, etc.
    *   **Verification:** Code changes implemented and unit tested.

2.  **Step 3.2: Develop CLI Tool (If Decided)**
    *   **Action:** If a CLI tool for project initialization or management is part of the strategy, develop its basic functionality using `Typer` (already a dependency).
    *   **Tooling:** `write_to_file` for new CLI modules, `replace_in_file` for `src/bin/cli.py`.
    *   **Verification:** CLI tool functions as per design.

**Phase 4: Documentation & Verification (ACT MODE)**

1.  **Step 4.1: Document Installation and Setup**
    *   **Action:** Write clear instructions for users on how to:
        *   Install the `aurite-agents` package via pip.
        *   Set up their project directory (based on the recommended structure).
        *   Configure paths for their STDIO servers, project configs, and custom workflows according to the chosen strategy.
        *   Use any CLI tools provided.
    *   **Tooling:** `write_to_file` or `replace_in_file` for `README.md` or new documentation files (e.g., `docs/usage/packaging.md`).
    *   **Verification:** Documentation is clear and accurate.

2.  **Step 4.2: Test Packaged Installation and Path Resolution**
    *   **Action:**
        *   Build the package: `python -m build`.
        *   Create a new virtual environment.
        *   Install the built wheel: `pip install dist/aurite_agents-*.whl`.
        *   Set up a sample user project outside the source directory, following the documented structure and path configuration methods.
        *   Run a simple test case that involves:
            *   Loading a project configuration.
            *   An agent using an STDIO server with `server_path` configured.
            *   A custom workflow with `module_path` configured.
    *   **Tooling:** `execute_command`.
    *   **Verification:** The packaged application runs correctly in a clean environment, resolving all user-provided paths as expected.

## 5. Testing Strategy
*   Unit tests for any new path resolution logic.
*   Manual end-to-end testing of the packaged installation in a clean environment, verifying that user-provided STDIO servers, configurations, and custom workflows are correctly loaded and executed based on the defined path strategies.

## 6. Potential Risks & Mitigation
*   **Risk:** Path resolution becomes overly complex or platform-dependent.
    *   **Mitigation:** Favor simpler, cross-platform solutions (e.g., paths relative to config files, absolute paths, standard Python import mechanisms). Clearly document any platform-specific considerations.
*   **Risk:** `pyproject.toml` misconfiguration leading to missing files in the distributed package.
    *   **Mitigation:** Thoroughly test the built package (wheel/sdist) to ensure all necessary data files are included. Use tools like `check-wheel-contents`.

## 7. Open Questions & Discussion Points
*   What is the preferred level of "magic" vs. explicitness for path resolution? (e.g., should the system try many ways to find a file, or require a clear method from the user?)
*   Should the package provide a command to initialize a new user project with a default structure and example config (e.g., `aurite-agents init-project`)?
*   How to handle `src/packaged_servers`? Should they be easily usable by users as examples, or are they purely internal? If usable, how should users reference them after pip install? (Likely via `importlib.resources` if they are package data).
