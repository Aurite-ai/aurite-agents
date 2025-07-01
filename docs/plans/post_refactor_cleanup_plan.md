# Implementation Plan: Post-Refactor Cleanup and Test Enhancement

**Version:** 1.0
**Date:** 2025-07-01
**Author(s):** Gemini

## 1. Goals
*   Re-implement critical functionality lost during the `ClientSessionGroup` refactor.
*   Improve the test infrastructure for the host layer to make it more maintainable and DRY.

## 2. Scope
*   **In Scope:**
    *   Modifying `src/aurite/host/host.py` to add back lost functionality.
    *   Modifying `tests/unit/host/conftest.py` to create shared fixtures.
    *   Refactoring tests in `tests/unit/host/` and `tests/integration/host/` to use the new fixtures.
*   **Out of Scope:**
    *   Changing the core `ClientSessionGroup`-based architecture.
    *   Adding new features not present in the previous implementation.

## 3. Implementation Steps

### Phase 1: Restore Lost Functionality

1.  **Step 1.1: Enhance `_get_server_params` with Environment and Secret Handling**
    *   **File(s):** `src/aurite/host/host.py`
    *   **Action:**
        *   Update the `_get_server_params` method to handle environment variable resolution for `stdio`, `local`, and `http_stream` transport types.
        *   Integrate `SecurityManager.resolve_gcp_secrets` to inject secrets into the environment for `stdio` and `local` clients.
        *   Add logic to replace placeholders (e.g., `{VAR_NAME}`) in `http_endpoint` URLs and `args` lists.
        *   Add the `DOCKER_ENV` check to replace `localhost` with `host.docker.internal` for `http_stream` clients.
    *   **Verification:**
        *   New unit tests will be added in Phase 2 to verify this functionality.

2.  **Step 1.2: Verify Component Unregistration**
    *   **File(s):** `src/aurite/host/host.py`, `src/aurite/host/resources/*.py`
    *   **Action:**
        *   Review the `ClientSessionGroup` documentation (or source if necessary) to understand its component lifecycle.
        *   For now, we will assume that when a session is closed, its components are no longer accessible through the group's properties (`.tools`, `.prompts`, etc.). We will rely on this behavior and will not add explicit unregistration calls.
    *   **Verification:**
        *   Integration tests will be written in Phase 2 to confirm that after a client is disconnected, its components are no longer present in the host's managers.

### Phase 2: Refactor Test Infrastructure

1.  **Step 2.1: Create Shared Fixtures in `conftest.py`**
    *   **File(s):** `tests/unit/host/conftest.py`
    *   **Action:**
        *   Create a `host_config_fixture` that provides a default `HostConfig` object.
        *   Create a `mock_client_session_group_fixture` that provides a mocked `ClientSessionGroup` instance with mock managers.
        *   Create a `mocker_fixture` for patching modules.
    *   **Verification:**
        *   The fixtures will be used in the following steps.

2.  **Step 2.2: Refactor Unit Tests**
    *   **File(s):** `tests/unit/host/*.py`
    *   **Action:**
        *   Update all unit tests in the `tests/unit/host/` directory to use the new shared fixtures from `conftest.py`.
        *   Remove redundant mocking and setup code from individual test files.
    *   **Verification:**
        *   All unit tests must pass after refactoring.

3.  **Step 2.3: Refactor Integration Tests**
    *   **File(s):** `tests/integration/host/test_mcp_host.py`
    *   **Action:**
        *   Update the integration tests to use the new shared fixtures.
        *   Add new integration tests to verify the functionality re-implemented in Phase 1 (e.g., secret injection, Docker environment handling).
    *   **Verification:**
        *   All integration tests must pass after refactoring and adding new tests.

## 4. Testing Strategy
*   **Unit Tests:** New unit tests will be added to cover the specific logic in `_get_server_params`.
*   **Integration Tests:** New integration tests will be added to verify the end-to-end behavior of the re-implemented features.
*   **Regression Testing:** The existing test suite will be run to ensure that the changes have not introduced any regressions.

## 5. Documentation
*   The final step of this plan is to review and update the documentation. Specifically, `docs/layers/3_host.md` will be reviewed to ensure it accurately reflects the new implementation details.
