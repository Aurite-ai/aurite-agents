# Implementation Plan: Project Configuration File Editing

**Objective:** Enable the frontend to list, view, and edit project configuration files (e.g., `*.json` files in `config/projects/`) by adding "Projects" as a selectable type in the "Configure" tab.

**Key Principles:**
*   Project configuration files are handled separately from individual component definition files (clients, agents, etc.).
*   Project files define a single project object, not an array.
*   Backend API endpoints for project file manipulation will reside in `src/bin/api/routes/project_api.py`.

## Phase 1: Backend API Implementation (`src/bin/api/routes/project_api.py`)

**Target File:** `src/bin/api/routes/project_api.py`

1.  **Ensure `GET /projects/list_files` is suitable:**
    *   This endpoint should already exist and list JSON files from `config/projects/`. Verify it meets frontend needs.

2.  **New Endpoint: `GET /projects/file/{filename:path}`**
    *   **Purpose:** Retrieve the raw JSON content of a specific project file.
    *   **Path:** `/projects/file/{filename:path}`
    *   **Method:** `GET`
    *   **Response Model:** `Any` (will return a parsed JSON object).
    *   **Logic:**
        *   Accept `filename` as a path parameter.
        *   Construct `file_path = PROJECT_ROOT_DIR / "config" / "projects" / filename`.
        *   **Security Check:** Ensure `file_path` is still within `PROJECT_ROOT_DIR / "config" / "projects"`.
        *   If `file_path` does not exist or is not a file, return `HTTPException` (404).
        *   Read the file content.
        *   Attempt to `json.loads()` the content.
        *   If `json.JSONDecodeError`, return `HTTPException` (e.g., 400 or 500, "Invalid JSON format").
        *   Return the parsed JSON object.

3.  **New Endpoint: `PUT /projects/file/{filename:path}`**
    *   **Purpose:** Save/update the content of a specific project file.
    *   **Path:** `/projects/file/{filename:path}`
    *   **Method:** `PUT`
    *   **Request Body Model:**
        ```python
        from pydantic import BaseModel
        from typing import Any
        class ProjectFileContent(BaseModel):
            content: Dict[str, Any] # Project files are single JSON objects
        ```
    *   **Response Model:** Success message or the saved content.
    *   **Logic:**
        *   Accept `filename` as a path parameter and `ProjectFileContent` as the request body.
        *   Construct `file_path = PROJECT_ROOT_DIR / "config" / "projects" / filename`.
        *   **Security Check:** Ensure `file_path` is within `PROJECT_ROOT_DIR / "config" / "projects"`.
        *   The `config_body.content` is the new full JSON object for the project.
        *   **Validation (Crucial):**
            *   Attempt to validate `config_body.content` against the `ProjectConfig` Pydantic model from `src.config.config_models`. This can be done by:
                `from src.config.config_models import ProjectConfig`
                `ProjectConfig(**config_body.content)`
            *   If validation fails (Pydantic `ValidationError`), return `HTTPException` (400 or 422) with error details.
            *   This step ensures that the saved file adheres to the expected project structure.
        *   If validation succeeds, write `config_body.content` to `file_path` (overwrite, pretty-print JSON).
        *   Return a success response (e.g., `{"status": "success", "filename": filename}`).
    *   **Note on Active Project:** This endpoint only saves the file. If the edited file corresponds to the currently active project in `HostManager`, these changes will *not* be live in the running application until the project is explicitly reloaded (e.g., via `POST /projects/change` or a server restart). This is acceptable for this phase.

## Phase 2: Frontend Implementation (Guidance for Ryan)

1.  **Update Component Type Selection:**
    *   In `ConfigListView.tsx` (or the relevant component managing the type dropdown):
        *   Add "Projects" to the list of selectable component types.
        *   Assign a key (e.g., `"projects"`) that the frontend will use to determine which API endpoints to call.

2.  **Adapt API Service Functions (`frontend/src/lib/apiClient.ts`):**
    *   **`listConfigFiles(componentType: string)`:**
        *   If `componentType === "projects"`, this function should call `GET /api/projects/list_files`.
        *   Otherwise, it calls `GET /api/configs/{componentType}` as it does now.
    *   **`getConfigFileContent(componentType: string, filename: string)`:**
        *   If `componentType === "projects"`, call `GET /api/projects/file/{filename}`.
        *   Otherwise, call `GET /api/configs/{componentType}/{filename}`.
    *   **`saveConfigFileContent(componentType: string, filename: string, content: any)`:**
        *   If `componentType === "projects"`, call `PUT /api/projects/file/{filename}` with `body: { content: content }`.
        *   Otherwise, call `PUT /api/configs/{componentType}/{filename}` with `body: { content: content }`.

3.  **`ConfigEditorView.tsx`:**
    *   No major changes should be needed here initially, as it's designed to display/edit generic JSON. It will now be fed project file JSON when "Projects" is selected.

## Phase 3: Testing

1.  **Backend Testing:**
    *   Use an API client (Postman, curl) to test:
        *   `GET /projects/list_files`.
        *   `GET /projects/file/{existing_project_file.json}` - verify content.
        *   `GET /projects/file/{non_existent_file.json}` - verify 404.
        *   `PUT /projects/file/{existing_project_file.json}` with valid `ProjectConfig` JSON in the body - verify file is updated.
        *   `PUT /projects/file/{new_project_file.json}` with valid `ProjectConfig` JSON - verify file is created.
        *   `PUT /projects/file/{existing_project_file.json}` with *invalid* project structure - verify 400/422 error and file is not updated.
2.  **Frontend Testing:**
    *   Select "Projects" in the Configure tab.
    *   Verify project files from `config/projects/` are listed.
    *   Open a project file; verify its content is displayed in the editor.
    *   Edit the content (making valid structural changes) and save. Verify the file is updated on the backend.
    *   Attempt to save invalid JSON or a structure that doesn't match `ProjectConfig` - observe if the backend rejects it and the frontend handles the error.

This plan focuses on providing basic CRUD for project files via the UI, leveraging existing Pydantic models for validation on save.
