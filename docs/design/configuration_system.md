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

*   `config/projects/*.json`: Defines specific "Projects." Each project file specifies the set of components (Clients, LLMs, Agents, Workflows) that constitute that project, either by referencing component definition files or by providing inline definitions. (Example keys used inside: `clients`, `llms`, `agents`, `simple_workflows`, `custom_workflows`)
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
*   `ProjectConfig`: The central model representing a fully resolved project. It contains dictionaries of all active components for that project (e.g., `clients: Dict[str, ClientConfig]`, `llms: Dict[str, LLMConfig]`, `agents: Dict[str, AgentConfig]`, `simple_workflows: Dict[str, WorkflowConfig]`, `custom_workflows: Dict[str, CustomWorkflowConfig]`). This model serves as the in-memory representation of the active project's complete configuration.
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
    *   Offers methods (`save_component_config`, `delete_component_config`, `create_component_file`, `save_components_to_file`) to manage component JSON files on disk. These operations also update the in-memory store and handle path relativization when saving.
    *   `save_component_config` and `create_component_file` operate on *single* component models, saving to a file named after the component's ID.
    *   `save_components_to_file` saves a list of components to a *specified filename* as a JSON array.
*   **Role**: The `ComponentManager` acts as a comprehensive library or registry of all parseable component definitions found on the filesystem. Its primary consumer is the `ProjectManager`, which uses it to look up and resolve component references when loading a specific project configuration.

### 2.4. `ProjectManager` (`src/config/project_manager.py`)

In this design, the `ProjectManager` is repurposed to be the central manager of the *currently active project's configuration state* in memory.

*   **Initialization**: Takes an instance of `ComponentManager` as a dependency, which it uses to resolve component references.
*   **Internal State**:
    *   `self.active_project_config: Optional[ProjectConfig]`: This attribute holds the fully resolved `ProjectConfig` object for the project that is currently loaded and active in the system. It is `None` if no project is loaded.
*   **Core Methods**:
    *   `load_project(project_config_file_path: Path) -> ProjectConfig`:
        *   Reads the specified project JSON file (e.g., `config/projects/my_project.json`). Project files use keys like `clients`, `llms`, `agents`, `simple_workflows`, `custom_workflows` for lists of component definitions or references.
        *   For each component entry in these lists:
            *   If the entry is a string (ID reference), it calls `self.component_manager.get_component_config()` to retrieve the corresponding validated component model.
            *   If the entry is an inline dictionary, it parses and validates this dictionary into the appropriate Pydantic model (e.g., `ClientConfig`, `AgentConfig`), resolving any path fields.
        *   Aggregates all resolved and inline-defined components into their respective dictionaries (e.g., `clients`, `llms`, `agents`).
        *   Constructs a new `ProjectConfig` object using these aggregated component dictionaries, along with the project's name and description. The `ProjectConfig` model itself stores these collections as dictionaries (e.g., `project_config.agents` is `Dict[str, AgentConfig]`).
        *   Sets `self.active_project_config` to this newly created and fully resolved `ProjectConfig` object.
        *   Returns the created `ProjectConfig` object.
    *   `unload_active_project()`: Sets `self.active_project_config = None`.
    *   `get_active_project_config() -> Optional[ProjectConfig]`: Returns `self.active_project_config`.
    *   `get_host_config_for_active_project() -> Optional[HostConfig]`: Constructs `HostConfig` from `self.active_project_config.clients`.
*   **Dynamic Update Methods (for the active project)**:
    *   `add_component_to_active_project(component_type_key: str, component_id: str, component_model: BaseModel)`:
        *   Updates the appropriate dictionary within `self.active_project_config` (e.g., `self.active_project_config.agents[component_id] = component_model`, where `component_type_key` would be `"agents"`).

## 3. Integration with the Framework

The configuration system, centered around `ComponentManager` and the stateful `ProjectManager`, integrates with higher-level components like `HostManager`, API entrypoints, and `ExecutionFacade` to manage the application's behavior.

### 3.1. Entrypoints (API) and `HostManager`
(No changes to this section's text based on key renaming)

### 3.2. `HostManager` Orchestration of `ProjectManager`
(No changes to this section's text based on key renaming, but internal logic of `HostManager` using `ProjectConfig` fields would have changed)

### 3.3. `HostManager` Orchestration of Configuration and Runtime Registration

`HostManager` acts as the coordinator for dynamic registrations...

*   **Dynamic Client Registration (`HostManager.register_client(client_config_data: Dict)`)**:
    (No changes to this section's text based on key renaming)
*   **Dynamic Agent, LLM, or Workflow Registration (e.g., `HostManager.register_agent(agent_config_data: Dict)`)**:
    1.  The API route calls the relevant `HostManager` method.
    2.  `HostManager` parses the data into the appropriate Pydantic model (e.g., `AgentConfig`).
    3.  It performs semantic validations. For an `AgentConfig`, this includes checking if any `client_ids` it references are currently registered and active in `self.host` (via `self.host.is_client_registered()`) and if its `llm_config_id` refers to an LLM configuration present in `self.project_manager.get_active_project_config().llms`. (Updated `llm_configs` to `llms`)
    4.  **If all validations pass**: `HostManager` calls `self.project_manager.add_component_to_active_project("<component_type_key>", component_model.id, component_model)`. (e.g., `component_type_key` would be `"agents"` or `"llms"`).
    5.  If validation fails, an error is raised, and the `ProjectConfig` is not modified.

### 3.4. `HostManager` Orchestration of `ExecutionFacade`

The `HostManager` is responsible for instantiating the `ExecutionFacade`...

*   **`ExecutionFacade` Access to Configurations**:
    *   When `ExecutionFacade` needs to execute a component (e.g., `run_agent(agent_name, ...)`), it looks up the necessary configuration (e.g., `AgentConfig`) directly from the `ProjectConfig` object it holds: `agent_config = self._current_project.agents.get(agent_name)`. (Updated `agent_configs` to `agents`)
    *   Similarly, it uses `self._current_project.llms`, `self._current_project.simple_workflows`, etc., to retrieve other required component configurations. (Updated field names)
    *   All runtime interactions with MCP servers (executing tools, getting prompts) are delegated to the `MCPHost` instance it holds (`self._host`).

## 4. Summary of Benefits
(No changes to this section's text based on key renaming)

This architecture provides a solid foundation for managing complex configurations and runtime behaviors within the Aurite Agent Framework.
