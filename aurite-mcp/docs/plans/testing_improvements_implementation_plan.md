# Testing Improvements - Implementation Plan

**Version:** 0.1 (Draft)
**Date:** 2025-04-06
**Related Design:** `testing_strategy.md`

## 1. Overview

This document details the technical steps to implement the revised testing strategy outlined in `testing_strategy.md`. The goal is to refactor the test suite for better organization, reusability, maintainability, and robust handling of asynchronous operations.

## 2. Technical Implementation Steps

**Step 1: Centralize Mocks (`tests/mocks/`)**

*   **1.1.** Create directory `aurite-mcp/tests/mocks/`. Create `__init__.py`.
*   **1.2.** Create `tests/mocks/mock_anthropic.py`. Define a function `get_mock_anthropic_client()` that returns a configured `unittest.mock.Mock` simulating the `anthropic.Anthropic` client and its `messages.create` method (similar to the logic currently in fixtures). Include variations for simple text responses and tool use responses if needed.
*   **1.3.** Refactor `tests/agents/test_agent.py`: Remove the `mock_anthropic_client` fixture. Import `get_mock_anthropic_client` and use `patch('src.agents.agent.anthropic.Anthropic', return_value=get_mock_anthropic_client())` within relevant tests or test-scoped fixtures. Adjust mock setup within tests (like `test_execute_tool_call_flow`) to configure the returned mock from `get_mock_anthropic_client` as needed (e.g., setting `side_effect`).
*   **1.4.** *(Deferred)* Consider creating `mock_mcp_host.py`, `mock_tool_manager.py` etc., in `tests/mocks/` as needed and refactoring tests to use them.

**Step 2: Centralize Fixtures (`tests/fixtures/`)**

*   **2.1.** Create directory `aurite-mcp/tests/fixtures/`. Create `__init__.py`.
*   **2.2.** Create `tests/fixtures/agent_fixtures.py`. Move `minimal_agent_config`, `agent_config_with_llm_params`, `agent_config_with_mock_host` fixtures from `tests/agents/test_agent.py` into this file. Import necessary models.
*   **2.3.** Create `tests/fixtures/host_fixtures.py`. Move `mock_host_config`, `mock_mcp_host` fixtures from `tests/agents/test_agent.py` into this file. Import necessary models and mocks.
*   **2.4.** Ensure `tests/fixtures/servers/` exists and contains the server fixture files (`echo_server_fixture.py`, `fastmcp_server_fixture.py`, `weather_mcp_server.py`). Ensure `__init__.py` exists. *(Self-correction: User confirmed these exist)*.
*   **2.5.** Update `tests/agents/test_agent.py` and `tests/agents/test_agent_e2e.py` to remove the moved fixture definitions (pytest will discover them automatically). Add necessary imports if fixtures rely on types defined elsewhere.

**Step 3: Refactor `conftest.py`**

*   **3.1.** Edit `aurite-mcp/tests/conftest.py`.
*   **3.2.** Implement `pytest_configure(config)` hook to register markers (`unit`, `integration`, `e2e`) using `config.addinivalue_line`.
*   **3.3.** Define the session-scoped `event_loop` fixture explicitly as discussed in the design doc.
*   **3.4.** Remove any existing broad fixtures if they were moved or are no longer needed at the root level.

**Step 4: Refactor Config Loading**

*   **4.1.** Edit `aurite-mcp/src/config.py`.
*   **4.2.** Add imports: `json`, `Path`, `HostConfig`, `ClientConfig`, `RootConfig`, `ValidationError` from Pydantic.
*   **4.3.** Define `load_host_config_from_json(config_path: Path) -> HostConfig`.
*   **4.4.** Implement the function by moving the JSON loading, path resolution (relative to project root - `Path(__file__).parent.parent` from within `src/config.py`), and Pydantic model instantiation logic from `src/main.py::lifespan`. Include error handling.
*   **4.5.** Edit `src/main.py`. Import `load_host_config_from_json` from `src.config`.
*   **4.6.** Modify the `lifespan` function in `main.py` to call `load_host_config_from_json(server_config.HOST_CONFIG_PATH)`.

**Step 5: Update Fixtures to Use JSON Config**

*   **5.1.** Create `aurite-mcp/config/agents/testing_config.json`. Define a minimal host configuration using the echo server fixture path:
    ```json
    {
      "agents": [
        {
          "client_id": "echo_server_test",
          "server_path": "tests/fixtures/servers/echo_server_fixture.py",
          "capabilities": ["tools"],
          "timeout": 10.0
        }
      ]
    }
    ```
    *(Note: Ensure `echo_server_fixture.py` exists at this path)*
*   **5.2.** Move the `real_mcp_host` fixture from `test_agent_e2e.py` to `tests/fixtures/host_fixtures.py`.
*   **5.3.** Modify the `real_mcp_host` fixture:
    *   Import `load_host_config_from_json` and `Path`.
    *   Define the path to `config/agents/testing_config.json` relative to the project root.
    *   Call `load_host_config_from_json` to get the `host_config`.
    *   Initialize `MCPHost` using this loaded config.

**Step 6: Apply Test Markers**

*   **6.1.** Edit `tests/agents/test_agent.py`. Add `@pytest.mark.unit` decorator to the `TestAgent` class.
*   **6.2.** Edit `tests/agents/test_agent_e2e.py`. Ensure `@pytest.mark.e2e` is on the `TestAgentE2E` class.
*   **6.3.** Edit `tests/host/test_exclusion.py`. Add `@pytest.mark.integration` decorator to the test class/functions (as it likely involves host-client interaction, even if mocked).

**Step 7: Configure `pyproject.toml` (Optional but Recommended)**

*   **7.1.** Edit `aurite-mcp/pyproject.toml`.
*   **7.2.** Add/Update the `[tool.pytest.ini_options]` section.
*   **7.3.** Define markers: `markers = ["unit: marks tests as unit tests", "integration: marks tests as integration tests", "e2e: marks tests as end-to-end tests"]`.
*   **7.4.** Set asyncio mode: `asyncio_mode = auto`.
*   **7.5.** Define test paths: `testpaths = ["tests"]`.

**Step 8: Refactor Existing Tests (Verification)**

*   **8.1.** Review `tests/agents/test_agent.py`, `tests/agents/test_agent_e2e.py`, `tests/host/test_exclusion.py`.
*   **8.2.** Ensure all imports are correct after moving mocks and fixtures.
*   **8.3.** Confirm tests are correctly using the discovered fixtures without defining them locally. Run tests selectively by marker (`pytest -m unit`, `pytest -m integration`, `pytest -m e2e`) to verify structure.

**Step 9: Address Async Issues & Fix E2E Test (`test_agent_e2e.py`)**

*   **9.1.** Run the specific e2e test again: `cd aurite-mcp && python -m pytest -v -m e2e tests/agents/test_agent_e2e.py::TestAgentE2E::test_agent_e2e_basic_execution_real_llm`.
*   **9.2.** If the `RuntimeError: Attempted to exit cancel scope...` persists, investigate the `real_mcp_host` fixture's teardown (`host.shutdown()`) and its interaction with the `module` scope and the event loop defined in `conftest.py`.
*   **9.3.** *Troubleshooting:* As a temporary measure, change `real_mcp_host` scope to `function` and re-run. If this fixes the error, it confirms an issue with async teardown across the module scope. A more permanent fix might involve adjusting how `AsyncExitStack` is used or ensuring teardown happens explicitly within the same loop/task context.

## 3. Next Steps

*   Begin implementation starting with Step 1.
