# Implementation Plan: Test Suite Reconstruction

**Version:** 1.0
**Date:** 2025-07-01
**Author(s):** Ryan, Gemini
**Related Design Document:** `tests/README.md`

## 1. Goals
*   Rebuild the test suite for the Aurite Agents framework from the ground up, following the principles of flexible, behavior-driven testing.
*   Establish a clear, maintainable structure for unit, integration, and e2e tests.
*   Ensure adequate test coverage for all three layers of the framework: Host, Orchestration, and Entrypoints.

## 2. Scope
*   **In Scope:**
    *   Creation of new unit and integration tests for all core framework components.
    *   Development of a new, resilient set of fixtures and mocks.
    *   Adherence to the testing strategy outlined in `tests/README.md`.
*   **Out of Scope:**
    *   End-to-end (e2e) tests will be deferred until the unit and integration test foundation is complete.
    *   Tests for non-core or experimental features.

## 3. Implementation Steps

The test suite will be rebuilt layer by layer, starting from the lowest level (Layer 3) and moving up. This ensures that foundational components are tested before the components that depend on them.

### Phase 1: Layer 3 - Host (`-m host`)

This phase focuses on testing the `MCPHost` and its internal managers.

1.  **Step 1.1: Unit Tests for Host Managers**
    *   **Files:**
        *   `tests/unit/host/test_client_manager.py`
        *   `tests/unit/host/test_tool_manager.py`
        *   `tests/unit/host/test_resource_manager.py`
        *   ... (and other managers)
    *   **Action:**
        *   For each manager, create unit tests that verify its specific responsibilities in isolation.
        *   Define mocks and fixtures *locally* within each test file first.
        *   **Iterative Refactoring:** As common patterns emerge (e.g., mocking an `MCPClient`), refactor the local mocks into shared fixtures in `tests/unit/host/conftest.py`.
    *   **Verification:** All unit tests for the manager pass.

2.  **Step 1.2: Integration Tests for `MCPHost`**
    *   **File:** `tests/integration/host/test_mcp_host.py`
    *   **Action:**
        *   Create integration tests that verify the public contract of `MCPHost`.
        *   These tests will use the real manager classes but will mock the external `MCPClient` dependency.
        *   Focus on behavior: registering servers, discovering tools, executing tools, and filtering.
    *   **Verification:** All integration tests for `MCPHost` pass.

### Phase 2: Layer 2 - Orchestration (`-m orchestration`)

This phase focuses on testing the `ExecutionFacade`, `Agent`, and `Workflow` components.

1.  **Step 2.1: Unit Tests for `Agent`**
    *   **File:** `tests/unit/orchestration/test_agent.py`
    *   **Action:**
        *   Create unit tests for the `Agent` class's logic, particularly the new configuration resolution.
        *   Mock its dependencies, including the `LiteLLMClient` and `MCPHost`. A `mock_mcp_host` can be created in `tests/unit/orchestration/conftest.py`.
    *   **Verification:** All unit tests for the `Agent` pass.

2.  **Step 2.2: Unit Tests for `ExecutionFacade`**
    *   **File:** `tests/unit/orchestration/test_facade.py`
    *   **Action:**
        *   Create unit tests for the `ExecutionFacade`'s logic of gathering configurations and preparing agent runs.
        *   Mock its dependencies (`Agent`, `HostManager`, etc.).
    *   **Verification:** All unit tests for the `ExecutionFacade` pass.

3.  **Step 2.3: Integration Tests for Orchestration**
    *   **File:** `tests/integration/orchestration/test_agent_execution.py`
    *   **Action:**
        *   Create integration tests that verify the flow from `ExecutionFacade` to `Agent`.
        *   Use a real `Agent` and `ExecutionFacade`, but a mocked `MCPHost` and `LiteLLMClient`.
        *   Verify that a call to `facade.run_agent()` results in the correct calls to the underlying mocked clients.
    *   **Verification:** All orchestration integration tests pass.

### Phase 3: Layer 1 - Entrypoints (`-m entrypoints`)

This phase focuses on testing the API, CLI, and other entrypoints.

1.  **Step 3.1: Integration Tests for API Endpoints**
    *   **Files:** `tests/integration/entrypoints/test_api_*.py`
    *   **Action:**
        *   Using a test client (like `httpx`), send requests to the API endpoints.
        *   Mock the entire `ExecutionFacade` to isolate the API layer from the core logic.
        *   Assert that the API returns the correct status codes and that the `ExecutionFacade` methods are called with the expected arguments.
    *   **Verification:** All API integration tests pass.

## 4. Final Documentation Review

*   **Action:** Upon completion of all phases, review `.clinerules/documentation_guide.md` to identify any documents that require updates based on the new test suite structure or any code changes made during testing.
*   **Verification:** All relevant documentation is updated and accurate.
