# Aurite-MCP Testing Environment

This directory contains the automated tests for the `aurite-mcp` project. The testing strategy aims for clarity, reusability, and effective handling of asynchronous components.

## Running Tests

Tests are run using `pytest`. Ensure you have installed the development dependencies (including `pytest` and `pytest-asyncio`). Run tests from the root `aurite-mcp` directory:

```bash
# Run all tests
python -m pytest

# Run only unit tests (fast, mocked dependencies)
python -m pytest -m unit

# Run only integration tests (component interactions, may use mocked clients/servers)
python -m pytest -m integration

# Run only end-to-end tests (require real dependencies like APIs, running servers)
# Note: Ensure necessary environment variables (e.g., ANTHROPIC_API_KEY) are set
python -m pytest -m e2e

# Run a specific file or test function
python -m pytest tests/agents/test_agent.py
python -m pytest tests/agents/test_agent.py::TestAgent::test_agent_initialization_minimal
```

Add `-v` for verbose output. Configuration options (markers, asyncio mode, etc.) are set in `pyproject.toml`.

## Directory Structure

*   **`agents/`**: Contains tests specifically for the `Agent` class and specific agent implementations.
    *   `test_agent.py`: Unit and integration tests for the base `Agent` class using mocks. Marked `@pytest.mark.unit`.
    *   `test_agent_e2e.py`: End-to-end tests for the base `Agent` class involving real host/servers. Marked `@pytest.mark.e2e`.
    *   `test_planning_agent.py`: Unit tests for the `PlanningAgent`. Marked `@pytest.mark.unit`.
    *   `test_planning_agent_e2e.py`: E2E tests for the `PlanningAgent`. Marked `@pytest.mark.e2e`.
*   **`api/`**: Contains API-level tests (e.g., Postman collections, potentially FastAPI `TestClient` tests later).
*   **`fixtures/`**: Contains reusable `pytest` fixtures.
    *   `agent_fixtures.py`: Fixtures for creating `AgentConfig` objects.
    *   `host_fixtures.py`: Fixtures for creating `HostConfig`, mock `MCPHost`, and the `real_mcp_host` (which initializes a host with a real server process).
    *   `servers/`: Fixtures and runnable scripts for test MCP servers (e.g., `echo_server_fixture.py`, `weather_mcp_server.py`).
*   **`host/`**: Contains tests specifically for the `MCPHost` class and its direct components.
    *   `test_exclusion.py`: Tests for component exclusion logic. Marked `@pytest.mark.integration`.
    *   `test_host_basic.py`: Basic initialization tests. Marked `@pytest.mark.integration`.
    *   `test_host_basic_e2e.py`: Basic E2E state/communication tests. Marked `@pytest.mark.e2e`.
*   **`mocks/`**: Contains reusable mock objects and factory functions (e.g., `mock_anthropic.py`). Tests import mocks from here instead of defining them inline.
*   **`servers/`**: Contains tests specifically for the custom MCP server implementations (both fixtures in `tests/fixtures/servers/` and actual servers in `src/servers/`).
    *   `test_generic_mcp_server.py`: Unit tests for generic MCP handler contracts. Marked `@pytest.mark.unit`.
    *   `test_generic_mcp_server_e2e.py`: E2E tests verifying basic responses from configured test servers. Marked `@pytest.mark.e2e`.
    *   `test_weather_mcp_server.py`: Unit tests for the weather server fixture logic. Marked `@pytest.mark.unit`.
    *   `test_weather_mcp_server_e2e.py`: E2E tests for the weather server fixture via the host. Marked `@pytest.mark.e2e`.
    *   *(Add tests for other servers like planning_server here as needed)*
*   **`conftest.py`**: The root configuration file for pytest. It defines global hooks (like `pytest_configure`), registers custom markers (`unit`, `integration`, `e2e`), and defines the core `event_loop` fixture. Fixtures defined in the `fixtures/` subdirectories are imported here to make them discoverable by pytest across all test files.
*   **`functional_mcp_client.py`**: (If applicable) Utility scripts for functional testing.

## Configuration for Tests

*   **`config/agents/testing_config.json`**: A dedicated JSON configuration file used by fixtures (like `real_mcp_host`) to define the `HostConfig` for integration/e2e tests. This allows testing the host's configuration loading mechanism using test-specific server fixtures (e.g., pointing `server_path` to scripts in `tests/fixtures/servers/`). The loading logic is handled by `src.config.load_host_config_from_json`.

## Async Handling & Known Issues

*   Tests involving asynchronous operations use `pytest-asyncio` (configured in `pyproject.toml` with `asyncio_mode = auto`).
*   The `event_loop` fixture is defined in `conftest.py` with `function` scope for safety against state leakage.
*   **Known Issue:** The `real_mcp_host` fixture (defined in `tests/fixtures/host_fixtures.py`) currently causes a `RuntimeError: Attempted to exit cancel scope...` during teardown when running e2e tests. This seems related to the interaction between `MCPHost.shutdown()` (specifically `AsyncExitStack.aclose()`), the `stdio_client` context manager, and the pytest/asyncio task management. Tests using this fixture (like `test_agent_e2e_basic_execution_real_llm`) are marked with `@pytest.mark.xfail` until this teardown issue is resolved.
