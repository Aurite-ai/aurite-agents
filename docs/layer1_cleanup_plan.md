# Implementation Plan: Task A - Layer 1 API Finalization & Documentation Update

**Version:** 1.1
**Date:** 2025-05-13
**Author(s):** Ryan, Gemini
**Related Design Document (Optional):** N/A (Refers to `docs/layers/1_entrypoints.md`)

## 1. Goals
*   Refactor, test, and document Layer 1 API components (`src/bin/api/`).
*   Update the CLI (`src/bin/cli.py`) to reflect any API changes.
*   Perform manual verification of CLI and Worker (`src/bin/worker.py`) functionality.
*   Update `docs/layers/1_entrypoints.md` and the root `README.md`.

## 2. Scope
*   **In Scope:**
    *   **API Router File Renaming:** Rename `src/bin/api/routes/*_api.py` to `src/bin/api/routes/*_routes.py`. Update `src/bin/api/api.py` imports accordingly.
    *   **API Code Review & Minor Refactoring:** Review `src/bin/api/api.py` and the (renamed) route files for clarity, consistency, error handling, and best practices. Implement minor refactors if needed.
    *   **API Testing (`pytest`):**
        *   Ensure existing tests in `tests/api/test_api_integration.py` and `tests/api/routes/` pass after refactoring.
        *   Augment tests in `tests/api/routes/test_config_routes.py`, `tests/api/routes/test_project_api.py`, and `tests/api/routes/test_components_api.py` for comprehensive coverage of all endpoints and scenarios.
        *   Add a `pytest` test for API static file serving (`src/bin/api/api.py`).
    *   **CLI Update & Manual Testing:**
        *   Update `src/bin/cli.py` commands to align with any changes to API endpoints or request/response structures.
        *   Implement placeholder `register` commands in `cli.py` if they are straightforward wrappers of existing API endpoints.
        *   Perform manual testing of key CLI commands against a running API server.
    *   **Worker Manual Testing:** Perform manual testing of basic Worker functionality (e.g., by triggering tasks via API/CLI and observing logs/behavior).
    *   **Documentation Update:**
        *   Update `docs/layers/1_entrypoints.md` to reflect all changes, current testing status, and manual verification outcomes.
        *   Update root `README.md` (architecture section links, config model paths, general review).
*   **Out of Scope (Optional but Recommended):**
    *   Automated `pytest` tests for `src/bin/cli.py` and `src/bin/worker.py` (will rely on manual testing for this task).
    *   Refactoring or testing of `src/bin/api/routes/evaluation_api.py`.
    *   Major refactoring of Layer 1 unless a critical issue is found.

## 3. Prerequisites (Optional)
*   Layers 2 and 3 refactoring, testing, and documentation are considered complete and stable.
*   Environment variables (e.g., `API_KEY`, `HOST_CONFIG_PATH`) are correctly set up for running the API and tests.

## 4. Implementation Steps

**Phase 1: API Router File Renaming & Initial Refactor**

1.  **Step 1.1: Rename API Router Files**
    *   **File(s):**
        *   `src/bin/api/routes/config_api.py` -> `src/bin/api/routes/config_routes.py`
        *   `src/bin/api/routes/components_api.py` -> `src/bin/api/routes/components_routes.py`
        *   `src/bin/api/routes/project_api.py` -> `src/bin/api/routes/project_routes.py`
        *   (evaluation_api.py is out of scope for renaming/refactoring)
    *   **Action:** Rename the specified files.
    *   **Verification:** Files are renamed in the filesystem.
2.  **Step 1.2: Update Imports in `src/bin/api/api.py`**
    *   **File(s):** `src/bin/api/api.py`
    *   **Action:** Update the import statements for `config_api`, `components_api`, and `project_api` to reflect their new `_routes.py` names.
    *   **Verification:** Application runs without import errors related to these routers. Existing API tests (if run at this stage) should still point to the correct logic.
3.  **Step 1.3: Review `src/bin/api/api.py`**
    *   **File(s):** `src/bin/api/api.py`
    *   **Action:** Review main API file for clarity, error handling, lifespan management, middleware, and static file serving. Identify any minor refactoring opportunities.
    *   **Verification:** Code review notes.
4.  **Step 1.4: Review Renamed API Route Files**
    *   **File(s):** `src/bin/api/routes/config_routes.py`, `src/bin/api/routes/components_routes.py`, `src/bin/api/routes/project_routes.py`
    *   **Action:** Review each route file for clarity, request/response models, dependency usage, error handling, and interaction with `HostManager`, `ComponentManager`, `ProjectManager`.
    *   **Verification:** Code review notes for each file.
5.  **Step 1.5 (If Necessary): Implement Approved Minor API Refactors**
    *   **File(s):** `src/bin/api/api.py`, and the renamed route files.
    *   **Action:** Implement any small, agreed-upon refactorings from steps 1.3-1.4.
    *   **Verification:** All existing API tests pass. Code changes improve clarity/maintainability.

**Phase 2: API Testing (`pytest`)**

1.  **Step 2.1: Update Test File Imports for Renamed Routers**
    *   **File(s):** `tests/api/routes/test_config_routes.py`, `tests/api/routes/test_components_api.py`, `tests/api/routes/test_project_api.py` (and their future renamed versions if tests are also renamed to match source).
    *   **Action:** If test files directly import from the route modules (less common for API tests using `TestClient`), update those imports. More likely, ensure test logic correctly targets the renamed API paths if paths were derived from module names. *Self-correction: TestClient targets URL paths, so direct import changes in test files are unlikely unless helper functions in tests import from routes.*
    *   **Verification:** Tests run without import errors.
2.  **Step 2.2: Enhance Tests for `config_routes.py`**
    *   **File(s):** `tests/api/routes/test_config_routes.py`
    *   **Action:** Review existing tests. Add new tests to cover all CRUD endpoints (`/configs/{component_type}/...`) for each component type, including success cases, error handling (400, 404, 409, 422), and authentication. Test with both single object and list payloads for POST/PUT where applicable.
    *   **Verification:** Comprehensive test coverage for `config_routes.py`. All tests pass.
3.  **Step 2.3: Enhance Tests for `components_routes.py`**
    *   **File(s):** `tests/api/routes/test_components_api.py`
    *   **Action:** Review existing tests. Add new tests for all registration and execution endpoints. For execution, test success and various error conditions (e.g., component not found, underlying execution error). For registration, test success, duplicates, and invalid references. Test streaming endpoint (`/agents/{agent_name}/execute-stream`) for SSE format and event sequence.
    *   **Verification:** Comprehensive test coverage for `components_routes.py`. All tests pass.
4.  **Step 2.4: Enhance Tests for `project_routes.py`**
    *   **File(s):** `tests/api/routes/test_project_api.py`
    *   **Action:** Review existing tests. Add new tests for all project management endpoints: `/active/component/...`, `/change`, `/create_file`, `/load_components`, `/list_files`, `/get_active_project_config`, `/file/{filename}` (GET and PUT). Test success and error conditions (e.g., file not found, invalid payload, auth).
    *   **Verification:** Comprehensive test coverage for `project_routes.py`. All tests pass.
5.  **Step 2.5: Implement API Static File Serving Test**
    *   **File(s):** `tests/api/test_api_integration.py` (or a dedicated test file for `api.py` specifics)
    *   **Action:** Add a `pytest` test using `TestClient` to verify that the `/` endpoint serves `index.html` from `frontend/dist/index.html` and `/assets/*` serves assets.
    *   **Verification:** Test passes and confirms static file serving.

**Phase 3: CLI Update & Manual Testing**

1.  **Step 3.1: Review and Update `src/bin/cli.py`**
    *   **File(s):** `src/bin/cli.py`
    *   **Action:** Review existing CLI commands. Update them to align with any changes made to API endpoint paths, request/response structures, or functionality during API refactoring.
    *   **Verification:** CLI commands reflect current API.
2.  **Step 3.2: Implement CLI `register` Commands (If Simple Wrappers)**
    *   **File(s):** `src/bin/cli.py`
    *   **Action:** Implement the placeholder `register client`, `register agent`, and `register workflow` commands if they are straightforward wrappers around the corresponding (and now well-tested) API registration endpoints.
    *   **Verification:** Basic `register` commands are functional.
3.  **Step 3.3: Manual CLI Testing**
    *   **File(s):** `src/bin/cli.py`
    *   **Action:** Perform manual testing of key CLI commands (execute and register) against a running API server. Verify correct output and error handling.
    *   **Verification:** Document manual test cases and outcomes.

**Phase 4: Worker Manual Testing**

1.  **Step 4.1: Manual Worker Testing**
    *   **File(s):** `src/bin/worker.py`
    *   **Action:** Perform manual testing of basic Worker functionality. This might involve:
        *   Starting the API server and the Worker.
        *   Making API calls that are expected to enqueue tasks for the Worker (e.g., certain types of registrations or asynchronous executions if implemented).
        *   Observing Worker logs for correct task processing and error handling.
        *   Checking expected outcomes (e.g., component registered, data updated in DB if applicable).
    *   **Verification:** Document manual test cases and outcomes. Confirm basic worker operation.

**Phase 5: Documentation Updates**

1.  **Step 5.1: Update `docs/layers/1_entrypoints.md`**
    *   **File(s):** `docs/layers/1_entrypoints.md`
    *   **Action:**
        *   Reflect the renaming of router files.
        *   Update descriptions of API functionality based on any refactoring.
        *   Update the "Testing" section (4.A, 4.C, 4.D) to accurately describe the current state of API testing (comprehensive `pytest`), CLI testing (manual, updated commands), and Worker testing (manual).
    *   **Verification:** Document accurately reflects Layer 1.
2.  **Step 5.2: Update Root `README.md` - Architecture Section**
    *   **File(s):** `README.md`
    *   **Action:**
        *   Enhance the "Architecture" section to clearly introduce layered documentation.
        *   Add direct links: `docs/layers/1_entrypoints.md`, `docs/layers/2_orchestration.md`, `docs/layers/3_host.md`. (Deferring `0_frontends.md` for now).
    *   **Verification:** README architecture section updated, links correct.
3.  **Step 5.3: Update Root `README.md` - Configuration Section**
    *   **File(s):** `README.md`
    *   **Action:** Correct Pydantic models path to `src/config/config_models.py`.
    *   **Verification:** Path corrected.
4.  **Step 5.4: Update Root `README.md` - General Review**
    *   **File(s):** `README.md`
    *   **Action:** Review for other outdated info (e.g., `docs/framework_overview.md`, `docs/testing_strategy.md` references - update or remove if superseded by layer docs/`tests/README.md`).
    *   **Verification:** README is accurate.

## 5. Testing Strategy
*   **API:** Primarily through `pytest` integration tests located in `tests/api/` and `tests/api/routes/`. Focus on endpoint functionality, request/response validation, error handling, and interaction with mocked/real dependencies as appropriate. Newman tests with Postman collection `tests/api/main_server.postman_collection.json` will serve as an additional E2E check.
*   **CLI:** Manual testing of commands against a running API server.
*   **Worker:** Manual testing by observing logs and behavior when tasks are enqueued via API/CLI.

## 6. Potential Risks & Mitigation (Optional)
*   **Risk:** API refactoring might break existing `pytest` or Postman tests.
    *   **Mitigation:** Run tests frequently after each significant change. Update tests promptly.
*   **Risk:** Manual testing of CLI/Worker might miss edge cases.
    *   **Mitigation:** Document manual test cases thoroughly. Prioritize testing critical paths. (Automated tests for these are deferred).

## 7. Open Questions & Discussion Points (Optional)
*   Is `docs/layers/0_frontends.md` relevant to link in the backend framework's root README? (Current plan: Defer, focus on backend layers).
*   Confirm status of `docs/framework_overview.md` and `docs/testing_strategy.md` for README update. (Current plan: Assume they might be superseded and verify).

