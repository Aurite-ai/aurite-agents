# Layer 0: Frontends (Developer UI)

**Version:** 0.1
**Date:** 2025-05-05

## 1. Overview

Layer 0 provides the user-facing interface for interacting with the Aurite Agents framework, specifically tailored for developers and low/no-code users. It allows users to manage configurations, register components, execute agents/workflows, and monitor system status through a web-based UI.

This layer consists of static web assets (HTML, CSS, JavaScript) served by the API entrypoint (Layer 1). It interacts directly with the API endpoints provided by `src/bin/api.py` to perform actions like registration and execution, effectively acting as a client to Layer 1.

The primary goal is to simplify common development and management tasks associated with the framework's agentic components.

## 2. Relevant Files

| File Path                               | Primary Class(es)/Modules | Core Responsibility                                                                 |
| :-------------------------------------- | :------------------------ | :---------------------------------------------------------------------------------- |
| `static/index.html`                     | HTML                      | Defines the structure, layout, forms, and elements of the web interface.            |
| `static/style.css`                      | CSS                       | Provides styling rules for the appearance and layout of the UI elements.            |
| `static/script.js`                      | JavaScript Functions      | Handles client-side logic: tab switching, API key input, form data handling, fetch API calls to backend. |
| `src/bin/api.py`                        | `FastAPI`, `FileResponse` | (Layer 1) Serves the static files (`index.html`, CSS, JS) and provides the backend API endpoints consumed by `script.js`. |
| `tests/api/test_api_integration.py`     | `TestClient`              | (Layer 1 Tests) Contains tests verifying API endpoints used by the frontend.        |
| `tests/api/main_server.postman_collection.json` | Postman Collection        | (Layer 1 Tests) Defines requests for manual testing of API endpoints used by the frontend. |

## 3. Functionality

Describes how the frontend components provide the user interface and interact with the backend.

**3.1. Multi-File Interactions & Core Flows:**

*   **Loading the UI:**
    1.  User navigates to the root URL (`/`) of the running API server.
    2.  `api.py` (Layer 1) serves `static/index.html` using `FileResponse`.
    3.  The browser parses `index.html`, which links to `static/style.css` and `static/script.js`.
    4.  The browser requests and loads the CSS and JavaScript files from the `/static` path mounted by `api.py`.
*   **Tab Navigation:**
    1.  User clicks a tab button (`.tab-btn` in `index.html`).
    2.  The `onclick` handler calls the `openTab` function in `script.js`.
    3.  `script.js` updates the `active` class on the relevant tab button and tab content (`div.tab-content`) to show the selected section and hide others. It also handles specific logic like showing/hiding the system prompt field when switching to the 'Execute' tab.
*   **Registering a Component:**
    1.  User selects component type, enters name and JSON config in the 'Register' tab (`index.html`).
    2.  User clicks the 'Register' button.
    3.  The `onclick` handler calls `registerComponent` in `script.js`.
    4.  `script.js` prompts for the API key using `getApiKey`.
    5.  `script.js` reads form values, parses the JSON configuration, and constructs the correct payload structure based on the component type.
    6.  `script.js` uses `fetch` to send a POST request to the corresponding API endpoint (e.g., `/clients/register`, `/agents/register`) provided by `api.py`, including the API key in the `X-API-Key` header.
    7.  `api.py` receives the request, validates the API key, parses the payload, calls the appropriate `HostManager.register_*` method (Layer 2).
    8.  `api.py` returns a JSON response (success or error).
    9.  `script.js` receives the response and displays the formatted JSON result or error message in the `#result` pre element (`index.html`).
*   **Executing a Component:**
    1.  User selects component type, enters name and JSON input in the 'Execute' tab (`index.html`).
    2.  User clicks the 'Execute' button.
    3.  The `onclick` handler calls `executeComponent` in `script.js`.
    4.  `script.js` prompts for the API key.
    5.  `script.js` reads form values, parses the JSON input, and constructs the correct payload and URL based on the component type (handling agent-specific system prompt logic).
    6.  `script.js` uses `fetch` to send a POST request to the corresponding API endpoint (e.g., `/agents/{name}/execute`) provided by `api.py`, including the API key.
    7.  `api.py` receives the request, validates the key, calls the appropriate `ExecutionFacade.run_*` method via `HostManager` (Layer 2).
    8.  `api.py` returns the execution result or error.
    9.  `script.js` displays the result/error in the `#result` element.
*   **Checking Status:**
    1.  User clicks the 'Check Status' button in the 'Status' tab (`index.html`).
    2.  The `onclick` handler calls `checkStatus` in `script.js`.
    3.  `script.js` makes `fetch` calls to `/health` (no auth) and `/status` (prompts for API key) endpoints in `api.py`.
    4.  `api.py` returns the status information.
    5.  `script.js` displays the results in the `#health-status` and `#system-status` divs (`index.html`).

**3.2. Individual File Functionality:**

*   **`index.html`:**
    *   **Structure:** Defines the main container, header, tab buttons, and tab content areas.
    *   **Forms:** Contains forms for registering components (type, name, JSON config) and executing components (type, name, JSON input, optional agent system prompt). Uses standard HTML form elements (`select`, `input`, `textarea`, `button`).
    *   **Display:** Includes elements (`pre#result`, `div#health-status`, `div#system-status`) to display feedback and results from the backend.
    *   **Event Handlers:** Uses `onclick` attributes on buttons to trigger JavaScript functions (`openTab`, `registerComponent`, `executeComponent`, `checkStatus`).
*   **`style.css`:**
    *   **Layout:** Uses flexbox for tabs and basic container styling. Defines max-width for the main container.
    *   **Styling:** Sets basic colors (using CSS variables), fonts, padding, margins, borders, and shadows for a clean appearance.
    *   **Responsiveness:** Includes a simple media query to stack tabs vertically on smaller screens.
    *   **States:** Defines `:hover` and `:active` styles for buttons and tabs.
*   **`script.js`:**
    *   **Tab Management (`openTab`):** Handles showing/hiding tab content and highlighting the active tab button. Includes logic to toggle the visibility of the agent-specific system prompt field.
    *   **API Interaction (`registerComponent`, `executeComponent`, `checkStatus`):**
        *   Uses `async/await` with `fetch` for making API calls.
        *   Handles API key input via `prompt()`.
        *   Parses JSON input/config from textareas, with basic `try/catch` for JSON parsing errors.
        *   Constructs appropriate request bodies and URLs based on selected component types.
        *   Sets `Content-Type` and `X-API-Key` headers.
        *   Processes responses, displaying results or error messages in the designated HTML elements. Handles non-OK HTTP responses by attempting to parse error details from the JSON body.
    *   **DOM Manipulation:** Selects elements by ID to read input values and update display areas (`getElementById`, `innerText`). Adds event listeners (`addEventListener`) for dynamic behavior (e.g., showing/hiding system prompt field on type change).
*   **`api.py` (Relevant Parts):**
    *   **Static Files:** Mounts the `static/` directory using `StaticFiles` and serves `index.html` from the root path (`/`) using `FileResponse`.
    *   **API Endpoints:** Provides the necessary HTTP endpoints (`/clients/register`, `/agents/register`, `/workflows/register`, `/agents/{agent_name}/execute`, `/workflows/{workflow_name}/execute`, `/custom_workflows/{workflow_name}/execute`, `/health`, `/status`) that are consumed by `script.js`. Handles request validation, authentication (API key), interaction with Layer 2 (`HostManager`), and response formatting.

## 4. Testing

**4.A. Testing Overview:**

*   **Execution:** Frontend testing is currently primarily **manual**. Users interact with the UI in a browser connected to a running API server. Backend API endpoints consumed by the frontend are tested via **API integration tests** (`pytest -m api_integration`) and potentially manually via the **Postman collection**.
*   **Location:**
    *   Manual UI Testing: Browser interaction.
    *   API Integration Tests: `tests/api/test_api_integration.py`
    *   Postman Collection: `tests/api/main_server.postman_collection.json`
*   **Approach:** The current approach relies heavily on the API integration tests (Layer 1) to ensure the backend endpoints function correctly. Frontend-specific logic (DOM manipulation, event handling, client-side validation in `script.js`) is not covered by automated tests.

**4.B. Testing Infrastructure:**

*   **Browser:** Used for manual testing.
*   **`fastapi.testclient.TestClient`:** Used in `tests/api/test_api_integration.py` to test the API endpoints called by the frontend.
*   **Postman:** Collection (`tests/api/main_server.postman_collection.json`) and Environment (`tests/api/main_server.postman_environment.json`) for manual API testing.
*   **(Missing):** No dedicated frontend testing framework (like Jest, Playwright, Cypress) is currently in use.

**4.C. Testing Coverage:**

| Functionality                      | Relevant File(s)             | Test Method(s) / Status                                                                 |
| :--------------------------------- | :--------------------------- | :-------------------------------------------------------------------------------------- |
| UI Rendering (HTML Structure)      | `index.html`                 | Manual Browser Inspection / Manual                                                      |
| UI Styling (CSS Application)       | `style.css`                  | Manual Browser Inspection / Manual                                                      |
| Tab Switching Logic                | `script.js` (`openTab`)      | Manual Browser Interaction / Manual/Missing                                             |
| API Key Prompting                  | `script.js` (`getApiKey`)    | Manual Browser Interaction / Manual/Missing                                             |
| Register Component Form Handling   | `script.js` (`registerComponent`) | Manual Browser Interaction / Manual/Missing (Client-side logic)                         |
| Execute Component Form Handling    | `script.js` (`executeComponent`)  | Manual Browser Interaction / Manual/Missing (Client-side logic)                         |
| Status Check Logic                 | `script.js` (`checkStatus`)    | Manual Browser Interaction / Manual/Missing (Client-side logic)                         |
| API Call - Register Client         | `script.js`, `api.py`        | `test_register_client_success`, `test_register_client_duplicate` (API Test) / API Tested |
| API Call - Register Agent          | `script.js`, `api.py`        | `test_register_agent_success`, etc. (API Test) / API Tested                             |
| API Call - Register Workflow       | `script.js`, `api.py`        | `test_register_workflow_success`, etc. (API Test) / API Tested                          |
| API Call - Execute Agent           | `script.js`, `api.py`        | `test_execute_agent_success` (API Test) / API Tested                                    |
| API Call - Execute Simple Workflow | `script.js`, `api.py`        | `test_execute_simple_workflow_success` (API Test) / API Tested                          |
| API Call - Execute Custom Workflow | `script.js`, `api.py`        | `test_execute_custom_workflow_success` (API Test) / API Tested                          |
| API Call - Health Check            | `script.js`, `api.py`        | `test_api_health_check` (API Test) / API Tested                                         |
| API Call - Status Check            | `script.js`, `api.py`        | `test_api_status_authorized` (API Test) / API Tested                                    |
| Static File Serving                | `api.py`                     | Manual Browser Access / Manual/Missing (Automated)                                      |

**4.D. Remaining Testing Steps:**

*   **JavaScript Unit Tests:**
    1.  Implement unit tests for functions in `script.js` using a framework like Jest.
    2.  Mock `fetch` calls to isolate JavaScript logic from the actual API.
    3.  Test form data parsing, payload construction, URL generation, and basic error handling within the script.
    4.  Test DOM manipulation logic (e.g., `openTab`, showing/hiding elements) using a DOM mocking library (like `jsdom` via Jest).
*   **End-to-End (E2E) UI Tests:**
    1.  Implement E2E tests using a framework like Playwright or Cypress.
    2.  Simulate user interactions: clicking tabs, filling forms, clicking buttons.
    3.  Verify UI updates (e.g., result display, tab switching).
    4.  Optionally, assert on network requests made to the backend API.
*   **API Static File Serving Test:** Add a simple `pytest` test in `tests/api/test_api_integration.py` to verify the `/` endpoint returns HTML content successfully.

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
