# Implementation Plan: Aura Configuration & Lifecycle System

**Version:** 1.0
**Date:** 2025-07-02
**Author(s):** Gemini, Ryan
**Related Design Document:** [Aura Configuration & Lifecycle System](docs/design/aura_configuration_and_lifecycle.md)

## 1. Goals

*   To implement the new Aura architecture as specified in the design document.
*   To refactor the framework to use the new `ConfigService`, `HostService`, and `LifecycleService`.
*   To implement Just-in-Time (JIT) component registration within the `ExecutionFacade`.
*   To ensure all existing functionality is preserved and all tests pass after the rebuild.

## 2. Scope

*   **In Scope:**
    *   Creation of a new `ConfigService` module.
    *   Significant refactoring of `src/aurite/host_manager.py` to become the new `Aurite` lifecycle service class.
    *   Significant refactoring of `src/aurite/execution/facade.py` to implement JIT logic.
    *   Deletion of `src/aurite/config/project_manager.py` and `src/aurite/config/component_manager.py`, as their responsibilities will be absorbed by the new `ConfigService`.
    *   Modification of `src/aurite/host/host.py` to simplify its interface.
    *   Updating all relevant tests to reflect the new architecture.
*   **Out of Scope:**
    *   Implementing a cloud-based configuration registry (the design will be extensible for it, but the implementation is deferred).
    *   Adding new component types beyond what currently exists.

## 3. Implementation Steps

This implementation is broken down into phases to ensure a logical and testable progression.

### Phase 1: Build the `ConfigManager`

The foundation of the new architecture is the `ConfigManager`. We will build this first as a self-contained unit.

1.  **Step 1.1: Create and Implement `ConfigManager`**
    *   **Action:** Rename `src/aurite/config/service.py` to `src/aurite/config/config_manager.py`.
    *   **Action:** Rename the class to `ConfigManager`.
    *   **Action:** Implement the constructor to read the `AURITE_CONFIG_FORCE_REFRESH` environment variable (defaulting to `true`).
    *   **Action:** Implement the `_initialize_sources` method to build the hierarchical list of configuration paths.
    *   **Action:** Implement the `_build_component_index` method. This method will scan all files in the source paths.
    *   **Action:** Implement the `_parse_and_index_file` helper. This method will parse each file and inspect its content to identify all components within (e.g., `llms`, `agents`), adding them to the `_component_index` dictionary. This supports both monolithic and modular files.
    *   **Verification:** Create a unit test `tests/unit/config/test_config_manager.py` that verifies the hierarchical loading, content-driven discovery, and correct indexing of components from various file types and structures.

2.  **Step 1.2: Implement Caching and Public API**
    *   **File(s):** `src/aurite/config/config_manager.py`
    *   **Action:** Implement the public methods `get_config(component_type, component_id)` and `list_configs(component_type)`.
    *   **Action:** The `get_config` method will incorporate the caching logic. If `AURITE_CONFIG_FORCE_REFRESH` is true, it will call `refresh()` before retrieving the config. Otherwise, it will serve from the in-memory index.
    *   **Action:** Implement the `refresh()` method, which clears the internal index and re-runs the `_build_component_index` method.
    *   **Verification:** Add unit tests to `test_config_manager.py` to verify the caching behavior and the `refresh` functionality.

### Phase 2: Decouple and Refactor Core Services

With the `ConfigService` built, we can now refactor the existing classes to align with the new design.

1.  **Step 2.1: Simplify `MCPHost` (`HostService`)**
    *   **File(s):** `src/aurite/host/host.py`
    *   **Action:** Remove any methods related to loading or managing configuration. The `MCPHost` should only be concerned with runtime operations. Its constructor should be simplified to not require a complex `HostConfig` object if possible.
    *   **Action:** Ensure the `register_client` method is clean and accepts a `ClientConfig` object directly.
    *   **Verification:** Update the unit tests for `MCPHost` (`tests/integration/host/test_mcp_host.py`) to reflect its simplified, runtime-only role.

2.  **Step 2.2: Refactor `host_manager.py` into the new `Aurite` Lifecycle Service**
    *   **File(s):** `src/aurite/host_manager.py`
    *   **Action:** We will keep the `Aurite` class name but completely overhaul its implementation to serve as the new lifecycle service.
    *   **Action:** The new `__init__` will instantiate `ConfigService`, `MCPHost`, and `ExecutionFacade`. It will no longer call `project_manager.load_project`.
    *   **Action:** The `run_agent` and `run_workflow` methods will be simplified to be direct pass-through calls to the `ExecutionFacade` instance.
    *   **Verification:** Update the relevant integration tests to use the new `Aurite` class initialization and execution flow.

### Phase 3: Implement JIT Logic in `ExecutionFacade`

This is the most critical phase, where the JIT registration is implemented.

1.  **Step 3.1: Refactor `ExecutionFacade` Constructor**
    *   **File(s):** `src/aurite/execution/facade.py`
    *   **Action:** Modify the constructor to accept instances of the `ConfigService` and `HostService` instead of the `ProjectConfig`.
    *   **Verification:** Update tests that instantiate `ExecutionFacade` to pass the new service dependencies.

2.  **Step 3.2: Implement JIT Logic in `run_agent`**
    *   **File(s):** `src/aurite/execution/facade.py`
    *   **Action:** Before the main execution logic in `run_agent`, implement the JIT workflow:
        1.  Use `self.config_service.get_config("agents", agent_name)` to get the agent's config.
        2.  Iterate through the agent's `mcp_servers` list.
        3.  For each server ID, check if it's registered in `self.host_service`.
        4.  If not registered, use `self.config_service.get_config("mcp_servers", server_id)` to get the server's config.
        5.  Call `self.host_service.register_client()` with the retrieved server config.
    *   **Verification:** Create a new integration test that uses a mock `ConfigService` and `HostService`. The test should verify that when `run_agent` is called for an agent with an unregistered server, the `register_client` method on the mock `HostService` is called exactly once with the correct `ClientConfig`.

### Phase 4: Cleanup and Finalization

1.  **Step 4.1: Delete Obsolete Files**
    *   **Action:** Delete `src/aurite/config/project_manager.py` and `src/aurite/config/component_manager.py`.
    *   **Verification:** Ensure the project still runs and all tests pass. Remove the corresponding test files.

2.  **Step 4.2: Full Test Suite Run**
    *   **Action:** Run the entire test suite for the project.
    *   **Verification:** All tests must pass. Address any failures, which are likely due to incorrect instantiation or mocking in the test files.

3.  **Step 4.3: Documentation Review**
    *   **Action:** When the implementation is complete and all tests are passing, review `.clinerules/documentation_guide.md` to identify all documents that require updates.
    *   **Action:** Read the identified documents and propose the necessary changes to reflect the new Aura architecture. Key documents will include `docs/layers/framework_overview.md`, `docs/layers/2_orchestration.md`, and `README.md`.

## 4. Testing Strategy

*   **Unit Tests:** New unit tests will be created for the `ConfigService`. Existing unit tests will be updated to reflect the refactored interfaces of `MCPHost` and the `Aurite` class.
*   **Integration Tests:** New integration tests will be created for the `ExecutionFacade` to specifically validate the JIT registration logic. Existing integration tests will be updated to use the new, simplified `Aurite` class for setting up test scenarios.
*   **Mocks:** Mocks for `ConfigService` and `HostService` will be crucial for testing the `ExecutionFacade` in isolation.
