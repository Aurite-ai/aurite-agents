# Agent Usage and API Execution Plan

**Version:** 1.0
**Date:** 2025-04-07

**Goal:** Enable defining agents (including their specific MCP client access) in the JSON configuration and executing them via a dedicated FastAPI endpoint.

---

## Phase 1: Model & Configuration Loading Update

**Objective:** Update data models and configuration loading logic to handle agent definitions within the JSON config.

1.  **Update `AgentConfig` Model:**
    *   **File:** `src/host/models.py`
    *   **Action:** Add a new optional field `client_ids: Optional[List[str]] = None` to the `AgentConfig` Pydantic model. This list will specify which `client_id`s (MCP servers) the agent is allowed to interact with via the host's filtered methods.
2.  **Update JSON Loading Logic:**
    *   **File:** `src/config.py`
    *   **Function:** `load_host_config_from_json`
    *   **Action:**
        *   Modify the function to parse the top-level "agents" list from the input JSON data alongside the "clients" list.
        *   For each entry in the "agents" list, create an `AgentConfig` instance, validating its fields (name, system\_prompt, client\_ids, model, etc.).
        *   Change the function's return type to `Tuple[HostConfig, Dict[str, AgentConfig]]`. The dictionary will map agent names (from the JSON) to their corresponding `AgentConfig` objects.
        *   Add error handling for missing or invalid agent definitions (e.g., missing "name").
3.  **Update Callers of `load_host_config_from_json`:**
    *   **File:** `src/main.py` (within `lifespan` context manager)
        *   **Action:** Update the call to `load_host_config_from_json` to receive the tuple `(host_config, agent_configs)`. Store both appropriately (e.g., `host_config` for `MCPHost` init, `agent_configs` potentially for passing to `MCPHost` or storing in `app.state`).
    *   **File:** `tests/fixtures/host_fixtures.py` (within `real_mcp_host` fixture)
        *   **Action:** Update the call to handle the returned tuple. The fixture might only need the `HostConfig` part for initializing the host, but it should correctly unpack the tuple.

## Phase 2: Agent Configuration Storage & Host Integration

**Objective:** Store the loaded agent configurations and ensure the host can utilize the `client_ids` for filtering during agent execution.

1.  **Store Agent Configurations:**
    *   **Decision:** Store the loaded `Dict[str, AgentConfig]` within the `MCPHost` instance.
    *   **File:** `src/host/host.py`
    *   **Action:**
        *   Modify `MCPHost.__init__` to accept an optional argument `agent_configs: Optional[Dict[str, AgentConfig]] = None`.
        *   Store this dictionary in a private attribute (e.g., `self._agent_configs`).
        *   Add a property or method (e.g., `get_agent_config(name: str) -> AgentConfig`) to retrieve a specific agent's configuration by name.
2.  **Pass Agent Configs during Host Initialization:**
    *   **File:** `src/main.py` (within `lifespan`)
    *   **Action:** Pass the `agent_configs` dictionary (obtained in Phase 1, Step 3) to the `MCPHost` constructor.
3.  **Enable Filtering in Agent Execution:**
    *   **File:** `src/agents/agent.py`
    *   **Method:** `execute_agent`
    *   **Action:** This method already takes the `host_instance`. When it calls host methods like `host_instance.tools.execute_tool`, `host_instance.get_prompt`, etc., it needs to pass the correct `filter_client_ids`.
    *   **Plan:** The *caller* of `Agent.execute_agent` (which will be the new API endpoint in Phase 3) will be responsible for:
        *   Retrieving the correct `AgentConfig` for the requested agent.
        *   Extracting the `client_ids` from that `AgentConfig`.
        *   Passing these `client_ids` explicitly to the host methods *through* the agent execution flow if necessary, OR relying on the host methods already having the `filter_client_ids` parameter.
        *   *Correction:* Reviewing `MCPHost.execute_tool`, `get_prompt`, `read_resource` shows they *already* accept `filter_client_ids`. The `Agent.execute_agent` method needs to be updated to accept `filter_client_ids: Optional[List[str]] = None` and pass this value down to the host method calls it makes.

## Phase 3: API Endpoint Implementation

**Objective:** Create a FastAPI endpoint to trigger the execution of a named, configured agent.

1.  **Define API Request/Response Models:**
    *   **File:** `src/main.py` (or a new `src/api_models.py`)
    *   **Action:**
        *   Create a Pydantic model for the request body (e.g., `ExecuteAgentRequest` with `user_message: str`).
        *   The response can likely reuse the dictionary structure returned by `Agent.execute_agent` (conversation history, final response, tool uses, error).
2.  **Create API Endpoint:**
    *   **File:** `src/main.py`
    *   **Action:** Add a new endpoint, e.g., `POST /agents/{agent_name}/execute`. It should depend on `get_api_key` and `get_mcp_host`.
3.  **Implement Endpoint Logic:**
    *   **File:** `src/main.py` (within the new endpoint function)
    *   **Action:**
        *   Get the `agent_name` from the URL path.
        *   Get the `MCPHost` instance using the dependency.
        *   Use the host's method (added in Phase 2, Step 1) to retrieve the `AgentConfig` for the given `agent_name`. Handle `AgentConfig` not found (raise 404).
        *   Instantiate the `Agent` class using the retrieved `AgentConfig`.
        *   Get the `user_message` from the request body (`ExecuteAgentRequest`).
        *   Extract the `client_ids` from the retrieved `AgentConfig`.
        *   Call `await agent.execute_agent(user_message=user_message, host_instance=host, filter_client_ids=agent_config.client_ids)`.
        *   Return the result dictionary from `execute_agent`. Handle potential exceptions during execution (e.g., return 500).

## Phase 4: Testing

**Objective:** Verify the new configuration loading, agent execution flow, and API endpoint.

1.  **Unit Tests:**
    *   Test the updated `load_host_config_from_json` in `src/config.py` with various valid and invalid JSON inputs (including agent definitions).
    *   Test the new API endpoint in `src/main.py` using FastAPI's `TestClient`. Mock the `MCPHost` and `Agent` classes to isolate endpoint logic.
2.  **Integration/E2E Tests:**
    *   Create or modify tests in `tests/agents/` or a new `tests/api/` test file.
    *   Use the `real_mcp_host` fixture (which should now load `testing_config.json` including agent definitions).
    *   Make requests to the new API endpoint using `TestClient`.
    *   Verify that agents execute correctly and that the `client_ids` filtering restricts tool/prompt/resource access as defined in `testing_config.json`. For example, ensure the "Weather Agent" cannot use planning tools.

---
