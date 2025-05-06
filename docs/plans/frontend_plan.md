# Frontend Implementation Plan: Aurite AI Studio

**Version:** 1.0
**Date:** 2025-05-06
**Author:** Gemini (AI Assistant)

## 1. Overview

This document outlines the plan for developing the frontend UI for the Aurite Agents framework, named "Aurite AI Studio". The UI will provide developers with tools to build, configure, execute, and evaluate agentic components. Development will follow a Test-Driven Development (TDD) approach, integrating with the existing backend API and expanding its test coverage where appropriate.

## 2. Core Requirements

*   **Security:** API key authentication with session persistence.
*   **Navigation:**
    *   Consistent top navigation: Company Logo, Title "Aurite AI Studio", User Profile Icon.
    *   Main interaction model: Four primary actions (Build, Configure, Execute, Evaluate) applicable to four component types (Clients, Agents, Simple Workflows, Custom Workflows).
*   **Functionality (Phased Implementation):**
    1.  Configuration Tab: CRUD operations for component JSON configuration files.
    2.  Execution Tab: Execute registered components, including dynamic registration of new/updated configurations.
    3.  Build Tab: UI for developing agentic components (details TBD, focusing on Custom Workflows initially).
    4.  Evaluation Tab: Placeholder for intern's work.
*   **Technology Stack:** React, TypeScript, Tailwind CSS, Vite.
*   **Backend API:** Interaction with `src/bin/api/api.py` and its routers (`config_api.py`, `components_api.py`).

## 3. Proposed UI Layout for Tabs & Components

*   **Top Navigation Bar:**
    *   Left: Company Logo (placeholder), "Aurite AI Studio" Title.
    *   Right: User Profile Icon (placeholder).
*   **Main Content Area:**
    *   **Primary Action Tabs (Horizontal Navigation):** A set of tabs at the top of the main content area: "Build", "Configure", "Execute", "Evaluate". Selecting one of these tabs sets the primary action.
    *   **Component Selection Sidebar (Vertical Navigation):** A sidebar on the left (or a secondary set of horizontal tabs below the primary action tabs) allowing the user to select the component type: "Clients", "Agents", "Simple Workflows", "Custom Workflows".
    *   **Dynamic Content Pane:** The central area will render content based on the selected Action Tab and Component Type. For example:
        *   `Configure` + `Agents` -> Shows a list of agent configurations, allows CRUD.
        *   `Execute` + `Simple Workflows` -> Shows a list of simple workflows, allows selection and execution.

    *Justification:* This layout clearly separates the "action" from the "target object (component)". It's a common pattern (e.g., AWS console sections, IDE views) and should be intuitive. The primary action tabs provide a high-level context, and the component selection refines that context.

## 4. Implementation Steps (Test-Driven Development)

### Phase 1: Security & API Key Handling

**Goal:** Implement API key authentication and persistence.

1.  **Step 1.1: API Key Modal & Storage**
    *   **Frontend:**
        *   Create a modal component (`ApiKeyModal.tsx`) that prompts the user for an API key.
        *   Implement logic to store the API key securely (e.g., `localStorage` or `sessionStorage`). `sessionStorage` is preferred for developer tools as it's cleared when the tab closes, offering a slight security advantage over `localStorage` if the browser is left open.
        *   Create a global state/context (e.g., Zustand or React Context) for managing the API key and authentication status.
        *   If no valid key is stored or validated, display the modal overlaying the entire app.
    *   **API Interaction:**
        *   Create a utility function/hook to make an API call to `/status` to validate the entered API key.
        *   On successful validation, hide the modal and store the key.
        *   On failure, display an error message in the modal.
    *   **Testing (Frontend - Vitest):**
        *   Test `ApiKeyModal.tsx` rendering, input handling, and submission.
        *   Mock API calls to test success/failure scenarios and state updates.
        *   Test API key storage (in `sessionStorage`) and retrieval.
    *   **Testing (Backend - Pytest - `tests/api/test_api_integration.py`):**
        *   Existing tests `test_api_status_unauthorized` and `test_api_status_authorized` cover API key validation for the `/status` endpoint. No new backend tests are strictly needed for this frontend step if the API is stable.

2.  **Step 1.2: API Client Wrapper**
    *   **Frontend:**
        *   Create an API client wrapper/service (e.g., a set of hooks or utility functions) that automatically includes the stored API key in the `X-API-Key` header for all requests to the backend.
        *   Implement global handling for 401 Unauthorized responses: clear the stored key and re-display the `ApiKeyModal`.
    *   **Testing (Frontend - Vitest):**
        *   Test that the wrapper correctly adds the API key to headers.
        *   Test 401 error handling: API key clearing and modal re-display.

### Phase 2: Home Page Layout & Basic Structure

**Goal:** Set up the main application layout, navigation, and placeholder tabs.

1.  **Step 2.1: Main Layout Component**
    *   **Frontend:**
        *   Create `Layout.tsx` component within `frontend/src/components/layout/`.
        *   Implement the top navigation bar (`TopNavbar.tsx`):
            *   Placeholder for Company Logo.
            *   "Aurite AI Studio" title.
            *   Placeholder for User Profile Icon.
        *   Implement the primary action tabs (`ActionTabs.tsx`) (Build, Configure, Execute, Evaluate).
        *   Implement the component selection sidebar (`ComponentSidebar.tsx`) (Clients, Agents, Simple Workflows, Custom Workflows).
        *   Use a state management solution (React Context or Zustand) to manage the currently selected action and component type. The main content pane will render based on these selections.
    *   **Testing (Frontend - Vitest):**
        *   Test `Layout.tsx`, `TopNavbar.tsx`, `ActionTabs.tsx`, `ComponentSidebar.tsx` for correct rendering of all static elements.
        *   Test that selecting different actions and components updates the global state correctly.

2.  **Step 2.2: Placeholder Tab Content & Dynamic Rendering**
    *   **Frontend:**
        *   Create basic placeholder components for the content of each combination of action and component type (e.g., `ConfigureAgentsView.tsx`, `ExecuteClientsView.tsx`).
        *   These components will initially display their name or a "Feature under development" message.
        *   The main content pane in `Layout.tsx` should dynamically render the appropriate placeholder based on the selected action and component type.
    *   **Testing (Frontend - Vitest):**
        *   Test that selecting different action/component combinations renders the correct placeholder content.

### Phase 3: Configuration Tab

**Goal:** Implement CRUD functionality for JSON configuration files. This phase will focus on the "Configure" action.

1.  **Step 3.1: List Configurations**
    *   **Frontend:**
        *   Create `ConfigListView.tsx`. When the "Configure" action is selected along with a component type (e.g., Agents):
            *   Fetch the list of configuration files using the `GET /configs/{component_type}` API endpoint.
            *   Display the list of filenames (e.g., `agent1.json`, `agent2.json`).
            *   Allow selection of a configuration file from the list.
    *   **API Interaction:** Uses `GET /configs/{component_type}`.
    *   **Testing (Frontend - Vitest):**
        *   Test fetching and displaying the list of configs for each component type.
        *   Test selection of a config file.
        *   Test handling of empty lists and API errors.
    *   **Testing (Backend - Pytest - `tests/api/routes/test_config_routes.py`):**
        *   Verify `test_list_configs_success`, `test_list_configs_empty`, `test_list_configs_invalid_type`, `test_list_configs_unauthorized` are comprehensive.

2.  **Step 3.2: View/Edit Configuration**
    *   **Frontend:**
        *   Create `ConfigEditorView.tsx`. When a config file is selected in `ConfigListView.tsx`:
            *   Fetch its content using `GET /configs/{component_type}/{filename}`.
            *   Display the JSON content in a code editor component (e.g., `@monaco-editor/react` or `react-simple-code-editor`).
            *   Provide a "Save" button.
    *   **API Interaction:** Uses `GET /configs/{component_type}/{filename}`.
    *   **Testing (Frontend - Vitest):**
        *   Test fetching and displaying config content in the editor.
        *   Test editor population and basic modification.
    *   **Testing (Backend - Pytest - `tests/api/routes/test_config_routes.py`):**
        *   Verify `test_get_config_success`, `test_get_config_not_found`, `test_get_config_invalid_filename`, `test_get_config_unauthorized`.

3.  **Step 3.3: Update Configuration (Save)**
    *   **Frontend:**
        *   In `ConfigEditorView.tsx`, when "Save" is clicked:
            *   Get the modified content from the code editor.
            *   Validate that it's valid JSON.
            *   Send it to the backend using `PUT /configs/{component_type}/{filename}` with `{"content": <json_object>}` payload.
            *   Provide feedback (success/error message using a toast notification or similar).
    *   **API Interaction:** Uses `PUT /configs/{component_type}/{filename}`.
    *   **Testing (Frontend - Vitest):**
        *   Test saving modified content.
        *   Test JSON validation before sending.
        *   Test success/error feedback mechanisms.
    *   **Testing (Backend - Pytest - `tests/api/routes/test_config_routes.py`):**
        *   Verify `test_update_config_success`, `test_update_config_not_found`, `test_update_config_invalid_type`, `test_update_config_invalid_filename`, `test_update_config_invalid_content`, `test_update_config_unauthorized`.

4.  **Step 3.4: Create New Configuration**
    *   **Frontend:**
        *   In `ConfigListView.tsx` (or a dedicated creation view), provide a "Create New" button.
        *   Prompt for a filename (ensuring `.json` extension).
        *   Open `ConfigEditorView.tsx` with a blank editor or pre-fill with a basic template for the selected component type.
        *   On save, use `POST /configs/{component_type}/{filename}`.
    *   **API Interaction:** Uses `POST /configs/{component_type}/{filename}`.
    *   **Testing (Frontend - Vitest):**
        *   Test creation flow: filename input, editor state (blank/template).
        *   Test saving new configuration.
    *   **Testing (Backend - Pytest - `tests/api/routes/test_config_routes.py`):**
        *   Verify `test_upload_config_success_new_file`, `test_upload_config_success_overwrite_file` (API uses POST for create/overwrite), `test_upload_config_invalid_type`, `test_upload_config_invalid_filename`, `test_upload_config_invalid_content`, `test_upload_config_unauthorized`.

5.  **Step 3.5: Delete Configuration**
    *   **Frontend:**
        *   In `ConfigListView.tsx`, provide a "Delete" button/icon for each configuration.
        *   Confirm deletion with the user via a modal.
        *   Use `DELETE /configs/{component_type}/{filename}`.
        *   Refresh the list of configurations upon successful deletion.
    *   **API Interaction:** Uses `DELETE /configs/{component_type}/{filename}`.
    *   **Testing (Frontend - Vitest):**
        *   Test deletion flow, confirmation modal, and list refresh.
    *   **Testing (Backend - Pytest - `tests/api/routes/test_config_routes.py`):**
        *   Verify `test_delete_config_success`, `test_delete_config_not_found`, `test_delete_config_invalid_type`, `test_delete_config_invalid_filename`, `test_delete_config_unauthorized`.

6.  **Step 3.6: Modular Component Design for Configuration Management**
    *   **Frontend:**
        *   Ensure components developed for the "Configure" action (e.g., `ConfigListView.tsx`, `ConfigEditorView.tsx`) are designed to be reusable or adaptable for other actions like "Execute" or "Build" where configuration selection or viewing might be needed.
        *   For example, a `ConfigSelectorComponent` could be extracted for use in the Execute tab.
    *   **Testing (Frontend - Vitest):**
        *   Ensure refactored/modular components are independently testable and maintain their functionality when used in different contexts.

### Phase 4: Execution Tab

**Goal:** Allow users to execute registered components and dynamically register new/updated ones from the "Configure" action.

1.  **Step 4.1: List and Select Component for Execution**
    *   **Frontend:**
        *   Create `ExecuteView.tsx`. When the "Execute" action is selected:
            *   Reuse or adapt `ConfigListView.tsx` (or the `ConfigSelectorComponent` from Step 3.6) to list available configurations for the selected component type (Agents, Simple Workflows, Custom Workflows).
            *   Allow user to select a component to execute.
    *   **API Interaction:** Uses `GET /configs/{component_type}`.
    *   **Testing (Frontend - Vitest):**
        *   Test listing and selection of components for execution.

2.  **Step 4.2: Provide Execution Input**
    *   **Frontend:**
        *   In `ExecuteView.tsx`, based on the selected component, display appropriate input fields:
            *   Agent: `user_message` (textarea), `system_prompt` (optional textarea).
            *   Simple Workflow: `initial_user_message` (textarea).
            *   Custom Workflow: `initial_input` (JSON editor or a structured form if schema is known/definable).
    *   **Testing (Frontend - Vitest):**
        *   Test rendering of correct input fields per component type.
        *   Test input data handling and state management for the form.

3.  **Step 4.3: Execute Component and Display Results**
    *   **Frontend:**
        *   In `ExecuteView.tsx`, provide an "Execute" button.
        *   On click, call the relevant API endpoint from `components_api.py`:
            *   Agent: `POST /agents/{agent_name}/execute`
            *   Simple Workflow: `POST /workflows/{workflow_name}/execute`
            *   Custom Workflow: `POST /custom_workflows/{workflow_name}/execute`
        *   Display the execution result (e.g., agent's response, workflow final message/result, errors) in a designated area, perhaps using a `CodeBlock` for formatted JSON or text.
    *   **API Interaction:** Uses POST endpoints from `src/bin/api/routes/components_api.py`.
    *   **Testing (Frontend - Vitest):**
        *   Test API call construction and execution for each component type.
        *   Test display of successful results and error messages.
        *   Mock API calls for various scenarios (success, failure, different data types).
    *   **Testing (Backend - Pytest - `tests/api/routes/test_components_api.py`):**
        *   Ensure existing tests for execution endpoints (`test_execute_agent_endpoint`, `test_execute_workflow_endpoint`, `test_execute_custom_workflow_endpoint`) are robust and cover various input/output scenarios.

4.  **Step 4.4: Dynamic Registration Integration from Configuration Tab**
    *   **Frontend:**
        *   Modify the save logic in the "Configure" action (Steps 3.3, 3.4) to *also* call the corresponding registration endpoint from `components_api.py` after a successful file save (`POST` or `PUT` to `/configs/...`). This ensures the `HostManager` is immediately aware of the new/updated component without requiring an API restart.
        *   The payload for registration will be the configuration content itself.
    *   **API Interaction:**
        *   After `POST/PUT /configs/...` is successful, call:
            *   `POST /clients/register` with `ClientConfig` payload.
            *   `POST /agents/register` with `AgentConfig` payload.
            *   `POST /workflows/register` with `WorkflowConfig` payload.
            *   (Note: `CustomWorkflowConfig` registration might need a dedicated endpoint or clarification if it's handled differently by `HostManager`'s dynamic registration).
    *   **Testing (Frontend - Vitest):**
        *   Test that saving a configuration in the "Configure" action also triggers the correct registration API call with the correct payload.
    *   **Testing (Backend - Pytest - `tests/api/routes/test_components_api.py`):**
        *   Ensure `test_register_client_endpoint`, `test_register_agent_endpoint`, `test_register_workflow_endpoint` are comprehensive.
        *   Verify behavior for re-registration (idempotency or updates as per `HostManager` logic).

### Phase 5: Build Tab (Initial Placeholder & Custom Workflow Focus)

**Goal:** Set up the Build tab, initially focusing on a UI for creating Custom Workflow Python files and their configurations.

1.  **Step 5.1: Build Tab Structure**
    *   **Frontend:**
        *   Create `BuildView.tsx`. When the "Build" action is selected:
            *   Allow selection of component type to build (Agent, Client, Simple Workflow, Custom Workflow).
            *   Initially, only "Custom Workflow" will have significant functionality. Other selections can show "Feature under development."
    *   **Testing (Frontend - Vitest):**
        *   Test component type selection within the Build action and display of appropriate content/placeholders.

2.  **Step 5.2: Custom Workflow Builder UI (Basic)**
    *   **Frontend:**
        *   When "Custom Workflow" is selected in the Build action:
            *   Provide input fields for:
                *   Workflow Name (e.g., `MyCoolWorkflow`)
                *   Python Module Filename (e.g., `my_cool_workflow.py` - to be saved under `src/custom_workflows/` or a similar designated, secure directory).
                *   Python Class Name (e.g., `MyCoolWorkflowExecutor`).
            *   Include a code editor (e.g., Monaco Editor) pre-filled with a basic Custom Workflow Python class template.
            *   A "Save Workflow" button.
    *   **API Interaction (Requires New Backend Endpoints/Logic):**
        *   Saving the workflow involves multiple steps:
            1.  **Save Python Code:** A new API endpoint (e.g., `POST /code/custom_workflow`) will be needed. This endpoint must:
                *   Accept the Python code content and desired filename.
                *   Perform **strict validation** on the filename and save path to ensure files are only written to a designated, secure subdirectory within the project (e.g., `src/custom_workflows/`). **Path traversal attacks must be prevented.**
                *   Return success/failure.
            2.  **Save CustomWorkflowConfig JSON:**
                *   The frontend will construct the `CustomWorkflowConfig` JSON object using the form inputs (name, module path like `src.custom_workflows.my_cool_workflow`, class name).
                *   Use the existing `POST /configs/custom_workflows/{config_filename}.json` endpoint (this implies "custom_workflows" needs to be a recognized `component_type` in `config_api.py`'s `CONFIG_DIRS` or a new router for custom types).
            3.  **Dynamically Register Custom Workflow:**
                *   After successful code and config file saving, call a new `POST /custom_workflows/register` endpoint (similar to other component registration endpoints in `components_api.py`) with the `CustomWorkflowConfig` payload.
    *   **Testing (Frontend - Vitest):**
        *   Test form input for workflow name, module filename, class name.
        *   Test code editor functionality and content retrieval.
        *   Test "Save Workflow" logic, mocking the multi-step API calls.
    *   **Testing (Backend - Pytest):**
        *   **New Tests Needed:**
            *   For the new `POST /code/custom_workflow` endpoint: test successful file creation, **critical security tests for path validation and preventing writes outside the allowed directory**, error handling for invalid content/filenames.
            *   If "custom_workflows" is added as a `component_type` to `config_api.py`: adapt existing `test_config_routes.py` tests for this new type.
            *   For the new `POST /custom_workflows/register` endpoint in `components_api.py`: test successful registration, error handling for invalid configs or missing Python files.

### Phase 6: Evaluation Tab (Placeholder)

**Goal:** Set up a placeholder for the Evaluation tab.

1.  **Step 6.1: Evaluation Tab Placeholder**
    *   **Frontend:**
        *   Create `EvaluateView.tsx`. When the "Evaluate" action is selected:
        *   Display a message like "Evaluation features are under development and will be integrated by the intern."
    *   **Testing (Frontend - Vitest):**
        *   Test that the placeholder content renders correctly when "Evaluate" is selected.

### Phase 7: Documentation & Final Testing

**Goal:** Update documentation and ensure comprehensive test coverage.

1.  **Step 7.1: Update Layer 0 Documentation**
    *   **Docs:**
        *   Update `docs/layers/0_frontends.md` to reflect the new UI architecture, components, functionalities, and API interactions.
        *   Include screenshots of the new UI for key views.
2.  **Step 7.2: Expand Test Coverage**
    *   **Frontend (Vitest):**
        *   Review all components and views for adequate unit and integration test coverage.
        *   Aim for high coverage of UI logic, state changes, and API interaction mocking.
        *   Consider adding a few E2E tests using Playwright or Cypress for critical user flows (e.g., API key auth, creating and executing a simple agent).
    *   **Backend (Pytest):**
        *   Review all API endpoints consumed by the frontend (in `config_api.py` and `components_api.py`) and ensure robust test coverage in `tests/api/routes/`.
        *   Ensure any new API endpoints added (especially for the "Build" tab) are thoroughly tested, with a strong focus on security for file writing operations.
3.  **Step 7.3: Final UI Polish & Review**
    *   Perform a thorough review of the UI for consistency, usability, accessibility (basic checks), and responsiveness.
    *   Address any minor bugs, styling inconsistencies, or usability issues.

## 5. Assumptions & Dependencies

*   The backend API (`src/bin/api/api.py` and its routers `config_api.py`, `components_api.py`) is relatively stable for existing functionalities as documented and tested.
*   New backend API endpoints will be required for the "Build" tab (saving Python code files securely) and potentially for registering custom workflows if not covered by existing mechanisms. These will be specified and tested as part of their respective frontend implementation steps.
*   The `X-API-Key` header is the sole authentication mechanism for the backend API.
*   The existing API tests in `tests/api/` (e.g., `test_api_integration.py`, `test_config_routes.py`, `test_components_api.py`) provide a good foundation.

## 6. Next Steps

*   Await approval of this plan from Ryan.
*   Upon approval, begin implementation with Phase 1, Step 1.1: API Key Modal & Storage.
