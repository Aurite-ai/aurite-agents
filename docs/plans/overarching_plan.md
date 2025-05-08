# AI Agent Framework Enhancement: Implementation Plan

## 1. Overall Goals

*   **Refactor Agent and LLM Systems:** Streamline Agent class structure and improve flexibility in LLM configuration and usage.
*   **Revamp Configuration Management:** Introduce a robust system for managing "Projects" and re-usable "Component" configurations, addressing current limitations in referencing and unregistering configurations.
*   **Centralize Configuration Logic:** Create a dedicated `ConfigManager` to handle loading, parsing, and providing access to project and component configurations, decluttering `HostManager` and API routes.

## 2. Proposed Implementation Order & Phasing

The tasks are interconnected, especially around configuration. Here's a suggested phased approach:

**Phase 1: Core Configuration System Refactor (Primarily Task 3)**
*Goal: Establish the new `ConfigManager` and `ProjectConfig` model as the foundation for how configurations are loaded and accessed.*

**Phase 2: Agent & LLM Class Refinements (Task 1)**
*Goal: Refactor agent classes and LLM client handling, leveraging the new configuration system where appropriate.*

**Phase 3: Advanced Configuration Features & Client Lifecycle Management (Task 2)**
*Goal: Implement the full "Project" and "Component" configuration system and add capabilities for resetting configurations and managing client lifecycles.*

## 3. Detailed Task Breakdown by Phase

---

### Phase 1: Core Configuration System Refactor (Task 3 Focus)

This phase focuses on creating the new `ConfigManager` and related structures. This will provide a solid base for subsequent changes.

**3.1. Create `src/config/` Directory and Relocate Core Config Files:**
    *   **Action:** Create the new directory `src/config/`.
    *   **Action:** Move `src/host/models.py` to `src/config/config_models.py`.
        *   *Note:* Update all imports across the project that reference `src.config.config_models`.
    *   **Action:** Move `src/config.py` to `src/config/config.py`.
        *   *Consideration:* The current `src/config.py` contains `ServerConfig` (loaded from environment variables) and `load_host_config_from_json` with its helpers.
        *   The `load_host_config_from_json` logic and its private helpers (e.g., `_load_client_configs`, `_load_agent_configs`) will be heavily refactored into the new `ConfigManager`.
        *   `ServerConfig` (for HOST, PORT, API_KEY etc.) might remain in `src/config/config.py` or be moved to a more specific `src/server_settings.py` if `src/config/config.py` becomes purely about the `ConfigManager`'s own operational config (if any). For now, assume `ServerConfig` stays, and `load_host_config_from_json` parts are moved/reused by `ConfigManager`.

**3.2. Define `ProjectConfig` Model:**
    *   **File:** `src/config/config_models.py`
    *   **Action:** Create the new `ProjectConfig` Pydantic model.
    *   **Structure:**
        ```python
        class ProjectConfig(BaseModel):
            name: str
            description: Optional[str] = None
            clients: Dict[str, ClientConfig] = {} # Maps client_id to ClientConfig
            llm_configs: Dict[str, LLMConfig] = {} # Maps llm_id to LLMConfig
            agent_configs: Dict[str, AgentConfig] = {} # Maps agent_name to AgentConfig
            simple_workflow_configs: Dict[str, WorkflowConfig] = {} # Maps workflow_name to WorkflowConfig
            custom_workflow_configs: Dict[str, CustomWorkflowConfig] = {} # Maps workflow_name to CustomWorkflowConfig
            # Add counters if they are truly part of the static project definition
            # If they are runtime counts, they might belong elsewhere (e.g., HostManager runtime state)
            # initial_agent_count: Optional[int] = None # Example
        ```
        *   *Note:* This `ProjectConfig` will effectively replace/expand the role of the current `HostConfig` for defining a whole project setup. The existing `HostConfig` might be simplified or deprecated if `ProjectConfig` covers all its aspects plus more.

**3.3. Implement `ConfigManager` (`src/config/config_manager.py`):**
    *   **File:** `src/config/config_manager.py`
    *   **Action:** Create the `ConfigManager` class.
    *   **Responsibilities:**
        *   **Initialization (`__init__`):**
            *   Scan predefined "component" directories (e.g., `config/agents/`, `config/llms/`, `config/clients/`) upon instantiation.
            *   Load all component JSON files found (e.g., `weather_agent.json`).
            *   Parse them into their respective Pydantic models (`AgentConfig`, `LLMConfig`, etc.).
            *   Store these component configurations in internal dictionaries, keyed by their ID/name (e.g., `self.component_agents: Dict[str, AgentConfig]`).
        *   **Method: `load_project(project_config_file_path: Path) -> ProjectConfig`:**
            *   Takes the path to a "project" configuration file (e.g., `config/projects/my_main_project.json`).
            *   Reads and parses this project file.
            *   The project file can contain:
                1.  Directly defined configurations (clients, agents, LLMs, etc.).
                2.  References to component configurations by ID (e.g., `"agent_ids": ["Weather Agent"]` or `"llm_config_ids": ["claude_default"]`).
            *   For referenced components, it looks them up in its internal storage (populated during `__init__`).
            *   Constructs and returns a fully resolved `ProjectConfig` object, with all configurations (either directly defined or resolved from components) populated.
        *   **CRUD methods for component JSON files:**
            *   Adapt logic from `src/bin/api/routes/config_api.py` for listing, getting, creating, updating, deleting individual component JSON files (e.g., `get_agent_component_config(name)`, `save_llm_component_config(llm_config_model)`). These methods will operate on the files in `config/agents/`, `config/llms/` etc.
            *   Ensure these methods also update the `ConfigManager`'s internal in-memory store of components if a file is changed.

**3.4. Refactor `HostManager` to Use `ConfigManager`:**
    *   **File:** `src/host_manager.py`
    *   **Action:**
        *   In `HostManager.__init__`, instantiate `ConfigManager`.
        *   In `HostManager.initialize()`:
            *   Call `self.config_manager.load_project(self.config_path)` to get the `ProjectConfig`.
            *   Store the returned `ProjectConfig` (e.g., `self.current_project: ProjectConfig`).
            *   Use `self.current_project.clients` to initialize `MCPHost`.
            *   Populate `self.agent_configs`, `self.llm_configs`, etc., from `self.current_project`.
        *   Remove direct JSON loading logic from `HostManager` (now handled by `ConfigManager`).
        *   Update methods like `get_agent_config`, `get_llm_config` to fetch from `self.current_project` (or directly from `self.agent_configs` which are sourced from `self.current_project`).
        *   Registration methods (`register_agent`, etc.) in `HostManager` might now primarily update the *in-memory* `self.current_project` and potentially call `ConfigManager` if dynamic changes should also persist to component files (this needs clarification - are dynamic registrations project-specific runtime changes or edits to underlying component files?).

**3.5. Refactor Config API Routes (`src/bin/api/routes/config_api.py`):**
    *   **Action:**
        *   Update API routes to use methods from the new `ConfigManager` for CRUD operations on *component* configuration files.
        *   The route for loading/switching a "project" (if it exists or is planned) would still call a method on `HostManager` (e.g., `HostManager.load_new_project(project_name)`), which in turn uses `ConfigManager` and handles client shutdowns/reinitializations.

---

### Phase 2: Agent & LLM Class Refinements (Task 1 Focus)

With the core configuration system in place, refactoring Agents and LLMs becomes cleaner.

**3.6. Improve `LLMConfig` Handling in LLM Clients (Task 1.2):**
    *   **Files:** `src/llm/base_client.py`, `src/llm/providers/anthropic_client.py` (and any other provider clients).
    *   **Action:**
        *   Modify `BaseLLM.__init__` and provider-specific `__init__` methods:
            *   They should initialize with sensible default parameters (model, temp, etc.) rather than requiring a specific `LLMConfig` at instantiation.
            *   They might take a reference to the `ConfigManager` or expect `LLMConfig` objects to be passed in per call.
        *   Modify `BaseLLM.create_message` (and its implementations):
            *   Add an optional `llm_config_id: Optional[str] = None` parameter.
            *   If `llm_config_id` is provided, the method should:
                1.  Fetch the corresponding `LLMConfig` object (e.g., from `HostManager.current_project.llm_configs` or via `ConfigManager`).
                2.  Use the parameters from this fetched `LLMConfig` for the API call (e.g., model name, temperature, system prompt). These would override any defaults set during client initialization for this specific call.
            *   If `llm_config_id` is not provided, use the client's default parameters or parameters passed directly to `create_message` (like `system_prompt_override`).
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

*   **LLMClient Instantiation with `ConfigManager`:** How will LLM clients (`BaseLLM` subclasses) access `LLMConfig` objects?
    *   Option A: `Agent` fetches its `LLMConfig` from `HostManager.current_project.llm_configs` (using `agent_config.llm_config_id`) and passes this specific `LLMConfig` object to `llm_client.create_message()`. The client then uses it.
    *   Option B: `llm_client.create_message()` takes `llm_config_id`, and the LLM client itself has a reference to `ConfigManager` (or `HostManager.current_project.llm_configs`) to look up the `LLMConfig`. (Your current proposal leans here and seems good).
*   **Dynamic Registration Persistence:** When `HostManager.register_agent()` (or for other components) is called dynamically (e.g., via an API), should this:
    1.  Only update the `HostManager.current_project` in memory for the current session?
    2.  Also attempt to save this new/updated configuration as a new "component" JSON file via `ConfigManager`?
    3.  Or, update the current "project" JSON file itself?
    *   This depends on the desired behavior for dynamic updates. Saving as a component seems most aligned with the new structure if it's meant to be reusable.
*   **`HostConfig` vs. `ProjectConfig`:** Clarify if the existing `HostConfig` model in `src/config/config_models.py` (once moved) will be entirely replaced by `ProjectConfig`, or if `ProjectConfig` will embed a simplified `HostConfig` (e.g., for just host name/description, if clients are listed directly in `ProjectConfig`). Your description implies `ProjectConfig` largely supersedes it by incorporating its fields and adding more.
*   **Error Handling for Missing Components:** When `ConfigManager.load_project()` encounters a reference to a component ID that doesn't exist in its loaded components, how should this be handled? Fail loudly? Log a warning and skip? This should be defined.
*   **Client Re-initialization:** When switching projects, after `shutdown_all_clients()`, the new project's clients will need to be initialized. `HostManager.initialize()` (or a part of it) will need to be callable again, or a new method `HostManager.initialize_clients_for_project(project_config: ProjectConfig)` could be created.
*   **Location of `ServerConfig`:** Confirm if `src/config/config.py` (the moved file) is the best place for `ServerConfig` (env var based settings) or if it should be separate from the `ConfigManager`-related code.

---
