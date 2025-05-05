# Layer 0: Frontends (Developer UI)

**Version:** 0.1
**Date:** 2025-05-05

## 1. Overview

Layer 0 provides the user-facing interface for interacting with the Aurite Agents framework, specifically tailored for developers and low/no-code users. It allows users to manage configurations, register components, execute agents/workflows, and monitor system status through a web-based UI.

This layer consists of a React frontend application built with Vite, TypeScript, and Tailwind CSS. The built static assets (HTML, CSS, JavaScript) are served by the API entrypoint (Layer 1). It interacts directly with the API endpoints provided by `src/bin/api/api.py` (and its routers in `src/bin/api/routes/`) to perform actions like configuration management, registration, and execution, effectively acting as a client to Layer 1.

The primary goal is to simplify common development and management tasks associated with the framework's agentic components, offering a more robust and maintainable UI compared to the previous static implementation.

## 2. Relevant Files

| File Path                               | Primary Class(es)/Modules | Core Responsibility                                                                 |
| :-------------------------------------- | :------------------------ | :---------------------------------------------------------------------------------- |
| `frontend/`                             | React Project             | Root directory for the Vite/React/TypeScript/Tailwind frontend application.         |
| `frontend/index.html`                   | HTML Entrypoint           | Main HTML file for the React application, includes root div and script tag.         |
| `frontend/src/main.tsx`                 | React Bootstrap           | Renders the root React component (`App`) into the DOM.                              |
| `frontend/src/App.tsx`                  | Root React Component      | Main application component, manages routing (if any), layout, and state.            |
| `frontend/src/components/`              | React Components          | Reusable UI components (e.g., tabs, forms, buttons, display areas).                 |
| `frontend/src/index.css`                | Tailwind CSS              | Main CSS file including Tailwind directives and potentially custom styles.          |
| `frontend/vite.config.ts`               | Vite Config               | Configuration for the Vite build tool (plugins, server options, build settings).    |
| `frontend/tailwind.config.js`           | Tailwind Config           | Configuration for the Tailwind CSS framework (theme, plugins).                      |
| `src/bin/api/api.py`                    | `FastAPI`, `FileResponse` | (Layer 1) Serves the built frontend static assets (`index.html`, `/assets/*`) and provides the backend API endpoints consumed by the frontend. |
| `src/bin/api/routes/`                   | `APIRouter`               | (Layer 1) Routers defining specific API endpoints (config, components).             |
| `tests/api/`                            | Pytest Tests              | (Layer 1 Tests) Contains integration tests verifying API endpoints used by the frontend. |

## 3. Functionality

Describes how the React frontend components provide the user interface and interact with the backend API.

**3.1. Multi-File Interactions & Core Flows:**

*   **Loading the UI:**
    1.  User navigates to the root URL (`/`) or any client-side route of the running API server.
    2.  `api.py` (Layer 1) serves the built `frontend/dist/index.html` using `FileResponse` via its catch-all route.
    3.  The browser parses `index.html`, which includes script tags for the bundled JavaScript (e.g., `/assets/index-<hash>.js`) and link tags for CSS (e.g., `/assets/index-<hash>.css`).
    4.  The browser requests the JS and CSS assets from the `/assets` path.
    5.  `api.py` serves these static assets via the `StaticFiles` mount point.
    6.  The JavaScript bundle executes, bootstrapping the React application via `main.tsx`.
    7.  `App.tsx` renders, potentially handling client-side routing and displaying the initial UI components.
*   **API Interaction (General Flow):**
    1.  A user interaction (e.g., button click, form submission) triggers an event handler within a React component (`frontend/src/components/`).
    2.  The event handler function likely uses a state management solution (e.g., Zustand, Context API, or local state) to manage UI state (loading indicators, form data, results).
    3.  An asynchronous function (often using `async/await`) is called to interact with the backend API. This function typically uses the `fetch` API or a library like `axios`.
    4.  The function retrieves the necessary API key (potentially stored in local storage or prompted from the user).
    5.  It constructs the appropriate request URL, method (GET, POST, PUT, DELETE), headers (`Content-Type`, `X-API-Key`), and request body (JSON payload).
    6.  The request is sent to the relevant endpoint defined in the API routers (`src/bin/api/routes/`).
    7.  The backend API (`api.py` and its routers) handles the request (authentication, validation, interaction with `HostManager`).
    8.  The backend returns a JSON response (success data or error details).
    9.  The frontend function receives the response, updates the application state (e.g., storing results, clearing loading state, setting error messages), causing the relevant React components to re-render and display the outcome to the user.

**3.2. Individual File Functionality:**

*   **`frontend/index.html`:** Minimal HTML structure, contains the root `<div>` where the React app is mounted and includes the entry point JavaScript bundle generated by Vite.
*   **`frontend/src/main.tsx`:** Initializes the React application by rendering the main `App` component into the root div defined in `index.html`. May include setup for routing or state management providers.
*   **`frontend/src/App.tsx`:** The top-level React component. Typically sets up the main layout (e.g., header, tabs/navigation), manages global state or routing, and renders child components corresponding to different sections of the UI (e.g., `RegisterTab`, `ExecuteTab`, `StatusTab`, `ConfigManagementTab`).
*   **`frontend/src/components/`:** Contains various reusable React components responsible for specific UI parts:
    *   **Tab Components (e.g., `RegisterTab.tsx`, `ExecuteTab.tsx`):** Render the forms, buttons, and display areas for each major section. Manage local form state and trigger API calls via handler functions.
    *   **UI Elements (e.g., `Button.tsx`, `Input.tsx`, `CodeEditor.tsx`):** Lower-level reusable components for consistent styling and behavior.
*   **`frontend/src/index.css`:** Includes Tailwind CSS base styles, components, and utilities. May contain custom CSS rules specific to the application.
*   **`frontend/vite.config.ts`:** Configures the Vite development server and build process (e.g., setting up React plugin, defining build output directory `dist`).
*   **`frontend/tailwind.config.js`:** Configures Tailwind CSS, defining theme customizations (colors, fonts), content paths for style purging, and plugins.
*   **`api.py` (Relevant Parts):**
    *   **Static Files:** Mounts the `frontend/dist/assets` directory to `/assets`.
    *   **Catch-all Route:** Serves `frontend/dist/index.html` for any path not matching other API routes or the `/assets` mount, enabling client-side routing in the React app.
    *   **API Routers:** Includes routers from `src/bin/api/routes/` which define the actual API endpoints consumed by the frontend.

## 4. Testing

**4.A. Testing Overview:**

*   **Execution:**
    *   **Frontend:** Unit/Integration tests run via Vitest (`pnpm test` within `frontend/`). Component behavior tested manually in the browser or potentially via E2E tests.
    *   **Backend API:** Endpoints consumed by the frontend are tested via API integration tests (`pytest -m api_integration` in the main project).
*   **Location:**
    *   Frontend Tests: `frontend/src/**/*.test.tsx` (or similar pattern).
    *   API Integration Tests: `tests/api/routes/` (for specific routers), `tests/api/test_api_integration.py` (for general app tests like health/status).
*   **Approach:** Relies on backend API tests (`pytest`) to ensure endpoint correctness and frontend tests (Vitest) to verify component logic, rendering, and state management. Manual testing bridges the gap. E2E tests (Playwright/Cypress) could be added for full user flow validation.

**4.B. Testing Infrastructure:**

*   **Frontend:**
    *   **Vite/Vitest:** Test runner and utilities for React component testing.
    *   **React Testing Library:** For querying and interacting with components in tests.
    *   **(Optional) MSW (Mock Service Worker):** To mock API requests during frontend tests.
*   **Backend:**
    *   **`pytest`:** Core testing framework.
    *   **`fastapi.testclient.TestClient`:** Used in API integration tests.
*   **(Missing):** No E2E testing framework (Playwright, Cypress) currently configured.

**4.C. Testing Coverage:**

| Functionality                      | Relevant File(s)             | Test Method(s) / Status                                                                 |
| :--------------------------------- | :--------------------------- | :-------------------------------------------------------------------------------------- |
| Component Rendering & Logic        | `frontend/src/**/*.tsx`      | Vitest Unit/Integration Tests / Status: Varies per component (Needs Implementation)     |
| State Management                   | `frontend/src/` (state logic) | Vitest Unit/Integration Tests / Status: Varies (Needs Implementation)                   |
| API Client/Fetching Logic          | `frontend/src/` (API hooks/fns) | Vitest (with MSW mocks) / Status: Varies (Needs Implementation)                         |
| API Call - Config CRUD             | `frontend/`, `config_api.py` | `tests/api/routes/test_config_routes.py` / API Tested                                   |
| API Call - Register Component      | `frontend/`, `components_api.py` | `tests/api/routes/test_components_api.py` / API Tested                                  |
| API Call - Execute Component       | `frontend/`, `components_api.py` | `tests/api/routes/test_components_api.py` / API Tested                                  |
| API Call - Health Check            | `frontend/`, `api.py`        | `tests/api/test_api_integration.py` / API Tested                                        |
| API Call - Status Check            | `frontend/`, `api.py`        | `tests/api/test_api_integration.py` / API Tested                                        |
| Static File Serving (React Build)  | `api.py`                     | Manual Browser Access / Manual/Missing (Automated)                                      |

**4.D. Remaining Testing Steps:**

*   **Frontend Unit/Integration Tests (Vitest):**
    1.  Implement tests for individual React components, verifying rendering based on props and state.
    2.  Test event handlers and state update logic within components.
    3.  Test custom hooks or utility functions used for API calls, likely mocking the `fetch` API or using MSW.
*   **E2E UI Tests (Optional but Recommended):**
    1.  Configure Playwright or Cypress.
    2.  Write tests simulating full user workflows (e.g., logging in, navigating tabs, filling a form, submitting, verifying results).
*   **API Static File Serving Test:** Add a `pytest` test in `tests/api/test_api_integration.py` to verify the catch-all route serves the `index.html` content successfully.

## 5. Next Steps (Planned Enhancements)

Based on the initial requirements, the following features are planned for this layer:

1.  **JSON Configuration Management (CRUD):**
    *   Develop UI forms/interfaces for creating, viewing, updating, and deleting agent/workflow/client configurations stored in JSON files.
    *   This will likely involve new API endpoints (Layer 1) to handle file operations and new frontend components (Layer 0) to interact with them.
2.  **Agentic Component Building UI:**
    *   Create a dedicated page/section for building Custom Workflows.
    *   Include a simple code editor pre-filled with the basic class structure.
    *   Provide UI elements (buttons, snippets) to easily inject code for calling other agents or workflows via the `ExecutionFacade`.
    *   Requires backend support (API endpoints) to save/manage these custom workflow Python files.
3.  **Dynamic Registration Integration:**
    *   Leverage the CRUD features (Step 1) to automatically trigger dynamic registration via existing API endpoints when configurations are saved/updated.
4.  **Execution Enhancements:**
    *   Improve the 'Execute' tab or create a dedicated execution interface.
    *   Potentially list available registered components dynamically.
    *   Provide clearer display of execution results and logs.
5.  **Evaluation Integration:**
    *   Integrate with Blake's prompt validation workflow (`src/prompt_validation`).
    *   Add UI elements to trigger evaluations and display results.
    *   Requires corresponding API endpoints (Layer 1) to interact with the validation workflows.

The choice between enhancing the current plain JavaScript approach or migrating to a more structured frontend framework (like React/Vue/Svelte with TypeScript/Tailwind) will be evaluated before implementing these features.
