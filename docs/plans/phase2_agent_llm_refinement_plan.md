# Implementation Plan: Phase 2 - Agent & LLM Class Refinements

This document outlines the detailed steps for completing Phase 2 of the AI Agent Framework Enhancement, focusing on Agent and LLM class refinements as per the `docs/plans/overarching_plan.md`.

## I. LLM Configuration Enhancements (Corresponds to Overarching Plan Task 3.7)

The goal is to allow LLM calls to dynamically use specific `LLMConfig` settings, overriding client defaults for a particular call.

1.  **Modify `src/llm/base_client.py`:**
    *   **Action:** Verify `BaseLLM.__init__` correctly uses default values for `temperature`, `max_tokens`, and `system_prompt` if `None` is passed. (Current behavior seems correct, this is a verification step).
    *   **Action:** Modify the `BaseLLM.create_message` method signature:
        *   Add a new optional parameter: `llm_config_override: Optional[LLMConfig] = None`.
    *   **Action:** Update the `BaseLLM.create_message` method logic:
        *   If `llm_config_override` is provided, its values (model_name, temperature, max_tokens, default_system_prompt) must take precedence over the client's instance-level defaults (`self.model_name`, `self.temperature`, etc.) for that specific call.
        *   The system prompt resolution hierarchy for the call should be:
            1.  `system_prompt_override` (existing method argument).
            2.  `llm_config_override.default_system_prompt` (if `llm_config_override` is provided).
            3.  `self.system_prompt` (the LLM client's instance-level default system prompt).

2.  **Modify `src/llm/providers/anthropic_client.py`:**
    *   **Action:** Update `AnthropicLLM.__init__` to align with any `BaseLLM` changes if necessary (current behavior seems correct).
    *   **Action:** Update the `AnthropicLLM.create_message` method signature to include `llm_config_override: Optional[LLMConfig] = None`.
    *   **Action:** Implement the logic within `create_message` to:
        *   Use parameters from `llm_config_override` if it's provided, otherwise fall back to the instance's defaults (`self.model_name`, `self.temperature`, etc.).
        *   Specifically, determine `model`, `temperature`, `max_tokens`, and the `system` prompt to be used for the Anthropic API call based on the presence of `llm_config_override` and the `system_prompt_override` argument, following the hierarchy defined in step 1.
        *   Ensure these resolved parameters are correctly passed to `self.anthropic_sdk_client.messages.create()`.

3.  **Update `src/execution/facade.py` (for LLMConfig Passing):**
    *   **Action:** In `ExecutionFacade.run_agent`:
        *   After `agent_config` is fetched, if `agent_config.llm_config_id` is present, fetch the corresponding `LLMConfig` object from `self._manager.llm_configs.get(agent_config.llm_config_id)`. Store this as `llm_config_for_override_obj`.
        *   This `llm_config_for_override_obj` (or `None` if no `llm_config_id` or not found) will be passed to the new `Agent` constructor later (see Part II).

4.  **Update `src/agents/agent_turn_processor.py`:**
    *   **Action:** Modify `AgentTurnProcessor.__init__` to accept a new optional parameter: `llm_config_for_override: Optional[LLMConfig] = None`. Store it as `self.llm_config_for_override`.
    *   **Action:** In `AgentTurnProcessor.process_turn`, when calling `self.llm.create_message(...)`, pass the `llm_config_override=self.llm_config_for_override` argument.

5.  **Update LLM Client Tests:**
    *   **Action:** Create/update unit tests for `BaseLLM` and `AnthropicLLM`.
    *   **Focus:** Verify that the `llm_config_override` parameter in `create_message` correctly overrides call-specific settings (model, temperature, max_tokens, system_prompt) and correctly falls back to instance defaults when `llm_config_override` or its specific fields are `None`.
    *   **Action:** Update tests for `AgentTurnProcessor` to ensure it correctly receives and passes the `llm_config_for_override` to the LLM client.

## II. Agent Class Consolidation & Refinement (Corresponds to Overarching Plan Tasks 3.8 & 3.9)

The goal is to merge `ConversationManager` into `Agent`, making `Agent` the primary class for managing conversation execution.

6.  **Merge `ConversationManager` into a new `Agent` class:**
    *   **File:** Perform changes in `src/agents/conversation_manager.py` initially.
    *   **Action:** Rename the class `ConversationManager` to `Agent`.
    *   **Action:** Update the `__init__` method of this newly renamed `Agent` class:
        *   Change signature from `__init__(self, agent: OldAgent, host_instance: MCPHost, initial_messages: List[MessageParam], system_prompt_override: Optional[str] = None)`
        *   To: `__init__(self, config: AgentConfig, llm_client: BaseLLM, host_instance: MCPHost, initial_messages: List[MessageParam], system_prompt_override: Optional[str] = None, llm_config_for_override: Optional[LLMConfig] = None)`.
        *   Inside `__init__`:
            *   Store `self.config = config`.
            *   Store `self.llm = llm_client`.
            *   Store `self.host = host_instance`.
            *   Store `self.llm_config_for_override = llm_config_for_override` (from Part I, Step 3).
            *   Keep other initializations from the former `ConversationManager` (e.g., `self.messages`, `self.conversation_history`, `self.system_prompt_override`).
            *   Remove the old `self.agent` attribute.
            *   Update all internal references from `self.agent.config` to `self.config` and `self.agent.llm` to `self.llm`.
    *   **Action:** Ensure all methods previously in `ConversationManager` (e.g., `run_conversation`, `_prepare_agent_result`) are now part of this new `Agent` class and use `self.config`, `self.llm` directly.
    *   **Action:** Within the new `Agent.run_conversation` method (previously `ConversationManager.run_conversation`), ensure `AgentTurnProcessor` is instantiated with the correct parameters, including `config=self.config`, `llm_client=self.llm`, `host_instance=self.host`, and the new `llm_config_for_override=self.llm_config_for_override`.

7.  **File System Changes for Agent Class:**
    *   **Action:** Rename the file `src/agents/conversation_manager.py` to `src/agents/agent.py`.
    *   **Action:** Delete the old `src/agents/agent.py` file (which previously contained the `OldAgent` class).

8.  **Update Imports Project-Wide:**
    *   **Action:** Globally search and replace imports:
        *   `from src.agents.conversation_manager import ConversationManager` should become `from src.agents.agent import Agent`.
        *   Any imports of the old `Agent` from `src.agents.agent` should now also point to `from src.agents.agent import Agent` (the new consolidated class).
    *   **Files to check carefully:** `src/execution/facade.py`, `src/workflows/simple_workflow.py`, and all relevant test files.

9.  **Refactor `src/execution/facade.py` for New Agent Usage:**
    *   **Action:** In `ExecutionFacade.run_agent`:
        *   Remove instantiation of the old `Agent` (if it was a separate step) and `ConversationManager`.
        *   Directly instantiate the new `Agent` class using the resolved `agent_config`, `llm_client_instance`, `self._host`, `initial_messages_for_agent`, `system_prompt` (as `system_prompt_override`), and the `llm_config_for_override_obj` (fetched in Part I, Step 3).
        *   The call will look like:
            ```python
            agent_instance = Agent(
                config=agent_config,
                llm_client=llm_client_instance,
                host_instance=self._host,
                initial_messages=initial_messages_for_agent,
                system_prompt_override=system_prompt, # from run_agent args
                llm_config_for_override=llm_config_for_override_obj
            )
            agent_result: AgentExecutionResult = await agent_instance.run_conversation()
            ```

10. **Review and Refactor New `src/agents/agent.py` (Corresponds to Overarching Plan Task 3.9):**
    *   **Action:** Focus on the `run_conversation` method in the new `src/agents/agent.py`.
    *   **Action:** Review the management of `self.messages` (list of messages for the next LLM call) and `self.conversation_history` (log of all messages for the `AgentExecutionResult`).
        *   Ensure clarity, efficiency, and correctness in how these lists are populated and used.
        *   Confirm that `AgentConfig.include_history` (handled by `ExecutionFacade` for loading/saving) does not negatively interact with the agent's internal message handling. The agent should correctly process the `initial_messages` it receives.
        *   The overarching plan notes the current history appending approach as "reasonable." Verify this still holds and the code is clean and simple.

11. **Update Agent-Related Tests:**
    *   **Action:** If `tests/agents/test_agent.py` exists and contains tests for the old `Agent`, merge its relevant tests into `tests/agents/test_conversation_manager.py`.
    *   **Action:** Rename `tests/agents/test_conversation_manager.py` to `tests/agents/test_agent.py`.
    *   **Action:** Update all tests within the new `tests/agents/test_agent.py` to:
        *   Reflect the new `Agent` class structure and its `__init__` signature.
        *   Test the consolidated functionality, including conversation flow, history accumulation in `AgentExecutionResult`, and interaction with `AgentTurnProcessor`.
        *   Ensure mock objects and assertions are updated for the new `Agent` class.
    *   **Action:** Update `tests/fixtures/agent_fixtures.py` if it provides fixtures for `Agent` or `ConversationManager`.
    *   **Action:** Review `tests/agents/test_agent_turn_processor.py`. Its direct dependencies might not change much, but ensure its instantiation in tests reflects any changes (e.g., if `llm_config_for_override` is now commonly passed).
    *   **Action:** Review and update any integration tests that instantiate or interact with Agents directly or via the `ExecutionFacade` (e.g., in `tests/orchestration/`, `tests/api/`, `tests/workflows/`).

## III. Documentation & Final Review

12. **Update Documentation:**
    *   **Action:** Briefly update `docs/design/agent_design.md` if necessary to reflect the consolidated `Agent` class structure and the new LLM configuration override mechanism.
    *   **Action:** Ensure all code comments in modified files are accurate.

13. **Final Review:**
    *   **Action:** Conduct a final review of all changed files for correctness, consistency, and adherence to project coding standards.
    *   **Action:** (Optional, if feasible) Manually test a few key agent execution scenarios to ensure the refactoring behaves as expected.
