# Implementation Plan: Dynamic Tool Swapping

**Version:** 1.0
**Date:** 2025-05-15
**Author(s):** Ryan, Gemini
**Related Design Document (Optional):** N/A

## 1. Goals
    *   Implement a "dynamic tool swapping" feature allowing `AgentConfig` to defer MCP client selection to an LLM.
    *   Modify `AgentConfig` to include an `auto` flag.
    *   Update `ExecutionFacade` to use an LLM to select `client_ids` when `auto` is true.
    *   Ensure the LLM is provided with necessary context (user message, system prompt, available tools) for selection.

## 2. Scope
    *   **In Scope:**
        *   `src/config/config_models.py`: Add `auto: Optional[bool] = False` to `AgentConfig`.
        *   `src/execution/facade.py`:
            *   Modify `run_agent` and `stream_agent_run` methods.
            *   Implement logic to call `AnthropicLLM` for tool selection if `AgentConfig.auto` is true.
            *   Construct a prompt for the LLM, including user message, agent system prompt, and descriptions of available `ClientConfig`s.
            *   Parse the LLM's response to get a list of `client_id`s.
            *   Use the LLM-selected `client_id`s for the agent's execution context, effectively overriding/populating `AgentConfig.client_ids` for that run.
        *   `src/llm/providers/anthropic_client.py`: No direct changes anticipated, but will be utilized.
        *   Unit tests for the new logic in `ExecutionFacade`.
    *   **Out of Scope (Optional but Recommended):**
        *   Caching LLM decisions for tool selection (per user, "run the llm ... every time").
        *   Complex merging strategies for LLM-selected `client_ids` with pre-existing `client_ids` if `auto` is true (current assumption: LLM selection replaces).
        *   UI changes to expose or manage the `auto` flag (can be a follow-up).

## 3. Prerequisites (Optional)
    *   Anthropic API key configured and accessible (`ANTHROPIC_API_KEY` environment variable).

## 4. Implementation Steps

**Phase 1: Configuration Model Update**

1.  **Step 1.1: Add `auto` field to `AgentConfig`**
    *   **File(s):** `src/config/config_models.py`
    *   **Action:**
        *   Modify the `AgentConfig(BaseModel)` class.
        *   Add a new field: `auto: Optional[bool] = Field(False, description="If true, an LLM will dynamically select client_ids for the agent at runtime.")`
        *   Ensure the default is `False` to maintain backward compatibility.
    *   **Verification:**
        *   Manually review the change.
        *   Ensure existing tests that load `AgentConfig` still pass or are updated.

**Phase 2: ExecutionFacade - LLM Tool Selection Logic**

1.  **Step 2.1: Design Prompt for LLM Tool Selection**
    *   **File(s):** (Conceptual, will be implemented in `ExecutionFacade`)
    *   **Action:**
        *   Define a clear and effective prompt template for the `AnthropicLLM`.
        *   The prompt should instruct the LLM to act as a tool/client selector.
        *   **Inputs to the prompt:**
            *   User's current message/query.
            *   The agent's system prompt (if available from `AgentConfig` or `LLMConfig`).
            *   A summarized list of available `ClientConfig`s. For each client, include:
                *   `client_id`
                *   A brief description (if available, perhaps from `ClientConfig.roots[j].name` or a new `description` field in `ClientConfig` if deemed necessary later).
                *   Key capabilities (e.g., from `ClientConfig.capabilities` and `ClientConfig.roots[j].capabilities`).
        *   **Output expectation from LLM:** A JSON list of `client_id` strings. Example: `{"selected_client_ids": ["client_A", "client_B"]}`.
    *   **Verification:**
        *   Review prompt clarity and completeness.
        *   Iterate on prompt design based on initial testing (manual or with LLM playground).

2.  **Step 2.2: Implement Helper Method in `ExecutionFacade` for LLM Tool Selection**
    *   **File(s):** `src/execution/facade.py`
    *   **Action:**
        *   Create a new private asynchronous method, e.g., `_get_llm_selected_client_ids(self, agent_config: AgentConfig, user_message: str, system_prompt_for_llm: Optional[str]) -> Optional[List[str]]:`.
        *   Inside this method:
            *   Retrieve all available `ClientConfig`s from `self._current_project.clients`.
            *   Format the client information and other inputs (user message, system prompt) into the designed prompt (Step 2.1).
            *   Instantiate or get a cached `AnthropicLLM` client instance (similar to how it's done for agent execution, potentially using a dedicated `LLMConfig` for this tool selection task, or a default one).
            *   Call the LLM's `create_message` method with the prompt. Request JSON output by providing a schema to the LLM.
                *   Schema example: `{"type": "object", "properties": {"selected_client_ids": {"type": "array", "items": {"type": "string"}}}, "required": ["selected_client_ids"]}`
            *   Parse the LLM's JSON response.
            *   Extract the list of `client_id`s.
            *   Perform basic validation: ensure returned `client_id`s are present in the available `ClientConfig`s. Log warnings for invalid IDs.
            *   Handle potential errors from the LLM call (e.g., API errors, parsing errors, empty response). Return `None` or an empty list in case of failure, with appropriate logging.
    *   **Verification:**
        *   Unit test this helper method with mock LLM responses (success, failure, invalid IDs).
        *   Test with mock `ClientConfig` data.

3.  **Step 2.3: Integrate Tool Selection into `run_agent`**
    *   **File(s):** `src/execution/facade.py`
    *   **Action:**
        *   In the `run_agent` method, after loading `agent_config`:
        *   Check if `agent_config.auto` is `True`.
        *   If true:
            *   Call the `_get_llm_selected_client_ids` helper method.
            *   If the helper returns a valid list of `client_id`s:
                *   Create a *copy* of the `agent_config` for this specific run (to avoid modifying the shared config object).
                *   Update `copied_agent_config.client_ids` with the LLM-selected IDs.
                *   Log the dynamically selected client IDs.
                *   Use this `copied_agent_config` for the rest of the `run_agent` logic (passing to `Agent` instantiation).
            *   If the helper fails or returns no IDs, decide on fallback behavior:
                *   Option A: Proceed with `agent_config.client_ids` if they exist (and log a warning about dynamic selection failure).
                *   Option B: Proceed with no tools / an empty `client_ids` list (and log a warning).
                *   Option C: Return an error to the user.
                *   **(Decision for plan: Implement Option A initially - fallback to static `client_ids` or empty if none, with a warning.)**
        *   If `agent_config.auto` is `False`, the existing logic for handling `client_ids` remains.
    *   **Verification:**
        *   Unit tests for `run_agent` covering:
            *   `auto = True`, LLM selection successful.
            *   `auto = True`, LLM selection fails, fallback behavior.
            *   `auto = False`, existing behavior.
        *   Integration test with a mock LLM to simulate the end-to-end flow for dynamic selection.

4.  **Step 2.4: Integrate Tool Selection into `stream_agent_run`**
    *   **File(s):** `src/execution/facade.py`
    *   **Action:**
        *   Apply similar logic as in Step 2.3 to the `stream_agent_run` method.
        *   Ensure that if `agent_config.auto` is true, the `_get_llm_selected_client_ids` method is called.
        *   The selected `client_ids` (or fallback) should be used when instantiating the `Agent` for streaming.
        *   Handle errors and fallbacks consistently with `run_agent`.
    *   **Verification:**
        *   Unit tests for `stream_agent_run` similar to those for `run_agent`.

**Phase 3: Testing and Refinement**

1.  **Step 3.1: Comprehensive Unit Testing**
    *   **File(s):** New test files in `tests/execution/` (e.g., `test_facade_dynamic_tools.py`)
    *   **Action:**
        *   Write thorough unit tests for all new logic and modifications in `ExecutionFacade`.
        *   Mock `AnthropicLLM` responses extensively to cover various scenarios (valid JSON, invalid JSON, API errors, different selections of client_ids).
        *   Test edge cases: no available clients, LLM selects no clients, LLM selects non-existent clients.
    *   **Verification:**
        *   All new unit tests pass.
        *   Test coverage for new code is adequate.

2.  **Step 3.2: Manual/Integration Testing (Optional, but Recommended)**
    *   **File(s):** N/A (manual execution or new test project config)
    *   **Action:**
        *   Create a test `ProjectConfig` with a few sample `ClientConfig`s.
        *   Create an `AgentConfig` with `auto = True`.
        *   Run the agent via API or CLI with different user messages to observe the LLM's tool selection.
        *   Monitor logs for correct behavior and any errors.
        *   Refine the LLM prompt (Step 2.1) based on observed results.
    *   **Verification:**
        *   The feature behaves as expected in a more integrated environment.
        *   LLM selects appropriate tools based on the input.

## 5. Testing Strategy
    *   **Unit Tests:**
        *   Focus on `ExecutionFacade`:
            *   `_get_llm_selected_client_ids`: Mock LLM responses, test prompt formatting, response parsing, error handling, validation of selected IDs.
            *   `run_agent` / `stream_agent_run`: Test conditional logic for `auto` flag, correct propagation of selected `client_ids` to `Agent` instance, fallback mechanisms.
        *   Location: `tests/execution/`.
    *   **Integration Tests (Lightweight):**
        *   Consider a test that uses a mock `AnthropicLLM` but runs through the `ExecutionFacade` to an `Agent` instance to verify `client_ids` are correctly passed based on the `auto` flag.
    *   **Manual Verification:**
        *   As described in Step 3.2, for prompt refinement and observing real LLM behavior.
    *   **Key Scenarios to Cover:**
        *   `AgentConfig.auto = True`:
            *   LLM successfully selects a subset of available client_ids.
            *   LLM selects all available client_ids.
            *   LLM selects no client_ids.
            *   LLM returns client_ids not in the available list (should be filtered out or handled gracefully).
            *   LLM call fails (API error, timeout).
            *   LLM returns malformed JSON.
        *   `AgentConfig.auto = False`: Ensure existing behavior is unchanged.
        *   `AgentConfig` has pre-existing `client_ids` and `auto = True` (LLM selection should override for the run).
        *   No `ClientConfig`s available in the project.

## 6. Potential Risks & Mitigation (Optional)
    *   **Risk:** LLM prompt is not effective, leading to poor tool selection.
        *   **Mitigation:** Iterative prompt design and testing (manual and automated). Clear instructions and examples in the prompt.
    *   **Risk:** LLM response parsing is brittle.
        *   **Mitigation:** Request structured JSON output from the LLM with a schema. Implement robust parsing and error handling.
    *   **Risk:** Increased latency due to the extra LLM call.
        *   **Mitigation:** Acknowledge this as a trade-off for dynamic behavior. For critical performance, `auto=False` can be used. Use a fast LLM model for the selection task if possible.
    *   **Risk:** Cost implications of an additional LLM call per agent run.
        *   **Mitigation:** Use a cost-effective model for the selection task. Feature is optional (`auto` flag).

## 7. Open Questions & Discussion Points (Optional)
    *   Clarify the exact behavior if `agent_config.client_ids` are pre-defined AND `auto = True`. Current plan assumes LLM selection *replaces* them for the run. Is this the desired outcome, or should they be merged/augmented? (Plan assumes replacement for now).
    *   Should there be a dedicated `LLMConfig` (e.g., `tool_selector_llm_config_id`) for the tool selection LLM call within `ExecutionFacade`, or use a default/existing one? (Plan assumes using a default or similar mechanism to agent LLM client instantiation for now).
    *   Consider adding a `description` field to `ClientConfig` to provide richer information to the LLM for selection, beyond just capabilities and root names. (Out of scope for initial plan, but a potential enhancement).

## 8. Rollback Plan (Optional - for critical changes)
    *   Revert changes to `src/config/config_models.py` and `src/execution/facade.py`.
    *   The feature is controlled by the `auto` flag, defaulting to `False`, so existing functionality remains unaffected if the new code paths are not invoked.
