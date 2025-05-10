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

### 2.1. Define Core TypeScript Types
*   **File:** `frontend/src/types/projectManagement.ts` (New file)
*   **Action:** Create this file and define the following interfaces based on `src/config/config_models.py` and API responses.

    ```typescript
    // frontend/src/types/projectManagement.ts

    // Based on src/config/config_models.py
    export interface GCPSecretConfig {
      secret_id: string;
      env_var_name: string;
    }

    export interface RootConfig {
      uri: string;
      name: string;
      capabilities: string[];
    }

    export interface ClientConfig {
      client_id: string;
      server_path: string; // In Python it's Path, in JSON/TS it will be string
      roots: RootConfig[];
      capabilities: string[];
      timeout?: number;
      routing_weight?: number;
      exclude?: string[];
      gcp_secrets?: GCPSecretConfig[];
    }

    export interface LLMConfig {
      llm_id: string;
      provider?: string;
      model_name?: string;
      temperature?: number;
      max_tokens?: number;
      default_system_prompt?: string;
      // Allow additional provider-specific fields
      [key: string]: any;
    }

    export interface AgentConfig {
      name?: string;
      client_ids?: string[];
      llm_config_id?: string;
      system_prompt?: string;
      config_validation_schema?: Record<string, any>;
      model?: string;
      temperature?: number;
      max_tokens?: number;
      max_iterations?: number;
      include_history?: boolean;
      exclude_components?: string[];
      evaluation?: string;
    }

    export interface WorkflowConfig { // For Simple Workflows
      name: string;
      steps: string[];
      description?: string;
    }

    export interface CustomWorkflowConfig {
      name: string;
      module_path: string; // In Python it's Path, in JSON/TS it will be string
      class_name: string;
      description?: string;
    }

    export interface ProjectConfig {
      name: string;
      description?: string;
      clients: Record<string, ClientConfig>;
      llm_configs: Record<string, LLMConfig>;
      agent_configs: Record<string, AgentConfig>;
      simple_workflow_configs: Record<string, WorkflowConfig>;
      custom_workflow_configs: Record<string, CustomWorkflowConfig>;
    }

    // For API responses
    export interface LoadComponentsResponse {
      success: boolean;
      message: string;
      details?: any; // Could be refined if backend provides specific details structure
    }

    export interface ApiError {
      message: string;
      status?: number;
      details?: any;
    }
    ```

### 2.2. API Service Functions
*   **File:** `frontend/src/lib/apiClient.ts`
*   **Action:** Add the following functions, utilizing the generic `apiClient` and the types defined above.

    ```typescript
    // Add to frontend/src/lib/apiClient.ts
    import type { ProjectConfig, LoadComponentsResponse, ApiError } from '../types/projectManagement'; // Adjust path

    // ... (existing apiClient code)

    export async function createProjectFile(
      filename: string,
      projectName: string,
      projectDescription?: string
    ): Promise<ProjectConfig> { // Assuming backend returns the full ProjectConfig on success
      const response = await apiClient('/projects/create_file', {
        method: 'POST',
        body: { filename, project_name: projectName, project_description: projectDescription },
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: response.statusText }));
        throw { message: errorData.detail || errorData.message || 'Failed to create project file', status: response.status, details: errorData } as ApiError;
      }
      return response.json() as Promise<ProjectConfig>;
    }

    export async function loadProjectComponents(
      projectConfigPath: string
    ): Promise<LoadComponentsResponse> {
      const response = await apiClient('/projects/load_components', {
        method: 'POST',
        body: { project_config_path: projectConfigPath },
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: response.statusText }));
        throw { message: errorData.detail || errorData.message || 'Failed to load project components', status: response.status, details: errorData } as ApiError;
      }
      return response.json() as Promise<LoadComponentsResponse>;
    }

    export async function listProjectFiles(): Promise<string[]> {
      const response = await apiClient('/projects/list_files', {
        method: 'GET',
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: response.statusText }));
        throw { message: errorData.detail || errorData.message || 'Failed to list project files', status: response.status, details: errorData } as ApiError;
      }
      return response.json() as Promise<string[]>;
    }
    ```

### 2.3. State Management (New Store)
*   **File:** `frontend/src/store/projectStore.ts` (New file)
*   **Action:** Create a new Zustand store for project management.

    ```typescript
    // frontend/src/store/projectStore.ts
    import { create } from 'zustand';
    import { listProjectFiles } from '../lib/apiClient'; // Adjust path
    import type { ApiError } from '../types/projectManagement'; // Adjust path

    interface ProjectState {
      availableProjectFiles: string[];
      isLoadingProjectFiles: boolean;
      projectFileError: ApiError | null;
      lastComponentsUpdateTimestamp: number | null; // For triggering UI refresh
      fetchAvailableProjectFiles: () => Promise<void>;
      notifyComponentsUpdated: () => void; // Action to update timestamp
    }

    const useProjectStore = create<ProjectState>((set) => ({
      availableProjectFiles: [],
      isLoadingProjectFiles: false,
      projectFileError: null,
      lastComponentsUpdateTimestamp: null,
      fetchAvailableProjectFiles: async () => {
        set({ isLoadingProjectFiles: true, projectFileError: null });
        try {
          const files = await listProjectFiles();
          set({ availableProjectFiles: files, isLoadingProjectFiles: false });
        } catch (error) {
          set({ projectFileError: error as ApiError, isLoadingProjectFiles: false });
          console.error("Failed to fetch project files:", error);
        }
      },
      notifyComponentsUpdated: () => {
        set({ lastComponentsUpdateTimestamp: Date.now() });
      }
    }));

    export default useProjectStore;
    ```

### 2.4. UI Components

#### 2.4.1. Create Project Modal
*   **File:** `frontend/src/components/projects/CreateProjectModal.tsx` (New file in a new `frontend/src/components/projects/` sub-directory)
*   **Trigger:** A "Create New Project" button in `Header.tsx`.
*   **Inputs:** "Project Filename" (e.g., `my_project.json`), "Project Name", "Project Description" (optional).
*   **Logic:**
    *   Uses local state for form inputs, loading, and error messages.
    *   On submit, calls `apiClient.createProjectFile()`.
    *   On success: Shows a success message, calls `projectStore.getState().fetchAvailableProjectFiles()` to refresh the list, and closes the modal.
    *   On error: Displays an error message.
*   **Styling:** Use Tailwind CSS consistent with the existing UI.

#### 2.4.2. Load Project Components Section/Modal
*   **File:** `frontend/src/components/projects/LoadProjectDropdown.tsx` (New file, designed as a dropdown menu in the header)
*   **Trigger:** A "Load Project" dropdown button in `Header.tsx`.
*   **Display:**
    *   A dropdown list populated by `projectStore.availableProjectFiles`.
    *   Each item, when clicked, initiates the load.
*   **Logic:**
    *   Fetches `availableProjectFiles` from `projectStore` on mount (or when dropdown is opened).
    *   Uses local state for loading and error/success messages related to the load operation.
    *   On selection and "Load" click (or direct click on item):
        *   Calls `apiClient.loadProjectComponents()` with the path (e.g., `config/projects/selected_file.json`).
        *   On success: Shows a success message, calls `projectStore.getState().notifyComponentsUpdated()` to trigger UI refresh.
        *   On error: Displays an error message.

### 2.5. Integration into Main Layout
*   **File:** `frontend/src/components/layout/Header.tsx`.
*   **Action:**
    *   Add a "Create Project" button that opens the `CreateProjectModal`.
    *   Add a "Load Project" dropdown button that uses/opens `LoadProjectDropdown.tsx`.
    *   Manage modal visibility for `CreateProjectModal` (e.g., using local state in `Header.tsx`).

### 2.6. UI Refresh Strategy (Post Load Project Components)
*   After `loadProjectComponents` succeeds and new components are added to the backend's active configuration, the frontend UI (especially `ComponentSidebar` and views like `ConfigListView`) must update.
*   **Implementation:**
    *   The `projectStore.ts` includes a `lastComponentsUpdateTimestamp: number | null` state and a `notifyComponentsUpdated()` action that sets this timestamp to `Date.now()`.
    *   The `LoadProjectDropdown.tsx` component (or the part of `Header.tsx` that handles loading) will call `projectStore.getState().notifyComponentsUpdated()` after a successful `loadProjectComponents()` API call.
    *   UI components responsible for displaying lists of components (e.g., `ConfigListView`, and potentially other views like `ExecuteView` or parts of `ComponentSidebar` if they directly fetch data) will subscribe to `projectStore` and use `useEffect` to listen for changes to this `lastComponentsUpdateTimestamp`.
    *   When `lastComponentsUpdateTimestamp` changes, these components will re-fetch their respective component data (e.g., agent lists, client lists, LLM lists, workflow lists) from the backend API endpoints (e.g., `/configs/agents`, `/configs/clients`, etc.).
    *   This ensures that all relevant parts of the UI refresh their data.

### 2.7. Path Construction
*   Ensure the frontend correctly constructs the `project_config_path` relative to the project root (e.g., `config/projects/my_project.json`) when calling `loadProjectComponents`. The backend expects paths relative to `PROJECT_ROOT_DIR`. The `apiClient` prepends `/api`, so the path passed to `loadProjectComponents` from the frontend function should be like `config/projects/my_project.json`.

## 3. Addressing Original Open Questions
*   **Conflict Handling:** The frontend will display errors returned by the API. If the `load_components` API returns specific conflict details (e.g., in `errorData.details` or `LoadComponentsResponse.details`), these can be shown to the user. The primary mechanism is the success/failure message from the API.
*   **UI Refresh Strategy:** Addressed in detail in section 2.6.
*   **Path Construction:** Addressed in detail in section 2.7.
