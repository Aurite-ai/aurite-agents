# AI Agent Framework Enhancement: Implementation Plan

## 1. Overall Goals

*   **Refactor Agent and LLM Systems:** Streamline Agent class structure and improve flexibility in LLM configuration and usage.
*   **Revamp Configuration Management:** Introduce a robust system for managing "Projects" and re-usable "Component" configurations, addressing current limitations in referencing and unregistering configurations.
*   **Centralize Configuration Logic:** Create dedicated managers (`ComponentManager`, `ProjectManager`) to handle loading, parsing, validation, CRUD, and providing access to component and project configurations, decluttering `HostManager` and API routes.

## 2. Proposed Implementation Order & Phasing

The tasks are interconnected, especially around configuration. Here's a suggested phased approach:

**Phase 1: Core Configuration System Refactor (Primarily Task 3)**
*Goal: Establish the new `ComponentManager`, `ProjectManager`, and `ProjectConfig` model as the foundation for how configurations are loaded and accessed.*

**Phase 2: Agent & LLM Class Refinements (Task 1)**
*Goal: Refactor agent classes and LLM client handling, leveraging the new configuration system where appropriate.*

**Phase 3: Advanced Configuration Features & Client Lifecycle Management (Task 2)**
*Goal: Implement the full "Project" and "Component" configuration system and add capabilities for resetting configurations and managing client lifecycles.*

## 3. Detailed Task Breakdown by Phase

---

### Phase 1: Core Configuration System Refactor (Task 3 Focus)

This phase focuses on creating the new `ComponentManager`, `ProjectManager`, and related structures. This will provide a solid base for subsequent changes.

**3.1. Establish New Config Structure:** (Done)
    *   **Action:** Create the new directory `src/config/`. (Done)
    *   **Action:** Move `src/host/models.py` to `src/config/config_models.py`. (Done)
    *   **Action:** Update all imports across the project that reference `src.config.config_models`. (Done by user)
    *   **Action:** Move `ServerConfig` and `PROJECT_ROOT_DIR` from `src/config.py` to `src/config/__init__.py`. (Done)
    *   **Action:** Correct `PROJECT_ROOT_DIR` definition in `src/config/__init__.py` to point to the actual project root. (Done)
    *   **Action:** Delete the now empty `src/config.py` file. (Done by user)

**3.2. Define `ProjectConfig` Model:** (Done)
    *   **File:** `src/config/config_models.py`
    *   **Action:** Create the new `ProjectConfig` Pydantic model. (Done)
    *   **Structure:** Includes `name`, `description`, and dictionaries for resolved `ClientConfig`, `LLMConfig`, `AgentConfig`, `WorkflowConfig` (as `simple_workflow_configs`), `CustomWorkflowConfig` (as `custom_workflow_configs`). (Done)

**3.3. Implement `ComponentManager` (`src/config/component_manager.py`):** (Done)
    *   **File:** `src/config/component_manager.py`
    *   **Action:** Create the `ComponentManager` class. (Done)
    *   **Responsibilities:**
        *   **Initialization (`__init__`):** Scan component directories (`config/clients/`, `config/llms/`, `config/agents/`, `config/workflows/`, `config/custom_workflows/`), load/parse/validate/store component JSONs in memory. Uses `config_utils.resolve_path_fields` for path handling. (Done)
        *   **Accessor Methods:** Provide methods to get loaded components by ID/name (e.g., `get_agent(name)`). (Done)
        *   **Listing Methods:** Provide methods to list loaded components or component filenames. (Done)
        *   **CRUD Methods:** Implement methods (`save_component_config`, `delete_component_config`, `create_component_file`) to manage component JSON files on disk and update the in-memory store. Uses `config_utils.relativize_path_fields` for saving paths. (Done)
    *   **Testing:** Unit tests created and passing (`tests/config/test_component_manager.py`). (Done)

**3.4. Implement `ProjectManager` (`src/config/project_manager.py`):** (Done)
    *   **File:** `src/config/project_manager.py`
    *   **Action:** Create the `ProjectManager` class. (Done)
    *   **Responsibilities:**
        *   **Initialization (`__init__`):** Takes a `ComponentManager` instance. (Done)
        *   **Method: `load_project(project_config_file_path: Path) -> ProjectConfig`:** Reads a project file (e.g., `config/projects/default.json`), resolves component ID references using `ComponentManager`, validates inline definitions (using `config_utils.resolve_path_fields`), merges them, and returns a fully resolved `ProjectConfig` object. (Done)
    *   **Testing:** Unit tests created and passing (`tests/config/test_project_manager.py`). (Done)

**3.5. Refactor `HostManager` to Use `ProjectManager`:** (Done)
    *   **File:** `src/host_manager.py`
    *   **Action:**
        *   In `HostManager.__init__`, instantiate `ComponentManager` and `ProjectManager`. (Done)
        *   In `HostManager.initialize()`:
            *   Call `self.project_manager.load_project(self.config_path)` to get the `ProjectConfig`. (Done)
            *   Store the returned `ProjectConfig` as `self.current_project`. (Done)
            *   Populate `self.agent_configs`, `self.llm_configs`, `self.workflow_configs` (simple), `self.custom_workflow_configs` from `self.current_project`. (Done)
            *   Construct `HostConfig` for `MCPHost` initialization using client data from `self.current_project`. (Done)
        *   Remove direct JSON loading logic and the obsolete `register_config_file` method/helpers from `HostManager`. (Done)
        *   Update methods like `get_agent_config`, `get_llm_config` to fetch from the dictionaries populated from `self.current_project`. (Done - confirmed no change needed).
        *   Dynamic registration methods (`register_agent`, etc.) remain runtime-only updates to `HostManager`'s dictionaries for Phase 1. (Done)
    *   **Testing:** Integration tests updated and passing (`tests/orchestration/test_host_manager.py`). (Done)

**3.6. Refactor Config API Routes (`src/bin/api/routes/config_api.py`):** (Done)
    *   **Action:**
        *   Update API routes (GET, POST, PUT, DELETE) to use methods from the `ComponentManager` for CRUD operations on *component* configuration files. (Done)
        *   Ensure API routes access the `ComponentManager` instance via FastAPI dependency injection (`Depends(get_component_manager)`). (Done)
    *   **Testing:** API tests updated and passing (`tests/api/routes/test_config_routes.py`). (Done)

---

### Phase 2: Agent & LLM Class Refinements (Task 1 Focus)

With the core configuration system in place, refactoring Agents and LLMs becomes cleaner.

**3.7. Improve `LLMConfig` Handling in LLM Clients (Task 1.2):**
    *   **Files:** `src/llm/base_client.py`, `src/llm/providers/anthropic_client.py` (and others).
    *   **Action:** Modify `BaseLLM` and provider `__init__` to use defaults. Modify `create_message` to accept an optional `llm_config_id` and use the corresponding `LLMConfig` (fetched via `ComponentManager` or from `HostManager.current_project`) to override defaults for that call.

**3.8. Merge Agent Class Files (Task 1.1):**
    *   **Files:** `src/agents/agent.py`, `src/agents/conversation_manager.py`.
    *   **Action:** Merge `ConversationManager` logic into a renamed `Agent` class in `src/agents/agent.py`. Delete `conversation_manager.py`. Update imports.

**3.9. Review and Refactor (New) Agent Class Logic (Task 1.3):**
    *   **File:** `src/agents/agent.py` (newly merged).
    *   **Action:** Review conversation history management (`self.messages`, `self.conversation_history`) for clarity and correctness, ensuring `AgentConfig.include_history` is handled.

---

### Phase 3: Advanced Configuration Features & Client Lifecycle Management (Task 2 Focus)

Builds upon the `ComponentManager` and `ProjectManager` to implement full project/component functionality and client management.

**3.10. Client Lifecycle Management (Task 2.2):**
    *   **Action: Create `ClientManager`:** (`src/host/foundation/clients.py`) Responsible for starting, stopping, and tracking client subprocesses.
    *   **Action: Refactor `MCPHost` (`src/host/host.py`):** Delegate client process management to `ClientManager`. Add `client_shutdown(id)` and `shutdown_all_clients()` methods.
    *   **Action: Implement Configuration Reset in `HostManager`:** Add `reset_host()` or `unload_project()` method to call `host.shutdown_all_clients()` and clear `current_project` state. Update the "load project" API route (if any) to use this.

## 4. Key Considerations & Open Questions

*   **LLMClient Instantiation with `LLMConfig`:** Confirmed plan: `create_message` takes `llm_config_id`, client looks it up (likely via `HostManager.current_project.llm_configs`).
*   **Dynamic Registration Persistence:** Confirmed plan for Phase 1: Dynamic registrations (`register_agent` etc. in `HostManager`) are runtime-only updates to the *current project's* in-memory config dictionaries (`self.agent_configs`, etc.). They do *not* modify component files via `ComponentManager` in this phase.
*   **`HostConfig` vs. `ProjectConfig`:** Confirmed plan: `ProjectConfig` is the primary definition. `HostManager` constructs a temporary `HostConfig` instance from `ProjectConfig` data solely for `MCPHost` initialization.
*   **Error Handling for Missing Components:** Confirmed plan: `ProjectManager._resolve_components` raises a `ValueError` if a referenced component ID is not found in `ComponentManager`.
*   **Client Re-initialization:** Confirmed plan: When switching projects (Phase 3), `HostManager` will need to call `host.shutdown_all_clients()`, load the new project via `ProjectManager`, and then re-initialize `MCPHost` (or relevant parts) with the new project's client configurations.
*   **Location of `ServerConfig`:** Confirmed plan: Moved to `src/config/__init__.py`. `src/config/config.py` deleted.

---
    *   **Agent Interaction:**
        *   When an `Agent` (via `AgentTurnProcessor`) calls `llm.create_message()`, it will pass its `agent_config.llm_config_id` if present.

**3.7. Merge Agent Class Files (Task 1.1):**
    *   **Files:** `src/agents/agent.py`, `src/agents/conversation_manager.py`.
    *   **Action:**
        1.  Move the content of the `Agent` class from `src/agents/agent.py` into `src/agents/conversation_manager.py`.
        2.  Merge the logic: The `ConversationManager` class effectively becomes the new `Agent` class. Its `__init__` already takes an `Agent` instance (which holds config and LLM). This structure can be retained, or `ConversationManager` can be renamed to `Agent` and directly take `AgentConfig` and `BaseLLM` in its constructor. The latter seems cleaner.
            *   If renaming `ConversationManager` to `Agent`:
                *   `ConversationManager.__init__(self, agent: OldAgent, ...)` becomes `NewAgent.__init__(self, config: AgentConfig, llm_client: BaseLLM, host_instance: MCPHost, ...)`
                *   The `self.agent.config` and `self.agent.llm` would become `self.config` and `self.llm`.
        3.  Rename `src/agents/conversation_manager.py` to `src/agents/agent.py`.
        4.  Delete the (now old and mostly empty) `src/agents/agent.py` file.
        5.  Update all imports referencing the old `Agent` or `ConversationManager`.

**3.8. Review and Refactor (New) Agent Class Logic (Task 1.3):**
    *   **File:** `src/agents/agent.py` (the newly merged/renamed file).
    *   **Action:**
        *   Focus on the `run_conversation` (or equivalent) method.
        *   Review how `self.messages` and `self.conversation_history` are managed.
            *   Ensure clarity and efficiency.
            *   Confirm that `include_history` from `AgentConfig` is correctly handled.
            *   The current approach of appending to `self.messages` (for next LLM call) and `self.conversation_history` (for logging/results) seems reasonable. The main check is for simplicity and correctness.

---

### Phase 3: Advanced Configuration Features & Client Lifecycle Management (Task 2 Focus)

Builds upon the `ConfigManager` to implement full project/component functionality and client management.

**3.9. Implement Full "Projects" and "Component" Configurations (Task 2.1):**
    *   **Action:**
        *   Ensure `ConfigManager` (from Phase 1) correctly loads individual component JSON files from subdirectories like `config/agents/`, `config/clients/`, `config/llms/`, `config/simple_workflows/`, `config/custom_workflows/`.
        *   Ensure `ConfigManager.load_project()` can correctly parse a project file (e.g., `config/projects/my_project.json`) that references these components by their IDs/names.
            *   Example project file structure:
                ```json
                // config/projects/main_project.json
                {
                  "name": "Main Project",
                  "description": "The main project configuration.",
                  "clients": ["weather_server_component_id", {"client_id": "inline_db_client", ...}], // Mix of refs and inline
                  "llm_configs": ["default_claude_haiku_id"],
                  "agent_configs": ["weather_agent_component_id", "planning_agent_ref"],
                  // ... etc. for simple_workflows, custom_workflows
                }
                ```
        *   Update `HostManager` and `ExecutionFacade` to work seamlessly with projects loaded this way.

**3.10. Client Lifecycle Management (Task 2.2):**
    *   **Action: Create `ClientManager`:**
        *   **File:** `src/host/foundation/clients.py`
        *   **Class:** `ClientManager`
        *   **Responsibilities:**
            *   Store and manage active client (MCP server process) instances.
            *   Logic for initializing a client (starting its server process, managing subprocess).
            *   Logic for shutting down a specific client process by ID.
            *   Logic for shutting down all active client processes.
        *   `MCPHost` will instantiate and use this `ClientManager`.
    *   **Action: Refactor `MCPHost` (`src/host/host.py`):**
        *   Delegate client initialization, tracking, and shutdown to `ClientManager`.
        *   Add `client_shutdown(client_id: str)` method (calls `ClientManager`).
        *   Add `shutdown_all_clients()` method (calls `ClientManager`).
        *   The existing `MCPHost.shutdown()` should call `self.client_manager.shutdown_all_clients()`.
    *   **Action: Implement Configuration Reset in `HostManager`:**
        *   **File:** `src/host_manager.py`
        *   **Method:** `reset_host()` (or a more descriptive name like `unload_project_and_shutdown_clients()`).
            *   Calls `self.host.shutdown_all_clients()`.
            *   Clears `self.current_project`, `self.agent_configs`, `self.llm_configs`, etc.
            *   The `MCPHost` instance itself might need to be re-initialized or have its internal state (like registered tools/prompts from clients) cleared if it's being reused for a new project. Alternatively, `MCPHost` could be shut down and a new one created when a new project is loaded. The latter is cleaner if project contexts are very distinct.
        *   The API route for loading a new project will call this reset method before loading the new project's configurations and re-initializing clients.

## 4. Key Considerations & Open Questions

*   **LLMClient Instantiation with `LLMConfig`:** (Deferred to Phase 2) Current plan remains: `ExecutionFacade` resolves LLM parameters based on `AgentConfig` and referenced `LLMConfig` (from `HostManager.llm_configs`) before instantiating the LLM client.
*   **Dynamic Registration Persistence:** (Confirmed for Phase 1) Dynamic registrations (`register_agent` etc. in `HostManager`) are runtime-only updates to the *current project's* in-memory config dictionaries (`self.agent_configs`, etc.). They do *not* modify component files via `ComponentManager` in this phase. Persistence via API requires using the component CRUD endpoints directly.
*   **`HostConfig` vs. `ProjectConfig`:** (Confirmed) `ProjectConfig` is the primary definition loaded by `ProjectManager`. `HostManager` constructs a temporary `HostConfig` instance from `ProjectConfig` data solely for `MCPHost` initialization.
*   **Error Handling for Missing Components:** (Confirmed) `ProjectManager._resolve_components` raises a `ValueError` if a referenced component ID is not found in `ComponentManager`, causing `load_project` to fail.
*   **Client Re-initialization:** (Deferred to Phase 3) Plan remains: When switching projects, `HostManager` will need a mechanism (e.g., `reset_host()`) to call `host.shutdown_all_clients()`, load the new project, and re-initialize `MCPHost`.
*   **Location of `ServerConfig`:** (Confirmed) Moved to `src/config/__init__.py`. `src/config/config.py` deleted.
*   **Path Resolution:** (Confirmed) `PROJECT_ROOT_DIR` defined in `src/config/__init__.py`. `config_utils.py` contains helpers (`resolve_path_fields`, `relativize_path_fields`) used by `ComponentManager` and `ProjectManager` to handle absolute/relative paths correctly during loading and saving.

---
