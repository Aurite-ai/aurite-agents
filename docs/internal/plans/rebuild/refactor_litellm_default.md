# Implementation Plan: Make LiteLLM the Default LLM Handler

**Version:** 1.0
**Date:** 2025-06-29
**Author(s):** Ryan, Gemini

## 1. Goals
*   Remove the `ENABLE_GATEWAY` feature flag and associated conditional logic.
*   Make `LiteLLMClient` the sole, default LLM client for all LLM interactions.
*   Remove the native `AnthropicLLM`, `GeminiLLM`, and `OpenAIClient` implementations.
*   Remove the corresponding direct dependencies (`anthropic`, `google-genai`, `openai`) from `pyproject.toml`.
*   Ensure the framework remains fully functional for both streaming and non-streaming agent execution.

## 2. Scope
*   **In Scope:**
    *   `src/aurite/execution/facade.py`: Modifying the `_create_llm_client` factory method.
    *   `src/aurite/host_manager.py`: Removing the `ENABLE_GATEWAY` environment variable check.
    *   `src/aurite/components/llm/providers/`: Deleting `anthropic_client.py`, `gemini_client.py`, and `openai_client.py`.
    *   `src/aurite/components/agents/agent_turn_processor.py`: Removing any provider-specific logic if found.
*   **Out of Scope:**
    *   Changing the `BaseLLM` abstract class interface.
    *   Modifying the external-facing API of the `ExecutionFacade`.

## 3. Implementation Steps

### Phase 1: Core Logic Refactoring

1.  **Step 1.1: Modify `ExecutionFacade`**
    *   **File(s):** `src/aurite/execution/facade.py`
    *   **Action:**
        *   In the `_create_llm_client` method, remove the `if os.getenv("ENABLE_GATEWAY", default=True):` block and all `elif` conditions for specific providers (`anthropic`, `gemini`, `openai`).
        *   The method body should be simplified to *only* instantiate and return `LiteLLMClient`.
        *   Remove the now-unused imports for `AnthropicLLM`, `GeminiLLM`, and `OpenAIClient`.
    *   **Verification:**
        *   The code should be cleaner and have only one execution path in `_create_llm_client`.

2.  **Step 1.2: Modify `HostManager`**
    *   **File(s):** `src/aurite/host_manager.py`
    *   **Action:**
        *   Search for and remove any checks for the `ENABLE_GATEWAY` environment variable. This logic is now obsolete.
    *   **Verification:**
        *   The framework's startup and initialization logic should no longer depend on this environment variable.

### Phase 2: Code and Dependency Cleanup

1.  **Step 2.1: Delete Obsolete LLM Clients**
    *   **File(s):**
        *   `src/aurite/components/llm/providers/anthropic_client.py`
        *   `src/aurite/components/llm/providers/gemini_client.py`
        *   `src/aurite/components/llm/providers/openai_client.py`
    *   **Action:** Delete these three files entirely.
    *   **Verification:** The files are removed from the project structure.

2.  **Step 2.2: Update `pyproject.toml`**
    *   **File(s):** `pyproject.toml`
    *   **Action:**
        *   In the `[project.dependencies]` section, remove the following lines:
            *   `"openai>=1.80.0"`
            *   `"anthropic>=0.49.0"`
            *   `"google-genai>=1.11.0"`
    *   **Verification:**
        *   Run `pip install -e .` to ensure dependencies can be resolved without errors.
        *   Run `deptry .` to confirm that the removed packages are no longer listed as dependencies.

### Phase 3: Verification

1.  **Step 3.1: Run Core Tests**
    *   **Action:** Execute the main test suite.
    *   **Command:** `pytest`
    *   **Verification:** All existing tests should pass, demonstrating that the refactor has not broken existing functionality. Pay close attention to tests related to agent execution and streaming.

2.  **Step 3.2: Final Documentation Review**
    *   **Action:** When the implementation is complete and all tests are passing, review `.clinerules/documentation_guide.md` to identify all documents that require updates, read them, and then propose the necessary changes. The `framework_overview.md` and `llm.md` component guide will likely need updates.

## 4. Testing Strategy
*   **Unit Tests:** The existing unit tests for `ExecutionFacade` and `Agent` should cover the core logic. We will need to update or remove any tests that specifically targeted the old, provider-specific clients.
*   **Integration Tests:** The integration tests that run agents with different LLM configurations (now all routed through LiteLLM) are critical. These will serve as the primary validation that the refactor was successful.
*   **Manual Verification:** After automated tests pass, a manual run of an agent via the CLI or API would be a good final check.

## 5. Open Questions & Discussion Points
*   We should confirm if any specific logic within `agent_turn_processor.py` was added to handle provider-specific response formats (e.g., `tool_calls` vs `tool_use`). A quick search shows it already handles both, which is great. No changes should be needed there.
