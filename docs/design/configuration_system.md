# Aurite Agent Framework: Configuration System Design

## 1. Introduction

This document outlines the design of the configuration system for the Aurite Agent Framework. The system is designed to be flexible, allowing for reusable components and project-specific compositions, while maintaining a clear separation of concerns between managing all available component definitions, managing the active project's configuration, and the runtime instantiation of these components.

The core goals of this configuration system are:
*   **Modularity**: Define components (Clients, LLMs, Agents, Workflows) independently for reusability.
*   **Composability**: Allow "Projects" to define a specific collection of components that work together.
*   **Clarity**: Maintain a clear and understandable structure for how configurations are defined, loaded, and used.
*   **Dynamic Operations**: Support changing the active project and dynamically registering new components at runtime.
*   **Consistency**: Ensure that the runtime state (e.g., active MCP client processes) aligns with the configured state of the active project.

## 2. Core Configuration Components

The configuration system revolves around several key Python classes and a structured directory layout for JSON configuration files.

### 2.1. Configuration File Structure (`config/`)

All raw configuration files are stored as JSON files within the `config/` directory at the project root. This directory is organized by component type and project definitions:

*   `config/projects/*.json`: Defines specific "Projects." Each project file specifies the set of components (Clients, LLMs, Agents, Workflows) that constitute that project, either by referencing component definition files or by providing inline definitions.
*   `config/clients/*.json`: Individual JSON files, each defining a `ClientConfig` for an MCP server.
*   `config/llms/*.json`: Individual JSON files, each defining an `LLMConfig` for a specific LLM setup.
*   `config/agents/*.json`: Individual JSON files, each defining an `AgentConfig`.
*   `config/workflows/*.json`: Individual JSON files, each defining a `WorkflowConfig` for a simple sequential workflow.
*   `config/custom_workflows/*.json`: Individual JSON files, each defining a `CustomWorkflowConfig` for a Python-based custom workflow.

Path fields within these JSON files (e.g., `server_path` in `ClientConfig`, `module_path` in `CustomWorkflowConfig`) are resolved relative to the `PROJECT_ROOT_DIR` during loading.

### 2.2. Configuration Models (`src/config/config_models.py`)

This file defines Pydantic models for all configuration entities, ensuring type safety, validation, and clear structure. Key models include:

*   `ClientConfig`: Defines parameters for an MCP client (server path, capabilities, roots, GCP secrets, etc.).
*   `LLMConfig`: Defines parameters for an LLM (provider, model name, temperature, default system prompt, etc.).
*   `AgentConfig`: Defines parameters for an agent (associated LLM config ID, client IDs, system prompts, validation schema, etc.).
*   `WorkflowConfig`: Defines steps (a list of agent names) for a simple sequential workflow.
*   `CustomWorkflowConfig`: Defines the module path and class name for a custom Python workflow.
*   `ProjectConfig`: The central model representing a fully resolved project. It contains dictionaries of all active components for that project (e.g., `clients: Dict[str, ClientConfig]`, `agent_configs: Dict[str, AgentConfig]`). This model serves as the in-memory representation of the active project's complete configuration.
*   `HostConfig`: A simpler model derived from `ProjectConfig`, primarily containing the project name, description, and a list of `ClientConfig` objects. It is used for initializing the `MCPHost`.

These models are utilized by `ComponentManager` for parsing individual component files and by `ProjectManager` for constructing the comprehensive `ProjectConfig`.

### 2.3. `ComponentManager` (`src/config/component_manager.py`)

The `ComponentManager` is responsible for discovering, loading, and managing all *available* individual component configuration files from their respective subdirectories within `config/`.

*   **Initialization**: On instantiation, it scans the predefined component directories (e.g., `config/agents/`, `config/clients/`).
    *   For each JSON file found, it attempts to parse it. A file can contain either a single JSON object representing one component, or a JSON array where each element is a component definition.
    *   If the file contains a single object, it's parsed into the corresponding Pydantic model (e.g., `AgentConfig`, `ClientConfig`).
    *   If the file contains an array, each element of the array is individually parsed into the corresponding Pydantic model.
    *   All successfully parsed and validated models (with paths resolved relative to `PROJECT_ROOT_DIR`) are stored in an in-memory dictionary, keyed by the component's *actual internal unique ID/name* (e.g., `client_id` for clients, `name` for agents).
    *   If a component ID is duplicated (either within the same file or across different files for the same component type), a warning is logged, and the first loaded component with that ID is retained.
*   **Accessors**: Provides methods like `get_component_config(component_type_key: str, component_id: str)` to retrieve a specific loaded and validated component model from its internal stores, based on the component's internal ID.
*   **CRUD Operations**:
    *   Offers methods (`save_component_config`, `delete_component_config`, `create_component_file`) to manage component JSON files on disk. These operations also update the in-memory store and handle path relativization when saving.
    *   **Important Note on `save_component_config` and `create_component_file`**: These methods currently operate on *single* component models. When saving, they will create/overwrite a JSON file named after the component's ID (e.g., `client_A.json`) containing only that single component's definition. If this filename matches a file that previously contained an array of components, that file will be overwritten with the single component structure. Modifying individual components within a multi-component file while preserving the list structure in that *same file* is not supported by these methods in the current implementation.
*   **Role**: The `ComponentManager` acts as a comprehensive library or registry of all parseable component definitions found on the filesystem. Its primary consumer is the `ProjectManager`, which uses it to look up and resolve component references when loading a specific project configuration. Its role remains unchanged in this refined design.

### 2.4. `ProjectManager` (`src/config/project_manager.py`)

In this design, the `ProjectManager` is repurposed to be the central manager of the *currently active project's configuration state* in memory.

*   **Initialization**: Takes an instance of `ComponentManager` as a dependency, which it uses to resolve component references.
*   **Internal State**:
    *   `self.active_project_config: Optional[ProjectConfig]`: This attribute holds the fully resolved `ProjectConfig` object for the project that is currently loaded and active in the system. It is `None` if no project is loaded.
*   **Core Methods**:
    *   `load_project(project_config_file_path: Path) -> ProjectConfig`:
        *   Reads the specified project JSON file (e.g., `config/projects/my_project.json`).
        *   For each component entry in the project file:
            *   If the entry is a string (ID reference), it calls `self.component_manager.get_component_config()` to retrieve the corresponding validated component model.
            *   If the entry is an inline dictionary, it parses and validates this dictionary into the appropriate Pydantic model (e.g., `ClientConfig`, `AgentConfig`), resolving any path fields.
        *   Aggregates all resolved and inline-defined components into their respective dictionaries (e.g., `clients`, `agent_configs`).
        *   Constructs a new `ProjectConfig` object using these aggregated component dictionaries, along with the project's name and description.
        *   Sets `self.active_project_config` to this newly created and fully resolved `ProjectConfig` object.
        *   Returns the created `ProjectConfig` object.
    *   `unload_active_project()`: Sets `self.active_project_config = None`, effectively clearing the currently loaded project's configuration from the `ProjectManager`'s active state.
    *   `get_active_project_config() -> Optional[ProjectConfig]`: Returns the current `self.active_project_config`. This is the primary way other parts of the system (like `HostManager` or `ExecutionFacade`) access the configuration of the active project.
    *   `get_host_config_for_active_project() -> Optional[HostConfig]`: If `self.active_project_config` is set, this method constructs and returns a `HostConfig` object. The `HostConfig` includes the name and description from `self.active_project_config` and a list of `ClientConfig` objects derived from `self.active_project_config.clients`. This `HostConfig` is specifically tailored for initializing the `MCPHost`.
*   **Dynamic Update Methods (for the active project)**:
    *   `add_component_to_active_project(component_type_key: str, component_id: str, component_model: BaseModel)`:
        *   This method is called (typically by `HostManager`) *after* a component has been successfully validated and, in the case of clients, after its runtime process has been initialized.
        *   It updates the appropriate dictionary within `self.active_project_config` (e.g., `self.active_project_config.agent_configs[component_id] = component_model`).
        *   Ensures that `self.active_project_config` always reflects the true set of active and registered components for the current project session, including those added dynamically.
    *   (Future: `remove_component_from_active_project` could be added if fine-grained dynamic unregistration within a project is needed, beyond full project unloads.)

## 3. Integration with the Framework

The configuration system, centered around `ComponentManager` and the stateful `ProjectManager`, integrates with higher-level components like `HostManager`, API entrypoints, and `ExecutionFacade` to manage the application's behavior.

### 3.1. Entrypoints (API) and `HostManager`

*   API endpoints (defined in `src/bin/api/routes/`) serve as the primary interface for external interactions, such as executing agents, changing projects, or dynamically registering components.
*   These endpoints use FastAPI's dependency injection to obtain an instance of `HostManager` (via `Depends(get_host_manager)`). `get_host_manager` retrieves the `HostManager` instance that is created and managed by the FastAPI application's `lifespan` context manager, ensuring a single `HostManager` instance per application lifecycle.
*   For operations that modify the active project or runtime state (e.g., changing projects, registering a new client process), API routes delegate these tasks to methods on the `HostManager`.

### 3.2. `HostManager` Orchestration of `ProjectManager`

The `HostManager` is the direct consumer and orchestrator of the `ProjectManager` for managing the lifecycle of the active project's configuration.

*   **Initialization (`HostManager.__init__`)**:
    *   Creates an instance of `ComponentManager`.
    *   Creates an instance of `ProjectManager`, providing it with the `ComponentManager` instance. These instances persist for the lifetime of the `HostManager`.
*   **Loading an Initial Project (`HostManager.initialize(config_path)`)**:
    *   This method is called once at application startup (via the FastAPI `lifespan` manager).
    *   It invokes `self.project_manager.load_project(config_path)`, which loads the specified project file, resolves all its component references using `ComponentManager`, and stores the resulting `ProjectConfig` object in `self.project_manager.active_project_config`.
    *   `HostManager` retrieves the active `ProjectConfig` (via `self.project_manager.get_active_project_config()`) and constructs a `HostConfig` (primarily client information) from it (via `self.project_manager.get_host_config_for_active_project()`).
    *   It instantiates `self.host` (the `MCPHost` instance) using this `HostConfig`. The `MCPHost` itself no longer maintains its own internal collection of all agent configurations; instead, specific `AgentConfig` objects are passed to its methods (like `execute_tool`) by the `ExecutionFacade` when an agent's context is required for operations like component filtering.
    *   `HostManager` then initializes `self.host`.
    *   Finally, `HostManager` instantiates `self.execution` (the `ExecutionFacade`), passing it the active `self.host` and the full active `ProjectConfig` (obtained from `self.project_manager.get_active_project_config()`).
*   **Unloading a Project (`HostManager.unload_project()`)**:
    *   Primarily, it calls `self.project_manager.unload_active_project()` to clear the active configuration state within the `ProjectManager`.
    *   It also handles shutting down the current `MCPHost` instance.
*   **Changing Projects (`HostManager.change_project(new_config_path)`)**:
    *   First, calls `self.unload_project()` to tear down the current project's runtime and clear its configuration state from `ProjectManager`.
    *   Then, it updates its internal `self.config_path` to `new_config_path`.
    *   Finally, it calls `self.initialize(self.config_path)` again. This re-runs the project loading sequence: `ProjectManager` loads the new project file into its `active_project_config`, and `HostManager` then uses this new active configuration to set up a new `MCPHost` and `ExecutionFacade`.

### 3.3. `HostManager` Orchestration of Configuration and Runtime Registration

`HostManager` acts as the coordinator for dynamic registrations, ensuring that changes to the runtime (like starting a new client) are reflected in the active project's configuration, and that configurations are validated against the current runtime state.

*   **Dynamic Client Registration (`HostManager.register_client(client_config_data: Dict)`)**:
    1.  The API route calls this `HostManager` method with the raw configuration data for the new client.
    2.  `HostManager` parses `client_config_data` into a `ClientConfig` model instance (performing initial validation).
    3.  It then calls `await self.host.register_client(client_config_model)`. `self.host` is the active `MCPHost` instance. `MCPHost` attempts to start the client's server process and establish an MCP session.
    4.  **If `self.host.register_client()` succeeds**: `HostManager` calls `self.project_manager.add_component_to_active_project("clients", client_config_model.client_id, client_config_model)`. This updates the `ProjectManager.active_project_config` to include the newly started client.
    5.  If `MCPHost` fails to start the client, an exception is raised, the `ProjectConfig` is *not* updated, and `HostManager` propagates the error to the API layer. This ensures configuration reflects runtime reality.
*   **Dynamic Agent, LLM, or Workflow Registration (e.g., `HostManager.register_agent(agent_config_data: Dict)`)**:
    1.  The API route calls the relevant `HostManager` method.
    2.  `HostManager` parses the data into the appropriate Pydantic model (e.g., `AgentConfig`).
    3.  It performs semantic validations. For an `AgentConfig`, this includes checking if any `client_ids` it references are currently registered and active in `self.host` (via `self.host.is_client_registered()`) and if its `llm_config_id` refers to an LLM configuration present in `self.project_manager.get_active_project_config().llm_configs`.
    4.  **If all validations pass**: `HostManager` calls `self.project_manager.add_component_to_active_project("<component_type_key>", component_model.id, component_model)`. (Note: `component_model.id` should correspond to the correct ID field, e.g., `agent_config_model.name`).
    5.  If validation fails, an error is raised, and the `ProjectConfig` is not modified.

### 3.4. `HostManager` Orchestration of `ExecutionFacade`

The `HostManager` is responsible for instantiating the `ExecutionFacade` and ensuring it always operates with the correct and current context.

*   **Instantiation**:
    *   A new `ExecutionFacade` instance is created by `HostManager.initialize()` *after* the `MCPHost` instance (`self.host`) has been successfully initialized and the active `ProjectConfig` has been loaded into `self.project_manager.active_project_config`.
*   **Dependencies Passed to `ExecutionFacade`**:
    *   `host_instance: MCPHost`: The currently active `MCPHost` instance from `HostManager.host`.
    *   `current_project: ProjectConfig`: A reference to the `ProjectConfig` object currently held in `ProjectManager.active_project_config`.
    *   `storage_manager: Optional[StorageManager]`: The `StorageManager` instance from `HostManager`.
*   **`ExecutionFacade` Access to Configurations**:
    *   When `ExecutionFacade` needs to execute a component (e.g., `run_agent(agent_name, ...)`), it looks up the necessary configuration (e.g., `AgentConfig`) directly from the `ProjectConfig` object it holds: `agent_config = self._current_project.agent_configs.get(agent_name)`.
    *   Similarly, it uses `self._current_project.llm_configs`, `self._current_project.simple_workflow_configs`, etc., to retrieve other required component configurations.
    *   All runtime interactions with MCP servers (executing tools, getting prompts) are delegated to the `MCPHost` instance it holds (`self._host`).
*   **Re-initialization on Project Change**:
    *   When `HostManager.change_project()` is called, it eventually calls `HostManager.initialize()`. This `initialize()` call creates a *new* `MCPHost` instance and loads a *new* `ProjectConfig` into the `ProjectManager`.
    *   Crucially, `initialize()` then creates a *new* instance of `ExecutionFacade`, passing these fresh references (`new_mcphost_instance`, `new_project_config_object`). This ensures that `HostManager.execution` always points to a facade that is correctly configured for the currently active project and its associated runtime host.

## 4. Summary of Benefits

This refined design for the configuration system offers several advantages:

*   **Clear Separation of Concerns**: Each manager (`ComponentManager`, `ProjectManager`, `HostManager`) and core class (`MCPHost`, `ExecutionFacade`) has a well-defined responsibility.
*   **Centralized Active Project State**: `ProjectManager` becomes the definitive source for the active project's configuration, including any dynamic modifications. This simplifies state tracking.
*   **Improved Consistency**: The "transactional" nature of dynamic client registration (config updated only after runtime success) ensures the active project configuration accurately reflects the operational state.
*   **Robustness for Dynamic Operations**: The explicit re-initialization of `ExecutionFacade` during project changes ensures it always operates with the correct context (active `MCPHost` and `ProjectConfig`).
*   **Enhanced Readability and Maintainability**: By reducing redundancy (e.g., `HostManager` not duplicating config stores) and clarifying roles, the system becomes easier to understand and maintain.

This architecture provides a solid foundation for managing complex configurations and runtime behaviors within the Aurite Agent Framework.
