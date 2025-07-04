# Implementation Plan: Unified Anchor and Hierarchical Context

**Version:** 1.0
**Date:** 2025-07-03
**Author(s):** Gemini, Ryan
**Related Design Document:** [Packaging and Runtime Behavior v1.3](../design/packaging_and_runtime_behavior.md)

## 1. Goals
*   Refactor the framework to use the unified `.aurite` anchor file for context discovery.
*   Implement a multi-level hierarchical configuration loading system.
*   Overhaul the `aurite init` CLI to support the new project and workspace scaffolding model.
*   Ensure all framework commands (`run`, `list`, `api`) are fully context-aware.

## 2. Scope
*   **In Scope:**
    *   `src/aurite/host_manager.py`: Modifying the `Aurite` class for context discovery.
    *   `src/aurite/config/config_manager.py`: Rewriting the `ConfigManager` for hierarchical loading.
    *   `src/aurite/bin/cli/main.py`: Re-implementing the CLI, especially the `init` command.
    *   `tests/`: Adding new unit and integration tests for the new functionality.
*   **Out of Scope:**
    *   Changes to the FastAPI server logic beyond how it's initialized.
    *   Changes to the core agent or workflow execution logic.

## 3. Implementation Steps

### Phase 0: Architectural Refactoring

**Objective:** Revert the initial changes and align the codebase with the improved architectural design.

1.  **Step 0.1: Revert Changes to `host_manager.py`**
    *   **File(s):** `src/aurite/host_manager.py`
    *   **Action:**
        *   Restore the file to its state before the `find_anchor_files` integration. The `Aurite` class `__init__` should be simplified, preparing it for a self-sufficient `ConfigManager`.
    *   **Verification:**
        *   The file is reverted to its previous state.

### Phase 1: Self-Contained Context Discovery in ConfigManager

**Objective:** Implement the context discovery and hierarchical loading logic entirely within the `ConfigManager`.

1.  **Step 1.1: Create Context Discovery Utilities**
    *   **File(s):** `src/aurite/config/config_utils.py`
    *   **Action:**
        *   Ensure the function `find_anchor_files(start_path: Path) -> List[Path]` exists and is correct.
    *   **Verification:**
        *   Create a unit test `tests/unit/config/test_config_utils.py` to verify `find_anchor_files`.

2.  **Step 1.2: Rewrite `ConfigManager` Initialization**
    *   **File(s):** `src/aurite/config/config_manager.py`
    *   **Action:**
        *   Modify the `ConfigManager` `__init__` method to take no arguments.
        *   Inside `__init__`, call `find_anchor_files(Path.cwd())` to discover the context.
        *   Store `context_paths`, `project_root`, etc., as internal attributes of the `ConfigManager`.
        *   The `__init__` method will now orchestrate the entire loading process: finding anchors, parsing `.aurite` files, merging settings, and building the component index.
    *   **Verification:**
        *   Update unit tests for `ConfigManager` to reflect the new initialization process.

3.  **Step 1.3: Simplify `Aurite` Host Class**
    *   **File(s):** `src/aurite/host_manager.py`
    *   **Action:**
        *   Modify the `Aurite` class's `__init__` method to simply instantiate `ConfigManager()` with no arguments.
        *   If the `Aurite` class needs access to the project root, it should get it from the `ConfigManager` instance (e.g., `self.config_manager.project_root`).
    *   **Verification:**
        *   Update integration tests in `tests/integration/orchestration/test_aurite_class.py` to assert that the `Aurite` class initializes correctly and can retrieve context information from the `ConfigManager`.

### Phase 2: Hierarchical Configuration Loading (in ConfigManager)

**Objective:** Implement the configuration merging and component loading logic within the `ConfigManager`.

1.  **Step 2.1: Implement `.aurite` File Parsing**
    *   **File(s):** `src/aurite/config/config_manager.py`
    *   **Action:**
        *   Create a helper function or method to parse a single `.aurite` TOML file. It should handle missing sections gracefully.
        *   This function will be responsible for reading the `[aurite]` and `[env]` tables.
    *   **Verification:**
        *   Unit test the parsing function with valid and malformed `.aurite` files.

2.  **Step 2.2: Implement Hierarchical Merging Logic**
    *   **File(s):** `src/aurite/config/config_manager.py`
    *   **Action:**
        *   Rewrite the `ConfigManager`'s loading methods.
        *   It should iterate through the `context_paths` from the `Aurite` class.
        *   For each path, it should parse the `.aurite` file and merge the settings (`[env]` variables, path lists) according to the rules in the design document.
    *   **Verification:**
        *   Unit test the merging logic specifically. For example, assert that project `[env]` variables override workspace variables.

3.  **Step 2.3: Implement Component Loading Logic**
    *   **File(s):** `src/aurite/config/config_manager.py`
    *   **Action:**
        *   Rewrite the methods that find and load components (e.g., `get_agent_config`).
        *   These methods must now search through the different configuration sources (Project, Workspace, Peer Projects) in the strict priority order defined in the design document, stopping at the first match.
    *   **Verification:**
        *   Create a comprehensive integration test with a mock file structure (Project A, Workspace, Project B) and assert that the `ConfigManager` correctly retrieves components from the right location based on the priority rules.

### Phase 3: CLI Overhaul

**Objective:** Re-implement the `aurite` CLI to be fully context-aware and support the new `init` subcommands.

1.  **Step 3.1: Implement `aurite init workspace`**
    *   **File(s):** `src/aurite/bin/cli/main.py`
    *   **Action:**
        *   Create the `init` command group in Typer.
        *   Implement the `workspace` subcommand. It should create a directory and a pre-configured `.aurite` file with `type = "workspace"`.
    *   **Verification:**
        *   Manual test: Run `aurite init workspace test-ws` and verify the created directory and file are correct.

2.  **Step 3.2: Implement `aurite init project`**
    *   **File(s):** `src/aurite/bin/cli/main.py`
    *   **Action:**
        *   Implement the `project` subcommand. It should create a directory, an empty `.aurite` file, and scaffold all the template files.
    *   **Verification:**
        *   Manual test: Run `aurite init project test-proj` and verify the full project structure is created correctly.

3.  **Step 3.3: Update `run` and `list` Commands**
    *   **File(s):** `src/aurite/bin/cli/main.py`
    *   **Action:**
        *   Ensure that the `run` and `list` command groups correctly initialize the `Aurite` class. No major changes should be needed here if the `ConfigManager` is implemented correctly, as the complexity is abstracted away.
    *   **Verification:**
        *   Create an end-to-end test fixture with a workspace and two projects. Run `aurite list agents` from within one project and verify it lists agents from the project, workspace, and peer project correctly.
        *   Run `aurite run agent <agent_name>` for an agent that only exists in the peer project and verify it executes successfully.

## 4. Testing Strategy
*   **Unit Tests:** Focus on pure functions: `find_anchor_files`, `.aurite` parsing, and config merging logic.
*   **Integration Tests:** Test the interaction between classes. The primary focus will be testing `ConfigManager`'s ability to find components within a complex, mocked file system structure.
*   **End-to-End (E2E) / Manual Tests:** Use the CLI commands in a temporary directory to verify the `init` process and the context-aware behavior of `run` and `list`.
