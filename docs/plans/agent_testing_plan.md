# Agent Usage API - Testing Plan

**Version:** 1.0
**Date:** 2025-04-07

**Goal:** Verify the implementation of JSON-defined agents and the `/agents/{agent_name}/execute` API endpoint.

---

## Phase 4: Testing (Detailed Plan)

**Objective:** Verify the new configuration loading, agent execution flow, and API endpoint.

1.  **Unit Test `load_host_config_from_json`:**
    *   **File:** Create `tests/config/test_config_loading.py` (or add to an existing relevant file if preferred).
    *   **Action:** Write unit tests for the updated `load_host_config_from_json` function in `src/config.py`.
    *   **Test Cases:**
        *   Valid JSON with both clients and agents (verify correct parsing of `HostConfig` and `AgentConfig` including `client_ids`).
        *   JSON missing the "agents" key (should still load `HostConfig` correctly, return empty agent dict).
        *   JSON with invalid agent definition (e.g., missing "name", invalid type for `temperature`) - verify `RuntimeError` is raised.
        *   JSON with valid agents but missing `client_ids` (should parse as `None`).
        *   Edge cases (empty clients/agents lists).

2.  **Update Agent Fixtures:**
    *   **File:** `tests/fixtures/agent_fixtures.py`
    *   **Action:** Modify existing fixtures (`minimal_agent_config`, `agent_config_with_llm_params`) or add new ones to include example `client_ids` lists. This will be needed for subsequent tests.

3.  **Integration Test API Endpoint (`/agents/{agent_name}/execute`):**
    *   **File:** Create `tests/api/test_api_endpoints.py`.
    *   **Action:** Write integration tests using FastAPI's `TestClient`.
    *   **Setup:**
        *   Use `pytest.mark.parametrize` to test different agent names.
        *   Create a fixture or use `patch` to provide a mock `MCPHost` instance to the app context (`app.state.mcp_host`). This mock host should have a working `get_agent_config` method returning predefined `AgentConfig` objects (using the updated fixtures from step 2).
        *   Patch `src.agents.agent.Agent.execute_agent` to prevent actual agent execution and allow assertion on its arguments.
    *   **Test Cases:**
        *   **Success Case:** Call the endpoint with a valid `agent_name` and `user_message`. Assert:
            *   Status code is 200.
            *   `host.get_agent_config` was called with the correct `agent_name`.
            *   `Agent.__init__` was called with the correct `AgentConfig`.
            *   The patched `Agent.execute_agent` was called *once* with the correct `user_message`, `host_instance`, and `filter_client_ids` (matching the `client_ids` from the mocked `AgentConfig`).
            *   The response body matches the return value of the mocked `Agent.execute_agent`.
        *   **Agent Not Found:** Call the endpoint with an invalid `agent_name`. Assert status code is 404.
        *   **Missing API Key:** Call without `X-API-Key`. Assert status code is 401.
        *   **Invalid API Key:** Call with incorrect `X-API-Key`. Assert status code is 403.

4.  **Update Agent Unit Tests (`filter_client_ids` Pass-through):**
    *   **File:** `tests/agents/test_agent.py`
    *   **Action:** Modify existing tests (like `test_execute_tool_call_flow`) or add new ones.
    *   **Test Cases:**
        *   Call `agent.execute_agent` with a specific `filter_client_ids` list.
        *   Assert that when `host_instance.execute_tool` (or other host methods like `get_prompt`) is called *within* `execute_agent`, the `filter_client_ids` parameter is correctly passed down with the list provided to `execute_agent`.

5.  **(Optional/Later) E2E Test API Endpoint:**
    *   **File:** `tests/api/test_api_endpoints.py` (or `tests/agents/test_agent_e2e.py`)
    *   **Action:** Write E2E tests using `TestClient` and the `real_mcp_host` fixture.
    *   **Test Cases:**
        *   Call the endpoint for the "Weather Agent" defined in `testing_config.json`. Provide a message that requires the weather tool. Assert the tool is called successfully (may require mocking the LLM response to request the tool).
        *   Call the endpoint for the "Weather Agent". Provide a message that *would* require a planning tool (if available). Assert that the planning tool *cannot* be called (due to `client_ids` filtering in `testing_config.json`). This verifies the filtering works end-to-end.
        *   Call the endpoint for the "Weather Planning Agent". Verify it *can* call both weather and planning tools.

---
