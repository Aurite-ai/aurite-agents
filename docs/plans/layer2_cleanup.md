# Layer 2 Cleanup & Improvement Suggestions

**Date:** 2025-05-05

This document lists potential cleanup and improvement suggestions identified after reviewing the Layer 2 source code files (`host_manager.py`, `config.py`, `host/models.py`, `execution/facade.py`, `agents/agent.py`, `workflows/simple_workflow.py`, `workflows/custom_workflow.py`) following the test fixes and Phase A refactoring implementation.

## Suggestions

1.  **Refactor `load_host_config_from_json` in `src/config.py`**
    *   **Description:** The current function handles loading and validation for multiple configuration types (clients, agents, simple workflows, custom workflows). It could be broken down into smaller, private helper functions (e.g., `_load_clients`, `_load_agents`, etc.) similar to the registration helpers in `HostManager`.
    *   **Benefit:** Improved readability, maintainability, and separation of concerns.
    *   **Priority:** Low (Current implementation is functional).

2.  **Implement Agent History (`include_history`) in `src/agents/agent.py`**
    *   **Description:** The `AgentConfig` includes an `include_history` flag, but the `execute_agent` method currently has a `TODO` and does not load or manage conversation history across multiple separate executions. It only maintains history within a single multi-turn execution.
    *   **Benefit:** Enables agents to maintain context across different execution requests if configured to do so.
    *   **Priority:** Medium (Implements an existing configuration option).

3.  **Re-enable Custom Workflow Signature Check in `src/workflows/custom_workflow.py`**
    *   **Description:** The code to strictly check the signature of the `execute_workflow` method (`(self, initial_input, executor)`) in custom workflow classes is currently commented out with a warning.
    *   **Benefit:** Provides stronger validation for custom workflow implementations, catching signature mismatches earlier.
    *   **Priority:** Low/Medium (Enhances validation and robustness).

4.  **Minor Logging/Error Handling Considerations**
    *   **Description:**
        *   Some `DEBUG` logs in `HostManager` and `config.py` could potentially be `INFO` for more visibility.
        *   `HostManager.register_config_file` could potentially aggregate errors and raise a final exception if any part fails, instead of just logging warnings/errors for individual component registration failures.
        *   `Agent.execute_agent` handles API call errors and tool execution errors slightly differently (returns error dict vs. sends error to LLM). Could potentially standardize the return value further.
    *   **Benefit:** Minor improvements to observability or error handling consistency.
    *   **Priority:** Very Low (Current implementation is functional and reasonable).
