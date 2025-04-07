# Simple Agent Workflows Plan

**Version:** 1.0
**Date:** 2025-04-07

**Goal:** Implement the ability to define and execute simple, sequential agent-based workflows configured via JSON.

---

## Phase 1: Models & Configuration Loading

**Objective:** Define data models for workflows and update configuration loading to handle them.

1.  **Define Workflow Models:**
    *   **File:** `src/host/models.py`
    *   **Action:**
        *   Create `WorkflowConfig` Pydantic model:
            *   `name: str`
            *   `steps: List[str]` (List of agent names representing the sequence)
            *   (Optional: Add `description: Optional[str]`)
2.  **Update JSON Loading Logic:**
    *   **File:** `src/config.py`
    *   **Function:** `load_host_config_from_json`
    *   **Action:**
        *   Modify the function to parse a new top-level "workflows" list from the input JSON data.
        *   For each entry, create a `WorkflowConfig` instance.
        *   **Validation:** During parsing, validate that each agent name listed in a workflow's `steps` exists as a key in the loaded `agent_configs_dict`. Raise an error if an unknown agent name is referenced.
        *   Change the function's return type to `Tuple[HostConfig, Dict[str, AgentConfig], Dict[str, WorkflowConfig]]`.
3.  **Update Callers of `load_host_config_from_json`:**
    *   **File:** `src/main.py` (within `lifespan` context manager)
        *   **Action:** Update the call to receive the tuple `(host_config, agent_configs, workflow_configs)`. Store `workflow_configs` in `app.state`.
    *   **File:** `tests/fixtures/host_fixtures.py` (within `real_mcp_host` fixture)
        *   **Action:** Update the call to handle the returned tuple (it likely only needs `host_config`).

## Phase 2: Workflow Storage & Host Integration

**Objective:** Store the loaded workflow configurations within the `MCPHost`.

1.  **Store Workflow Configurations:**
    *   **File:** `src/host/host.py`
    *   **Action:**
        *   Modify `MCPHost.__init__` to accept an optional argument `workflow_configs: Optional[Dict[str, WorkflowConfig]] = None`.
        *   Store this dictionary in a private attribute (e.g., `self._workflow_configs`).
        *   Add a method `get_workflow_config(name: str) -> WorkflowConfig` to retrieve a specific workflow's configuration by name (raising `KeyError` if not found).
2.  **Pass Workflow Configs during Host Initialization:**
    *   **File:** `src/main.py` (within `lifespan`)
    *   **Action:** Pass the `workflow_configs` dictionary (obtained in Phase 1, Step 3) to the `MCPHost` constructor.
3.  **Update Host Shutdown:**
    *   **File:** `src/host/host.py`
    *   **Method:** `shutdown`
    *   **Action:** Add `self._workflow_configs.clear()` during shutdown.

## Phase 3: API Endpoint & Workflow Execution Logic

**Objective:** Create a FastAPI endpoint to trigger workflow execution and implement the sequential agent execution logic.

1.  **Define API Request/Response Models:**
    *   **File:** `src/main.py` (or `src/api_models.py`)
    *   **Action:**
        *   Create `ExecuteWorkflowRequest` model with `initial_user_message: str`.
        *   Define a response model (e.g., `ExecuteWorkflowResponse`) containing the final output message (`final_message: str`) and potentially intermediate steps or errors (`status: str`, `error: Optional[str]`).
2.  **Create API Endpoint:**
    *   **File:** `src/main.py`
    *   **Action:** Add `POST /workflows/{workflow_name}/execute` endpoint, depending on `get_api_key` and `get_mcp_host`.
3.  **Implement Workflow Execution Logic:**
    *   **File:** `src/main.py` (within the new endpoint function)
    *   **Action:**
        *   Get `workflow_name` and `initial_user_message`.
        *   Retrieve `WorkflowConfig` using `host.get_workflow_config(workflow_name)`. Handle `KeyError` (404).
        *   Initialize `current_message = initial_user_message`.
        *   Initialize list to store intermediate results/errors if needed for response.
        *   **Loop through `agent_name` in `workflow_config.steps`:**
            *   Retrieve the `AgentConfig` for `agent_name` using `host.get_agent_config(agent_name)`. Handle potential `KeyError` (internal error 500, as validation should prevent this).
            *   Instantiate `Agent(config=agent_config)`.
            *   Extract `filter_ids = agent_config.client_ids`.
            *   **Execute Agent:** Call `result = await agent.execute_agent(user_message=current_message, host_instance=host, filter_client_ids=filter_ids)`.
            *   **Error Handling:** Check if `result.get("error")` exists or if `result.get("final_response")` is missing/invalid. If error, log it, potentially store it, and break the loop (or raise HTTPException 500).
            *   **Output Extraction:** Extract the text output from `result["final_response"].content`. Assume the first block is text: `current_message = result["final_response"].content[0].text`. Add robust checks for content type and existence.
            *   (Optional: Store intermediate `current_message` or `result`).
        *   **Return Response:** Construct and return `ExecuteWorkflowResponse` with the final `current_message` and status.

## Phase 4: Testing

**Objective:** Verify workflow configuration loading, execution logic, and the API endpoint.

1.  **Unit Tests:**
    *   Test `load_host_config_from_json` for workflow parsing and validation (including checking for non-existent agent names in steps).
2.  **Integration Tests (API Endpoint):**
    *   **File:** `tests/api/test_api_endpoints.py` (add new tests).
    *   **Action:** Use `TestClient`.
    *   **Setup:**
        *   Mock `MCPHost` to provide known `WorkflowConfig` and `AgentConfig`s.
        *   Patch `src.main.Agent.execute_agent`. Configure its `side_effect` to return a sequence of expected results (simulating output from step 1, step 2, etc.) based on the expected input message for each step.
    *   **Test Cases:**
        *   Execute a valid 2-step workflow. Assert:
            *   Status code 200.
            *   `host.get_workflow_config` called correctly.
            *   `host.get_agent_config` called for each agent in the workflow steps.
            *   `Agent.execute_agent` called the correct number of times (once per step).
            *   `Agent.execute_agent` called with the correct `user_message` for each step (initial message for step 1, output of step 1 for step 2).
            *   `Agent.execute_agent` called with the correct `filter_client_ids` for each step's agent config.
            *   Final response contains the expected output from the last step.
        *   Test workflow not found (404).
        *   Test workflow where an agent step simulation returns an error (e.g., 500 or specific error response).
3.  **(Optional/Later) E2E Tests:**
    *   Use `TestClient` and `real_mcp_host`.
    *   Define a simple workflow in `testing_config.json` using existing test agents (e.g., Weather Agent -> Planning Agent).
    *   Call the workflow endpoint. Mock LLM responses if necessary to control the flow. Verify the final output and potentially tool calls made by each agent step, respecting filters.

---
