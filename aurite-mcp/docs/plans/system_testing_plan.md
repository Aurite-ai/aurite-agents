# System Testing & Planning Agent Implementation Plan

**Version:** 1.0
**Date:** 2025-04-06
**Related Plan:** `overarching_host_refactor_plan.md` (Follows Phase 3)

## 1. Overview

This plan details the steps to enhance test coverage for the `aurite-mcp` system after the Phase 3 refactor and before proceeding to Phase 4 (Workflow Implementation). The goals are:
1.  Create generic tests applicable to all MCP servers for basic functionality.
2.  Create comprehensive tests for the specific `weather_mcp_server.py` fixture.
3.  Create basic tests for the `MCPHost` using existing fixtures.
4.  Implement and test a new `PlanningAgent` that utilizes the `planning_server.py`.

This will help verify the stability of the core host, server interactions, and agent framework, particularly concerning asynchronous operations and the recent testing infrastructure updates.

## 2. Implementation Steps

### Step 1: Generic MCP Server Tests

*   **Objective:** Ensure all MCP servers (used in testing) can start, shut down, and respond to basic MCP requests (`list_tools`, `call_tool`, `list_prompts`, `get_prompt` if implemented).
*   **1.1. Unit Test (`tests/servers/test_generic_mcp_server.py`):**
    *   Create a new test file.
    *   Focus on testing the *server-side* logic abstractly. Use mocking (`unittest.mock` or `pytest-mock`) to simulate server instantiation and method calls for a hypothetical server implementing the core MCP methods.
    *   Verify that handlers for `list_tools`, `call_tool`, etc., return correctly formatted responses based on the `mcp.types`.
    *   Mark tests with `@pytest.mark.unit`.
*   **1.2. E2E Test (`tests/servers/test_generic_mcp_server_e2e.py`):**
    *   Create a new test file.
    *   Utilize the `real_mcp_host` fixture (defined in `tests/fixtures/host_fixtures.py`), which loads `config/agents/testing_config.json`.
    *   Parameterize tests to run against *each* server defined in `testing_config.json` (e.g., echo server, weather server).
    *   For each server, use the `host_instance` provided by the fixture to:
        *   Call `host_instance.tools.list_tools()`, `host_instance.prompts.list_prompts()`. Verify basic response structure.
        *   If tools exist, attempt a simple `host_instance.tools.execute_tool()` call (e.g., echo tool's basic function). Verify a non-error response.
        *   If prompts exist, attempt `host_instance.prompts.get_prompt()`. Verify a non-error response.
    *   Mark tests with `@pytest.mark.e2e`.
    *   Apply `@pytest.mark.xfail(reason="Known issue with real_mcp_host teardown")` if the async teardown issue persists during these tests.

### Step 2: Weather MCP Server Tests

*   **Objective:** Create specific tests verifying the functionality of `tests/fixtures/servers/weather_mcp_server.py`.
*   **2.1. Unit Test (`tests/servers/test_weather_mcp_server.py`):**
    *   Create a new test file.
    *   Import `create_server` from `weather_mcp_server.py`.
    *   Instantiate the server logic directly (`app = create_server()`).
    *   Test the specific tool logic (`weather_lookup`, `current_time`) by calling the underlying async functions directly with various arguments (e.g., different locations, units, timezones, invalid inputs). Assert correct outputs based on the mock data/logic within the server.
    *   Test the `get_prompt` logic similarly, verifying personalization.
    *   Test `list_tools` and `list_prompts` for correctness.
    *   Mark tests with `@pytest.mark.unit`.
*   **2.2. E2E Test (`tests/servers/test_weather_mcp_server_e2e.py`):**
    *   Create a new test file.
    *   Ensure `weather_mcp_server.py` is configured as a client in `config/agents/testing_config.json`.
    *   Use the `real_mcp_host` fixture.
    *   Use the `host_instance` to call `weather_lookup` and `current_time` tools via `host_instance.tools.execute_tool()` with various valid/invalid arguments. Assert the content of the returned `TextContent`.
    *   Use `host_instance.prompts.get_prompt()` to fetch the `weather_assistant` prompt with different arguments. Assert the returned message content.
    *   Mark tests with `@pytest.mark.e2e`.
    *   Apply `@pytest.mark.xfail` if necessary due to the teardown issue.

### Step 3: Basic MCP Host Tests

*   **Objective:** Add simple tests for the `MCPHost` class itself, focusing on initialization and basic state.
*   **3.1. Integration Test (`tests/host/test_host_basic.py`):**
    *   Create a new test file (or add to an existing host test file if appropriate).
    *   Use `mock_host_config` fixture or create specific `HostConfig` instances.
    *   Test `MCPHost` initialization with different configurations (e.g., empty clients, clients with exclusions).
    *   Verify the host's internal state after initialization (e.g., `host.clients` list).
    *   *(Consider adding tests for the exclusion logic if not already covered in `test_exclusion.py`)*.
    *   Mark tests with `@pytest.mark.integration` (as host tests typically involve component interaction, even if mocked).
*   **3.2. E2E Test (`tests/host/test_host_basic_e2e.py`):**
    *   Create a new test file.
    *   Use the `real_mcp_host` fixture (likely connected to the echo server by default via `testing_config.json`).
    *   Perform basic checks on the initialized `host_instance`:
        *   Check `host_instance.get_status()`.
        *   Check `host_instance.is_running`.
        *   Call `host_instance.tools.list_tools()` and `host_instance.prompts.list_prompts()` to ensure basic communication with the connected server works via the host.
    *   Mark tests with `@pytest.mark.e2e`.
    *   Apply `@pytest.mark.xfail` if necessary.

### Step 4: Planning Agent Implementation and Tests

*   **Objective:** Create and test an agent that interacts with `src/servers/management/planning_server.py`.
*   **4.1. Implement Agent (`src/agents/management/planning_agent.py`):**
    *   Create the new agent file.
    *   Define `PlanningAgent` class (likely inheriting from `src.agents.agent.Agent`).
    *   Implement methods like:
        *   `async save_new_plan(self, host_instance: MCPHost, plan_name: str, plan_content: str, tags: Optional[List[str]] = None)`: Uses `host_instance.tools.execute_tool` to call the `save_plan` tool on the planning server.
        *   `async list_existing_plans(self, host_instance: MCPHost, tag: Optional[str] = None)`: Uses `host_instance.tools.execute_tool` to call the `list_plans` tool.
        *   *(Optional)* `async generate_plan(self, host_instance: MCPHost, user_request: str)`: Uses `Agent.execute` with the `create_plan_prompt` from the planning server to generate plan content via an LLM, potentially followed by a call to `save_new_plan`.
    *   Ensure appropriate `AgentConfig` is handled.
*   **4.2. Unit Test (`tests/agents/test_planning_agent.py`):**
    *   Create the new test file.
    *   Use `mock_mcp_host` fixture and mock the `anthropic` client.
    *   Configure the `mock_mcp_host.tools.execute_tool` mock to simulate responses from the `save_plan` and `list_plans` tools.
    *   Instantiate `PlanningAgent` with a mock `AgentConfig`.
    *   Call the agent's methods (`save_new_plan`, `list_existing_plans`) and assert that the correct parameters are passed to `mock_mcp_host.tools.execute_tool`.
    *   If `generate_plan` is implemented, test the interaction with the mocked LLM (`Agent.execute`) and subsequent tool calls.
    *   Mark tests with `@pytest.mark.unit`.
*   **4.3. E2E Test (`tests/agents/test_planning_agent_e2e.py`):**
    *   Create the new test file.
    *   Ensure `planning_server.py` is configured as a client in `config/agents/testing_config.json`.
    *   Use the `real_mcp_host` fixture.
    *   Create an `AgentConfig` that links to the `host_config` used by `real_mcp_host`.
    *   Instantiate `PlanningAgent` with this config.
    *   Call agent methods (`save_new_plan`, `list_existing_plans`) using the `host_instance` from the fixture.
    *   Assert results by checking the actual output from the planning server (e.g., verify plan files are created/listed in `src/servers/management/plans/`). Clean up created files during test teardown.
    *   Mark tests with `@pytest.mark.e2e`.
    *   Apply `@pytest.mark.xfail` if necessary.

### Step 5: Documentation & Memory

*   **5.1.** Update `tests/README.md` to reflect the new test files and structure.
*   **5.2.** Propose adding notes to `memory/bank.md` regarding:
    *   The persistent `real_mcp_host` teardown issue and the use of `xfail`.
    *   Any significant findings or patterns observed during test implementation.
