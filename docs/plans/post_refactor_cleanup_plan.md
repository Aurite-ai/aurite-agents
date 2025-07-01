# Implementation Plan: Post-Refactor Cleanup

**Version:** 1.0
**Date:** 2025-07-01
**Author(s):** Gemini

## 1. Goals
*   Improve the robustness of the configuration models by removing legacy default values.
*   Enhance encapsulation by moving agent-specific setup logic into the `Agent` class.
*   Simplify the `ExecutionFacade` by delegating agent preparation.
*   Optimize the tool filtering process to improve efficiency.

## 2. Scope
*   **In Scope:**
    *   `src/aurite/config/config_models.py`
    *   `src/aurite/execution/facade.py`
    *   `src/aurite/components/agents/agent.py`
    *   `src/aurite/host/host.py`
    *   `src/aurite/host/resources/tool_manager.py` (Implicitly, for tool formatting)
    *   Relevant test files for the above.
*   **Out of Scope:**
    *   Any functional changes not directly related to the cleanup tasks.
    *   Changes to the API layer or other entrypoints beyond what is necessary to support the refactoring.

## 3. Implementation Steps

### Phase 1: Configuration & Facade Cleanup

1.  **Step 1.1: Make `provider` and `model` mandatory in `LLMConfig`**
    *   **File(s):** `src/aurite/config/config_models.py`
    *   **Action:**
        *   In the `LLMConfig` class, remove the `default` values from the `provider` and `model` fields to make them explicitly required in configuration files.
    *   **Verification:**
        *   Tests that relied on these defaults will fail.

2.  **Step 1.2: Centralize Defaulting Logic in `LiteLLMClient`**
    *   **File(s):** `src/aurite/components/llm/providers/litellm_client.py`
    *   **Action:**
        *   Modify the `LiteLLMClient.__init__` method to use internal defaults (e.g., `model_name="gpt-3.5-turbo"`, `provider="openai"`) if `model_name` or `provider` are not provided.
    *   **Verification:**
        *   The client can be instantiated without parameters and will use the internal defaults.

3.  **Step 1.3: Simplify `ExecutionFacade._get_llm_client`**
    *   **File(s):** `src/aurite/execution/facade.py`
    *   **Action:**
        *   Refactor `_get_llm_client`. If an `llm_config_id` is not found, it should call `LiteLLMClient()` with no arguments, relying on the client's new internal defaults.
    *   **Verification:**
        *   Facade tests should be updated for this new simplified logic.

4.  **Step 1.4: Update All Tests**
    *   **File(s):** All failing test files from the previous steps.
    *   **Action:**
        *   Update test configurations and mocks to provide explicit `provider` and `model` values where `LLMConfig` is used.
    *   **Verification:**
        *   All tests should pass.

### Phase 2: Agent Initialization Refactoring

**Architectural Goal:** To improve configuration transparency by resolving the final LLM parameters at the point of use (`Agent` initialization) rather than at the point of execution (`LiteLLMClient`). This makes the final, effective configuration inspectable throughout the agent's lifecycle.

1.  **Step 2.1: Make `Agent` the Configuration Resolver**
    *   **File(s):** `src/aurite/components/agents/agent.py`
    *   **Action:**
        *   Modify the `Agent.__init__` signature. It will now accept the base `LLMConfig` and the `AgentConfig`.
        *   Add logic within `__init__` to merge the base `LLMConfig` and the `AgentConfig` overrides into a single, final `resolved_llm_config` object. Store this as a public property on the instance (e.g., `self.resolved_llm_config`).
        *   The `Agent` will then use this resolved config to instantiate its own internal `LiteLLMClient`.
    *   **Verification:**
        *   Agent-related tests will fail. This is expected.

2.  **Step 2.2: Simplify `LiteLLMClient`**
    *   **File(s):** `src/aurite/components/llm/providers/litellm_client.py`
    *   **Action:**
        *   Remove the `llm_config_override` parameter from all methods.
        *   Simplify the `_build_request_params` method to no longer perform any merging logic. It will now be initialized with the final, resolved parameters.
    *   **Verification:**
        *   `LiteLLMClient` tests will fail. This is expected.

3.  **Step 2.3: Simplify `ExecutionFacade`**
    *   **File(s):** `src/aurite/execution/facade.py`
    *   **Action:**
        *   Refactor `_prepare_agent_for_run` to be a simple "gatherer". It will fetch the `AgentConfig` and the base `LLMConfig` from the project and pass them to the `Agent` constructor.
        *   Remove all logic related to creating `LiteLLMClient` instances or override objects from the facade.
    *   **Verification:**
        *   Facade-related tests will fail. This is expected.

4.  **Step 2.4: Update All Tests**
    *   **File(s):** All failing test files from the previous steps.
    *   **Action:**
        *   Update tests for `Agent`, `LiteLLMClient`, and `ExecutionFacade` to align with the new, cleaner separation of responsibilities.
    *   **Verification:**
        *   All tests should pass.

### Phase 3: Tool Formatting Optimization

1.  **Step 3.1: Investigate Tool Formatting**
    *   **File(s):** `src/aurite/host/host.py`, `src/aurite/host/resources/tool_manager.py`
    *   **Action:**
        *   Read the `ToolManager` to confirm if `get_formatted_tools` can be optimized by receiving the `tool_names` list.
    *   **Verification:**
        *   Confirm the optimization path.

2.  **Step 3.2: Refactor `ToolManager`**
    *   **File(s):** `src/aurite/host/resources/tool_manager.py`, `src/aurite/host/host.py`
    *   **Action:**
        *   If the optimization is viable, modify `ToolManager.format_tools_for_llm` to accept `tool_names`.
        *   Update `MCPHost.get_formatted_tools` to pass the `tool_names` down to the manager.
    *   **Verification:**
        *   Run tests related to tool formatting.

## 4. Testing Strategy
*   **Unit Tests:** Each step includes a verification phase where relevant unit tests are run and updated. The primary goal is to ensure existing functionality is preserved after refactoring.
*   **Final Review:** After all phases are complete, a full test run (`pytest`) will be executed to ensure no regressions were introduced.
