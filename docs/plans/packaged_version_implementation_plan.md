# Implementation Plan: Aurite Agents Packaged Version

**Version:** 1.0
**Date:** 2025-05-16
**Author(s):** Ryan, Gemini
**Related Design Document:** `docs/design/packaged_version.md`

## 1. Goals

*   Implement the "Hybrid Project-Centric" strategy for packaging `aurite-agents`.
*   Refactor configuration loading to support package-internal defaults and user-project specific configurations.
*   Enable path resolution relative to a dynamic `current_project_root`.
*   Prepare the package for PyPI distribution, including a CLI for project initialization.

## 2. Scope

*   **In Scope:**
    *   Modifications to `src/config/component_manager.py`, `src/config/project_manager.py`, `src/config/config_utils.py`.
    *   Creation of `src/aurite/packaged/` directory and its subdirectories (`component_configs`, `example_mcp_servers`, `example_custom_workflow_src`, `project_templates`) and populating them with example/default files.
    *   Modifications to `src/bin/dependencies.py` regarding `PROJECT_ROOT`.
    *   Creation of a new CLI command `aurite-agents init`.
    *   Updates to `pyproject.toml` for packaging, CLI entry points, and exposing the public API.
    *   Updates to `src/aurite/__init__.py` to define the public API.
    *   Creation of a `MANIFEST.in` if necessary for including package data.
    *   Unit tests for new/modified logic.
*   **Out of Scope (for this plan):**
    *   Full-scale creation of all example MCP servers or complex custom workflows (only basic examples/templates for `packaged`).
    *   Publishing to PyPI (this plan covers preparation up to local build and test).
    *   Extensive documentation updates beyond what's needed to explain the new packaging and project structure (a separate task can cover full documentation overhaul).

## 3. Prerequisites

*   Approved `docs/design/packaged_version.md`.
*   Development environment set up for `aurite-agents`.

## 4. Implementation Steps

**Phase 1: Setup Package Structure & Default Configurations**

1.  **Step 1.1: Create `src/aurite/packaged/` Directory Structure**
    *   **File(s):** New directory `src/aurite/packaged/`
    *   **Action:**
        *   Create the directory `src/aurite/packaged/`.
        *   Inside `src/aurite/packaged/`, create subdirectories:
            *   `component_configs/`
                *   `agents/`
                *   `clients/`
                *   `llms/`
                *   `workflows/`
                *   `custom_workflows/`
                *   `projects/` (for project templates like prompt_validation_config.json)
            *   `example_mcp_servers/`
            *   `example_custom_workflow_src/`
    *   **Verification:** Directory structure exists as specified.

2.  **Step 1.2: Populate `packaged/` Subdirectories with Examples and Templates**
    *   **File(s):** JSON files within `src/aurite/packaged/component_configs/` subdirectories (including `projects/`), Python scripts in `src/aurite/packaged/example_mcp_servers/`, and Python modules in `src/aurite/packaged/example_custom_workflow_src/`.
    *   **Action:**
        *   Copy representative example JSON component definitions from the current `config/` subdirectories into the corresponding `src/aurite/packaged/component_configs/` subdirectories.
        *   Move `config/projects/prompt_validation_config.json` to `src/aurite/packaged/component_configs/projects/prompt_validation_config.json`.
        *   Place example MCP server Python scripts (e.g., a simplified weather server) into `src/aurite/packaged/example_mcp_servers/`.
        *   Place example custom workflow Python modules into `src/aurite/packaged/example_custom_workflow_src/`.
        *   Ensure paths within example JSONs (e.g., `server_path` in a client config, `module_path` in a custom workflow config) correctly point to these packaged examples, relative to the `src/aurite/packaged/` directory (e.g., `../example_mcp_servers/weather.py` if the client JSON is in `component_configs/clients/`). The `resolve_path_fields` will need to handle this using `importlib.resources.files('aurite.packaged')` as its base.
    *   **Verification:** Example files are present, parsable, and internal path references are consistent with the new packaged structure. `prompt_validation_config.json` is moved.

3.  **Step 1.3: Refactor `PROJECT_ROOT` Definitions**
    *   **File(s):** `src/config/__init__.py`, `src/bin/dependencies.py`
    *   **Action:**
        *   Remove or comment out the static `PROJECT_ROOT_DIR` definition from `src/config/__init__.py` (and any other location it might be defined for similar purposes). Note its replacement by the dynamic `current_project_root`.
        *   In `src/bin/dependencies.py`, review the `PROJECT_ROOT` definition. Clarify its purpose (likely for package-internal paths, e.g., finding `frontend/dist` if bundled). Ensure it's not used for resolving user project file paths. If `frontend/dist` is to be bundled, this `PROJECT_ROOT` might be adjusted or `importlib.resources` used directly in `api.py` for serving.
    *   **Verification:** Static `PROJECT_ROOT_DIR` (for user files) is removed. The role of `PROJECT_ROOT` in `dependencies.py` is clarified and confirmed not to conflict with `current_project_root` logic.

**Phase 2: Refactor `ComponentManager`**

1.  **Step 2.1: Modify `ComponentManager.__init__` to Load Packaged Defaults**
    *   **File(s):** `src/config/component_manager.py`
    *   **Action:**
        *   Import `importlib.resources`.
        *   Modify `_load_all_components` (or a new internal method called by `__init__`) to first load component JSONs from `src/aurite/packaged/component_configs/`.
        *   Use `importlib.resources.files('aurite.packaged').joinpath('component_configs', sub_dir_name)` to get the path to each component type's subdirectory (e.g., `agents`, `llms`).
        *   Iterate through JSON files in these packaged directories and parse them using the existing `_parse_component_file` logic.
        *   When calling `_parse_component_file` (and subsequently `resolve_path_fields`) for these packaged defaults, the `base_path_for_resolution` should be `importlib.resources.files('aurite.packaged')`. This allows paths within default component JSONs (like a `server_path` pointing to `../example_mcp_servers/server.py`) to be resolved correctly relative to the `packaged` directory root.
        *   Store these loaded defaults in the respective component dictionaries (e.g., `self.clients`, `self.llms`).
    *   **Verification:** Unit tests to confirm that `ComponentManager` loads default components from `src/aurite/packaged/component_configs/` upon initialization, and that any internal paths (e.g., to example servers) are correctly resolved.

2.  **Step 2.2: Adapt `COMPONENT_TYPES_DIRS` and Path Logic**
    *   **File(s):** `src/config/component_manager.py`
    *   **Action:**
        *   The global `COMPONENT_TYPES_DIRS` currently uses `PROJECT_ROOT_DIR`. This needs to change.
        *   One approach: `COMPONENT_TYPES_DIRS` could store *relative* sub-paths like `"clients": Path("config/clients")`.
        *   Methods like `_get_component_file_path` will need to accept a `base_dir: Path` argument (which would be `current_project_root` for user components).
        *   The `_load_all_components` method will need to be split or refactored: one part for `importlib.resources` (as in 2.1) and another for loading from a user's project directory.
    *   **Verification:** Review changes to ensure path construction is flexible.

3.  **Step 2.3: Add `load_project_components(self, project_root_path: Path)` Method**
    *   **File(s):** `src/config/component_manager.py`
    *   **Action:**
        *   Create a new public method `load_project_components(self, project_root_path: Path)`.
        *   This method will iterate through `COMPONENT_META`. For each component type:
            *   Construct the path to the user's component subdirectory (e.g., `project_root_path / "config" / "agents"`). Use the relative paths from the adapted `COMPONENT_TYPES_DIRS`.
            *   If the directory exists, scan for JSON files.
            *   Parse these files using `_parse_component_file`. Crucially, `_parse_component_file` (and `resolve_path_fields` it calls) must now use `project_root_path` as the base for resolving any relative paths *within these user JSONs*.
            *   Add/override components in `self.clients`, `self.llms`, etc. Log warnings for overrides.
    *   **Verification:** Unit tests to show that calling `load_project_components` with a mock project structure correctly loads and overrides components.

4.  **Step 2.4: Update `_parse_component_file` and `_prepare_data_for_save`**
    *   **File(s):** `src/config/component_manager.py`
    *   **Action:**
        *   Modify `_parse_component_file` to accept `base_path_for_resolution: Path` as an argument. This will be passed to `resolve_path_fields`.
        *   Modify `_prepare_data_for_save` to accept `base_path_for_relativization: Path`. This will be passed to `relativize_path_fields`.
        *   Update calls to these methods throughout `ComponentManager` to pass the correct base path (either from `importlib.resources` context or `project_root_path`).
    *   **Verification:** Existing tests for component parsing and saving should be updated and pass.

5.  **Step 2.5: Update Component CRUD Methods**
    *   **File(s):** `src/config/component_manager.py`
    *   **Action:**
        *   Methods like `save_component_config`, `delete_component_config`, `create_component_file`, `save_components_to_file` currently operate based on the old `PROJECT_ROOT_DIR` via `COMPONENT_TYPES_DIRS`.
        *   These methods are primarily for managing components *within a user's project*. They should now require a `project_root_path: Path` argument to determine where to save/delete files (e.g., `project_root_path / "config" / "agents" / "my_agent.json"`).
        *   Update `_get_component_file_path` to take `project_root_path: Path` and use it as the base for constructing file paths.
    *   **Verification:** Unit tests for CRUD operations, ensuring they target the correct user project paths.

**Phase 3: Refactor `ProjectManager`**

1.  **Step 3.1: Remove Static `PROJECT_ROOT_DIR` Usage**
    *   **File(s):** `src/config/project_manager.py`
    *   **Action:**
        *   Remove any import or usage of the static `PROJECT_ROOT_DIR` from `src.config`.
    *   **Verification:** Code inspection.

2.  **Step 3.2: Establish `current_project_root` in `load_project`**
    *   **File(s):** `src/config/project_manager.py`
    *   **Action:**
        *   In `load_project(self, project_config_file_path: Path)`:
            *   Set `current_project_root = project_config_file_path.parent`.
            *   Store `current_project_root` as an instance variable, e.g., `self.current_project_root`. Make this accessible (e.g., via a property) if `HostManager` needs it for custom workflow path validation.
        *   After parsing the project file data but before fully resolving it, call `self.component_manager.load_project_components(self.current_project_root)`. This ensures user project components are loaded and can override defaults before the project file itself tries to reference them.
    *   **Verification:** Debugging or logging to confirm `current_project_root` is set correctly and `load_project_components` is called. `current_project_root` is accessible.

3.  **Step 3.3: Pass `current_project_root` to Path Resolution Utilities**
    *   **File(s):** `src/config/project_manager.py`
    *   **Action:**
        *   In `_parse_and_resolve_project_data` (and its helper `_resolve_components`):
            *   When calling `resolve_path_fields` for inline component definitions, pass `self.current_project_root` as the `base_path` argument.
    *   **Verification:** Unit tests for project loading with inline definitions containing relative paths.

4.  **Step 3.4: Update `HostManager` for `prompt_validation_config.json` and Custom Workflow Path Validation**
    *   **File(s):** `src/host_manager.py`
    *   **Action:**
        *   Modify `HostManager.initialize`: Instead of loading `prompt_validation_path` with a hardcoded relative path, load it from `src/aurite/packaged/component_configs/projects/prompt_validation_config.json` using `importlib.resources` to get its path, then call `self.project_manager.parse_project_file()` and integrate its components, or ensure these components are part of the default load.
        *   Modify `HostManager.register_custom_workflow`: Update the `module_path` validation to use `self.project_manager.current_project_root` instead of the old static `PROJECT_ROOT_DIR`.
    *   **Verification:** `prompt_validation_config.json` is loaded correctly from its new packaged location. Custom workflow registration validates paths against the correct project root.

**Phase 4: Refactor `config_utils.py` and `src/bin/dependencies.py`**

1.  **Step 4.1: Modify Path Resolution/Relativization Functions in `config_utils.py`**
    *   **File(s):** `src/config/config_utils.py`
    *   **Action:**
        *   Modify `resolve_path_fields(data: Dict, model_class: Type, base_path: Path)` to accept `base_path` instead of `project_root_dir`. Update its internal logic to use `base_path`.
        *   Modify `relativize_path_fields(data: Dict, model_class: Type, base_path: Path)` similarly.
    *   **Verification:** Unit tests for these utility functions with various base paths and relative/absolute path inputs.

2.  **Step 4.2: Review and Adjust `PROJECT_ROOT` in `src/bin/dependencies.py`**
    *   **File(s):** `src/bin/dependencies.py`
    *   **Action:**
        *   Confirm that `PROJECT_ROOT` defined in this file (calculated as `Path(__file__).parent.parent.parent`) correctly points to the root of the `aurite-agents` package when installed. This is generally used for locating package-internal, non-Python files (like `frontend/dist` if bundled).
        *   Ensure this `PROJECT_ROOT` is not used for resolving user-project specific paths (which is the role of `current_project_root` from `ProjectManager`).
        *   If `frontend/dist/` is to be bundled with the pip package (see Phase 6.2), `api.py` should ideally use `importlib.resources` to access these files rather than relying on this `PROJECT_ROOT` for robustness, or ensure `PROJECT_ROOT` correctly resolves within an installed package context.
    *   **Verification:** The purpose and usage of `PROJECT_ROOT` in `dependencies.py` are clear and do not conflict with the dynamic `current_project_root` strategy. Frontend asset serving strategy is confirmed.

**Phase 5: Implement `aurite-agents init` CLI Command**

1.  **Step 5.1: Create CLI Script**
    *   **File(s):** New file, e.g., `src/aurite/cli/main.py` (or integrate into `src/bin/cli.py` if structure allows).
    *   **Action:**
        *   Use a library like `click` or `argparse` for command-line argument parsing.
        *   Implement the logic described in Design Document section 3.5:
            *   Take `<project_directory_name>` as an argument.
            *   Create the directory.
            *   Create a default project JSON file (e.g., `aurite_config.json`) with minimal content.
            *   Create subdirectories: `config/agents`, `config/llms`, etc., `mcp_servers`, `custom_workflow_src`.
            *   Optionally, copy basic example files (e.g., from `src/aurite/packaged/component_configs/`, `src/aurite/packaged/example_mcp_servers/` or new minimal templates) into these user directories.
    *   **Verification:** Manually run the CLI command and verify the directory structure and files are created as expected.

2.  **Step 5.2: Add Entry Point in `pyproject.toml`**
    *   **File(s):** `pyproject.toml`
    *   **Action:**
        *   Add a console script entry point:
          ```toml
          [project.scripts]
          aurite-agents = "aurite.cli.main:cli_entry_point" # Adjust module:function path
          ```
    *   **Verification:** After installing the package (locally editable for now), check if `aurite-agents init` command is available and works.

**Phase 6: Update `pyproject.toml` for Packaging**

1.  **Step 6.1: Add Package Metadata**
    *   **File(s):** `pyproject.toml`
    *   **Action:**
        *   Ensure all required fields are present: `name = "aurite-agents"`, `version`, `authors`, `description`, `readme`, `requires-python`, `classifiers`, `dependencies` (add `importlib_resources` if Python < 3.9, though your README says >=3.12 so it's built-in).
        *   Add `license`.
        *   Add `project.urls` (Homepage, Repository).
    *   **Verification:** Review `pyproject.toml`.

2.  **Step 6.2: Configure Inclusion of `packaged_configs`**
    *   **File(s):** `pyproject.toml` and potentially `MANIFEST.in` (if using setuptools and `include_package_data`).
    *   **Action:**
        *   Ensure that the entire `src/aurite/packaged/` directory (and all its subdirectories and files) is included in the built package.
        *   If the developer UI (`frontend/dist/`) is to be bundled, ensure it's also included.
        *   For setuptools, this might involve `include_package_data = true` in `pyproject.toml`'s `[tool.setuptools]` section and a `MANIFEST.in` file:
            ```
            recursive-include src/aurite/packaged *
            # If bundling frontend:
            # recursive-include frontend/dist *
            ```
        *   Or, using `package_data` directly in `pyproject.toml` if preferred by the build backend.
    *   **Verification:** Build the sdist and wheel (`python -m build`). Inspect the contents of the built wheel (it's a zip file) to ensure the full `packaged/` directory structure and its contents (and `frontend/dist` if applicable) are present.

2.  **Step 6.3: Define Public API in `src/aurite/__init__.py`**
    *   **File(s):** `src/aurite/__init__.py`
    *   **Action:**
        *   Import and expose key public classes and functions that users of the library will need. This should include at least:
            *   `HostManager` from `src.host_manager`
            *   Configuration models like `AgentConfig`, `ClientConfig`, `LLMConfig`, `WorkflowConfig`, `CustomWorkflowConfig`, `ProjectConfig` from `src.config.config_models`.
            *   Potentially other relevant types or utilities.
        *   Use `__all__` to explicitly define the public API if desired.
    *   **Verification:** After local installation, confirm that `from aurite import HostManager` (and other key classes) works.

**Phase 7: Initial Testing and Documentation Notes**

1.  **Step 7.1: Local Installation and Basic Test**
    *   **Action:**
        *   In a clean virtual environment, install the locally built wheel (`pip install dist/aurite-*.whl`).
        *   Run `aurite-agents init test_project`.
        *   Navigate into `test_project`.
        *   Create a simple agent config in `test_project/config/agents/my_test_agent.json`.
        *   Create a `test_project/main_project_config.json` that references this agent.
        *   Write a short Python script that sets `PROJECT_CONFIG_PATH` to `test_project/main_project_config.json`, initializes `ComponentManager` and `ProjectManager`, and tries to load the agent.
    *   **Verification:** The script runs successfully and loads the agent, demonstrating that default loading, project-specific loading, and path resolution are working at a basic level.

2.  **Step 7.2: Update Key Documentation Sections (Placeholders)**
    *   **File(s):** `README.md`, new `docs/getting_started_packaged.md` (or similar).
    *   **Action:**
        *   Briefly update `README.md` to mention pip installation.
        *   Create placeholder sections or a new document outlining:
            *   `pip install aurite-agents`
            *   Using `aurite-agents init`
            *   The new project structure and configuration file locations.
            *   How paths are resolved relative to the main project config file.
    *   **Verification:** Documentation provides initial guidance for packaged version users.

## 5. Testing Strategy

*   **Unit Tests:**
    *   New tests for `ComponentManager` to verify loading of packaged defaults and project-specific components, including override behavior.
    *   New tests for `ProjectManager` to verify correct establishment of `current_project_root` and its use in path resolution.
    *   Update existing tests for `config_utils.py` to use parameterized base paths.
    *   Tests for the `aurite-agents init` CLI command (might require subprocess testing or testing the underlying init function).
*   **Integration Tests:**
    *   The manual test in Step 7.1 serves as an initial integration test. More comprehensive integration tests should be developed to cover various scenarios of using the packaged framework.
*   **Manual Verification:**
    *   Building and installing the package in a clean environment.
    *   Running the `init` command.
    *   Setting up and running a small sample project using the packaged version.

## 6. Potential Risks & Mitigation

*   **Path Resolution Complexity:** Ensuring all edge cases for path resolution (absolute paths in configs, symlinks, etc.) are handled correctly. Mitigation: Thorough unit testing of `config_utils.py` and path-related logic in managers.
*   **Packaging `packaged/` directory:** Ensuring all necessary data files and example scripts within `src/aurite/packaged/` are correctly included in sdist and wheel. Mitigation: Inspecting built artifacts; testing installation from the wheel.
*   **CLI Dependencies:** Ensuring CLI dependencies (like `click`) are correctly specified. Mitigation: Testing the CLI in a clean environment.

## 7. Open Questions & Discussion Points

*   (None at this time)

## 8. Rollback Plan (Optional - for critical changes)

*   Given this is a significant refactor, version control (Git) is the primary rollback mechanism. Committing frequently after each logical step is crucial.
*   If major issues are found post-merge, a revert of the feature branch would be the rollback.
