# Overarching Cleanup and Host Filtering Feature Plan

**Version:** 1.0
**Date:** 2025-04-07

**Goal:** Systematically review and clean up the `aurite-agents` codebase after the recent major refactor, update documentation, and implement the planned MCPHost filtering feature.

---

## Phase 1: Documentation Update [COMPLETED]

**Objective:** Bring core documentation in line with the current architecture.

1.  **Update `docs/architecture_overview.md`:**
    *   Revise the System Architecture diagram and descriptions to reflect the removal of Layer 4 (Agent Framework) components like WorkflowManager from the *host's direct management*. Describe the new `Agent` class (`src/agents/agent.py`) as the component now responsible for agent execution, utilizing the host.
    *   Update Layer 3 description to remove the Storage Manager.
    *   Update Layer 2 description to reflect the consolidation into `routing.py` and removal of `transport.py`.
    *   Ensure the "Core Components" section accurately describes the focused role of `MCPHost` and the separate `Agent` framework layer.
    *   Update the "Implementation Status" section.
2.  **Update `docs/host/host_implementation.md`:**
    *   Remove sections detailing removed managers and methods (WorkflowManager, StorageManager, `prepare_prompt_with_tools`, `execute_prompt_with_tools`, memory methods).
    *   Accurately describe the current managers and their roles within the host's focused scope.
    *   Detail the new convenience methods (`get_prompt`, `execute_tool`, `read_resource`, `list_tools`, etc.) and the client discovery logic when `client_name` is not provided.
    *   Explain the `ClientConfig.exclude` feature and how it's applied during client initialization.
    *   Remove discussion points related to already removed components. Add new points if necessary based on the current state.
3.  **Review `tests/README.md`:** Ensure it accurately reflects the current testing setup, fixtures, and known issues (like the `real_mcp_host` teardown). Make minor updates if needed.

## Phase 2: Code Cleanup & Simplification [COMPLETED]

**Objective:** Improve code clarity, remove dead code, and ensure consistency after the refactor.

1.  **Review `src/host/`:**
    *   Examine `host.py` and manager classes (`roots.py`, `routing.py`, `security.py`, `prompts.py`, `resources.py`, `tools.py`).
    *   Remove any unused imports, variables, or helper functions.
    *   Simplify logic where possible (e.g., redundant checks, overly complex conditions).
    *   Improve comments and docstrings for clarity, ensuring they match the current functionality.
    *   Check for consistency in naming and patterns.
2.  **Review `src/agents/agent.py`:**
    *   Refine comments and docstrings.
    *   Ensure error handling is robust (e.g., Anthropic API errors, tool execution errors).
    *   Check for potential simplifications in the `execute_agent` loop.
3.  **Review `src/main.py` and `src/config.py`:**
    *   Verify configuration loading and usage are clear and correct.
    *   Ensure FastAPI setup (`lifespan`, dependencies, middleware) is clean.
    *   Remove any commented-out code or unused imports.
4.  **Review `src/host/models.py`:**
    *   Ensure Pydantic models are well-defined and accurately represent the configuration structure.

## Phase 3: Test Review & Refinement [COMPLETED]

**Objective:** Ensure tests are relevant, clear, and effectively cover the refactored codebase.

1.  **Review `tests/host/`:** Ensure tests target the current `MCPHost` functionality (initialization, convenience methods, exclusion logic). Update or remove tests related to deleted features.
2.  **Review `tests/agents/`:** Ensure tests focus on the `Agent` class logic, mocking the `MCPHost` appropriately for unit tests (`mock_mcp_host`) and using `real_mcp_host` for E2E tests.
3.  **Review `tests/servers/` and `tests/fixtures/`:** Verify fixtures (`host_fixtures.py`, `agent_fixtures.py`, server fixtures) are up-to-date and used correctly. Ensure `testing_config.json` aligns with the tests using `real_mcp_host`.
4.  **Improve Test Clarity:** Refactor tests for better readability and maintainability where needed.
5.  **(Optional/Deferred):** Investigate the `real_mcp_host` teardown issue if time permits or if it becomes blocking, but prioritize other phases first as it's marked `xfail`.

## Phase 4: Implement MCPHost Filtering Feature [WIP]

**Objective:** Allow `MCPHost` convenience methods to operate on a specified subset of clients.

1.  **Modify `MCPHost` Method Signatures:**
    *   Update `get_prompt`, `execute_tool`, `read_resource`, `list_tools`, `list_prompts`, `list_resources` (and potentially others like `get_clients_for_tool` if used internally by these) to accept an optional parameter, e.g., `filter_client_ids: Optional[List[str]] = None`. (Alternatively, consider accepting a `filter_config: Optional[HostConfig] = None` if filtering based on capabilities/roots within the filter is desired, but `filter_client_ids` seems simpler based on the changelog description).
2.  **Update Method Logic:**
    *   Inside each method, if `filter_client_ids` is provided, filter the set of clients considered *before* performing discovery (if `client_name` is None) or direct execution/listing.
    *   For discovery methods (e.g., finding a unique client for a tool when `client_name` is None), ensure the discovery only happens within the filtered set of clients.
    *   For listing methods (e.g., `list_tools`), ensure they only return components from the filtered set of clients.
    *   For direct execution/retrieval methods (when `client_name` *is* provided), ensure the specified `client_name` is also present in the `filter_client_ids` if the filter is active.
3.  **Add Unit Tests:** Create new tests in `tests/host/` specifically for this filtering functionality. Test cases should include:
    *   No filter applied (behaves as before).
    *   Filter applied, `client_name` specified (valid and invalid client_name within filter).
    *   Filter applied, `client_name` is None (discovery works correctly within the filtered set; handles ambiguity within the filter).
    *   Filter applied to listing methods.
    *   Empty filter list.
    *   Filter list with non-existent client IDs.
4.  **Add Integration/E2E Tests (Optional but Recommended):** Consider adding a test using `real_mcp_host` where an `Agent` instance uses the host with this filtering enabled to interact with a subset of servers defined in `testing_config.json`.

---

**Next Steps:** Review this plan with Ryan. Upon approval, proceed with Phase 1.
