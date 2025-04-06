# Aurite-MCP Testing Strategy - Design

**Version:** 0.1 (Draft)
**Date:** 2025-04-06

## 1. Overview

This document outlines the design for a revised testing strategy for the `aurite-mcp` project. The goal is to create a robust, maintainable, and understandable testing environment that effectively handles the asynchronous nature of the `MCPHost`, `Agent`, and MCP server interactions. This strategy aims to simplify test creation and improve confidence in the system's correctness.

This follows the recent project refactoring and cleanup efforts.

## 2. Key Design Principles

*   **Clear Separation of Concerns:** Distinguish between unit, integration, and end-to-end (e2e) tests.
*   **Modularity & Reusability:** Utilize fixtures for common setups and mocks for isolating components.
*   **Readability & Maintainability:** Structure tests and fixtures logically.
*   **Effective Async Handling:** Implement consistent patterns for managing asyncio event loops and operations within tests.
*   **Minimal Setup:** Avoid unnecessary global setup; fixtures should provide only what's needed for a specific test or module.

## 3. Proposed Structure and Components

### 3.1. Test Directory Structure (`tests/`)

```
tests/
├── agents/             # Tests specifically for Agent classes
│   ├── __init__.py
│   ├── test_agent.py       # Unit/Integration tests for Agent (using mocks)
│   └── test_agent_e2e.py   # E2E tests for Agent (real host/servers, maybe real LLM)
├── api/                # API level tests (e.g., Postman, or using TestClient)
│   └── ...
├── fixtures/           # Reusable pytest fixtures
│   ├── __init__.py
│   ├── host_fixtures.py  # Fixtures related to MCPHost setup (mock or real)
│   ├── agent_fixtures.py # Fixtures related to Agent setup
│   └── servers/          # Fixtures for setting up test MCP servers
│       ├── __init__.py
│       ├── echo_server_fixture.py # Renamed from mcp_server_fixture?
│       ├── fastmcp_server_fixture.py
│       └── weather_mcp_server.py # Example complex server
├── host/               # Tests specifically for MCPHost and its components
│   ├── __init__.py
│   └── test_exclusion.py # Example existing test
├── mocks/              # Centralized mock objects and utilities
│   ├── __init__.py
│   ├── mock_mcp_host.py
│   ├── mock_anthropic.py
│   └── mock_tool_manager.py # etc.
├── servers/            # Tests specifically for custom MCP server implementations
│   ├── __init__.py
│   └── test_planning_server.py # Example existing test
├── __init__.py
├── conftest.py         # Root conftest for project-wide hooks/fixtures
└── README.md           # Guide to running tests
```
*(Self-correction: Renamed `mcp_server_fixture.py` to `echo_server_fixture.py` for clarity, assuming it's the basic echo server)*

### 3.2. Mocks (`tests/mocks/`)

*   **Goal:** Centralize reusable mock classes or factory functions.
*   **Implementation:** Create files like `mock_mcp_host.py`, `mock_anthropic.py`, etc. These can provide pre-configured `unittest.mock.Mock` objects simulating the behavior of external dependencies or complex internal components.
*   **Usage:** Tests will import mocks from this directory instead of defining them inline.

### 3.3. Fixtures (`tests/fixtures/`)

*   **Goal:** Provide reusable setup and teardown logic for test components.
*   **`host_fixtures.py`:** Fixtures for creating `HostConfig`, potentially a mocked `MCPHost`, or even a fully initialized `MCPHost` with specific mock/real clients (scoped appropriately, e.g., `function` or `module`).
*   **`agent_fixtures.py`:** Fixtures for creating `AgentConfig` instances (minimal, with params, etc.), potentially pre-initialized `Agent` instances using host fixtures.
*   **`servers/`:** Fixtures that can start/stop actual test MCP servers (like the echo server) for integration/e2e tests. These should handle process management and cleanup.

### 3.4. `conftest.py`

*   **Goal:** Define project-wide configurations, hooks, and potentially very core, universally used fixtures.
*   **Avoid:** Heavy session-scoped fixtures like initializing a full `MCPHost`, as not all tests need it. This slows down test collection and execution.
*   **Include:**
    *   Potentially the `event_loop` fixture management (see Async Handling).
    *   Pytest hooks if needed (e.g., `pytest_sessionstart`, `pytest_sessionfinish`).
    *   Configuration for markers.
    *   Maybe simple, shared utility functions used across tests.

### 3.5. Async Handling

*   **Challenge:** Managing event loops correctly, especially with session/module-scoped fixtures that involve async setup/teardown (like starting servers or initializing the host). The `RuntimeError: Attempted to exit cancel scope...` likely stems from improper async context management across different tasks or scopes.
*   **Approach:**
    1.  **Standardize Event Loop Fixture:** Explicitly define the `pytest-asyncio` event loop scope. Using `function` scope is often safest to avoid state leakage between tests, although `module` or `session` might be necessary for expensive fixtures like `real_mcp_host`. We need to ensure fixtures clean up within the same task/loop they were created in. The `real_mcp_host` fixture likely needs careful review of its async context management (`AsyncExitStack`, `anyio` task groups if used).
    2.  **Fixture Scopes:** Be mindful of `scope` (`function`, `module`, `session`) for async fixtures. Session-scoped async fixtures can be tricky; ensure teardown logic is robust.
    3.  **`pytest-asyncio` Mode:** Ensure `pytest-asyncio` is running in `auto` mode (usually default, but check `pyproject.toml` or `pytest.ini`).
    4.  **Review `MCPHost.shutdown()`:** Ensure the `AsyncExitStack` usage within `MCPHost` and the `stdio_client` context manager correctly handle cleanup, especially when used within pytest fixtures with different scopes.

### 3.6. Test Markers (`@pytest.mark`)

*   **Goal:** Categorize tests for selective runs.
*   **Proposed Markers:**
    *   `@pytest.mark.unit`: Fast tests, isolated components, heavy mocking.
    *   `@pytest.mark.integration`: Tests interaction between components (e.g., Agent + Mock Host, Host + Mock Client).
    *   `@pytest.mark.e2e`: Tests involving real external dependencies (real MCP servers, real APIs like Anthropic).
    *   `@pytest.mark.asyncio`: Already used for async tests.
*   **Configuration:** Define markers in `pyproject.toml` or `pytest.ini` to avoid warnings.

### 3.7. `pyproject.toml` / `pytest.ini`

*   **Goal:** Configure pytest behavior.
*   **Settings:**
    *   Define markers.
    *   Set `asyncio_mode = auto`.
    *   Potentially configure test paths (`testpaths`).
    *   Set default options (e.g., `-v`).

## 4. Implementation Steps (High-Level)

1.  **Create `tests/mocks/`:** Move existing mock setups (like `mock_anthropic_client`) into reusable functions/classes here. Refactor `test_agent.py` to use them.
2.  **Create `tests/fixtures/`:** Define core fixtures for `AgentConfig`, `HostConfig`, potentially mock `MCPHost`, etc. Refactor tests to use these fixtures.
3.  **Refactor `conftest.py`:** Define the event loop scope explicitly. Move any overly broad fixtures out. Add marker definitions if not using `pyproject.toml`.
4.  **Address Async Issues:** Review the `real_mcp_host` fixture and `MCPHost.shutdown` for correct async context management, potentially adjusting the fixture scope or teardown logic.
5.  **Apply Markers:** Add `@pytest.mark.unit/integration/e2e` to existing tests.
6.  **(Optional) Configure `pyproject.toml`:** Add pytest settings.
7.  **Refactor Existing Tests:** Update `test_agent.py`, `test_agent_e2e.py`, `test_exclusion.py` to align with the new structure, fixtures, and mocks.
8.  **Fix `test_agent_e2e.py`:** Re-run and debug the e2e test using the improved infrastructure.

## 5. Next Steps

*   Review and refine this design document.
*   Once approved, create the detailed `testing_improvements_implementation_plan.md`.
