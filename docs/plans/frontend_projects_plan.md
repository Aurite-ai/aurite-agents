# Implementation Plan: Frontend Project Management

**Objective:** Implement "Create Project" and "Load Project Components (Additive)" features in the frontend, allowing users to create new project configuration files and load components from project files into the currently active system configuration without resetting existing components or client connections.

## 1. Backend Changes (Prerequisites)

This plan assumes the following backend changes will be implemented first or in parallel:

### 1.1. `src/config/project_manager.py`
    *   **New Method:** `parse_project_file(self, project_config_file_path: Path) -> ProjectConfig`
        *   Action: Reads the specified project JSON file, resolves component references (similar to current `load_project`), and returns a `ProjectConfig` object.
        *   This method **does not** modify `self.active_project_config`.
    *   **Modify `load_project` (Optional Refinement):**
        *   Current `load_project` will call `parsed_config = self.parse_project_file(...)`, then set `self.active_project_config = parsed_config`.
    *   **Modify `create_project_file`**:
        *   Ensure it can be called with empty lists for `client_configs`, `llm_configs`, `agent_configs`, etc., to create a minimal project file containing only `name`, `description`, and empty component dictionaries (e.g., `"clients": {}`).

### 1.2. `src/host_manager.py`
    *   **New Method:** `async def load_components_from_project(self, project_config_path: Path)`
        *   Action:
            1.  Uses `parsed_config = self.project_manager.parse_project_file(project_config_path)`.
            2.  If no project is currently active (`self.project_manager.active_project_config` is `None` and `self.host` is `None`):
                *   Sets `self.project_manager.active_project_config = parsed_config`.
                *   Initializes `self.host` using clients from `parsed_config`.
                *   Initializes `self.execution` facade.
                *   (Effectively performs an initial project load).
            3.  Else (a project is active):
                *   Iterates through `client_config` in `parsed_config.clients.values()`:
                    *   If client ID is not already registered in `self.host`: Calls `await self.register_client(client_config)`.
                    *   Else: Log warning or skip (current `register_client` raises an error on duplicates; this behavior might need adjustment or be handled by the API response).
                *   Iterates through `llm_config` in `parsed_config.llm_configs.values()`:
                    *   If LLM ID is not in `self.project_manager.active_project_config.llm_configs`: Calls `await self.register_llm_config(llm_config)`.
                *   Iterates through `agent_config` in `parsed_config.agent_configs.values()`:
                    *   If agent name is not in `self.project_manager.active_project_config.agent_configs`: Calls `await self.register_agent(agent_config)`.
                *   Similar for `simple_workflow_configs` and `custom_workflow_configs`.
        *   This method ensures components are added to the existing active configuration without shutting down/restarting existing clients.

### 1.3. `src/bin/api/routes/project_api.py`
    *   **New Endpoint:** `POST /projects/create_file`
        *   Request Body: `{ "filename": "my_project.json", "project_name": "My Project", "project_description": "Optional desc" }`
        *   Dependencies: `get_host_manager` (to access `project_manager`).
        *   Action:
            *   Constructs `project_file_path = PROJECT_ROOT_DIR / "config" / "projects" / request.filename`.
            *   Calls `host_manager.project_manager.create_project_file(project_name=request.project_name, project_file_path=project_file_path, project_description=request.project_description, client_configs=[], llm_configs=[], agent_configs=[], simple_workflow_configs=[], custom_workflow_configs=[], overwrite=False)`.
            *   Returns the created project config (as JSON) or success/error.
    *   **New Endpoint:** `POST /projects/load_components`
        *   Request Body: `{ "project_config_path": "config/projects/my_project.json" }` (Path relative to `PROJECT_ROOT_DIR`).
        *   Dependencies: `get_host_manager`.
        *   Action: Calls `await host_manager.load_components_from_project(Path(request.project_config_path))`.
        *   Returns success/failure, possibly with a summary of components added/skipped/conflicted.
    *   **New Endpoint:** `GET /projects/list_files`
        *   Action: Lists all `.json` files in the `PROJECT_ROOT_DIR / "config" / "projects"` directory.
        *   Response: `List[str]` (e.g., `["project1.json", "project2.json"]`).

## 2. Frontend Implementation Steps

### 2.1. API Service Functions
*   **File:** `frontend/src/lib/apiClient.ts` (or equivalent)
*   **Add functions:**
    *   `createProjectFile(filename: string, projectName: string, projectDescription?: string): Promise<ProjectConfig | ApiError>`
    *   `loadProjectComponents(projectConfigPath: string): Promise<LoadComponentsResponse | ApiError>` (Define `LoadComponentsResponse` type, e.g., `{ success: boolean, message: string, details?: any }`)
    *   `listProjectFiles(): Promise<string[] | ApiError>`

### 2.2. State Management (Zustand - `uiStore.ts` or new `projectStore.ts`)
*   **State:**
    *   `availableProjectFiles: string[]`
    *   `isLoadingProjectFiles: boolean`
    *   `projectFileError: string | null`
*   **Actions:**
    *   `fetchAvailableProjectFiles(): Promise<void>`: Calls `listProjectFiles` API and updates state.
*   **Consideration:** After `loadProjectComponents` succeeds, the frontend stores for agents, clients, LLMs, etc. (used by `ComponentSidebar` and other views) will need to be updated. This might involve re-fetching all component lists from their respective `/configs/*` endpoints, or the `load_components` API could return a comprehensive list of all *active* components.

### 2.3. UI Components

#### 2.3.1. Create Project Modal/View
*   **Trigger:** A "Create New Project" button (e.g., in `Header.tsx` or a new project management section).
*   **Inputs:** "Project Filename" (e.g., `my_project.json`), "Project Name", "Project Description" (optional).
*   **Logic:** On submit, calls `apiClient.createProjectFile()`. Displays success/error. Refreshes `availableProjectFiles`.

#### 2.3.2. Load Project Components Modal/View
*   **Trigger:** A "Load Project Components" button/dropdown.
*   **Display:** A dropdown or selectable list populated by `availableProjectFiles`.
*   **Logic:** On selection and "Load" click, calls `apiClient.loadProjectComponents()` with the path (e.g., `config/projects/selected_file.json`). Displays success/error. Triggers a refresh of component data for UI elements like `ComponentSidebar`.

### 2.4. Integration into Main Layout
*   Place the new UI triggers (buttons/dropdowns) in an appropriate location (e.g., `Header.tsx` or a dedicated project panel).
*   Manage modal visibility and state.

## 3. Open Questions / Considerations
*   **Conflict Handling:** Define how the `load_components` API (and subsequently the frontend) communicates conflicts (e.g., component ID already exists). Should it error out, or skip and warn?
*   **UI Refresh Strategy:** Finalize how the frontend UI (especially `ComponentSidebar`) updates its lists of available agents, clients, etc., after components are additively loaded.
*   **Path Construction:** Ensure the frontend correctly constructs the `project_config_path` relative to the project root (e.g., `config/projects/my_project.json`) for API calls.
