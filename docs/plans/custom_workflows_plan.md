# Custom Workflows Implementation Plan

**Objective:** Implement the ability to define and execute custom Python-based workflows alongside JSON-defined agents and workflows.

**Owner:** Ryan Wilcox (assisted by Gemini)

**Status:** Proposed

**Related Docs:**
*   [Architecture Overview](docs/architecture_overview.md) (To be updated if needed)

**Background:**
Currently, workflows are defined purely in JSON as a sequence of agent names. This plan introduces "custom workflows" where users can define workflow logic in a Python file, allowing for more complex interactions, data manipulation, and control flow between steps. These custom workflows will leverage the existing `Agent` class for LLM interactions and tool usage via the `MCPHost`.

**High-Level Plan:**

1.  **Model Definition:** Define a Pydantic model (`CustomWorkflowConfig`) for custom workflow configuration.
2.  **Configuration Loading:** Update `src/config.py` to parse the new `custom_workflows` section in the JSON config file and validate using the new model.
3.  **Workflow Manager:** Create a dedicated `CustomWorkflowManager` class (`src/workflows/manager.py`) to handle loading and execution of custom workflows.
4.  **Host Refactoring:** Remove custom workflow responsibilities from `MCPHost` (`src/host/host.py`).
5.  **API Endpoint & Lifespan:** Update `src/main.py` to instantiate the `CustomWorkflowManager` during startup and modify the API endpoint to use both the manager and the host.
6.  **Testing:** Add/update unit and integration tests for the manager, configuration loading, refactored host, and API endpoint.
7.  **Documentation:** Update relevant documentation (e.g., README, architecture overview) if necessary.

**Detailed Implementation Steps:**

1.  **Define `CustomWorkflowConfig` Model:**
    *   **File:** `src/host/models.py`
    *   **Action:** Add the `CustomWorkflowConfig` class as discussed:
        ```python
        from pathlib import Path
        from pydantic import BaseModel
        from typing import Optional

        # ... (other models)

        class CustomWorkflowConfig(BaseModel):
            """
            Configuration for a custom Python-based workflow.
            """
            name: str
            module_path: Path # Resolved absolute path to the python file
            class_name: str   # Name of the class within the file implementing the workflow
            description: Optional[str] = None
        ```
    *   **Verification:** Ensure imports are correct.

2.  **Update Configuration Loading (`load_host_config_from_json`):**
    *   **File:** `src/config.py`
    *   **Action:**
        *   Import `CustomWorkflowConfig` from `src.host.models`.
        *   Modify the function signature and return type to include `Dict[str, CustomWorkflowConfig]`.
        *   Add logic to parse the `custom_workflows` list from the JSON data.
        *   For each item in `custom_workflows`:
            *   Validate the presence of `name`, `module_path`, and `class_name`. Raise `RuntimeError` if missing.
            *   Resolve the `module_path` relative to `PROJECT_ROOT_DIR`. Log a warning if the path doesn't exist, but allow loading to continue (execution will fail later).
            *   Instantiate `CustomWorkflowConfig` with the data.
            *   Store the validated config in a `custom_workflow_configs_dict` keyed by `name`.
            *   Handle potential `ValidationError` during instantiation.
        *   Return the `custom_workflow_configs_dict` along with the existing host and agent configs.
    *   **Verification:** Update unit tests in `tests/config/test_config_loading.py` to cover loading valid and invalid `custom_workflows` sections (missing keys, non-existent paths, validation errors).

3.  **Create `CustomWorkflowManager`:**
    *   **File:** `src/workflows/manager.py` (Create this file and directory `src/workflows/`)
    *   **Action:**
        *   Define the `CustomWorkflowManager` class.
        *   Add `__init__` method that takes `custom_workflow_configs: Dict[str, CustomWorkflowConfig]` and stores it.
        *   Implement `get_custom_workflow_config` method (similar to the one previously planned for `MCPHost`).
        *   Implement `execute_custom_workflow` method:
            *   This method will take `workflow_name: str`, `initial_input: Any`, and crucially `host_instance: MCPHost` as arguments.
            *   Include the logic for dynamic import (`importlib`), class instantiation, security checks (path validation), method checking (`execute_workflow`), and execution (calling `workflow_instance.execute_workflow(initial_input=initial_input, host_instance=host_instance)`).
            *   Include robust error handling (FileNotFound, ImportError, AttributeError, PermissionError, TypeError, internal workflow exceptions).
            ```python
            # Example structure in src/workflows/manager.py
            import importlib
            import inspect
            import logging
            from pathlib import Path
            from typing import Any, Dict
            from src.host.models import CustomWorkflowConfig
            from src.host.host import MCPHost # Import MCPHost for type hint
            from src.config import PROJECT_ROOT_DIR # For path validation

            logger = logging.getLogger(__name__)

            class CustomWorkflowManager:
                def __init__(self, custom_workflow_configs: Dict[str, CustomWorkflowConfig]):
                    self._custom_workflow_configs = custom_workflow_configs
                    logger.info(f"CustomWorkflowManager initialized with {len(self._custom_workflow_configs)} workflow(s).")

                def get_custom_workflow_config(self, workflow_name: str) -> CustomWorkflowConfig:
                    # ... (implementation as before) ...

                async def execute_custom_workflow(self, workflow_name: str, initial_input: Any, host_instance: MCPHost) -> Any:
                    # ... (implementation of dynamic loading and execution as before) ...
                    # Key change: Pass host_instance to the workflow's execute method
                    # result = await execute_method(initial_input=initial_input, host_instance=host_instance)
                    # ... (rest of the logic) ...
            ```
    *   **Verification:** Create unit tests in `tests/workflows/test_workflow_manager.py`. Mock `importlib`, file system, `MCPHost`, and the custom workflow class to test the manager's logic thoroughly.

4.  **Refactor `MCPHost`:**
    *   **File:** `src/host/host.py`
    *   **Action:**
        *   Remove the `custom_workflow_configs` parameter from `__init__`.
        *   Remove the `self._custom_workflow_configs` attribute.
        *   Remove the `get_custom_workflow_config` method.
        *   Remove the `execute_custom_workflow` method.
        *   Remove the clearing of `self._custom_workflow_configs` from the `shutdown` method.
        *   Remove unused imports related to custom workflows (`CustomWorkflowConfig`, `importlib`, `inspect`, `Any`, potentially `Path` if not used elsewhere).
    *   **Verification:** Run existing host unit tests (`tests/host/`) to ensure no regressions. Remove tests from `tests/host/test_host_custom_workflows.py` as this file will be deleted or repurposed for the manager tests.

5.  **Update FastAPI Lifespan and Add Endpoint:**
    *   **File:** `src/main.py`
    *   **Action:**
        *   Import `CustomWorkflowManager` from `src.workflows.manager`.
        *   Modify `lifespan` function:
            *   Update the call to `load_host_config_from_json` to receive the fourth tuple element (`custom_workflow_configs_dict`).
            *   Remove `custom_workflow_configs` from the `MCPHost` constructor call.
            *   Instantiate `CustomWorkflowManager`: `manager = CustomWorkflowManager(custom_workflow_configs_dict)`.
            *   Store the `manager` instance in `app.state.workflow_manager`.
            *   Remove storing `custom_workflow_configs_dict` in `app.state`.
            *   Ensure `workflow_manager` is cleaned up in the `finally` block (`del app.state.workflow_manager`).
        *   Add Dependency Function `get_workflow_manager`:
            ```python
            async def get_workflow_manager(request: Request) -> CustomWorkflowManager:
                manager = getattr(request.app.state, "workflow_manager", None)
                if not manager:
                    logger.error("CustomWorkflowManager not initialized or not found in app state.")
                    raise HTTPException(status_code=503, detail="WorkflowManager is not available.")
                return manager
            ```
        *   Keep Request/Response Models (`ExecuteCustomWorkflowRequest`, `ExecuteCustomWorkflowResponse`).
        *   Modify API Endpoint (`/custom_workflows/{workflow_name}/execute`):
            *   Add `manager: CustomWorkflowManager = Depends(get_workflow_manager)` dependency alongside `host: MCPHost = Depends(get_mcp_host)`.
            *   Change the core execution call to:
                ```python
                result = await manager.execute_custom_workflow(
                    workflow_name=workflow_name,
                    initial_input=request_body.initial_input,
                    host_instance=host # Pass the host instance here
                )
                ```
            *   Adjust error handling based on exceptions potentially raised by the manager.
    *   **Verification:** Update integration tests in `tests/workflows/test_custom_workflow_api.py`. Mock the `CustomWorkflowManager.execute_custom_workflow` method instead of the host's method.

6.  **Create Example Custom Workflow and Test:**
    *   **File:** `tests/fixtures/custom_workflows/example_workflow.py`
    *   **Action:** No changes needed to the example workflow itself (it already accepts `host_instance`).
    *   **File:** `config/agents/testing_config.json`
    *   **Action:** No changes needed here.
    *   **Verification:** Update the E2E test in `tests/workflows/test_custom_workflow_api.py`. It should now work without needing the explicit dependency override for `get_mcp_host`, as the dependencies (`get_mcp_host`, `get_workflow_manager`) should be resolved correctly via the updated lifespan setup and standard dependency injection. Ensure the `real_mcp_host` fixture is correctly configured and used implicitly by the app lifespan during the E2E run.

7.  **Documentation Update:**
    *   **Files:** `README.md`, `docs/architecture_overview.md` (if applicable)
    *   **Action:** Update descriptions to reflect the role of `CustomWorkflowManager`. Explain the separation between the Host and the Manager.
    *   **Verification:** Review documentation for clarity and accuracy.

**Detailed Implementation Steps:**

1.  **Define `CustomWorkflowConfig` Model:**
    *   **File:** `src/host/models.py`
    *   **Action:** Add the `CustomWorkflowConfig` class as discussed:
        ```python
        from pathlib import Path
        from pydantic import BaseModel
        from typing import Optional

        # ... (other models)

        class CustomWorkflowConfig(BaseModel):
            """
            Configuration for a custom Python-based workflow.
            """
            name: str
            module_path: Path # Resolved absolute path to the python file
            class_name: str   # Name of the class within the file implementing the workflow
            description: Optional[str] = None
        ```
    *   **Verification:** Ensure imports are correct.

2.  **Update Configuration Loading (`load_host_config_from_json`):**
    *   **File:** `src/config.py`
    *   **Action:**
        *   Import `CustomWorkflowConfig` from `src.host.models`.
        *   Modify the function signature and return type to include `Dict[str, CustomWorkflowConfig]`.
        *   Add logic to parse the `custom_workflows` list from the JSON data.
        *   For each item in `custom_workflows`:
            *   Validate the presence of `name`, `module_path`, and `class_name`. Raise `RuntimeError` if missing.
            *   Resolve the `module_path` relative to `PROJECT_ROOT_DIR`. Log a warning if the path doesn't exist, but allow loading to continue (execution will fail later).
            *   Instantiate `CustomWorkflowConfig` with the data.
            *   Store the validated config in a `custom_workflow_configs_dict` keyed by `name`.
            *   Handle potential `ValidationError` during instantiation.
        *   Return the `custom_workflow_configs_dict` along with the existing host and agent configs.
