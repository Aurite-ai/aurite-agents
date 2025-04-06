# Agent Implementation and Model Refinement - Technical Plan (Phase 3) [COMPLETED]

**Version:** 0.1 (Draft)
**Date:** 2025-04-06
**Related Plan:** `overarching_host_refactor_plan.md`

## 1. Overview

This document details the technical implementation steps for Phase 3 of the MCP Host refactor. This phase focuses on:
A. Implementing the core `Agent` class abstraction.
B. Refining the shared Pydantic configuration models (`src/host/models.py`) to support Agent configuration, linking Agents to a single `HostConfig`.
C. Migrating agent execution logic (`prepare_prompt_with_tools`, `execute_prompt_with_tools`) from `MCPHost` to the `Agent` class.

## 2. Technical Implementation Steps

### Step 1: Refine Configuration Models (`src/host/models.py`)

*   **Objective:** Update `AgentConfig` to link to a `HostConfig` and include agent-specific LLM parameters.
*   **1.1.** Modify `AgentConfig`:
    *   Add `host: Optional[HostConfig] = None` field.
    *   Ensure optional LLM parameters exist: `model: Optional[str] = None`, `temperature: Optional[float] = None`, `system_prompt: Optional[str] = None`, `max_tokens: Optional[int] = None`. *(Keep existing `include_history`)*.
    *   Remove any direct `clients` field if present.
*   **1.2.** Review `HostConfig`, `ClientConfig`, `RootConfig` for consistency (no changes anticipated).
*   **1.3.** Add/Update docstrings for `AgentConfig` explaining the new structure.

### Step 2: Create Agent Class Structure (`src/agents/agent.py`)

*   **Objective:** Define the basic `Agent` class structure.
*   **2.1.** Create the new file `aurite-mcp/src/agents/agent.py`.
*   **2.2.** Define the `Agent` class signature.
*   **2.3.** Implement `Agent.__init__(self, config: AgentConfig)`:
    *   Store the `config` instance (`self.config = config`).
    *   *(Decision: Defer host instantiation/linking logic to execution time).*
*   **2.4.** Add basic docstrings for the `Agent` class and `__init__`.
w
### Step 3: Implement Agent Execution Logic (`src/agents/agent.py`)

*   **Objective:** Migrate and adapt the core LLM interaction and tool execution logic from `MCPHost`.
*   **3.1.** Define the `Agent.execute(self, user_message: str, host_instance: MCPHost, anthropic_api_key: Optional[str] = None) -> Dict[str, Any]` method signature. *(Confirms passing the instantiated `MCPHost`)*.
*   **3.2.** Adapt `prepare_prompt_with_tools` logic:
    *   Check if `host_instance` is provided. Raise `ValueError` if not.
    *   Use `host_instance.prompts` and `host_instance.tools` managers.
    *   Implement parameter prioritization and fallback: Use `self.config` values (model, temp, system_prompt, max_tokens) if provided, otherwise use hardcoded defaults:
        *   `model`: "claude-3-opus-20240229"
        *   `temperature`: 0.7
        *   `system_prompt`: "You are a helpful assistant."
        *   `max_tokens`: 4096
    *   Call `host_instance.tools.format_tools_for_llm()`.
*   **3.3.** Adapt `execute_prompt_with_tools` main loop logic:
    *   Instantiate Anthropic client.
    *   Manage message history (consider `self.config.include_history`).
    *   Call `client.messages.create` using prepared data.
    *   Handle `ToolUseBlock`: Call `host_instance.tools.execute_tool()` and `host_instance.tools.create_tool_result_blocks()`.
    *   Append results and loop (implement max iterations).
*   **3.4.** Return the conversation history and final response structure.
*   **3.5.** Add docstrings for the `execute` method.

### Step 4: Remove Old Methods from Host (`src/host/host.py`)

*   **Objective:** Clean up `MCPHost` by removing the migrated logic.
*   **4.1.** Delete the `prepare_prompt_with_tools` method.
*   **4.2.** Delete the `execute_prompt_with_tools` method.
*   **4.3.** Add comments indicating the logic moved to `src/agents/agent.py`.

### Step 5: Define Initial Testing Strategy (`tests/agents/test_agent.py`)

*   **Objective:** Plan foundational tests for the `Agent` class.
*   **5.1.** Create the new file `aurite-mcp/tests/agents/test_agent.py`.
*   **5.2.** Outline necessary imports and basic test class structure (`TestAgent`).
*   **5.3.** Plan test cases:
    *   `test_agent_initialization`: Create `Agent` with various `AgentConfig`.
    *   `test_execute_requires_host`: Verify `execute` raises `ValueError` if `host_instance` is missing.
    *   `test_execute_parameter_prioritization`: Mock `host_instance` and Anthropic; verify agent LLM params override others.
    *   `test_execute_tool_call_flow`: Mock `host_instance` (with `MockToolManager`), mock Anthropic response, mock `tool_manager.execute_tool`, verify correct `tool_result` block generation.
*   **5.4.** List required mocks/fixtures: `MockAgentConfig`, `MockHostConfig`, `MockMCPHost`, `MockToolManager`, `MockPromptManager`, mocked `anthropic.Anthropic`.

### Step 6: Plan Documentation Updates

*   **Objective:** Ensure documentation reflects the changes.
*   **6.1.** Add/Update docstrings for new/modified classes/methods.
*   **6.2.** Update `aurite-mcp/docs/agents/agent_architecture.md`.
*   **6.3.** Update `aurite-mcp/docs/host/host_system.md`.
*   **6.4.** Add comments in `host.py` pointing to `Agent`.
*   **6.5.** *(Optional)* Update project `README.md`.

## 3. Final Decisions

*   The instantiated `MCPHost` object will be passed as an argument to the `Agent.execute()` method.
*   LLM parameter fallback logic: Use `AgentConfig` value if provided, otherwise use hardcoded defaults within `Agent.execute` (`model="claude-3-opus-20240229"`, `temperature=0.7`, `system_prompt="You are a helpful assistant."`, `max_tokens=4096`).
