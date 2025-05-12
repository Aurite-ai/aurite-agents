# Project Rules: Testing (aurite-agents)

## 1. Objective

The primary objective of testing in the **Aurite Agents** project is to systematically verify that new features or modifications work as expected across different layers of the architecture (Entrypoints, Orchestration, Host). This involves writing unit, integration, and potentially end-to-end tests within the appropriate layer-specific directories.

This document complements the global `comprehensive_testing_rules.md`.

## 2. Core Principles

*   **Layered Testing:** Tests should primarily reside within the directory corresponding to the layer they target (`tests/api`, `tests/orchestration`, `tests/host`).
*   **Thoroughness:** Aim for comprehensive test coverage of new or modified functionality within its layer.
*   **Isolation:** Utilize mocks and fixtures effectively to isolate components, especially for unit tests.
*   **Reusability:** Leverage shared fixtures and mocks from `tests/fixtures/`, `tests/mocks/`, and relevant `conftest.py` files.
*   **Clarity:** Test code should be clear, readable, and maintainable.
*   **Convention:** Follow existing testing patterns and naming conventions within the project.

## 3. Project Test Structure & Key Files

*   **`tests/`**: Root directory for all tests.
    *   **`tests/api/`**: Tests for Layer 1 (Entrypoints - FastAPI). Contains `tests/api/conftest.py` for API-specific fixtures (like `api_client`).
    *   **`tests/orchestration/`**: Tests for Layer 2 (Orchestration - HostManager, Facade, Agent, Workflows, LLM Clients).
    *   **`tests/host/`**: Tests for Layer 3 (Host Infrastructure - MCPHost, Foundation, Resources). Contains `tests/host/conftest.py` for Host-specific fixtures/mocks.
    *   **`tests/clients/`**: Tests specifically for MCP client interactions or packaged server behavior (related to Layer 4 interactions).
    *   **`tests/config/`**: Tests for configuration loading and management utilities.
    *   **`tests/storage/`**: Tests for database interactions (Layer persistence).
    *   **`tests/prompt_validation/`**: Specific workflows and tests for validating agent outputs.
*   **`tests/conftest.py`**: Root configuration file, providing global fixtures (like `anyio_backend`) and importing fixtures from `tests/fixtures/`.
*   **`tests/fixtures/`**: Contains reusable pytest fixtures (e.g., pre-configured objects, server setups).
*   **`tests/mocks/`**: Contains mock objects for external dependencies or complex internal components (e.g., `mock_mcp_host`, `fake_llm_client`).

## 4. Workflow & Procedures (Adapted from Global Rules)

1.  **Understand Scope & Define Test Strategy (PLAN MODE):**
    *   Clarify the specific features/modules requiring testing and identify the primary layer involved.
    *   Review Implementation Plans, Design Docs, and relevant source code.
    *   **Tool Usage (`read_file`, `search_files`):** Examine existing tests in the relevant layer directory (`tests/api/`, `tests/orchestration/`, `tests/host/`). Check `tests/fixtures/`, `tests/mocks/`, and relevant `conftest.py` files for reusable utilities.
    *   Propose a test strategy: types of tests, key areas, positive/negative cases, edge cases.
    *   **Tool Usage (`plan_mode_respond`):** Discuss the strategy and specific test cases with Ryan.

2.  **Write/Modify Tests (ACT MODE):**
    *   **Tool Usage (`write_to_file`, `replace_in_file`):** Create/edit test files within the **correct layer directory** (`tests/api/`, `tests/orchestration/`, `tests/host/`).
    *   Follow the test creation strategy (start simple, use `#TODO` for planned cases).
    *   **Leverage Shared Components:** Actively use fixtures from `tests/fixtures/` and mocks from `tests/mocks/` where applicable. Utilize fixtures defined in root or layer-specific `conftest.py`.
    *   Follow project conventions (e.g., naming like `test_component_unit.py`, `test_component_integration.py`).

3.  **Test Execution and Iteration (ACT MODE):**
    *   **Tool Usage (`execute_command`):**
        *   **Targeted Run:** Run tests within the specific file being worked on (e.g., `pytest tests/orchestration/agent/test_agent.py`).
        *   **Layer Run:** Run all tests for the layer being modified (e.g., `pytest tests/orchestration/`).
        *   **Failure Handling:** If a test fails, analyze, fix, and re-run *only the failed test* (`pytest path/to/test_file.py::test_name`). If multiple fail, analyze collectively, fix one, re-run failed, repeat.
        *   **Post-Fix Verification:** Re-run tests in the modified file or layer scope.
        *   **Full Suite:** Periodically run the entire test suite (`pytest tests/`) to catch cross-layer regressions.
    *   **Known Issue (Anyio Shutdown):** Be aware of potential `anyio` errors during MCP client shutdown in test teardown phases. These often relate to `AsyncExitStack` context management across tasks. If a test fails *only* during teardown with such an error, and the core test logic passed, it can often be marked with `@pytest.mark.xfail(reason="Known anyio shutdown issue")` after confirming it's not impacting test validity. Discuss with Ryan if unsure.

4.  **Analyze Results & Iterate (ACT MODE / PLAN MODE):**
    *   Follow the global rules for analyzing results (coverage, refactoring tests, debugging failures).
    *   If failures point to source code bugs, potentially switch back to Implementation/Debugging phases.
    *   **Tool Usage (`attempt_completion` / `ask_followup_question`):** Report results to Ryan.

## 5. Tool Usage Specifics

*   Aligns with the global `comprehensive_testing_rules.md`, emphasizing placing files in correct layer directories.

## 6. Considerations for Mocks & Fixtures

*   **Prioritize Reuse:** Before creating new mocks or fixtures, check `tests/mocks/`, `tests/fixtures/`, and relevant `conftest.py` files.
*   **Scope Appropriately:** Define fixtures in the most specific `conftest.py` possible (layer-specific before root) unless truly global utility is needed.
*   **Clarity:** Ensure mocks accurately represent the contract of the mocked object.

