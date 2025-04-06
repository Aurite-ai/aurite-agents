# PlanningAgent Workflow Implementation Plan

**Date:** 2025-04-06
**Author:** Gemini
**Related Plan:** Agent Workflow Refactor Implementation Plan

## 1. Goal

Implement the `execute_workflow` method in the `PlanningAgent` class (`src/agents/management/planning_agent.py`) following the agreed pattern. This will enable the agent to perform a specific two-step workflow:
1.  Generate plan content using an LLM call with no tools.
2.  Save the generated plan content using the `save_plan` tool via the host.

## 2. Background

The base `Agent` class has been refactored to include an `_make_llm_call` helper and rename the standard execution method to `execute_agent`. This plan details how `PlanningAgent` will leverage these changes to implement its specific workflow logic.

## 3. Proposed Solution

Add an `async def execute_workflow(...)` method to `PlanningAgent`. This method will:
1.  Perform initial setup (validate host, get API key, create client).
2.  Execute Step 1: Call `self._make_llm_call` with a specific planning prompt and no tools (`tools=[]`). Extract the plan text from the response.
3.  Execute Step 2: If Step 1 was successful, call the existing `self.save_new_plan` method (which internally calls `host_instance.execute_tool`) to save the generated plan content.
4.  Handle errors gracefully at each step.
5.  Return a dictionary detailing the workflow steps, the final output (result from `save_plan`), and any errors.

## 4. Implementation Steps

**Phase: Coding & Implementation**

1.  **[Add Imports]**
    *   **File:** `aurite-mcp/src/agents/management/planning_agent.py`
    *   **Action:** Ensure necessary imports are present: `os`, `anthropic`, `logging`, `List`, `Optional`, `Dict`, `Any`, `MessageParam`, `TextBlock`, `MCPHost`, `Agent`. Add any missing ones. Initialize logger if not already present.
    *   **Verification:** Code lints correctly.

2.  **[Implement `execute_workflow` Method Stub]**
    *   **File:** `aurite-mcp/src/agents/management/planning_agent.py`
    *   **Action:** Define the `execute_workflow` method signature:
        ```python
        async def execute_workflow(
            self,
            user_message: str,
            host_instance: MCPHost,
            anthropic_api_key: Optional[str] = None,
            plan_name: Optional[str] = "default_plan_name",
            tags: Optional[List[str]] = None
        ) -> Dict[str, Any]:
            # Implementation follows
            pass
        ```
    *   **Verification:** Method definition is syntactically correct.

3.  **[Implement Workflow Setup Logic]**
    *   **File:** `aurite-mcp/src/agents/management/planning_agent.py`
    *   **Action:** Inside `execute_workflow`, add the initial setup code:
        *   Initialize `workflow_steps = []`.
        *   Validate `host_instance`.
        *   Get `api_key` (from param or environment).
        *   Create `anthropic.Anthropic` client instance.
        *   Determine `model`, `temperature`, `max_tokens` from `self.config`.
        *   Include `try...except` block for client initialization.
        *   Return appropriate error dictionaries on failure.
    *   **Verification:** Setup logic matches the example sketch.

4.  **[Implement Step 1: Generate Plan (LLM Call)]**
    *   **File:** `aurite-mcp/src/agents/management/planning_agent.py`
    *   **Action:** Add the logic for the first step within a `try...except` block:
        *   Define the `planning_system_prompt`.
        *   Prepare the `messages` list.
        *   Append step details to `workflow_steps`.
        *   Call `await self._make_llm_call(...)` with `tools=[]`.
        *   Extract `plan_content` from the response's `TextBlock`.
        *   Handle potential `ValueError` if the response format is unexpected.
        *   Append success/failure details to `workflow_steps`.
        *   Return error dictionary on failure.
    *   **Verification:** LLM call uses `_make_llm_call` correctly with no tools. Text extraction logic is sound.

5.  **[Implement Step 2: Save Plan (Tool Call)]**
    *   **File:** `aurite-mcp/src/agents/management/planning_agent.py`
    *   **Action:** Add the logic for the second step within an `if plan_content:` block and a `try...except` block:
        *   Append step details to `workflow_steps`.
        *   Call `await self.save_new_plan(...)`, passing `host_instance`, `plan_name`, `plan_content`, and `tags`.
        *   Store the `save_result`.
        *   Append success/failure details to `workflow_steps`.
        *   Return error dictionary on failure.
    *   **Verification:** Tool call uses the existing `save_new_plan` method correctly.

6.  **[Implement Final Return]**
    *   **File:** `aurite-mcp/src/agents/management/planning_agent.py`
    *   **Action:** Add the final return statement at the end of the method, returning the dictionary with `workflow_steps`, `final_output` (set to `save_result`), and `error` (set to `None`).
    *   **Verification:** Return dictionary structure matches the defined pattern.

**Phase: Testing & Verification**

7.  **[Add Workflow Unit/Integration Tests]**
    *   **File:** `aurite-mcp/tests/agents/test_planning_agent.py` (or potentially `test_planning_agent_e2e.py` if relying on real host/tools)
    *   **Action:** Create new test cases specifically for `execute_workflow`:
        *   Test successful execution path (mocking LLM response and `save_new_plan` or using real components if E2E).
        *   Test failure during LLM call (Step 1).
        *   Test failure during tool call (Step 2).
        *   Verify the structure and content of the returned dictionary (`workflow_steps`, `final_output`, `error`).
    *   **Verification:** New tests cover the workflow logic and pass.

## 5. Potential Issues & Mitigation

*   **LLM Response Format:** The plan generation step assumes the LLM returns a single `TextBlock`. If the LLM response is different, the extraction logic will need adjustment. Mitigation: Add robust checking of `llm_response.content`.
*   **Tool `save_plan` Dependency:** The workflow relies on the `save_plan` tool being available and correctly implemented by the corresponding server and registered with the host. Mitigation: Ensure the test setup includes a host configured with a planning server providing this tool.
*   **Error Handling:** Ensure errors in each step are caught and reported correctly in the final return dictionary.
