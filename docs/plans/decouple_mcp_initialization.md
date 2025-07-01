# Implementation Plan: Decouple MCP Server Initialization

**Version:** 1.0
**Date:** 2025-06-30
**Author(s):** Ryan, Gemini

## 1. Goals
*   Decouple the initialization of MCP servers (clients) from the main application startup to improve performance and resilience.
*   Introduce a mechanism to initialize MCP servers on-demand (Just-in-Time) when an agent that requires them is executed.
*   Control this behavior with an environment variable for flexibility.

## 2. Scope
*   **In Scope:**
    *   `src/aurite/host_manager.py`: Modifying the `Aurite` class methods `initialize` and `run_agent`.
    *   `src/aurite/host/host.py`: Modifying the `MCPHost` class method `initialize`.
*   **Out of Scope:**
    *   Changes to workflow execution logic (`run_workflow`, `run_custom_workflow`). The JIT logic will only apply to `run_agent` for now.

## 3. Implementation Steps

### Phase 1: Modify MCPHost to Allow Optional Client Connection

1.  **Step 1.1: Update `MCPHost.initialize` method signature**
    *   **File(s):** `src/aurite/host/host.py`
    *   **Action:**
        *   Modify the `initialize` method signature to accept a new boolean parameter: `connect_clients_on_startup: bool = True`.
    *   **Verification:**
        *   The method signature is updated correctly.

2.  **Step 1.2: Make client connection loop conditional**
    *   **File(s):** `src/aurite/host/host.py`
    *   **Action:**
        *   Wrap the `for` loop that iterates through `self.client_manager.get_all_client_configs()` inside an `if connect_clients_on_startup:` block.
    *   **Verification:**
        *   Run existing tests for `MCPHost`. They should continue to pass as the default behavior is unchanged.

### Phase 2: Implement Conditional Startup and JIT Logic in Aurite

1.  **Step 2.1: Update `Aurite.initialize` to control MCPHost initialization**
    *   **File(s):** `src/aurite/host_manager.py`
    *   **Action:**
        *   Read the `AURITE_REGISTER_MCP_ON_STARTUP` environment variable, defaulting to `"true"`.
        *   Convert the string value to a boolean.
        *   Pass this boolean value to `await self.host.initialize(connect_clients_on_startup=...)`.
    *   **Verification:**
        *   Set `AURITE_REGISTER_MCP_ON_STARTUP=false` and confirm from logs that the client connection loop in `MCPHost` is skipped during startup.

2.  **Step 2.2: Add JIT registration logic to `Aurite.run_agent`**
    *   **File(s):** `src/aurite/host_manager.py`
    *   **Action:**
        *   Inside the `run_agent` method, before the call to `self.execution.run_agent`, add the following logic:
            1.  Get the `AgentConfig` for the `agent_name`.
            2.  If the agent config exists and has `mcp_servers` defined:
            3.  Iterate through each `client_id` in `agent_config.mcp_servers`.
            4.  Check if the client is already active using `self.host.is_client_registered(client_id)`.
            5.  If not registered, retrieve the `ClientConfig` from `self.component_manager.get_mcp_server(client_id)`.
            6.  If the `ClientConfig` is found, call `await self.register_client(client_config)`.
            7.  If the `ClientConfig` is not found, raise a `ValueError`.
    *   **Verification:**
        *   Create a new test case that:
            1.  Starts Aurite with `AURITE_REGISTER_MCP_ON_STARTUP=false`.
            2.  Calls `run_agent` for an agent that uses an MCP server.
            3.  Asserts that `host.is_client_registered()` is `true` for that server *after* the agent run.

## 4. Testing Strategy
*   **Unit Tests:**
    *   Existing tests for `MCPHost` and `Aurite` should be run to ensure no regressions in the default startup behavior.
    *   A new test will be added to `tests/orchestration/test_host_manager.py` to specifically verify the JIT registration logic in `run_agent` when on-demand initialization is enabled.
*   **Manual Verification:**
    *   Run the application with `AURITE_REGISTER_MCP_ON_STARTUP=false`.
    *   Observe the startup logs to confirm that client connections are skipped.
    *   Execute an agent via the API or CLI that requires an MCP server and confirm from the logs that the server is initialized just before execution.

## 5. Documentation
*   The final step of this implementation will be to review `.clinerules/documentation_guide.md` to identify and update all relevant documents, particularly those related to configuration and framework behavior.
