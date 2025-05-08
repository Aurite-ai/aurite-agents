# Phase 1: Core Configuration System Refactor - Detailed Implementation Plan (Revised for Manager Split)

**Overall Goal:** Establish a robust configuration system by separating responsibilities into a `ComponentManager` (for managing reusable component files) and a `ProjectManager` (for loading and resolving project definitions), using the `ProjectConfig` model. This primarily addresses Task 3 from the initial requirements.

**Relevant Files (Initial State):**
*   `src/host/models.py` (Moved)
*   `src/config.py` (Deleted)
*   `src/config/config_manager.py` (Deleted)
*   `src/host_manager.py` (To be refactored)
*   `src/bin/api/routes/config_api.py` (To be refactored)

**New/Modified Files:**
*   `src/config/` (Directory - Exists)
*   `src/config/__init__.py` (Updated)
*   `src/config/config_models.py` (Created from `host/models.py`)
*   `src/config/component_manager.py` (New)
*   `src/config/project_manager.py` (New)
*   `src/config/utils.py` (Optional, if needed later)

---

## Implementation Steps (Revised):

**Step 1.1: Finalize Initial File Structure & Basic Setup**
    *   **1.1.1:** Create `src/config/` directory (Done).
    *   **1.1.2:** Move `src/host/models.py` to `src/config/config_models.py` (Done).
    *   **1.1.3:** Update imports for `config_models.py` across the project (Done by user).
    *   **1.1.4:** Move `ServerConfig` and `PROJECT_ROOT_DIR` from `src/config/config.py` to `src/config/__init__.py` (Done).
    *   **1.1.5:** Delete the now empty `src/config/config.py` file (Done by user).
    *   **1.1.6:** Delete the existing `src/config/config_manager.py` file as we are replacing it (Done).
    *   **1.1.7:** Define `ProjectConfig` model in `src/config/config_models.py` (Done).

---

**Step 1.2: Implement `ComponentManager`**
    *   **File:** `src/config/component_manager.py`
    *   **1.2.1. Create `ComponentManager` Class:** (Done)
        *   Define the class structure.
        *   Implement `__init__`: Initialize component dictionaries, call `_load_all_components()`.
    *   **1.2.2. Implement `_load_all_components`:** (Done)
        *   Define `COMPONENT_TYPES_DIRS` and `COMPONENT_META`.
        *   Implement logic to iterate, find files, parse, validate, resolve paths, and store models. Use `_parse_component_file` helper.
    *   **1.2.3. Implement Component Accessor Methods:** (Done)
        *   Implement `get_component_config(type, id)` and type-specific helpers (`get_client`, `get_agent`, etc.).
    *   **1.2.4. Implement Component Listing Methods:** (Done)
        *   Implement `list_components(type)` and type-specific helpers (`list_clients`, `list_agents`, etc.).
        *   Implement `list_component_files(type)`.
    *   **1.2.5. Implement Component CRUD Methods:** (Done)
        *   Implement `save_component_config(type, data)`.
        *   Implement `delete_component_config(type, id)`.
        *   Implement helper methods `_get_component_file_path` and `_prepare_data_for_save`.
    *   **Testing:** Create `tests/config/test_component_manager.py` with unit tests. (Pending)

---

**Step 1.3: Implement `ProjectManager`**
    *   **File:** `src/config/project_manager.py`
    *   **1.3.1. Create `ProjectManager` Class:** (Done)
        *   Define the class structure.
        *   Implement `__init__` accepting `ComponentManager`.
    *   **1.3.2. Implement `load_project(project_config_file_path: Path) -> ProjectConfig`:** (Done)
        *   Read and parse the project JSON file.
        *   Implement the core logic to resolve component references using `_resolve_components` helper.
        *   Instantiate and return the fully resolved `ProjectConfig` object.
    *   **Testing:** Create `tests/config/test_project_manager.py` with unit tests. Mock `ComponentManager`. (Pending)

---

**Step 1.4: Refactor `HostManager` to Use `ProjectManager`**
    *   **File:** `src/host_manager.py`
    *   **1.4.1. Update `HostManager.__init__`:** (Done)
        *   Instantiate `ComponentManager` and `ProjectManager`. Store `ProjectManager`.
    *   **1.4.2. Update `HostManager.initialize()`:** (Done)
        *   Call `self.project_manager.load_project()`.
        *   Populate internal config dicts from `self.current_project`.
        *   Construct `HostConfig` for `MCPHost` from `self.current_project`.
        *   Remove obsolete `register_config_file` call and method/helpers.
    *   **Testing:** Update `tests/orchestration/test_host_manager*.py`. Mock `ProjectManager`. (Pending)

---

**Step 1.5: Refactor Config API Routes to Use `ComponentManager`**
    *   **File:** `src/bin/api/routes/config_api.py`
    *   **1.5.1. Inject/Access `ComponentManager`:** (Pending)
        *   Update FastAPI dependency injection.
    *   **1.5.2. Update CRUD Endpoints:** (Pending)
        *   Modify list, get, upload/update, delete endpoints to call `ComponentManager` methods.
    *   **Testing:** Update `tests/api/routes/test_config_routes.py`. Mock `ComponentManager`. (Pending)

---

**Step 1.6: Final Review and Cleanup**
    *   **Action:** Review all changed files for consistency, clarity, and potential improvements.
    *   **Action:** Consider if a `src/config/utils.py` is warranted for shared helpers.
    *   **Action:** Ensure all tests pass.
    *   **Action:** Update any relevant documentation (e.g., README, architecture diagrams).

---
