# Implementation Plan: Simplify Project Configuration Keys

**Objective:** Simplify keys in project configuration files (`config/projects/*.json`) and the corresponding `ProjectConfig` Pydantic model by removing `_configs` suffixes (e.g., `agent_configs` becomes `agents`) and making `llm_configs` consistently `llms`.

**Affected Keys:**
*   `agent_configs` -> `agents`
*   `simple_workflow_configs` -> `simple_workflows`
*   `custom_workflow_configs` -> `custom_workflows`
*   `llm_configs` -> `llms`
*   (`clients` will remain unchanged unless specified otherwise).

## Phase 1: Update Core Data Model (`ProjectConfig`)

**Target File:** `src/config/config_models.py`

1.  **Modify `ProjectConfig` Pydantic Model:**
    *   Rename the field `llm_configs: Dict[str, LLMConfig]` to `llms: Dict[str, LLMConfig]`.
    *   Rename the field `agent_configs: Dict[str, AgentConfig]` to `agents: Dict[str, AgentConfig]`.
    *   Rename the field `simple_workflow_configs: Dict[str, WorkflowConfig]` to `simple_workflows: Dict[str, WorkflowConfig]`.
    *   Rename the field `custom_workflow_configs: Dict[str, CustomWorkflowConfig]` to `custom_workflows: Dict[str, CustomWorkflowConfig]`.
    *   Ensure all type hints and default values (if any) are correctly transferred.

## Phase 2: Update `ProjectManager` Logic

**Target File:** `src/config/project_manager.py`

1.  **Modify `_parse_and_resolve_project_data` method:**
    *   In the calls to `self._resolve_components`:
        *   Change `project_key="llm_configs"` to `project_key="llms"`.
        *   Change `project_key="agent_configs"` to `project_key="agents"`.
        *   Change `project_key="simple_workflow_configs"` to `project_key="simple_workflows"`.
        *   Change `project_key="custom_workflow_configs"` to `project_key="custom_workflows"`.
    *   When instantiating `ProjectConfig` at the end of this method, ensure the resolved dictionaries are passed to the new field names:
        ```python
        project_config = ProjectConfig(
            # ... other fields
            llms=resolved_llm_configs,
            agents=resolved_agents,
            simple_workflows=resolved_simple_workflows,
            custom_workflows=resolved_custom_workflows,
            # ...
        )
        ```

2.  **Modify `add_component_to_active_project` method:**
    *   The `component_type_key` argument (e.g., `"llms"`, `"agents"`) passed to this method will now directly match the new attribute names on `ProjectConfig`.
    *   The line `target_dict = getattr(self.active_project_config, component_type_key, None)` should work correctly.
    *   Verify that the `component_type_key` values used by callers (likely `HostManager`) align with these new short names (e.g., check `COMPONENT_META` keys if they are used for this).

3.  **Modify `create_project_file` method:**
    *   When constructing the `ProjectConfig` model instance within this method, use the new field names:
        ```python
        project_config_model = ProjectConfig(
            # ...
            llms=llms_dict, # if llms_dict is derived from llm_configs input
            agents=agents_dict,
            simple_workflows=simple_workflows_dict,
            custom_workflows=custom_workflows_dict,
            # ...
        )
        ```
    *   The input arguments to `create_project_file` (e.g., `llm_configs: Optional[List[LLMConfig]]`) can remain as is for now, with the mapping to the new field names happening internally during `ProjectConfig` instantiation, or they can be updated for consistency.

## Phase 3: Update Consumers of `ProjectConfig`

1.  **Target File: `src/host_manager.py`**
    *   Globally search for `active_project_config.llm_configs` and replace with `active_project_config.llms`.
    *   Globally search for `active_project_config.agent_configs` and replace with `active_project_config.agents`.
    *   Globally search for `active_project_config.simple_workflow_configs` and replace with `active_project_config.simple_workflows`.
    *   Globally search for `active_project_config.custom_workflow_configs` and replace with `active_project_config.custom_workflows`.
    *   Pay attention to any logic that might be dynamically constructing these attribute names.

2.  **Target File: `src/execution/facade.py`**
    *   Perform the same search and replace operations for `self._current_project.llm_configs`, `self._current_project.agent_configs` etc., on its `ProjectConfig` instance.

## Phase 4: Update Project Configuration Files

1.  **Action:** Manually or via a script, update all existing `*.json` files within the `config/projects/` directory.
    *   Change the key `"llm_configs"` to `"llms"`.
    *   Change the key `"agent_configs"` to `"agents"`.
    *   Change the key `"simple_workflow_configs"` to `"simple_workflows"`.
    *   Change the key `"custom_workflow_configs"` to `"custom_workflows"`.
    *   Example: `config/projects/testing_config.json` will need these changes.

## Phase 5: Update Tests

1.  **Action:** Review and update all tests across the codebase:
    *   **Unit tests for `ProjectConfig`**: Reflect new field names.
    *   **Unit tests for `ProjectManager`**: Update mock project data and assertions.
    *   **Unit tests for `HostManager` and `ExecutionFacade`**: Update mocks and assertions related to `ProjectConfig`.
    *   **Integration/API tests**: Update any test payloads or expected structures for project configurations.

## Phase 6: Documentation (Minor Update)

1.  **Target File:** `docs/design/configuration_system.md`
    *   Briefly update any explicit mentions of the old suffixed keys (including `llm_configs`) in the context of `ProjectConfig` fields or project file examples to reflect the new, simpler keys.

This refactoring will improve the clarity and ergonomics of project configuration files.
