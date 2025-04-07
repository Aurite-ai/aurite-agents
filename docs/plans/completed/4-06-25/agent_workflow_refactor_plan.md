# Agent Workflow Refactor Implementation Plan

**Date:** 2025-04-06
**Author:** Gemini

## 1. Goal

Refactor the `Agent` class (`src/agents/agent.py`) to support both standard agent execution (using all available host tools) and custom, multi-step agent workflows with finer control over LLM calls and tool usage at each step.

## 2. Background

The current `Agent.execute` method bundles the entire LLM interaction and tool usage, making it unsuitable for workflows requiring distinct steps with varying prompts or tool availability (e.g., generating text without tools, then using a specific tool).

## 3. Proposed Solution

Introduce a clear separation between standard agent execution and workflow execution:

1.  **Create `_make_llm_call` Helper:** Add a private helper method to `Agent` to encapsulate the raw Anthropic API call, accepting parameters for `system_prompt` and `tools`.
2.  **Rename `execute` to `execute_agent`:** Rename the existing method for clarity.
3.  **Refactor `execute_agent`:** Update this method to use `_make_llm_call`. It will remain responsible for the multi-turn conversation loop using all host tools by default.
4.  **Define `execute_workflow` Concept:** Establish that workflow agents (subclasses) will implement their own `execute_workflow` method, using `_make_llm_call` and `host_instance.execute_tool` to orchestrate steps. No default implementation in the base class.
5.  **Update Call Sites:** Modify existing code (mainly tests) to use the renamed `execute_agent`.

## 4. Implementation Steps

**Phase: Coding & Implementation**

1.  **[Implement `_make_llm_call`]**
    *   **File:** `aurite-mcp/src/agents/agent.py`
    *   **Action:** Define the private async method `_make_llm_call` with the signature:
        ```python
        async def _make_llm_call(
            self,
            client: anthropic.Anthropic,
            messages: List[MessageParam],
            system_prompt: Optional[str],
            tools: Optional[List[Dict]], # Anthropic tool format
            model: str,
            temperature: float,
            max_tokens: int
        ) -> anthropic.types.Message:
        ```
    *   **Details:** Move the core `client.messages.create(...)` call into this method. Handle potential API exceptions gracefully (e.g., log and re-raise or return an error indicator). Ensure parameters like `system` and `tools` are only passed if provided.
    *   **Verification:** Unit test (if feasible without full integration) or integration test later.

2.  **[Rename `execute` to `execute_agent`]**
    *   **File:** `aurite-mcp/src/agents/agent.py`
    *   **Action:** Rename the public method `execute` to `execute_agent`. Update its docstring accordingly.

3.  **[Refactor `execute_agent` to use `_make_llm_call`]**
    *   **File:** `aurite-mcp/src/agents/agent.py`
    *   **Action:** Modify the `execute_agent` method:
        *   Remove the direct `client.messages.create` call.
        *   Inside the conversation loop, call `await self._make_llm_call(...)`.
        *   Pass the necessary parameters: `client`, current `messages`, `system_prompt` (from config or default), `tools_data` (formatted from `host_instance.tools.format_tools_for_llm()`), `model`, `temperature`, `max_tokens`.
        *   Ensure the rest of the loop logic (handling tool calls, results, history) correctly uses the response from `_make_llm_call`.
    *   **Verification:** Integration tests (updated in next step).

4.  **[Update Call Sites (Tests)]**
    *   **Files:** Primarily `aurite-mcp/tests/agents/test_agent_e2e.py`, potentially others calling `Agent.execute`.
    *   **Action:** Search for `agent.execute(` and replace with `agent.execute_agent(`.
    *   **Verification:** Run affected tests (e.g., `pytest aurite-mcp/tests/agents/test_agent_e2e.py`) to ensure they pass after the rename and refactoring.

## 5. Future Work (Separate Task)

*   Implement `execute_workflow` in `PlanningAgent` (`aurite-mcp/src/agents/management/planning_agent.py`) to demonstrate the new pattern, using `_make_llm_call` and `host_instance.execute_tool`.
*   Add tests specifically for workflow execution in `PlanningAgent`.

## 6. Potential Issues & Mitigation

*   **Refactoring Errors:** Carefully test the refactored `execute_agent` loop to ensure conversation history and tool handling remain correct. Integration tests are key.
*   **API Changes:** The `_make_llm_call` signature depends on the `anthropic` library. Future library updates might require adjustments.
