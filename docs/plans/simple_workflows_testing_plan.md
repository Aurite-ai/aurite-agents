# Simple Workflows - Testing Plan

**Version:** 1.0
**Date:** 2025-04-07

**Goal:** Verify the implementation of JSON-defined simple workflows and the `/workflows/{workflow_name}/execute` API endpoint.

---

## Phase 1: Configuration Setup

**Objective:** Define example workflows in configuration files for use in tests.

1.  **Update `config/agents/testing_config.json`:** [COMPLETED by Ryan]
2.  **(Optional) Update `config/agents/aurite_agents.json`:** [COMPLETED by Ryan]

## Phase 2: Unit Tests (Config Loading Validation)

**Objective:** Ensure workflow definitions are correctly parsed and validated during configuration loading.

1.  **Enhance Config Loading Tests:**
    *   **File:** `tests/config/test_config_loading.py`
    *   **Action:** Add new test cases for `load_host_config_from_json`.
    *   **Test Cases:**
        *   Valid JSON including a "workflows" section (verify correct parsing into `WorkflowConfig` objects and inclusion in the returned tuple).
        *   JSON missing the "workflows" key (should load successfully, return empty workflow dict).
        *   JSON with a workflow referencing a non-existent agent name in `steps` (verify `RuntimeError` is raised during validation).
        *   JSON with a workflow having an empty `steps` list (should load successfully).

## Phase 3: Integration Tests (API Endpoint)

**Objective:** Verify the logic of the `/workflows/{workflow_name}/execute` endpoint using mocks.

1.  **Create Workflow API Test File:**
    *   **File:** `tests/workflows/test_workflow_api.py`
2.  **Write Integration Tests:**
    *   **Action:** Use FastAPI's `TestClient`.
    *   **Setup:**
        *   Similar to `tests/api/test_api_endpoints.py`, use a fixture (`mock_dependencies`) to mock `get_api_key` and provide a mock `MCPHost`.
        *   Configure the mock `MCPHost`'s `get_workflow_config` and `get_agent_config` methods to return predefined `WorkflowConfig` and `AgentConfig` objects.
        *   Patch `src.main.Agent.execute_agent`. Configure its `side_effect` to return a *sequence* of mock results, simulating the output progression through workflow steps. The mock should check that the `user_message` passed to it matches the expected output from the previous step.
    *   **Test Cases:**
        *   **Success Case (Multi-step):** Execute a valid 2-step workflow. Assert:
            *   Status code 200.
            *   `host.get_workflow_config` called once with the correct workflow name.
            *   `host.get_agent_config` called once for *each* agent in the workflow steps.
            *   `Agent.execute_agent` called twice (once per step).
            *   Verify `Agent.execute_agent`'s `user_message` argument for step 1 matches the initial request message.
            *   Verify `Agent.execute_agent`'s `user_message` argument for step 2 matches the (mocked) text output from step 1's result.
            *   Verify `Agent.execute_agent`'s `filter_client_ids` argument matches the config for the agent being executed in *each* step.
            *   Final response (`ExecuteWorkflowResponse`) has `status="completed"` and `final_message` matching the (mocked) output of the last step.
        *   **Workflow Not Found:** Call endpoint with an invalid `workflow_name`. Assert 404.
        *   **Agent Step Failure:** Configure the mocked `Agent.execute_agent` to return an error (`{"error": "..."}`) on the first step. Assert the response has `status="failed"` and includes the error message. Verify the second agent step was *not* executed.
        *   **Output Extraction Failure:** Configure the mocked `Agent.execute_agent` to return a response without a valid text block in `final_response.content`. Assert the response has `status="failed"` and includes an appropriate error message.
        *   **Empty Workflow:** Execute a workflow with an empty `steps` list. Assert `status="completed_empty"` and `final_message` matches the initial input.

## Phase 4: E2E Tests (API Endpoint)

**Objective:** Verify the end-to-end workflow execution using real test servers.

1.  **Create Workflow E2E Test File:**
    *   **File:** `tests/workflows/test_workflow_e2e.py` (or add to `test_workflow_api.py` with `@pytest.mark.e2e`).
2.  **Write E2E Tests:**
    *   **Action:** Use `TestClient` and the `real_mcp_host` fixture.
    *   **Setup:** Ensure `config/agents/testing_config.json` has a defined workflow (from Phase 1, Step 1).
    *   **Test Cases:**
        *   Execute the defined workflow (e.g., "Weather Summary Workflow").
        *   **Challenge:** Controlling the output between real agent steps requires either:
            *   A) Carefully crafting the initial message and relying on the real LLM (if `test_agent_e2e` uses it) to produce suitable intermediate output (less reliable).
            *   B) Mocking the `Anthropic` client within the `Agent` instances created during the workflow execution to control the `final_response.content` passed between steps (more complex mocking setup).
            *   C) Using simpler test agents/servers in the workflow that have predictable outputs not requiring an LLM.
        *   **Focus:** Initially, focus on verifying the workflow completes successfully (status 200, `status="completed"`) and that the correct agents *could* have been called (e.g., by checking logs if possible, or by designing test agents/tools that leave a trace). Verifying the exact intermediate message passing might be deferred depending on complexity.
        *   Verify that agent client filtering is respected across steps if feasible.

---
