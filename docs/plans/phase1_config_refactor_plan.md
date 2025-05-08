# Phase 1: Core Configuration System Refactor - Detailed Implementation Plan

**Overall Goal:** Establish the new `ConfigManager` and `ProjectConfig` model as the foundation for how configurations are loaded and accessed throughout the system. This primarily addresses Task 3 from the initial requirements.

**Relevant Files (Initial State):**
*   `src/host/models.py` (to be moved and refactored)
*   `src/config.py` (to be moved and refactored)
*   `src/host_manager.py` (to be refactored to use `ConfigManager`)
*   `src/bin/api/routes/config_api.py` (to be refactored to use `ConfigManager`)

**New Files/Directories to be Created:**
*   `src/config/` (directory)
*   `src/config/config_models.py`
*   `src/config/config.py`
*   `src/config/config_manager.py`

---

## Implementation Steps:

**Step 1.1: Create `src/config/` Directory and Relocate Core Config Files**

*   **1.1.1. Create New Directory:**
    *   **Action:** Create the directory `src/config/`.
    *   **Verification:** Directory `src/config/` exists.
*   **1.1.2. Move and Rename `models.py`:**
    *   **Action:** Move `src/host/models.py` to `src/config/config_models.py`.
    *   **Verification:** `src/host/models.py` no longer exists. `src/config/config_models.py` exists with the original content.
*   **1.1.3. Update Imports for `config_models.py`:**
    *   **Action:** Search across the entire project (e.g., `src/`, `tests/`) for imports like `from src.config.config_models import ...` or `from ..host.models import ...`.
    *   **Action:** Update these imports to `from src.config.config_models import ...` or `from ..config.config_models import ...` as appropriate based on the file location.
    *   **Key Files to Check (non-exhaustive):**
        *   `src/config.py` (soon to be `src/config/config.py`)
        *   `src/host_manager.py`
        *   `src/agents/agent.py` (and `conversation_manager.py`)
        *   `src/agents/agent_turn_processor.py`
        *   `src/llm/base_client.py`
        *   `src/execution/facade.py`
        *   Relevant test files.
    *   **Verification:** Project runs basic commands (e.g., linter, potentially some simple tests that rely on these models) without import errors related to these models.
*   **1.1.4. Move and Rename `config.py`:**
    *   **Action:** Move `src/config.py` to `src/config/config.py`.
    *   **Verification:** `src/config.py` (old location) no longer exists. `src/config/config.py` (new location) exists with the original content.
*   **1.1.5. Update Imports for `config.py`:**
    *   **Action:** Search across the project for imports like `from src.config import ...` (e.g., `load_host_config_from_json`, `PROJECT_ROOT_DIR`, `ServerConfig`).
    *   **Action:** Update these to `from src.config.config import ...`.
    *   **Key Files to Check (non-exhaustive):**
        *   `src/host_manager.py`
        *   `src/bin/api/routes/config_api.py`
        *   `src/bin/cli.py` (if it uses `ServerConfig` or `PROJECT_ROOT_DIR`)
        *   `src/bin/worker.py` (if it uses `ServerConfig`)
        *   Relevant test files.
    *   **Verification:** Project runs basic commands without import errors related to these elements.

---

**Step 1.2: Define `ProjectConfig` Model**

*   **File:** `src/config/config_models.py`
*   **1.2.1. Add `ProjectConfig` Class:**
    *   **Action:** Add the `ProjectConfig` Pydantic model definition as discussed in the overarching plan:
        ```python
        from pydantic import BaseModel, Field # Ensure BaseModel is imported
        from typing import Dict, Optional, List # Ensure these are imported
        # ... other model imports like ClientConfig, LLMConfig, AgentConfig, WorkflowConfig, CustomWorkflowConfig

        class ProjectConfig(BaseModel):
            name: str
            description: Optional[str] = None
            clients: Dict[str, ClientConfig] = Field(default_factory=dict)
            llm_configs: Dict[str, LLMConfig] = Field(default_factory=dict)
            agent_configs: Dict[str, AgentConfig] = Field(default_factory=dict)
            simple_workflow_configs: Dict[str, WorkflowConfig] = Field(default_factory=dict) # Renamed from workflow_configs for clarity
            custom_workflow_configs: Dict[str, CustomWorkflowConfig] = Field(default_factory=dict)
            # Consider if counters are needed here or are runtime state in HostManager
        ```
    *   **Note:** Changed default values to `Field(default_factory=dict)` for mutable defaults.
    *   **Consideration:** The existing `HostConfig` model might be deprecated or simplified later if `ProjectConfig` fully covers its role. For now, both will exist.
    *   **Verification:** The model is syntactically correct.

---

**Step 1.3: Implement `ConfigManager` Stub and Core Logic**

*   **File:** `src/config/config_manager.py`
*   **1.3.1. Create `ConfigManager` Class Stub:**
    *   **Action:** Create the file and the basic class structure:
        ```python
        import logging
        from pathlib import Path
        from typing import Dict, Any, Optional, List, Tuple # Add List, Tuple as needed
        import json

        from .config_models import ( # Relative import
            ProjectConfig,
            ClientConfig,
            LLMConfig,
            AgentConfig,
            WorkflowConfig,
            CustomWorkflowConfig,
            # Potentially HostConfig if it's used by ConfigManager directly
        )
        # Import load_host_config_from_json and its helpers if they are to be adapted
        # from .config import _load_client_configs, _load_agent_configs, etc. OR refactor them here.
        # For now, assume we'll adapt parts of load_host_config_from_json's logic.

        logger = logging.getLogger(__name__)

        # Define component base directories relative to project root (similar to config_api.py)
        # This needs access to PROJECT_ROOT_DIR, which might be defined in src/config/config.py
        try:
            from .config import PROJECT_ROOT_DIR
        except ImportError:
            # Fallback or error if PROJECT_ROOT_DIR is not found.
            # This indicates a potential issue with how PROJECT_ROOT_DIR is defined/accessed.
            # For now, assume it's accessible.
            logger.error("PROJECT_ROOT_DIR not found. ConfigManager may not function correctly.")
            PROJECT_ROOT_DIR = Path(".") # Placeholder, needs proper resolution

        COMPONENT_TYPES_DIRS = {
            "clients": PROJECT_ROOT_DIR / "config/clients",
            "llm_configs": PROJECT_ROOT_DIR / "config/llms", # Assuming a new dir for LLM components
            "agents": PROJECT_ROOT_DIR / "config/agents",
            "simple_workflows": PROJECT_ROOT_DIR / "config/workflows", # Existing dir for simple workflows
            "custom_workflows": PROJECT_ROOT_DIR / "config/custom_workflows",
        }

        class ConfigManager:
            def __init__(self):
                self.component_clients: Dict[str, ClientConfig] = {}
                self.component_llm_configs: Dict[str, LLMConfig] = {}
                self.component_agents: Dict[str, AgentConfig] = {}
                self.component_simple_workflows: Dict[str, WorkflowConfig] = {}
                self.component_custom_workflows: Dict[str, CustomWorkflowConfig] = {}

                self._load_all_components()
                logger.info("ConfigManager initialized and all components loaded.")

            def _load_all_components(self):
                # Iterates through COMPONENT_TYPES_DIRS
                # For each type, lists .json files, reads, parses, and stores them
                # in the respective self.component_* dictionaries.
                for component_type, component_dir in COMPONENT_TYPES_DIRS.items():
                    component_dir.mkdir(parents=True, exist_ok=True) # Ensure dir exists
                    for file_path in component_dir.glob("*.json"):
                        try:
                            with open(file_path, "r") as f:
                                data = json.load(f)

                            # Determine ID field and Pydantic model based on component_type
                            component_id = None
                            model_class = None
                            target_dict = None

                            if component_type == "clients":
                                component_id = data.get("client_id")
                                model_class = ClientConfig
                                target_dict = self.component_clients
                            elif component_type == "llm_configs":
                                component_id = data.get("llm_id")
                                model_class = LLMConfig
                                target_dict = self.component_llm_configs
                            elif component_type == "agents":
                                component_id = data.get("name")
                                model_class = AgentConfig
                                target_dict = self.component_agents
                            elif component_type == "simple_workflows":
                                component_id = data.get("name")
                                model_class = WorkflowConfig
                                target_dict = self.component_simple_workflows
                            elif component_type == "custom_workflows":
                                component_id = data.get("name")
                                model_class = CustomWorkflowConfig
                                target_dict = self.component_custom_workflows

                            if component_id and model_class is not None and target_dict is not None:
                                # Special handling for paths in ClientConfig and CustomWorkflowConfig
                                if component_type == "clients" and "server_path" in data:
                                    data["server_path"] = (PROJECT_ROOT_DIR / data["server_path"]).resolve()
                                if component_type == "custom_workflows" and "module_path" in data:
                                    data["module_path"] = (PROJECT_ROOT_DIR / data["module_path"]).resolve()

                                component_model = model_class(**data)
                                target_dict[component_id] = component_model
                            else:
                                if not component_id:
                                    logger.warning(f"Component file {file_path} missing ID field for type '{component_type}'.")
                                if model_class is None:
                                     logger.warning(f"No model class defined for component type '{component_type}' from file {file_path}.")

                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to decode JSON from component file {file_path}: {e}")
                        except Exception as e: # Catch Pydantic validation errors and others
                            logger.error(f"Failed to load component from {file_path} (type: {component_type}): {e}")
                logger.debug("_load_all_components finished.")


            def load_project(self, project_config_file_path: Path) -> ProjectConfig:
                if not project_config_file_path.is_file():
                    logger.error(f"Project configuration file not found: {project_config_file_path}")
                    raise FileNotFoundError(f"Project configuration file not found: {project_config_file_path}")

                try:
                    with open(project_config_file_path, "r") as f:
                        project_data = json.load(f)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing project configuration file {project_config_file_path}: {e}")
                    raise RuntimeError(f"Error parsing project configuration file: {e}") from e

                project_name = project_data.get("name", "Unnamed Project")
                project_description = project_data.get("description")

                resolved_clients: Dict[str, ClientConfig] = {}
                resolved_llm_configs: Dict[str, LLMConfig] = {}
                resolved_agents: Dict[str, AgentConfig] = {}
                resolved_simple_workflows: Dict[str, WorkflowConfig] = {}
                resolved_custom_workflows: Dict[str, CustomWorkflowConfig] = {}

                # Helper to resolve components
                def _resolve_components(data_list: List[Any], component_dict: Dict[str, Any], model_class: type, id_field: str, type_name: str):
                    resolved_items = {}
                    for item_ref in data_list:
                        if isinstance(item_ref, str): # It's an ID
                            if item_ref in component_dict:
                                resolved_items[item_ref] = component_dict[item_ref]
                            else:
                                logger.warning(f"{type_name} component ID '{item_ref}' not found for project '{project_name}'.")
                        elif isinstance(item_ref, dict): # Inline definition
                            item_id = item_ref.get(id_field)
                            if item_id:
                                try:
                                    # Path resolution for relevant types
                                    if model_class == ClientConfig and "server_path" in item_ref:
                                         item_ref["server_path"] = (PROJECT_ROOT_DIR / item_ref["server_path"]).resolve()
                                    if model_class == CustomWorkflowConfig and "module_path" in item_ref:
                                         item_ref["module_path"] = (PROJECT_ROOT_DIR / item_ref["module_path"]).resolve()

                                    inline_item = model_class(**item_ref)
                                    resolved_items[item_id] = inline_item
                                except Exception as e:
                                    logger.error(f"Failed to parse inline {type_name} definition '{item_id}' in project '{project_name}': {e}")
                            else:
                                logger.warning(f"Inline {type_name} definition missing '{id_field}' in project '{project_name}'.")
                        else:
                            logger.warning(f"Invalid {type_name} reference in project '{project_name}': {item_ref}")
                    return resolved_items

                resolved_clients = _resolve_components(project_data.get("clients", []), self.component_clients, ClientConfig, "client_id", "Client")
                resolved_llm_configs = _resolve_components(project_data.get("llm_configs", []), self.component_llm_configs, LLMConfig, "llm_id", "LLMConfig")
                resolved_agents = _resolve_components(project_data.get("agent_configs", []), self.component_agents, AgentConfig, "name", "Agent")
                resolved_simple_workflows = _resolve_components(project_data.get("simple_workflow_configs", []), self.component_simple_workflows, WorkflowConfig, "name", "SimpleWorkflow")
                resolved_custom_workflows = _resolve_components(project_data.get("custom_workflow_configs", []), self.component_custom_workflows, CustomWorkflowConfig, "name", "CustomWorkflow")

                return ProjectConfig(
                    name=project_name,
                    description=project_description,
                    clients=resolved_clients,
                    llm_configs=resolved_llm_configs,
                    agent_configs=resolved_agents,
                    simple_workflow_configs=resolved_simple_workflows,
                    custom_workflow_configs=resolved_custom_workflows,
                )

            # Add stubs for CRUD methods for components later (e.g., get_agent_component)
        ```
    *   **Action:** Implement the `__init__` method to initialize component dictionaries.
    *   **Action:** Implement a basic `_load_all_components` method. This method will:
        *   Define `COMPONENT_TYPES_DIRS` mapping component types (like "agents", "llm_configs") to their respective directory paths (e.g., `PROJECT_ROOT_DIR / "config/agents"`).
        *   Iterate through these directories. For each, ensure the directory exists (create if not).
        *   List all `.json` files.
        *   For each file, read and parse the JSON.
        *   **Crucial:** Determine how the component's ID (e.g., `AgentConfig.name`, `LLMConfig.llm_id`) is derived (is it in the filename, or a field within the JSON like "name" or "id"? Your current structure implies it's a field like `name` or `llm_id`).
        *   Validate the parsed data against the corresponding Pydantic model (e.g., `AgentConfig(**data)`). Resolve paths for `ClientConfig.server_path` and `CustomWorkflowConfig.module_path` relative to `PROJECT_ROOT_DIR`.
        *   Store the validated model in the appropriate dictionary (e.g., `self.component_agents[agent_id] = agent_model`).
        *   Handle errors gracefully (e.g., JSON parsing errors, validation errors, missing ID field).
    *   **Verification:** `ConfigManager` can be instantiated. After instantiation, `_load_all_components` has run (can verify with log messages or by inspecting the `self.component_*` dicts if sample component files are created).
    *   **Note:** Create a new directory `config/llms/` if it doesn't exist, for storing LLM component JSON files.

*   **1.3.2. Implement `load_project` Method (Core Logic):**
    *   **Action:** Implement the `load_project` method. This is a key piece.
        *   It takes `project_config_file_path: Path`.
        *   Reads and parses the JSON from this file.
        *   The project JSON can contain:
            *   Top-level keys like `name`, `description`.
            *   Keys for each component type, e.g., `clients`, `llm_configs`, `agents`, `simple_workflow_configs`, `custom_workflow_configs`. The value for these can be a list.
            *   Each item in these lists can be either:
                1.  A string ID (e.g., `"weather_agent_ref"`): In this case, look up the ID in the corresponding `self.component_agents` dictionary. If not found, log a warning or raise an error (decide on strategy: for now, log warning and skip).
                2.  A full JSON object defining the component inline: In this case, parse and validate this inline definition directly (e.g., `AgentConfig(**inline_agent_data)`). Resolve paths for `ClientConfig.server_path` and `CustomWorkflowConfig.module_path` if defined inline.
        *   It needs to merge these: if an ID is provided and also an inline definition for the same ID, decide precedence (e.g., inline overrides component, or error). Simplest is to not allow both for the same ID, or let inline override. (Current stub implies inline definitions are distinct items).
        *   Constructs a `ProjectConfig` Pydantic model instance, populating its dictionaries (`clients`, `llm_configs`, `agent_configs`, etc.) with the fully resolved and validated component models.
        *   Return the `ProjectConfig` instance.
    *   **Verification:**
        *   Create a sample project JSON file (e.g., `config/projects/test_project.json`) that includes a mix of component ID references and inline definitions.
        *   Create corresponding sample component JSON files in `config/agents/`, `config/llms/` etc.
        *   Call `config_manager.load_project("config/projects/test_project.json")` and verify that the returned `ProjectConfig` object is correctly populated with resolved components. Check for correct handling of missing component IDs.

---

**Step 1.4: Refactor `HostManager` to Use `ConfigManager`**

*   **File:** `src/host_manager.py`
*   **1.4.1. Instantiate `ConfigManager` in `HostManager.__init__`:**
    *   **Action:**
        ```python
        from src.config.config_manager import ConfigManager # Adjust import path
        from src.config.config_models import ProjectConfig # Import ProjectConfig

        class HostManager:
            def __init__(self, config_path: Path): # config_path is now project config path
                # ...
                self.config_manager = ConfigManager()
                self.current_project: Optional[ProjectConfig] = None # To store loaded project
                # ...
        ```
    *   **Verification:** `HostManager` instantiates without error.
*   **1.4.2. Modify `HostManager.initialize()`:**
    *   **Action:**
        *   Change `self.config_path` to represent the *project* config file path (e.g., `config/projects/default.json` as specified by `HOST_CONFIG_PATH` env var).
        *   Call `self.current_project = self.config_manager.load_project(self.config_path)`.
        *   Populate `self.agent_configs = self.current_project.agent_configs`.
        *   Populate `self.llm_configs = self.current_project.llm_configs`.
        *   Populate `self.workflow_configs = self.current_project.simple_workflow_configs`.
        *   Populate `self.custom_workflow_configs = self.current_project.custom_workflow_configs`.
        *   The `HostConfig` for `MCPHost` initialization will now be constructed using data from `self.current_project`:
            ```python
            from src.config.config_models import HostConfig # Keep this import for HostConfig model

            # Inside HostManager.initialize, after loading self.current_project
            if self.current_project:
                host_config_for_mcphost = HostConfig(
                    name=self.current_project.name,
                    description=self.current_project.description,
                    clients=list(self.current_project.clients.values()) # MCPHost expects a list
                )
                self.host = MCPHost(
                    config=host_config_for_mcphost,
                    agent_configs=self.agent_configs, # Still pass this for now, MCPHost uses it
                )
                # ... rest of MCPHost initialization
            else:
                raise RuntimeError("Failed to load project, HostManager cannot initialize MCPHost.")
            ```
        *   Remove the old `load_host_config_from_json(self.config_path)` call and its direct parsing logic from `HostManager`.
    *   **Verification:** `HostManager.initialize()` successfully loads a project using `ConfigManager`. `MCPHost` is initialized correctly with clients, name, and description from the project. Agent/LLM/Workflow configs are populated in `HostManager`.
*   **1.4.3. Update Config Accessor Methods:**
    *   **Action:** Methods like `get_agent_config(name)` should now fetch from `self.agent_configs` (which is sourced from `self.current_project`). This part might not change much if `self.agent_configs` is still the direct source after `initialize`.
    *   **Verification:** Existing tests that rely on these accessor methods still pass.
*   **1.4.4. Review Dynamic Registration Methods (e.g., `register_agent`):**
    *   **Action:** Decide how dynamic registration interacts with `ConfigManager` and `current_project`.
        *   Option 1 (Runtime only): `register_agent` only adds to `self.agent_configs` (and thus `self.current_project.agent_configs` if it's a reference). No file system change.
        *   Option 2 (Persist as component): `register_agent` calls a new `self.config_manager.save_agent_component(agent_config)` method, then reloads or updates `self.current_project`.
        *   For Phase 1, runtime-only might be sufficient. Persistence can be a later enhancement.
    *   **Verification:** Dynamic registration behaves as per the chosen strategy.

---

**Step 1.5: Refactor Config API Routes (`src/bin/api/routes/config_api.py`)**

*   **File:** `src/bin/api/routes/config_api.py`
*   **1.5.1. Inject/Access `ConfigManager`:**
    *   **Action:** The API routes need access to a `ConfigManager` instance. This could be done via FastAPI's dependency injection if `ConfigManager` is managed as a singleton or request-scoped dependency. For simplicity, if `HostManager` is already available via dependency injection (e.g. as `app.state.host_manager`), then `config_manager = host_manager.config_manager`.
    *   **Verification:** API routes can access the `ConfigManager`.
*   **1.5.2. Update CRUD Operations for *Component* Configs:**
    *   **Action:**
        *   `list_config_files(component_type)`: Should call a method on `ConfigManager`, e.g., `config_manager.list_component_files(component_type)` or `list(config_manager.component_agents.keys())` etc.
        *   `get_config_file(component_type, filename)`: Should call `config_manager.get_component_config(component_type, filename_or_id)`.
        *   `upload_config_file(...)` / `update_config_file(...)`: Should call `config_manager.save_component_config(component_type, config_model)`.
        *   `delete_config_file(...)`: Should call `config_manager.delete_component_config(component_type, filename_or_id)`.
    *   **Action:** `ConfigManager` will need these corresponding CRUD methods that operate on the component JSON files in `config/agents/`, `config/llms/`, etc., and also update its internal in-memory cache of components.
    *   **Verification:** API tests for CRUD operations on component configurations pass, interacting with the new `ConfigManager` methods.
*   **1.5.3. "Load Project" API Route (if applicable):**
    *   **Action:** If there's an API route to switch/load a new project, it should call a method on `HostManager` (e.g., `host_manager.load_new_project(project_name_or_path)`). This `HostManager` method would:
        1.  (Later, in Phase 3) Call `host_manager.reset_host()` to shut down old clients and clear old configs.
        2.  Call `self.config_manager.load_project(new_project_path)`.
        3.  Re-initialize `MCPHost` with new clients.
        4.  Update `self.current_project` and related config dictionaries.
    *   For Phase 1, this route might not be fully implemented with client shutdown, but the `HostManager` part using `ConfigManager` can be set up.

---

## Testing Strategy for Phase 1:

*   **New Unit Tests:**
    *   **`tests/config/test_config_manager.py` (New File):**
        *   Thoroughly test `ConfigManager._load_all_components` with various scenarios:
            *   Empty component directories.
            *   Malformed JSON in component files.
            *   Valid component files for each type (agents, llms, clients, etc.).
            *   Component files missing required ID fields (e.g., `name`, `llm_id`).
            *   Component files with incorrect GCloud secret configurations.
            *   Correct path resolution for `ClientConfig.server_path` and `CustomWorkflowConfig.module_path`.
        *   Test `ConfigManager.load_project` with diverse project files:
            *   Projects referencing component IDs.
            *   Projects with inline component definitions.
            *   Projects mixing references and inline definitions.
            *   Projects referencing non-existent component IDs (ensure graceful handling/logging).
            *   Projects with invalid inline component definitions.
            *   Correct path resolution for `server_path`/`module_path` in inline definitions.
        *   Test `ConfigManager` CRUD methods for component JSON files (e.g., `save_component_config`, `get_component_config`, `delete_component_config`) ensuring they interact with the filesystem and update in-memory stores correctly.
    *   **`tests/config/test_config_models.py` (Potentially New or Expanded):**
        *   Add specific Pydantic validation tests for the new `ProjectConfig` model.
        *   Verify existing model tests if `src/config/config_models.py` (formerly `src/host/models.py`) undergoes any other subtle changes beyond adding `ProjectConfig`.

*   **Updates to Existing Test Files:**
    *   **Import Path Updates (General Refactoring Check):**
        *   Run the entire test suite (`pytest tests/`) after Steps 1.1.3 and 1.1.5 (file moves and initial import updates). This will catch most direct import errors.
        *   **Key files likely needing import updates:**
            *   `tests/orchestration/config/test_config_loading.py`
            *   `tests/orchestration/test_host_manager.py`
            *   `tests/orchestration/test_host_manager_unit.py`
            *   `tests/api/routes/test_config_routes.py`
            *   `tests/api/routes/test_components_api.py` (if it uses models directly)
            *   `tests/fixtures/host_fixtures.py`
            *   `tests/fixtures/agent_fixtures.py`
            *   `tests/llm/test_anthropic_client_unit.py` and `test_anthropic_client_integration.py` (if they use `LLMConfig` or other models directly)
            *   `tests/orchestration/agent/test_agent_unit.py` and `test_agent_integration.py`
            *   `tests/orchestration/facade/test_facade_unit.py` and `test_facade_integration.py`
            *   Many other test files using these core models or config loading utilities.
    *   **`tests/orchestration/config/test_config_loading.py`:**
        *   Review and refactor. Parts of this file's tests might become obsolete if `load_host_config_from_json` is entirely consumed by `ConfigManager`.
        *   Tests related to `ServerConfig` (if it remains in `src/config/config.py`) might stay.
        *   Tests for helper functions like `_load_client_configs` (if they are moved into `ConfigManager` or still used by it) should be covered by `test_config_manager.py`.
    *   **`tests/orchestration/test_host_manager.py` and `tests/orchestration/test_host_manager_unit.py`:**
        *   Update `HostManager` initialization tests to reflect its use of `ConfigManager`.
        *   Mock `ConfigManager` and its methods (`load_project`) in unit tests for `HostManager`.
        *   Verify that `HostManager` correctly populates its internal config dictionaries (`agent_configs`, `llm_configs`, etc.) from the `ProjectConfig` returned by `ConfigManager`.
        *   Test `HostManager`'s dynamic registration methods (`register_agent`, etc.) based on the chosen strategy (runtime-only or persistence via `ConfigManager`).
    *   **`tests/api/routes/test_config_routes.py`:**
        *   Update tests for CRUD endpoints (`/configs/{component_type}/...`) to mock `ConfigManager` and verify that the API routes call the correct `ConfigManager` methods.
        *   Ensure tests cover interactions with component files in their new respective subdirectories (`config/agents/`, `config/llms/`, etc.).
    *   **`tests/api/test_api_integration.py`:**
        *   Review and update any integration tests that cover the configuration management API endpoints.

*   **Refactoring Checks (General):**
    *   After each significant step (especially file moves and `HostManager`/API refactoring), run `pytest tests/`.
    *   Pay close attention to tests involving `HostManager` initialization, config loading, and any API endpoints related to configuration.
    *   Ensure test coverage remains high or improves.

---

This detailed plan for Phase 1 should provide a clear path forward. We can adjust as we go.
