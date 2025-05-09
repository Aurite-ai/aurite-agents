# Implementation Plan: Configuration System Refactor

**Objective:** Refactor the configuration management and execution flow to align with the new design specified in `docs/design/configuration_system.md`. This involves centralizing active project state in `ProjectManager`, simplifying `HostManager` and `MCPHost`, and ensuring `ExecutionFacade` uses the correct context.

**Key Files to Modify:**
1.  `src/host/host.py` (`MCPHost`)
2.  `src/config/project_manager.py` (`ProjectManager`)
3.  `src/host_manager.py` (`HostManager`)
4.  `src/execution/facade.py` (`ExecutionFacade`)
5.  `src/bin/api/routes/project_api.py`
6.  `src/bin/api/routes/components_api.py` (for dynamic registration calls)
7.  `src/bin/dependencies.py`
8.  Associated test files for each of the above.

**Unaffected Core Files (as per current understanding):**
*   `src/config/config_models.py`
*   `src/config/component_manager.py`
*   `src/agents/agent.py`
*   `src/workflows/custom_workflow.py`
*   `src/llm/*`

**Potentially Minor Changes:**
*   `src/workflows/simple_workflow.py` (Simplifying `__init__` signature).

---

## Implementation Steps (Order of Execution)

**General Testing Note:** After completing the code changes for each primary source file (e.g., `MCPHost`, `ProjectManager`), the corresponding test files should be updated. These tests must be run, reviewed for correctness (i.e., they are testing the new logic appropriately), and any failures fixed before proceeding to the next step.

---

### **Phase 1: `MCPHost` Simplification**
*   **Goal:** Remove agent configuration storage from `MCPHost` as it's no longer needed directly by `MCPHost` for its core operations. Agent-specific context for filtering will be passed directly to its methods by `ExecutionFacade`.
*   **File:** `src/host/host.py`
    1.  **Modify `MCPHost.__init__`**:
        *   Remove the `agent_configs: Optional[Dict[str, AgentConfig]] = None` parameter from the signature.
        *   Remove the line `self._agent_configs = agent_configs or {}`.
    2.  **Remove `MCPHost.get_agent_config()` method.**
    3.  **Verification**: Double-check that no other internal `MCPHost` methods were relying on `self._agent_configs` or `self.get_agent_config()`. The primary consumers (like `execute_tool`, `get_prompt`) already accept an `agent_config` parameter.
*   **Testing (`MCPHost`):**
    1.  **Update `tests/host/test_host_basic.py`, `tests/host/test_host_dynamic_registration.py`, and any other tests that directly instantiate or interact with `MCPHost`:**
        *   Adjust `MCPHost` instantiation in test setups/fixtures to no longer pass the `agent_configs` argument.
        *   Remove any tests that specifically targeted `MCPHost.get_agent_config()`.
        *   Ensure that tests for methods like `execute_tool`, `get_prompt`, etc., are updated to correctly mock or provide the `agent_config: Optional[AgentConfig]` parameter if they were implicitly relying on the host's internal storage before.
    2.  **Run relevant tests:** Execute `pytest tests/host/`. Review logs, fix any failures, and ensure all pass.

---

### **Phase 2: `ProjectManager` Enhancement**
*   **Goal:** Repurpose `ProjectManager` to be the stateful manager of the *currently active* `ProjectConfig`.
*   **File:** `src/config/project_manager.py`
    1.  **Modify `ProjectManager.__init__`**:
        *   Add the attribute: `self.active_project_config: Optional[ProjectConfig] = None`.
    2.  **Modify `ProjectManager.load_project(project_config_file_path: Path) -> ProjectConfig`**:
        *   After the `project_config = ProjectConfig(...)` line (where the object is successfully created), add:
            ```python
            self.active_project_config = project_config
            logger.info(f"Project '{project_config.name}' set as active in ProjectManager.")
            ```
        *   The method should continue to return the `project_config` object.
    3.  **Add `ProjectManager.unload_active_project()` method**:
        ```python
        def unload_active_project(self):
            if self.active_project_config:
                logger.info(f"Unloading active project '{self.active_project_config.name}' from ProjectManager.")
                self.active_project_config = None
            else:
                logger.info("No active project to unload from ProjectManager.")
        ```
    4.  **Add `ProjectManager.get_active_project_config() -> Optional[ProjectConfig]` method**:
        ```python
        def get_active_project_config(self) -> Optional[ProjectConfig]:
            return self.active_project_config
        ```
    5.  **Add `ProjectManager.get_host_config_for_active_project() -> Optional[HostConfig]` method**:
        ```python
        from .config_models import HostConfig # Ensure HostConfig is imported

        def get_host_config_for_active_project(self) -> Optional[HostConfig]:
            if not self.active_project_config:
                logger.warning("Cannot get HostConfig: No active project loaded in ProjectManager.")
                return None
            return HostConfig(
                name=self.active_project_config.name,
                description=self.active_project_config.description,
                clients=list(self.active_project_config.clients.values())
            )
        ```
    6.  **Add `ProjectManager.add_component_to_active_project(component_type_key: str, component_id: str, component_model: BaseModel)` method**:
        ```python
        from pydantic import BaseModel # Ensure BaseModel is imported

        def add_component_to_active_project(self, component_type_key: str, component_id: str, component_model: BaseModel):
            if not self.active_project_config:
                logger.error("Cannot add component: No active project loaded in ProjectManager.")
                raise RuntimeError("No active project to add component to.")

            target_dict = getattr(self.active_project_config, component_type_key, None)
            if target_dict is None or not isinstance(target_dict, dict):
                logger.error(f"Invalid component_type_key '{component_type_key}' for active_project_config.")
                raise ValueError(f"Invalid component type key: {component_type_key}")

            target_dict[component_id] = component_model
            logger.info(f"Component '{component_id}' of type '{component_type_key}' added to active project '{self.active_project_config.name}'.")
        ```
*   **Testing (`ProjectManager`):**
    1.  **Update `tests/config/test_project_manager.py`**:
        *   Add new test cases to verify the stateful behavior:
            *   After `load_project`, check that `get_active_project_config()` returns the loaded project.
            *   Test `unload_active_project()` correctly sets `active_project_config` to `None`.
            *   Test `get_host_config_for_active_project()` returns a correctly structured `HostConfig` or `None`.
            *   Test `add_component_to_active_project` correctly adds components (e.g., a new `AgentConfig`, `ClientConfig`) to the `active_project_config`'s respective dictionaries. Test edge cases like trying to add to no active project.
    2.  **Run tests:** Execute `pytest tests/config/test_project_manager.py`. Review, fix, and ensure all pass.

---

### **Phase 3: `HostManager` and `ExecutionFacade` Refactor**
*   **Goal:** Decouple `ExecutionFacade` from the broader `HostManager` class by passing explicit dependencies (`MCPHost` instance, `ProjectConfig` object). Simplify `HostManager` to use `ProjectManager` for managing active configuration state.
*   **Files:** `src/execution/facade.py` (ExecutionFacade), `src/host_manager.py` (HostManager)

    **3.1. `ExecutionFacade` Changes (`src/execution/facade.py`)**:
    1.  **Modify `ExecutionFacade.__init__`**:
        *   Change signature from `(self, host_manager: "HostManager", storage_manager: Optional["StorageManager"] = None)` to:
            ```python
            from ..config.config_models import ProjectConfig, AgentConfig, LLMConfig, WorkflowConfig, CustomWorkflowConfig # Add necessary imports
            # ...
            def __init__(
                self,
                host_instance: "MCPHost",
                current_project: ProjectConfig,
                storage_manager: Optional["StorageManager"] = None,
            ):
            ```
        *   Store `self._host = host_instance`.
        *   Store `self._current_project = current_project`.
        *   Remove `self._manager` attribute.
        *   Update initial validation:
            ```python
            if not host_instance:
                raise ValueError("MCPHost instance is required for ExecutionFacade.")
            if not current_project:
                raise ValueError("Current ProjectConfig is required for ExecutionFacade.")
            ```
    2.  **Update `ExecutionFacade.run_agent()`**:
        *   Change config lookups:
            *   `agent_config = self._current_project.agent_configs.get(agent_name)`
            *   `llm_config_for_override_obj = self._current_project.llm_configs.get(agent_config.llm_config_id)`
        *   When instantiating `Agent`, ensure `host_instance=self._host` is used.
    3.  **Update `ExecutionFacade.run_simple_workflow()`**:
        *   The `config_lookup` callable should become: `lambda name: self._current_project.simple_workflow_configs.get(name)`.
        *   When setting up `SimpleWorkflowExecutor` in `executor_setup`:
            *   Pass `agent_configs=self._current_project.agent_configs`.
            *   Pass `host_instance=self._host`.
    4.  **Update `ExecutionFacade.run_custom_workflow()`**:
        *   The `config_lookup` callable should become: `lambda name: self._current_project.custom_workflow_configs.get(name)`.
    5.  **Review `ExecutionFacade._execute_component()`**: Ensure its `config_lookup` and `executor_setup` parameters are compatible with these changes (they should be, as they are callables).

    **3.2. `HostManager` Changes (`src/host_manager.py`)**:
    1.  **Remove Attributes**: Delete `self.agent_configs`, `self.llm_configs`, `self.workflow_configs`, `self.custom_workflow_configs`. Also, `self.current_project` can be removed if all accesses go through `self.project_manager.get_active_project_config()`. For clarity during transition, we might keep `self.current_project` but ensure it's just a reference to `self.project_manager.active_project_config`. *Decision: Let's aim to remove `self.current_project` from `HostManager` and always use `self.project_manager.get_active_project_config()`.*
    2.  **Modify `HostManager.initialize()`**:
        *   After `self.project_manager.load_project(self.config_path)`, get the active project: `active_project = self.project_manager.get_active_project_config()`.
        *   If `active_project` is `None`, raise a `RuntimeError("Failed to load project into ProjectManager.")`.
        *   Remove the lines that copy configs from `active_project` to the now-deleted `self.agent_configs`, etc.
        *   When instantiating `MCPHost`:
            *   `host_cfg_for_mcphost = self.project_manager.get_host_config_for_active_project()`. If `None`, raise error.
            *   `self.host = MCPHost(config=host_cfg_for_mcphost)` (no `agent_configs` argument).
        *   When instantiating `ExecutionFacade`:
            *   `self.execution = ExecutionFacade(host_instance=self.host, current_project=active_project, storage_manager=self.storage_manager)`.
        *   Update DB sync: `self.storage_manager.sync_all_configs(agents=active_project.agent_configs, llm_configs=active_project.llm_configs, ...)`
    3.  **Modify `HostManager.unload_project()`**:
        *   After `await self.host.shutdown()` (with existing robust error handling) and `self.host = None`:
            *   Call `self.project_manager.unload_active_project()`.
            *   Set `self.execution = None`.
    4.  **Modify Dynamic Registration Methods**:
        *   `register_client(self, client_config_data: Dict)`:
            1.  Parse `client_config_data` to `ClientConfig` model.
            2.  Call `await self.host.register_client(client_config_model)`.
            3.  If successful: `self.project_manager.add_component_to_active_project("clients", client_config_model.client_id, client_config_model)`.
        *   `register_agent(self, agent_config_data: Dict)`:
            1.  Parse `agent_config_data` to `AgentConfig` model.
            2.  Validate:
                *   `active_project = self.project_manager.get_active_project_config()`. If `None`, raise error.
                *   Check `client_ids` against `self.host.is_client_registered()`.
                *   Check `llm_config_id` against `active_project.llm_configs`.
            3.  If valid: `self.project_manager.add_component_to_active_project("agent_configs", agent_config_model.name, agent_config_model)`.
            4.  DB Sync: `self.storage_manager.sync_agent_config(agent_config_model)` (if `storage_manager` exists).
        *   Similar logic for `register_llm_config`, `register_workflow`, `register_custom_workflow`, ensuring they fetch `active_project` from `ProjectManager` for validation and then update it.
    5.  **Modify Config Access Methods (e.g., `get_agent_config`)**:
        *   `get_agent_config(self, agent_name: str) -> Optional[AgentConfig]`:
            ```python
            active_project = self.project_manager.get_active_project_config()
            if active_project and active_project.agent_configs:
                return active_project.agent_configs.get(agent_name)
            return None
            ```
        *   Similar for `get_llm_config`.

    **3.3. `SimpleWorkflowExecutor` Simplification (`src/workflows/simple_workflow.py`)**:
    1.  **Modify `SimpleWorkflowExecutor.__init__`**:
        *   Remove `llm_client: "BaseLLM"` and `host_instance: MCPHost` parameters.
        *   Remove `self._llm_client` and `self._host` attributes.
    2.  **Update `ExecutionFacade.run_simple_workflow`**:
        *   In `executor_setup`, when creating `SimpleWorkflowExecutor`, do not pass `llm_client` or `host_instance`. It already correctly passes `agent_configs=self._current_project.agent_configs` and `facade=self`.

*   **Testing (`HostManager`, `ExecutionFacade`, `SimpleWorkflowExecutor`):**
    1.  **Update `tests/orchestration/test_host_manager*.py` and `tests/fixtures/host_fixtures.py`**:
        *   The `host_manager` fixture in `host_fixtures.py` will need to correctly set up the `ProjectManager` and `MCPHost` according to the new `HostManager.initialize()` logic.
        *   Tests that assert on `host_manager.agent_configs` (etc.) will need to be updated to check `host_manager.project_manager.get_active_project_config().agent_configs`.
        *   Verify dynamic registration tests correctly update `ProjectManager.active_project_config`.
        *   Ensure `change_project` tests confirm that `ExecutionFacade` is re-instantiated with the new context.
    2.  **Update `ExecutionFacade` tests** (if any direct unit tests exist).
    3.  **Update `SimpleWorkflowExecutor` tests** for its changed `__init__` signature.
    4.  Run tests: `pytest tests/orchestration/`, `pytest tests/workflows/`. Review, fix, pass.

---

### **Phase 4: API Layer Adjustments**
*   **Goal:** Ensure API routes and dependencies correctly interface with the refactored `HostManager`.
*   **Files:** `src/bin/api/routes/project_api.py`, `src/bin/api/routes/components_api.py`, `src/bin/dependencies.py`.

    1.  **`src/bin/dependencies.py`**:
        *   Add `get_project_manager` dependency:
            ```python
            def get_project_manager(hm: HostManager = Depends(get_host_manager)) -> ProjectManager:
                if not hm.project_manager: # Should always exist if HostManager is initialized
                    logger.error("ProjectManager not found on HostManager instance.")
                    raise HTTPException(status_code=503, detail="ProjectManager not available.")
                return hm.project_manager
            ```
    2.  **API Routes for Dynamic Registration (e.g., in `src/bin/api/routes/components_api.py`)**:
        *   These routes should continue to `Depends(get_host_manager)` and call the respective `host_manager.register_client()`, `host_manager.register_agent()`, etc. methods. No significant changes expected here as `HostManager` still exposes these top-level orchestration methods.
    3.  **Project API (`src/bin/api/routes/project_api.py`)**:
        *   In `change_project` endpoint, update response message construction:
            ```python
            # After await manager.change_project(new_path)
            active_project = manager.project_manager.get_active_project_config()
            project_name_for_response = active_project.name if active_project else "Unknown"
            return {
                "status": "success",
                "message": f"Successfully changed project to {project_name_for_response}",
                "current_project_path": str(manager.config_path),
            }
            ```
*   **Testing (API):**
    1.  **Update `tests/api/routes/test_project_api.py`**:
        *   The `test_change_project_success` should pass if all underlying refactors are correct. Verify assertions related to the response message and project state (e.g., listed agents after change).
    2.  **Update `tests/api/routes/test_components_api.py`**:
        *   Ensure dynamic registration tests continue to pass.
    3.  Run all API tests: `pytest tests/api/`. Review, fix, pass.

---

### **Phase 5: Final Review and Documentation Update**
*   **Goal:** Ensure the implemented system aligns with the design and all documentation is updated.
    1.  Thoroughly review all code changes against the `docs/design/configuration_system.md`.
    2.  Update `docs/design/configuration_system.md` to reflect any necessary deviations or improvements discovered and implemented.
    3.  Review and update any other relevant documentation (e.g., READMEs, inline docstrings that might refer to old structures).
    4.  Perform a final round of full test suite execution (`pytest`).

---
