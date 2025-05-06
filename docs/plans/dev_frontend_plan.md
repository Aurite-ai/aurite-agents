# Implementation Plan: Developer Frontend Enhancements

**Version:** 1.0
**Date:** 2025-05-05
**Status:** Proposed

## 1. Goals

*   Enhance the developer UI to support managing agentic component configurations (CRUD).
*   Enable building custom workflows directly within the UI.
*   Integrate dynamic registration based on configuration changes.
*   Improve the component execution interface.
*   Integrate prompt validation/evaluation features.
*   Migrate the frontend from plain HTML/CSS/JS to React, TypeScript, and Tailwind CSS for better scalability and maintainability.

## 2. Technology Stack

*   **Frontend Framework:** React
*   **Language:** TypeScript
*   **Styling:** Tailwind CSS
*   **Build Tool:** Vite (Recommended for fast setup and development server)
*   **API Client:** `fetch` API (built-in) or potentially `axios`.

## 3. High-Level Plan & Phasing

We will implement the features in the following phases:

1.  **Phase 1: Setup & Foundation:** Set up the React + TypeScript + Tailwind project structure and migrate the existing UI functionality (Register, Execute, Status tabs) to the new stack.
2.  **Phase 2: JSON Configuration Management (CRUD):** Implement UI components and corresponding backend API endpoints to allow users to create, read, update, and delete agent, client, and workflow configuration files (likely stored in the `config/` directory or a dedicated subdirectory).
3.  **Phase 3: Dynamic Registration Integration:** Connect the CRUD operations from Phase 2 to the existing dynamic registration API endpoints. When a configuration is created or updated via the UI, automatically trigger the relevant `/register` API call.
4.  **Phase 4: Enhanced Execution UI:** Improve the execution interface, potentially listing available components dynamically based on registered configurations.
5.  **Phase 5: Agentic Component Building UI:** Create the interface for building Custom Workflows, including a code editor and helper elements. Requires backend API for saving/managing Python files.
6.  **Phase 6: Evaluation Integration:** Add UI elements and API interactions to run prompt validation workflows and display results.

## 4. Detailed Implementation Steps

### Phase 1: Setup & Foundation (React + TS + Tailwind)

*Goal: Establish the new frontend project structure and replicate existing functionality.*

1.  **Setup Project:**
    *   Choose a location for the new frontend code (e.g., create a `frontend/` directory at the project root, or potentially replace the contents of `static/` if we integrate the build output). **Decision:** Let's create a new `frontend/` directory to keep it separate during development.
    *   Initialize a new React + TypeScript project using Vite: `npm create vite@latest frontend --template react-ts`.
    *   Install Tailwind CSS following the official guide for Vite: `npm install -D tailwindcss postcss autoprefixer && npx tailwindcss init -p`. Configure `tailwind.config.js` and `postcss.config.js`. Import Tailwind directives into `src/index.css`.
    *   Configure Vite (`vite.config.ts`) to proxy API requests to the backend FastAPI server (running on port 8000) to avoid CORS issues during development. Example proxy config:
        ```typescript
        // vite.config.ts
        import { defineConfig } from 'vite'
        import react from '@vitejs/plugin-react'

        export default defineConfig({
          plugins: [react()],
          server: {
            proxy: {
              // Proxy API requests (excluding static files)
              '/api': { // Or use a more specific path like '/agents', '/workflows', etc. if preferred
                target: 'http://localhost:8000', // Your backend server
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api/, '') // Optional: remove '/api' prefix if backend doesn't expect it
              },
              // Ensure static files served by FastAPI are still accessible if needed directly
              // '/static': {
              //   target: 'http://localhost:8000',
              //   changeOrigin: true,
              // }
            }
          }
        })
        ```
    *   **Verify Setup:** Run `npm run dev` in `frontend/` and ensure the default Vite React app loads. Check that Tailwind utility classes work.
2.  **Create Core Layout:**
    *   Design the main application layout component (`App.tsx`).
    *   Include a header component.
    *   Implement a tab navigation component similar to the existing one, managing the active tab state using React state (`useState`).
3.  **Migrate Status Tab:**
    *   Create a `StatusTab` component.
    *   Implement the "Check Status" button and display areas.
    *   Replicate the `checkStatus` fetch logic using TypeScript and React state (`useState`, `useEffect`) to store and display health/status results. Handle API key input securely (avoiding `prompt`, perhaps using a state-managed input field temporarily).
4.  **Migrate Register Tab:**
    *   Create a `RegisterTab` component.
    *   Build the form using controlled components (React state for form inputs).
    *   Replicate the `registerComponent` fetch logic, handling JSON parsing and payload construction within the component. Display results/errors using state.
5.  **Migrate Execute Tab:**
    *   Create an `ExecuteTab` component.
    *   Build the form using controlled components.
    *   Replicate the `executeComponent` fetch logic, including the conditional display of the system prompt field based on component type. Display results/errors using state.
6.  **Build & Integration:**
    *   Run `npm run build` in `frontend/`. This will generate static assets in `frontend/dist/`.
    *   Modify the FastAPI backend (`src/bin/api.py`) to serve the built React app:
        *   Mount the `frontend/dist` directory as static files.
        *   Add a catch-all route (`/{full_path:path}`) that serves `frontend/dist/index.html` to support client-side routing in React (if we add routing later). This needs to be configured carefully to avoid conflicts with existing API routes.
        *   Remove the old `static/` mounting and root route serving `static/index.html`.
    *   **Test:** Run the backend server and ensure the React UI loads and functions correctly.

### Phase 2: JSON Configuration Management (CRUD)

*Goal: Allow users to manage configuration files via the UI.*

1.  **Backend API Endpoints (New - Layer 1):**
    *   Define and implement new FastAPI endpoints for CRUD operations on configuration files (e.g., in `config/agents/`, `config/workflows/`, `config/clients/`).
    *   `GET /configs/{component_type}`: List available config files for a type (agent, workflow, client).
    *   `GET /configs/{component_type}/{filename}`: Get the content of a specific config file.
    *   `POST /configs/{component_type}`: Create a new config file with given content and filename.
    *   `PUT /configs/{component_type}/{filename}`: Update the content of an existing config file.
    *   `DELETE /configs/{component_type}/{filename}`: Delete a config file.
    *   **Security:** Ensure these endpoints are protected by the API key and perform path validation to prevent access outside designated config directories.
2.  **Frontend UI - Config Management Page:**
    *   Create a new main tab/page for "Configuration Management".
    *   Add sub-navigation (e.g., sidebar, secondary tabs) for Agents, Workflows, Clients.
3.  **Frontend UI - List View:**
    *   For each component type (Agent, Workflow, Client):
        *   Fetch the list of config files using the new `GET /configs/{component_type}` endpoint.
        *   Display the filenames in a list or table.
        *   Include buttons/links for "View/Edit", "Delete", and "Create New".
4.  **Frontend UI - Editor/Viewer Form:**
    *   Create a component to display/edit configuration content.
    *   When "View/Edit" is clicked: Fetch file content using `GET /configs/{component_type}/{filename}`. Display content in a textarea or potentially a JSON editor component (e.g., `react-json-editor-ajrm`).
    *   When "Create New" is clicked: Show an empty editor form, prompting for a filename.
    *   Implement "Save" functionality: Use `POST` (for new) or `PUT` (for existing) endpoints to send the filename and content to the backend.
    *   Implement "Delete" functionality: Use the `DELETE` endpoint. Provide confirmation dialog.
5.  **State Management:** Use React state and context or a dedicated state management library (like Zustand or Redux Toolkit) to manage the list of files and the content of the currently edited file.

*(Detailed steps for Phases 3-6 will be added as we approach them.)*

## 5. Backend API Changes Required

*   **Phase 1:** Modify static file serving in `src/bin/api.py` to serve the built React app from `frontend/dist/` instead of `static/`. Add a catch-all route for client-side routing.
*   **Phase 2:** Implement new CRUD API endpoints in `src/bin/api.py` for managing configuration files. This will involve file system operations (reading, writing, deleting JSON files within specific `config/` subdirectories) and careful path validation/security checks.
*   **Phase 3:** No new endpoints, but ensure CRUD endpoints (Phase 2) correctly trigger existing `/register/*` endpoints after successful file saves.
*   **Phase 4:** Potentially new endpoints to list dynamically registered components (querying `HostManager` state).
*   **Phase 5:** New endpoints to save/manage Python files for custom workflows. Security considerations are paramount here.
*   **Phase 6:** New endpoints to trigger prompt validation workflows and retrieve results.

## 6. Anticipated Issues & Risks

*   **Frontend Complexity:** Managing state in React can become complex. Choosing the right state management approach early is important. Integrating a code editor component might have challenges.
*   **Backend File Operations:** Implementing secure file CRUD operations on the backend requires careful validation to prevent security vulnerabilities (e.g., path traversal). Error handling for file system issues is crucial.
*   **Build/Deployment:** Integrating the frontend build process (`npm run build`) into the overall project workflow or deployment process needs consideration.
*   **API Design:** Designing robust and secure API endpoints for file management and custom code saving needs careful thought.
*   **Testing:** Lack of existing frontend tests means initial migration carries risk. Implementing frontend tests (unit, E2E) early in the process is recommended.
*   **Learning Curve:** Team familiarity with React/TS/Tailwind might impact initial development speed.

## 7. Next Steps

1.  Review and confirm this implementation plan.
2.  Begin **Phase 1, Step 1:** Set up the React + TypeScript + Tailwind project in the `frontend/` directory.
