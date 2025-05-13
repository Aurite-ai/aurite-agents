# Agent Improvement Progress (May 7, 2025)

This document tracks the progress of refactoring and improving the Agent class and related components, based on the plan outlined in `docs/design/agent_design.md`.

## Overall Goals

1.  **Standardize Agent Output:** Define clear Pydantic models for agent execution results (`AgentExecutionResult`, `AgentOutputMessage`, `AgentOutputContentBlock`).
2.  **Abstract LLM Interaction:** Create an `LLM` client abstraction (`BaseLLM`, `AnthropicLLM`) to decouple the `Agent` class from specific LLM provider SDKs.
3.  **Simplify Agent Logic:** Refactor the `Agent` class to use the `LLM` abstraction, simplifying its execution flow and improving testability.
4.  **Enhance Configuration:** Introduce `LLMConfig` and link it to `AgentConfig` for better LLM management.

## Progress So Far

**Phase 1: Standardize Agent Output using Pydantic Models**
*   **Step 1.1:** Defined `AgentOutputContentBlock`, `AgentOutputMessage`, `AgentExecutionResult` in `src/agents/models.py`. (Completed)
*   **Step 1.2:** Updated `Agent.execute_agent` in `src/agents/agent.py` to:
    *   Return `AgentExecutionResult`. (Completed)
    *   Construct the `AgentExecutionResult` by serializing internal history and the final LLM response. (Completed, including fixes for user message and tool result serialization)
*   **Step 1.3:** Began updating consumers, focusing on unit tests (`tests/orchestration/agent/test_agent_unit.py`).
    *   Updated mocks and assertions for several test cases (`test_execute_agent_success_no_tool_use`, `test_execute_agent_success_with_tool_use`, etc.) to align with `AgentExecutionResult`. (Partially Completed - encountered mock/serialization issues)
    *   Ran initial tests (`test_execute_agent_success_no_tool_use`, `test_execute_agent_success_with_tool_use`), identified and fixed issues related to mock configuration and serialization logic in `agent.py`. (Completed for `...no_tool_use`, ongoing for `...with_tool_use`)

**Phase 2: Abstract LLM Interaction** (Started due to difficulties in testing Phase 1)
*   **Step 2.1a:** Added `LLMConfig` definition to `src/host/models.py`. (Completed)
*   **Step 2.1b:** Deleted incorrect `src/llm/models.py`. (Completed)
*   **Step 2.2:** Created `src/llm/client.py` and defined `BaseLLM` abstract class and `AnthropicLLM` implementation. (Completed)
*   **Step 2.3:** Began refactoring `Agent` class (`src/agents/agent.py`).
    *   Modified `Agent.__init__` to accept `llm_client: BaseLLM` argument and store it as `self.llm`. (Completed)

## Current Status

*   Paused **Step 2.3 (Refactor Agent Class)** after modifying `Agent.__init__`.
*   Encountered repeated failures with the `replace_in_file` tool while attempting further modifications to `Agent.__init__` (removing old client setup) and `execute_agent`.
*   User (Ryan) is investigating the tool issue.

## Remaining Steps (Based on Design Doc)

1.  **Complete Phase 2: Abstract LLM Interaction**
    *   Finish refactoring `Agent.__init__` (remove old client setup).
    *   Remove `Agent._make_llm_call`.
    *   Update `Agent.execute_agent` to use `self.llm.create_message()` and handle the returned `AgentOutputMessage`.
    *   Update `AgentConfig` in `src/host/models.py` (add `llm_config_id` - *already done during Step 2.1a*).
    *   Update `HostManager` and/or `ExecutionFacade` to instantiate and pass the correct `LLM` client to the `Agent`.
    *   Create unit tests for `AnthropicLLM` (`tests/llm/test_client.py`).

2.  **Revisit Phase 1: Standardize Agent Output**
    *   Complete updates to unit tests in `tests/orchestration/agent/test_agent_unit.py` now that the `Agent` uses the `LLM` abstraction (mocks should target `self.llm.create_message`).
    *   Update integration tests and any other consumers of `Agent.execute_agent`.

3.  **Phase 3: Simplify Agent Logic** (If necessary after LLM abstraction)
    *   Further simplify `Agent.execute_agent` loop if possible.
    *   Refine error handling.

4.  **Address Original Bug:** Re-run the failing prompt validation test (`tests/api/routes/test_evaluation_api.py::test_execute_prompt_validation_file_success`) after refactoring is complete to see if the changes resolved the underlying serialization issue. Debug further if necessary.
