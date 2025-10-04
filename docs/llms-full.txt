# Aurite Agents LLM Documentation

This document provides a comprehensive overview of the Aurite Agents framework, intended to be used as a knowledge base for an LLM-powered coding assistant. It covers core concepts, architecture, component configuration, usage patterns, and practical examples.

---

## Part 1: Introduction & Core Concepts

### Aurite Agents Framework

<p align="center">
  <img src="docs/images/aurite_logo.png" alt="Aurite Logo" width="200"/>
</p>

<p align="center">
  <strong>A Python framework for building, testing, and running AI agents.</strong>
</p>

---

**Aurite Agents** is a powerful, configuration-driven framework designed for building and orchestrating sophisticated AI agents. It enables agents to interact with a variety of external tools, prompts, and resources through the Model Context Protocol (MCP), allowing them to perform complex, multi-step tasks.

Whether you're creating advanced AI assistants, automating processes, or experimenting with agentic workflows, Aurite provides the modular building blocks and robust infrastructure you need.

### Key Features

- **Hierarchical Configuration:** Organize your components with a powerful **Workspace -> Project** system that allows for shared configurations and clear separation of concerns.
- **Declarative Components:** Define agents, LLMs, tools, and workflows in simple JSON or YAML files.
- **Interactive CLI & TUIs:** A rich command-line interface (`aurite`) and two built-in Textual User Interfaces (TUIs) for interactive chat and configuration editing.
- **Extensible Tooling:** Connect to any tool or service using the **Model Context Protocol (MCP)**, with built-in support for local and remote servers.
- **Flexible Orchestration:** Chain agents together in `linear_workflows` for sequential tasks or write custom Python logic in `custom_workflows` for complex orchestration.
- **REST API:** A comprehensive FastAPI server that exposes all framework functionality for programmatic access and UI development.

### Core Concepts

#### 1. Workspaces & Projects

Aurite uses a hierarchical system to organize your work, defined by a special `.aurite` file.

- **Workspace:** A top-level container that can manage multiple projects and share common configurations (e.g., a standard set of LLMs).
- **Project:** A self-contained directory holding all the configurations for a specific application or task.

This structure allows for clean separation and promotes reusable components.

#### 2. Components

Your application is built by defining and combining different types of components in `.json` or `.yaml` files.

- **Agents:** The core actors, powered by an LLM and capable of using tools.
- **LLMs:** Configurations for different language models (e.g., GPT-4, Claude 3).
- **MCP Servers:** Connections to external tools and resources.
- **Linear Workflows:** A sequence of agents to be executed in order.
- **Custom Workflows:** Complex orchestration logic defined in your own Python code.

#### 3. Interfaces

Aurite provides multiple ways to interact with the framework:

- **Web Interface (Aurite Studio):** Modern React web application for visual agent management, workflow design, and real-time execution monitoring.
- **TypeScript/JavaScript API:** Production-ready API client for building web applications and integrations with full type safety and streaming support.
- **Command-Line Interface (CLI):** The primary tool for managing your projects. Use it to `init`, `list`, `show`, `run`, and `edit` your components.
- **Textual User Interfaces (TUIs):** Rich, in-terminal applications for interactive chat with agents (`aurite run <agent_name>`) and live configuration editing (`aurite edit`).
- **REST API:** A complete FastAPI server (`aurite api`) that exposes all framework functionality for UIs and programmatic control.

---

## Part 2: Framework Architecture

### Aurite Framework Architecture Overview

**Version:** 1.0
**Date:** 2025-08-02

#### Overview

The Aurite Framework is a comprehensive system for building and executing AI agents and workflows with distributed tool access through the Model Context Protocol (MCP). The framework provides a unified interface for orchestrating complex AI interactions while maintaining clean separation of concerns through a layered architecture centered around the `Aurite` class and its internal `AuriteKernel`.

**Key Problem Solved**: Unified AI agent and workflow orchestration with distributed tool access, persistent session management, and comprehensive configuration management across complex project hierarchies.

#### Framework Architecture

```mermaid
graph TD
    A[Aurite Framework] --> B[Public API Layer]
    A --> C[Kernel Layer]
    A --> D[Execution Layer]
    A --> E[Infrastructure Layer]

    B --> F[Aurite Class]
    B --> G[CLI Interface]
    B --> H[REST API]
    B --> I[TUI Interface]

    C --> J[AuriteKernel]
    C --> K[Lazy Initialization]
    C --> L[Lifecycle Management]

    D --> M[AuriteEngine]
    D --> N[Agent Execution]
    D --> O[Workflow Execution]
    D --> P[Streaming Support]

    E --> Q[ConfigManager]
    E --> R[MCPHost]
    E --> S[SessionManager]
    E --> T[Storage Systems]

    style A fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
    style B fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    style C fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    style D fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    style E fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    style F fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
    style J fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
    style M fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
```

#### Core Framework Components

The Aurite Framework is built around a two-tier architecture that separates public interfaces from internal implementation details while providing comprehensive AI orchestration capabilities.

##### Public Interface Layer

=== "Aurite Class"

    **Purpose**: Main framework entrypoint providing a clean, async-native API for AI agent and workflow execution.

    **Key Responsibilities**:
    - **Lazy Initialization**: Components initialized only when first used for optimal performance
    - **Lifecycle Management**: Automatic resource cleanup and graceful shutdown handling
    - **Public API**: Simple, intuitive methods for agent and workflow execution
    - **Programmatic Registration**: Runtime component registration for testing and notebooks
    - **Context Management**: Async context manager support for explicit resource control

    **Core API Methods**:
    ```python
    # Agent execution
    async def run_agent(self, agent_name: str, user_message: str,
                       system_prompt: Optional[str] = None,
                       session_id: Optional[str] = None) -> AgentRunResult

    # Streaming agent execution
    async def stream_agent(self, agent_name: str, user_message: str,
                          system_prompt: Optional[str] = None,
                          session_id: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]

    # Workflow execution
    async def run_linear_workflow(self, workflow_name: str,
                                 initial_input: Any) -> LinearWorkflowExecutionResult
    async def run_custom_workflow(self, workflow_name: str, initial_input: Any,
                                 session_id: Optional[str] = None) -> Any

    # Component registration
    async def register_agent(self, config: AgentConfig)
    async def register_llm(self, config: LLMConfig)
    async def register_mcp_server(self, config: ClientConfig)
    ```

    **Design Patterns**:
    - **Wrapper Pattern**: Encapsulates complex async lifecycle management
    - **Lazy Initialization**: Services started only when needed
    - **Graceful Degradation**: Continues operation even with partial component failures

=== "Interface Diversity"

    **CLI Interface**: Command-line tools for development and operations
    - Component management (list, create, update, delete)
    - Execution commands for agents and workflows
    - Configuration validation and testing
    - Session management and cleanup

    **REST API**: HTTP endpoints for web applications and integrations
    - RESTful component CRUD operations
    - Execution endpoints with streaming support
    - Session history and management APIs
    - Real-time execution monitoring

    **TUI Interface**: Terminal-based interactive interface
    - Visual component browsing and management
    - Interactive execution with real-time feedback
    - Session exploration and debugging tools
    - Configuration editing and validation

    **Python API**: Direct programmatic access
    - Jupyter notebook integration
    - Testing framework support
    - Custom application embedding
    - Programmatic component registration

##### Kernel Layer

=== "AuriteKernel"

    **Purpose**: Internal framework kernel managing core component lifecycle and coordination.

    **Architecture Responsibilities**:
    - **Component Initialization**: Manages startup sequence and dependencies
    - **Resource Coordination**: Coordinates between ConfigManager, MCPHost, and storage systems
    - **Environment Configuration**: Handles environment-based feature toggles and settings
    - **Cleanup Management**: Ensures proper resource cleanup including external library cleanup

    **Component Initialization Flow**:
    ```python
    # AuriteKernel.__init__
    self.config_manager = ConfigManager(start_dir=start_dir)
    self.project_root = self.config_manager.project_root
    self.host = MCPHost()

    # Conditional storage initialization
    if os.getenv("AURITE_ENABLE_DB", "false").lower() == "true":
        self._db_engine = create_db_engine()
        self.storage_manager = StorageManager(engine=self._db_engine)

    # Session management setup
    cache_dir = self.project_root / ".aurite_cache" if self.project_root else Path(".aurite_cache")
    self.cache_manager = CacheManager(cache_dir=cache_dir)

    # Observability integration
    if os.getenv("LANGFUSE_ENABLED", "false").lower() == "true":
        self.langfuse = Langfuse(...)

    # Central execution engine
    self.execution = AuriteEngine(
        config_manager=self.config_manager,
        host_instance=self.host,
        storage_manager=self.storage_manager,
        cache_manager=self.cache_manager,
        langfuse=self.langfuse,
    )
    ```

    **Async Lifecycle Management**:
    ```python
    async def initialize(self):
        # Database initialization
        if self.storage_manager:
            self.storage_manager.init_db()

        # MCP Host startup
        if self.host:
            await self.host.__aenter__()

    async def shutdown(self):
        # External library cleanup (litellm)
        # MCP Host cleanup
        # Database connection cleanup
        # Resource disposal
    ```

    **Key Design Decisions**:
    - **Environment-Driven Configuration**: Features enabled through environment variables
    - **Graceful Degradation**: Optional components (DB, Langfuse) don't prevent startup
    - **Project-Aware Caching**: Cache directory based on detected project structure
    - **Comprehensive Cleanup**: Handles cleanup of external libraries and resources

##### Execution Layer

=== "AuriteEngine Integration"

    **Purpose**: Central execution orchestrator coordinating all framework components for unified AI operations.

    **Integration Architecture**:
    ```mermaid
    graph TD
        A[AuriteEngine] --> B[ConfigManager Integration]
        A --> C[MCPHost Integration]
        A --> D[SessionManager Integration]
        A --> E[Component Execution]

        B --> F[Component Resolution]
        B --> G[Configuration Validation]
        B --> H[Path Resolution]

        C --> I[JIT Server Registration]
        C --> J[Tool Execution]
        C --> K[Resource Access]

        D --> L[History Management]
        D --> M[Result Persistence]
        D --> N[Session Lifecycle]

        E --> O[Agent Orchestration]
        E --> P[Workflow Coordination]
        E --> Q[Streaming Management]

        style A fill:#2196F3,stroke:#1976D2,stroke-width:2px,color:#fff
        style B fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style C fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style D fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
        style E fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
    ```

    **Orchestration Capabilities**:
    - **Unified Execution Interface**: Single API for agents, linear workflows, and custom workflows
    - **JIT Resource Provisioning**: Dynamic MCP server registration based on component requirements
    - **Session Coordination**: Automatic session management with history persistence
    - **Streaming Support**: Real-time event streaming for interactive applications
    - **Error Handling**: Comprehensive error management with context preservation

##### Infrastructure Layer

=== "Configuration Management"

    **ConfigManager**: Hierarchical configuration discovery and management system.

    **Key Capabilities**:
    - **Project/Workspace Discovery**: Automatic detection of project boundaries and hierarchies
    - **Priority-Based Resolution**: Context-aware configuration with proper precedence handling
    - **Component Indexing**: Comprehensive indexing of agents, LLMs, MCP servers, and workflows
    - **CRUD Operations**: Full component lifecycle management with validation
    - **Path Resolution**: Context-aware path resolution for relative configurations

=== "Distributed Tool Management"

    **MCPHost**: Model Context Protocol server management and tool orchestration.

    **Key Capabilities**:
    - **Multi-Transport Support**: STDIO, local command, and HTTP stream transports
    - **JIT Registration**: Dynamic server registration based on agent requirements
    - **Component Discovery**: Automatic tool, prompt, and resource discovery
    - **Security & Filtering**: Comprehensive access control and filtering systems
    - **Session Management**: Robust session lifecycle with proper cleanup

=== "Session & Storage Management"

    **SessionManager + CacheManager**: Persistent conversation and execution result management.

    **Key Capabilities**:
    - **Two-Tier Storage**: High-level session operations with low-level file management
    - **Metadata Tracking**: Comprehensive session metadata with validation
    - **Relationship Management**: Parent-child relationships for workflow sessions
    - **Retention Policies**: Automatic cleanup with age and count-based policies
    - **Partial ID Matching**: Flexible session retrieval with ambiguity resolution

    **Storage Options**:
    - **File-Based (CacheManager)**: JSON files with in-memory caching for development
    - **Database (StorageManager)**: PostgreSQL/SQLite for production environments

#### Framework Integration Patterns

##### Lazy Initialization Pattern

The framework implements comprehensive lazy initialization to optimize startup performance and resource usage:

```python
# Aurite class initialization
def __init__(self, start_dir: Optional[Path] = None, disable_logging: bool = False):
    # Only create kernel, don't initialize services
    self.kernel = AuriteKernel(start_dir=start_dir, disable_logging=disable_logging)
    self._initialized = False

async def _ensure_initialized(self):
    # Services initialized only on first use
    if not self._initialized:
        await self.kernel.initialize()
        self._initialized = True
```

##### Component Coordination Pattern

The framework coordinates between multiple specialized components through the AuriteEngine:

```python
# Component coordination in AuriteEngine
async def run_agent(self, agent_name: str, user_message: str, ...):
    # 1. Configuration resolution through ConfigManager
    agent_config = self._config_manager.get_config("agent", agent_name)

    # 2. JIT server registration through MCPHost
    for server_name in agent_config.mcp_servers:
        if server_name not in self._host.registered_server_names:
            await self._host.register_client(server_config)

    # 3. Session management through SessionManager
    if session_id and self._session_manager:
        history = self._session_manager.get_session_history(session_id)

    # 4. Agent execution with coordinated resources
    agent_instance = Agent(config, llm_config, host, initial_messages)
    result = await agent_instance.run_conversation()

    # 5. Result persistence
    self._session_manager.save_agent_result(session_id, result)
```

#### Framework Execution Flows

##### Agent Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant Aurite
    participant Kernel
    participant Engine
    participant Config
    participant Host
    participant Session

    User->>Aurite: run_agent(name, message)
    Aurite->>Aurite: _ensure_initialized()
    Aurite->>Kernel: initialize() [if needed]
    Aurite->>Engine: run_agent(name, message)
    Engine->>Config: get_config("agent", name)
    Config-->>Engine: agent_config
    Engine->>Host: register_servers(mcp_servers)
    Host-->>Engine: servers_registered
    Engine->>Session: get_session_history(session_id)
    Session-->>Engine: conversation_history
    Engine->>Engine: execute_agent()
    Engine->>Session: save_agent_result(result)
    Engine-->>Aurite: AgentRunResult
    Aurite-->>User: result
```

---

## Part 3: Component Configuration

### Projects and Workspaces

The Aurite framework uses a powerful hierarchical configuration system built on two core concepts: **Projects** and **Workspaces**. This system is driven by a special anchor file named `.aurite`, which tells the framework how to discover and prioritize configurations.

!!! info "The `.aurite` Anchor File"
The framework finds configurations by searching upwards from your current directory for `.aurite` files. This file marks a directory as a **Project** or a **Workspace** root and specifies which subdirectories contain configuration files.

---

#### Configuration Contexts

Your configurations are organized into contexts, allowing for both separation of concerns and sharing of common components.

=== ":material-folder-home-outline: Project"

    A **Project** is a self-contained directory for a specific task or set of related tasks. It's the most common organizational unit.

    To define a project, create an `.aurite` file in its root directory.

    **`.aurite` File Fields:**

    |  Field  |  Type  |  Required  |  Description  |
    |----|----|----|----|
    | `type` | `string` | Yes | Must be set to `"project"`. |
    | `include_configs` | `list[string]` | Yes | A list of directories (relative to the `.aurite` file) where component configurations are stored. |

    **Example `.aurite`:**
    ```toml
    # .aurite
    [aurite]
    type = "project"
    include_configs = ["config", "shared_components"]
    ```

=== ":material-folder-multiple-outline: Workspace"

    A **Workspace** is a higher-level container that can manage multiple projects and shared configurations.

    **`.aurite` File Fields:**

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `type` | `string` | Yes | Must be set to `"workspace"`. |
    | `include_configs` | `list[string]` | Yes | A list of directories containing shared, workspace-level configurations. |
    | `projects` | `list[string]` | No | An optional list of subdirectories that are individual projects. |

    **Example `.aurite`:**
    ```toml
    # .aurite
    [aurite]
    type = "workspace"
    projects = ["project-a", "project-b"]
    include_configs = ["workspace_config"]
    ```

---

#### Priority Resolution

When the framework looks for a component, it searches contexts in a specific order. A component found in a higher-priority context overrides one with the same name from a lower-priority context.

The priority is as follows, from highest to lowest:

1.  **In-Memory**: Programmatically registered components (highest priority).
2.  **Project Level**: Configurations from the current project's `include_configs` directories.
3.  **Workspace Level**: Configurations from the parent workspace's `include_configs` directories.
4.  **Other Projects**: Configurations from other projects within the same workspace.

!!! example "Overriding Example"
You could define a `standard-llm` at the workspace level, and a `standard-llm` at the project level. The framework automatically picks the most specific one based on your current directory.

---

#### Path Resolution

When a component configuration references a local file (e.g., `server_path` in an MCP server), you can use a relative path.

**All relative paths are resolved from the location of the `.aurite` file that defines their context.**

This makes your configurations portable and easy to share.

!!! example "Path Resolution Example"
Imagine the following setup:

    - Your workspace is at `/path/to/my-workspace/`.
    - Its `.aurite` file is at `/path/to/my-workspace/.aurite`.
    - A shared server is defined in `/path/to/my-workspace/workspace-config/servers.json`.
    - The server's `server_path` is set to `mcp_servers/shared_server.py`.

    The framework will correctly resolve the full path to `/path/to/my-workspace/mcp_servers/shared_server.py`.

### Agent Configuration

Agents are the primary actors in the Aurite framework, responsible for executing tasks by interacting with tools and models. The agent configuration defines an agent's identity, its capabilities, and its behavior.

An agent configuration is a JSON or YAML object with a `type` field set to `"agent"`.

!!! tip "Configuration Location"

    Agent configurations can be placed in any directory specified in your project's `.aurite` file (e.g., `config/agents/`, `shared/agents/`). The framework will automatically discover them.

---

#### Schema

The `AgentConfig` defines the structure for an agent configuration. Below are the available fields, categorized for clarity.

=== ":material-format-list-bulleted-type: Core Fields"

    These fields define the fundamental properties of the agent.

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `name` | `string` | Yes | A unique identifier for the agent. This name is used to reference the agent in workflows and commands. |
    | `description` | `string` | No | A brief, human-readable description of what the agent does. |
    | `llm_config_id` | `string` | `None` | The `name` of an `llm` component to use. This is the recommended way to assign an LLM, allowing for reusable configurations. |
    | `system_prompt` | `string` | No | The primary system prompt for the agent. This can be overridden by the `system_prompt` in the `llm` block. |
    | `mcp_servers` | `list[string]` | `[]` | A list of `mcp_server` component names this agent can use. The agent gains access to all tools, prompts, and resources from these servers. |
    | `config_validation_schema` | `dict` | `None` | A JSON schema for validating agent-specific configurations. |

=== ":material-tools: Tool Management"

    These fields control which tools and resources the agent can access.

    | Field | Type | Default | Description |
    | --- | --- | --- | --- |
    | `exclude_components` | `list[string]` | `None` | A list of component names (tools, prompts, resources) to explicitly exclude, even if provided by allowed `mcp_servers`. |
    | `auto` | `boolean` | `false` | If `true`, an LLM dynamically selects the most appropriate `mcp_servers` at runtime based on the user's prompt. |

=== ":simple-amd: LLM Overrides"

    These fields control the Large Language Model that powers the agent's reasoning.

    | Field | Type | Default | Description |
    | --- | --- | --- | --- |
    | `model`          | `string`  | None    | Override the model name (e.g., `"gpt-3.5-turbo"`). |
    | `temperature`    | `float`   | None    | Override the sampling temperature for the agent's LLM. |
    | `max_tokens`     | `integer` | None    | Override the maximum token limit for responses. |
    | `system_prompt`  | `string`  | None    | Provide a more specific system prompt for this agent. |
    | `api_base`       | `string`  | None    | Custom API endpoint base URL for the LLM provider. |
    | `api_key`        | `string`  | None    | Custom API key for the LLM provider. |
    | `api_version`    | `string`  | None    | Custom API version for the LLM provider. |
    | *other fields*   | *various* | None    | Any other provider-specific parameters supported by the [LLM Configuration](../config/llm.md). |

    !!! abstract "LLM Overrides"
        Agent Configurations can include llm variables (See LLM Overrides in the table above). These variables will replace the corresponding values in the LLM Configuration referenced by `llm_config_id`. This allows for agent-specific customization while still using a shared LLM configuration.

=== ":material-cogs: Behavior Control"

    These fields fine-tune how the agent executes its tasks.

    | Field | Type | Default | Description |
    | --- | --- | --- | --- |
    | `max_iterations` | `integer` | `50` | The maximum number of conversational turns before stopping automatically. This is a safeguard to prevent infinite loops. |
    | `include_history` | `boolean` | `None` | If `true`, the entire conversation history is included in each turn. If `false` or `None`, the agent is stateless and only sees the latest message. |

---

#### Configuration Examples

Here are some practical examples of agent configurations.

=== "Simple Agent"

    A basic agent that uses a centrally-defined LLM and has access to a set of tools.

    ```json
    {
      "type": "agent",
      "name": "code-refactor-agent",
      "description": "An agent that helps refactor Python code by using static analysis tools.",
      "mcp_servers": ["pylint-server", "file-system-server"],
      "llm_config_id": "claude-3-opus",
      "system_prompt": "You are an expert Python programmer. You will be given a file and your goal is to refactor it to improve readability and performance.",
      "max_iterations": 10
    }
    ```

=== "Agent with LLM Overrides"

    This agent uses a base LLM configuration but overrides the model and temperature for its specific task.

    ```json
    {
      "type": "agent",
      "name": "creative-writer-agent",
      "description": "An agent for brainstorming creative ideas.",
      "mcp_servers": ["internet-search-server"],
      "llm_config_id": "gpt-4-base",
      "model": "gpt-4-1106-preview",
      "temperature": 0.9
    }
    ```

=== "Stateful Agent"

    This agent is configured to be stateful (`include_history` is `true`), allowing it to maintain context across multiple turns.

    ```json
    {
      "type": "agent",
      "name": "simple-calculator-agent",
      "description": "A stateless agent that performs a single calculation.",
      "mcp_servers": ["calculator-tool-server"],
      "llm_config_id": "gpt-3.5-turbo",
      "include_history": true
    }
    ```

=== "Agent with Schema"

    This agent includes a custom validation schema to ensure its configuration adheres to specific rules.

    ```json
    {
      "type": "agent",
      "name": "data-validation-agent",
      "description": "An agent that validates data formats.",
      "mcp_servers": ["data-validator-server"],
      "llm_config_id": "gpt-3.5-turbo",
      "config_validation_schema": {
        "type": "object",
        "properties": {
          "input_format": { "type": "string" },
          "output_format": { "type": "string" }
        },
        "required": ["input_format", "output_format"]
      }
    }
    ```

### LLM Configuration

LLM (Large Language Model) configurations are reusable components that define the settings for a specific model from a particular provider. By defining LLMs centrally, you can easily share them across multiple agents and manage your model settings in one place.

An LLM configuration is a JSON or YAML object with a `type` field set to `"llm"`.

!!! tip "Configuration Location"

    LLM configurations can be placed in any directory specified in your project's `.aurite` file (e.g., `config/`, `shared/llms/`). The framework will automatically discover them.

---

#### Schema

The `LLMConfig` defines the structure for an LLM configuration. Below are the available fields, categorized for clarity.

=== ":material-format-list-bulleted-type: Core Fields"

    These fields are essential for defining the identity and source of the model.

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `name` | `string` | Yes | A unique identifier for the LLM configuration. This name is used in an agent's `llm_config_id` field to link to this configuration. |
    | `provider` | `string` | Yes | The name of the LLM provider, corresponding to a provider supported by the underlying model library (e.g., LiteLLM). Common values include `openai`, `anthropic`, `gemini`, `groq`. |
    | `model` | `string` | Yes | The specific model name as recognized by the provider (e.g., `gpt-4-1106-preview`). |
    | `description` | `string` | No | A brief, human-readable description of the LLM configuration. |

=== ":material-tune: Common Parameters"

    These are standard LLM parameters that can be set as defaults for this configuration. Agents can override these values.

    | Field | Type | Default | Description |
    | --- | --- | --- | --- |
    | `temperature` | `float` | `None` | The sampling temperature to use (0-2). Higher values (e.g., 0.8) make output more random; lower values (e.g., 0.2) make it more deterministic. |
    | `max_tokens` | `integer` | `None` | The maximum number of tokens to generate in the completion. |
    | `default_system_prompt` | `string` | `None` | A default system prompt for this LLM. An agent's `system_prompt` will override this value. |

=== ":material-api: Provider-Specific Fields"

    These fields are used for connecting to specific APIs, especially for self-hosted or non-standard endpoints.

    | Field | Type | Default | Description |
    | --- | --- | --- | --- |
    | `api_base` | `string` | `None` | The base URL for the API endpoint. Commonly used for local models (e.g., `http://localhost:8000/v1`) or custom provider endpoints. |
    | `api_key_env_var` | `string` | `None` | The environment variable name for the API key if not using a default (e.g., `ANTHROPIC_API_KEY`). |
    | `api_version` | `string` | `None` | The API version string required by some providers (e.g., Azure OpenAI). |

---

#### Agent Overrides

While `LLMConfig` provides a central place for model settings, individual agents can override them at runtime using the same configuration variables inserted directly into the AgentConfig. This provides flexibility for agent-specific needs.

!!! example "See the [Agent Configuration](../config/agent.md) documentation for more details on how to apply these overrides."

---

#### Configuration Examples

Here are some practical examples of LLM configurations for different providers.

=== "OpenAI"

    ```json
    {
      "type": "llm",
      "name": "gpt-4-turbo",
      "description": "Configuration for OpenAI's GPT-4 Turbo model.",
      "provider": "openai",
      "model": "gpt-4-1106-preview",
      "temperature": 0.5,
      "max_tokens": 4096
    }
    ```

=== "Anthropic"

    ```json
    {
      "type": "llm",
      "name": "claude-3-sonnet",
      "description": "Configuration for Anthropic's Claude 3 Sonnet model.",
      "provider": "anthropic",
      "model": "claude-3-sonnet-20240229",
      "temperature": 0.7,
      "default_system_prompt": "You are a helpful and friendly assistant."
    }
    ```

=== "Local (Ollama)"

    This example configures a local Llama 3 model served by Ollama.

    ```json
    {
      "type": "llm",
      "name": "local-llama3",
      "description": "Configuration for a local Llama 3 model served by Ollama.",
      "provider": "ollama",
      "model": "llama3",
      "api_base": "http://localhost:11434",
      "temperature": 0.7
    }
    ```

### MCP Server Configuration

MCP (Model-Context-Protocol) Servers are the backbone of an agent's capabilities. They are responsible for providing the tools, prompts, and resources that an agent can use to perform tasks. Each `mcp_server` configuration tells the framework how to connect to and interact with a specific server.

An MCP server configuration is a JSON or YAML object with a `type` field set to `"mcp_server"`.

!!! tip "Configuration Location"

    MCP Server configurations can be placed in any directory specified in your project's `.aurite` file (e.g., `config/mcp_servers/`). The framework will automatically discover them.

---

#### Schema

!!! info "Transport Types"
The `ClientConfig` model defines the structure for an MCP server configuration. There are three main transport types: `stdio`, `http_stream`, and `local`. Each transport type has its own required fields. The framework will infer the transport type based on the fields you provide.

=== ":material-format-list-bulleted-type: Core Fields"

    These fields define the fundamental properties of the server.

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `name` | `string` | Yes | A unique identifier for the MCP server. This name is used in an agent's `mcp_servers` list and as a prefix for its components (e.g., `my_server-tool_name`). |
    | `description` | `string` | No | A brief, human-readable description of the server's purpose. |
    | `capabilities` | `list[string]` | Yes | A list of the types of components this server provides. Accepted values are `"tools"`, `"prompts"`, and `"resources"`. |

=== ":material-transit-connection-variant: Transport Types"

    You must configure one of the following transport types. The framework will automatically infer the `transport_type` based on the fields you provide.

    ---
    **`stdio`**

    This is the most common transport for running local Python scripts as servers.

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `server_path` | `string` or `Path` | Yes | The path to the Python script that runs the MCP server. This path can be relative to the `.aurite` file of its context. |

    ---
    **`http_stream`**

    This transport is used for connecting to servers that are already running and accessible via an HTTP endpoint.

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `http_endpoint` | `string` | Yes | The full URL of the server's streaming endpoint. |
    | `headers` | `dict[str, str]` | No | A dictionary of HTTP headers to include in the request (e.g., for authentication). |

    ---
    **`local`**

    This transport is for running any executable command as a server.

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `command` | `string` | Yes | The command or executable to run. |
    | `args` | `list[string]` | No | A list of arguments to pass to the command. |

=== ":material-cogs: Advanced Fields"

    These fields provide fine-grained control over the server's behavior.

    | Field | Type | Default | Description |
    | --- | --- | --- | --- |
    | `timeout` | `float` | `10.0` | The default timeout in seconds for operations (like tool calls) sent to this server. |
    | `registration_timeout` | `float` | `30.0` | The timeout in seconds for registering this server. |
    | `exclude` | `list[string]` | `None` | A list of component names (tools, prompts, or resources) to exclude from this server's offerings. |
    | `roots` | `list[object]` | `[]` | A list of root objects describing the server's capabilities. This is typically auto-discovered and rarely needs to be set manually. |

---

#### Configuration Examples

Here are some practical examples for each transport type.

=== "Stdio Transport"

    This example runs a local Python script as an MCP server.

    ```json
    {
      "type": "mcp_server",
      "name": "weather-server",
      "description": "Provides weather forecast tools.",
      "server_path": "mcp_servers/weather_server.py",
      "capabilities": ["tools"]
    }
    ```

=== "HTTP Stream Transport"

    This example connects to a custom running service. Note the use of an environment variable in the header for authentication.

    ```json
    {
      "type": "mcp_server",
      "name": "my-remote-service",
      "description": "Connects to a custom remote service.",
      "http_endpoint": "https://my-custom-service.com/mcp",
      "headers": {
        "X-API-Key": "{MY_SERVICE_API_KEY}"
      },
      "capabilities": ["tools", "resources"]
    }
    ```

=== "Local Command Transport"

    This example runs a pre-compiled binary as a server.

    ```json
    {
      "type": "mcp_server",
      "name": "my-custom-binary-server",
      "description": "A server running from a custom binary.",
      "command": "bin/my_server",
      "args": ["--port", "8080"],
      "capabilities": ["tools"]
    }
    ```

### Linear Workflow Configuration

Linear workflows provide a straightforward way to execute a series of components in a predefined, sequential order. They are perfect for tasks that follow a linear process, such as "first run the data-ingestion agent, then run the analysis agent."

A linear workflow configuration is a JSON or YAML object with a `type` field set to `"linear_workflow"`.

!!! info "How It Works"
When you execute a linear workflow, the framework iterates through the `steps` list in order. The output from one step is passed as the input to the next, allowing you to chain components together to create a processing pipeline.

---

#### Schema

The `WorkflowConfig` defines the structure for a linear workflow.

=== ":material-format-list-bulleted-type: Core Fields"

    These fields define the fundamental properties of the workflow.

    | Field             | Type                     | Required | Description                                                                                                                         |
    | ----------------- | ------------------------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------- |
    | `name`            | `string`                 | Yes      | A unique identifier for the workflow. This name is used to run the workflow from the CLI or API.                                    |
    | `description`     | `string`                 | No       | A brief, human-readable description of what the workflow accomplishes.                                                              |
    | `steps`           | `list[string or object]` | Yes      | An ordered list of the components to execute. See "Steps Configuration" below for details.                                          |
    | `include_history` | `boolean`                | `None`   | If set, overrides the `include_history` setting for all agents in the workflow, forcing them all to either save or discard history. |

=== ":material-step-forward: Steps Configuration"

    The core of a linear workflow is the `steps` list. Each item in the list can be either a simple string (the component name) or a detailed object.

    **Simple Step (by Name)**

    The easiest way to define a step is to provide the `name` of the component.

    ```json
    "steps": ["fetch-data-agent", "process-data-agent"]
    ```

    **Detailed Step (by Object)**

    For more clarity, you can specify the component `type` along with its `name`. This is useful if you have components of different types with the same name.

    ```json
    "steps": [
      { "name": "fetch-data-agent", "type": "agent" },
      { "name": "analysis-pipeline", "type": "linear_workflow" }
    ]
    ```

    The `type` can be `"agent"`, `"linear_workflow"`, or `"custom_workflow"`.

---

#### Configuration Examples

=== "Simple Pipeline"

    This example defines a two-step workflow for processing customer feedback.

    ```json
    {
      "type": "linear_workflow",
      "name": "customer-feedback-pipeline",
      "description": "Fetches customer feedback, analyzes sentiment, and saves the result.",
      "steps": ["fetch-feedback-agent", "analyze-sentiment-agent"]
    }
    ```

=== "Workflow with History Override"

    This workflow forces all agents within it to maintain conversation history, which is useful for debugging or creating a continuous conversational experience across multiple agents.

    ```json
    {
      "type": "linear_workflow",
      "name": "stateful-support-flow",
      "description": "A multi-agent support flow that remembers the conversation.",
      "include_history": true,
      "steps": ["greeting-agent", "support-agent", "followup-agent"]
    }
    ```

=== "Nested Workflow"

    This example shows how a linear workflow can include another workflow as one of its steps.

    ```json
    {
      "type": "linear_workflow",
      "name": "daily-reporting-process",
      "description": "A top-level workflow that orchestrates other workflows and agents.",
      "steps": [
        { "name": "ingestion-workflow", "type": "linear_workflow" },
        { "name": "analysis-agent", "type": "agent" },
        { "name": "distribution-workflow", "type": "custom_workflow" }
      ]
    }
    ```

### Custom Workflow Configuration

When a `linear_workflow` isn't enough to capture your logic, you can implement a **Custom Workflow** directly in Python. This gives you complete control over the execution flow, allowing for conditional logic, branching, looping, and complex data manipulation between steps.

A custom workflow configuration is a JSON or YAML object with a `type` field set to `"custom_workflow"`. Its purpose is to link a component name to your Python code.

!!! info "How It Works" 1. **Configuration:** You create a config file that gives your workflow a `name` and points to the `module_path` and `class_name` of your Python code. 2. **Implementation:** You write a Python class that inherits from `aurite.BaseCustomWorkflow` and implements the `run` method. 3. **Execution:** When you run the workflow by its `name`, the framework dynamically loads your Python class, instantiates it, and calls its `run` method, passing in the initial input and an execution engine.

---

#### Schema and Implementation

Configuring a custom workflow involves two parts: the configuration file and the Python implementation.

=== ":material-file-document-outline: Configuration Schema"

    The configuration file tells the framework where to find your Python code.

    | Field         | Type     | Required | Description                                                                                             |
    |---------------|----------|----------|---------------------------------------------------------------------------------------------------------|
    | `name`        | `string` | Yes      | A unique identifier for the custom workflow.                                                            |
    | `description` | `string` | No       | A brief, human-readable description of what the workflow does.                                          |
    | `module_path` | `string` | Yes      | The path to the Python file containing your workflow class, relative to your project's root directory.  |
    | `class_name`  | `string` | Yes      | The name of the class within the module that implements the workflow.                                   |

=== ":material-code-braces: Python Implementation"

    Your Python class must inherit from `BaseCustomWorkflow` and implement the `run` method.

    ```python
    from typing import Any, Optional
    from aurite import AuriteEngine, BaseCustomWorkflow, AgentRunResult

    class MyWorkflow(BaseCustomWorkflow):
        async def run(
            self,
            initial_input: Any,
            executor: "AuriteEngine",
            session_id: Optional[str] = None
        ) -> Any:
            # Your custom logic goes here
            print(f"Workflow started with input: {initial_input}")

            # You can run agents using the executor instance passed to this method
            result: AgentRunResult = await executor.run_agent(
                agent_name="my-agent",
                user_message="What is the weather in SF?",
                session_id=session_id # Pass the session_id for history
            )

            return {"final_output": result.message_content}

        def get_input_type(self) -> Any:
            """(Optional) Returns the expected type of `initial_input`."""
            return str

        def get_output_type(self) -> Any:
            """(Optional) Returns the expected type of the workflow's final output."""
            return dict
    ```

    **Key Components:**

    - **`BaseCustomWorkflow`**: The required base class from `aurite`.
    - **`run(self, initial_input, executor, session_id)`**: The main entry point for your workflow's logic. This method must be implemented.
        - `initial_input`: The data passed to the workflow when it's executed.
        - `executor`: An instance of `AuriteEngine`, which allows you to run other components like agents (`executor.run_agent(...)`).
        - `session_id`: An optional session ID for maintaining conversation history.
    - **`get_input_type()` (Optional)**: A method that returns the expected Python type for `initial_input`. This can be used for documentation or validation.
    - **`get_output_type()` (Optional)**: A method that returns the expected Python type for the value your `run` method returns.

---

#### End-to-End Example

This example shows how to create a custom workflow that intelligently routes a task to one of two agents based on the input. The file structure illustrates how the `module_path` is relative to the directory containing the `.aurite` file.

=== "1. Project Structure"

    ```
    my_project/
    ├── .aurite
    ├── config/
    │   └── workflows/
    │       └── routing_workflow.json  <-- Configuration File
    └── custom_workflows/
        └── my_routing_logic.py      <-- Python Implementation
    ```

=== "2. Configuration File"

    `my_project/config/workflows/routing_workflow.json`

    ```json
    {
      "type": "custom_workflow",
      "name": "intelligent-routing-workflow",
      "description": "A workflow that dynamically routes tasks to different agents based on input content.",
      "module_path": "custom_workflows/my_routing_logic.py",
      "class_name": "MyRoutingWorkflow"
    }
    ```

=== "3. Python Implementation"

    `my_project/custom_workflows/my_routing_logic.py`

    ```python
    from typing import Any, Dict, Optional
    from aurite import AuriteEngine, BaseCustomWorkflow, AgentRunResult

    class MyRoutingWorkflow(BaseCustomWorkflow):
        """
        This workflow checks the input for keywords and routes the request
        to either a weather agent or a calculator agent.
        """
        async def run(
            self,
            initial_input: Dict[str, Any],
            executor: "AuriteEngine",
            session_id: Optional[str] = None
        ) -> AgentRunResult:
            user_message = initial_input.get("message", "")

            if "weather" in user_message.lower():
                agent_to_run = "weather-agent"
            elif "calculate" in user_message.lower():
                agent_to_run = "calculator-agent"
            else:
                agent_to_run = "general-qa-agent"

            print(f"Routing to agent: {agent_to_run}")

            # Run the selected agent using the provided executor
            result = await executor.run_agent(
                agent_name=agent_to_run,
                user_message=user_message,
                session_id=session_id
            )
            return result
    ```

---

## Part 4: Usage and Interaction

### API Reference

The Aurite Framework API is organized around four core managers, each with its own base path and specific responsibilities. This document provides a comprehensive reference for all available endpoints.

!!! info "Interactive API Docs"
For detailed request/response schemas and to try out the API live, please use the interactive documentation interfaces available when the server is running:

    -   `/api-docs` - Swagger UI interface
    -   `/redoc` - ReDoc documentation interface
    -   `/openapi.json` - Raw OpenAPI schema

---

#### Authentication & Base URL

All API endpoints require authentication via an API key.

- **Header:** `X-API-Key: your-api-key-here`
- **Base URL:** `http://localhost:8000`

---

#### API Endpoints

The API is structured around four main routers.

=== ":material-cogs: Configuration (`/config`)"

    Handles all configuration file operations, component CRUD, and project/workspace management.

    **Component CRUD**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `GET` | `/config/components` | List all component types. |
    | `GET` | `/config/components/{type}` | List all components of a specific type. |
    | `POST` | `/config/components/{type}` | Create a new component. |
    | `GET` | `/config/components/{type}/{id}` | Get a specific component's details. |
    | `PUT` | `/config/components/{type}/{id}` | Update an existing component. |
    | `DELETE` | `/config/components/{type}/{id}` | Delete a component. |
    | `POST` | `/config/components/{type}/{id}/validate` | Validate a component's configuration. |

    **Project & Workspace Management**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `GET` | `/config/projects` | List all projects in the current workspace. |
    | `POST` | `/config/projects` | Create a new project. |
    | `GET` | `/config/projects/active` | Get the currently active project. |
    | `GET` | `/config/projects/{name}` | Get details for a specific project. |
    | `PUT` | `/config/projects/{name}` | Update a project. |
    | `DELETE` | `/config/projects/{name}` | Delete a project. |
    | `GET` | `/config/workspaces/active` | Get the active workspace details. |

    **Configuration File Operations**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `GET` | `/config/sources` | List all configuration source directories. |
    | `GET` | `/config/files/{source}` | List config files within a specific source. |
    | `POST` | `/config/files` | Create a new configuration file. |
    | `GET` | `/config/files/{source}/{path}` | Get a config file's content. |
    | `PUT` | `/config/files/{source}/{path}` | Update a config file's content. |
    | `DELETE` | `/config/files/{source}/{path}` | Delete a configuration file. |
    | `POST` | `/config/refresh` | Force a refresh of the configuration index. |
    | `POST` | `/config/validate` | Validate all loaded configurations. |

=== ":material-tools: MCP Host (`/tools`)"

    Manages runtime operations for MCP servers, tool discovery, and execution.

    **Tool Discovery & Execution**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `GET` | `/tools` | List all available tools from registered servers. |
    | `GET` | `/tools/{tool_name}` | Get detailed information for a specific tool. |
    | `POST` | `/tools/{tool_name}/call` | Execute a specific tool with arguments. |

    **Runtime Server Management**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `GET` | `/tools/servers` | List all currently registered MCP servers. |
    | `GET` | `/tools/servers/{server_name}` | Get detailed runtime status of a server. |
    | `POST` | `/tools/servers/{server_name}/restart` | Restart a registered server. |
    | `GET` | `/tools/servers/{server_name}/tools` | List all tools provided by a specific server. |
    | `POST` | `/tools/servers/{server_name}/test` | Test a server configuration. |
    | `DELETE` | `/tools/servers/{server_name}` | Unregister a server from the host. |

    **Server Registration**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `POST` | `/tools/register/config` | Register a server using a config object. |
    | `POST` | `/tools/register/{server_name}` | Register a server by its configured name. |

=== ":material-robot-happy: Execution (`/execution`)"

    Handles agent and workflow execution, history management, and testing.

    **Agent & Workflow Execution**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `POST` | `/execution/agents/{agent_name}/run` | Execute an agent and wait for the result. |
    | `POST` | `/execution/agents/{agent_name}/stream` | Execute an agent and stream the response. |
    | `POST` | `/execution/workflows/linear/{workflow_name}/run` | Execute a linear workflow. |
    | `POST` | `/execution/workflows/custom/{workflow_name}/run` | Execute a custom workflow. |

    **Testing & Validation**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `POST` | `/execution/agents/{agent_name}/test` | Test an agent's configuration. |
    | `POST` | `/execution/llms/{llm_config_id}/test` | Test an LLM configuration. |
    | `POST` | `/execution/workflows/linear/{workflow_name}/test` | Test a linear workflow. |
    | `POST` | `/execution/workflows/custom/{workflow_name}/test` | Test a custom workflow. |

    **Execution History**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `GET` | `/execution/history` | List all sessions (paginated). Filter with `agent_name` or `workflow_name` query params. |
    | `GET` | `/execution/history/{session_id}` | Get the full history for a specific session. |
    | `DELETE` | `/execution/history/{session_id}` | Delete a session's history. |
    | `POST` | `/execution/history/cleanup` | Clean up old sessions based on retention policy. |

=== ":material-server: System (`/system`)"

    Provides system information, environment management, and monitoring.

    **System Information**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `GET` | `/system/info` | Get detailed system information. |
    | `GET` | `/system/health` | Perform a comprehensive health check. |
    | `GET` | `/system/version` | Get framework version information. |
    | `GET` | `/system/capabilities` | List system capabilities and features. |

    **Environment & Dependencies**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `GET` | `/system/environment` | Get environment variables (sensitive values masked). |
    | `PUT` | `/system/environment` | Update non-sensitive environment variables. |
    | `GET` | `/system/dependencies` | List all installed Python dependencies. |
    | `POST` | `/system/dependencies/check` | Check the health of critical dependencies. |

    **Monitoring**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `GET` | `/system/monitoring/metrics` | Get current system metrics (CPU, memory, etc.). |
    | `GET` | `/system/monitoring/active` | List active Aurite-related processes. |

### CLI Reference

The Aurite Command Line Interface (CLI) is the primary tool for interacting with the Aurite framework. It allows you to initialize projects, manage configurations, run agents and workflows, and start services.

---

#### Commands

The CLI is organized into several main commands.

=== ":material-rocket-launch: `aurite init`"

    Initializes a new Aurite project or workspace.

    | Argument / Option | Type | Description |
    | --- | --- | --- |
    | `[NAME]` | `string` | An optional name for the new project or workspace. |
    | `-p`, `--project` | `flag` | Initialize a new project. |
    | `-w`, `--workspace` | `flag` | Initialize a new workspace. |

    !!! info "Interactive Wizard"
        Running `aurite init` without options starts an interactive wizard to guide you through creating a project or workspace (recommended).

=== ":material-format-list-bulleted: `aurite list`"

    Inspects and lists configurations for different component types. If run without a subcommand, it displays a complete index of all available components.

    | Subcommand | Description |
    | --- | --- |
    | `all` | Lists all available component configurations, grouped by type. |
    | `agents` | Lists all available agent configurations. |
    | `llms` | Lists all available LLM configurations. |
    | `mcp_servers` | Lists all available MCP server configurations. |
    | `linear_workflows` | Lists all available linear workflow configurations. |
    | `custom_workflows` | Lists all available custom workflow configurations. |
    | `workflows` | Lists all workflow configurations (both linear and custom). |
    | `index` | Prints the entire component index as a formatted table. |

    **Examples**

    ```bash
    # List all available agents
    aurite list agents

    # List all workflows (linear and custom)
    aurite list workflows
    ```

=== ":material-eye: `aurite show`"

    Displays the detailed configuration for a specific component or all components of a certain type.

    | Argument / Option | Type | Description |
    | --- | --- | --- |
    | `<NAME_OR_TYPE>` | `string` | The name of a specific component (e.g., `my_agent`) or a component type (e.g., `agents`). |
    | `-f`, `--full` | `flag` | Display the complete, unabridged configuration. |
    | `-s`, `--short` | `flag` | Display a compact, summary view. |

    **Examples**

    ```bash
    # Show the full configuration for the "Weather Agent"
    aurite show "Weather Agent" --full

    # Show a summary of all linear workflow configurations
    aurite show linear_workflows -s
    ```

=== ":material-play: `aurite run`"

    Executes a runnable framework component, such as an agent or a workflow.

    | Argument / Option | Type | Description |
    | --- | --- | --- |
    | `[NAME]` | `string` | The name of the component to run. |
    | `[USER_MESSAGE]` | `string` | The initial user message or input to provide to the component. |
    | `--system-prompt` | `string` | Override the agent's default system prompt for this run. |
    | `-id`, `--session-id` | `string` | Specify a session ID to maintain conversation history. |
    | `-s`, `--short` | `flag` | Display a compact, one-line summary of the run output. |
    | `-d`, `--debug` | `flag` | Display the full, raw event stream for debugging. |

    !!! abstract "Execution Behavior"
        - **Interactive Chat:** Running an agent by `NAME` without a `USER_MESSAGE` launches an interactive chat TUI.
        - **Single-Shot:** Providing a `USER_MESSAGE` runs the component once and streams the output to the terminal.

    **Examples**

    ```bash
    # Run the "Weather Agent" in interactive chat mode
    aurite run "Weather Agent"

    # Run the "Weather Agent" once with a specific question
    aurite run "Weather Agent" "What is the weather in London?"

    # Run the "Weather Planning Workflow"
    aurite run "Weather Planning Workflow" "Plan a trip to Paris next week"

    # Run the "Example Custom Workflow" with JSON input
    aurite run "Example Custom Workflow" '{"city": "Tokyo"}'
    ```

=== ":material-api: `aurite api`"

    Starts the Aurite FastAPI server, which exposes the framework's functionality via a REST API. This is used to power web frontends and programmatic integrations.

    ```bash
    aurite api
    ```

=== ":material-desktop-mac: `aurite studio`"

    Starts the Aurite Studio integrated development environment, which launches both the API server and React frontend concurrently. This provides a unified development experience with automatic dependency management and graceful shutdown handling.

    | Option | Description |
    | --- | --- |
    | `--rebuild-fresh` | Clean all build artifacts and rebuild frontend packages from scratch |

    !!! info "Integrated Development Environment"
        The studio command automatically:

        - Validates Node.js and npm dependencies
        - Installs frontend workspace dependencies if needed
        - Builds frontend packages when artifacts are missing
        - Starts the API server (if not already running)
        - Launches the React development server on port 3000
        - Provides unified logging with `[API]` and `[STUDIO]` prefixes
        - Handles graceful shutdown with Ctrl+C

    **System Requirements**

    - Node.js >= 18.0.0
    - npm >= 8.0.0

    **Examples**

    ```bash
    # Start the integrated development environment
    aurite studio

    # Start with a fresh rebuild of frontend packages
    aurite studio --rebuild-fresh
    ```

    **Fresh Rebuild Process**

    When using `--rebuild-fresh`, the command performs:

    1. **Clean Build Artifacts**: Runs `npm run clean` to remove all build outputs
    2. **Clear npm Cache**: Removes `node_modules/.cache` directory
    3. **Rebuild Packages**: Runs `npm run build` to rebuild all workspace packages
    4. **Start Servers**: Proceeds with normal server startup

    **Ports Used**

    - API Server: Configured port (default 8000)
    - Studio UI: http://localhost:3000

=== ":material-pencil: `aurite edit`"

    Starts the Aurite configuration editor TUI, a powerful terminal-based interface for creating and modifying component configurations.

    | Argument | Type | Description |
    | --- | --- | --- |
    | `[COMPONENT_NAME]` | `string` | (Optional) The name of a component to open directly for editing. |

    !!! info "TUI Interface"
        The editor features a three-pane layout for navigation, component listing, and editing, with interactive widgets and dropdowns for easy configuration.

    **Examples**

    ```bash
    # Open the TUI editor
    aurite edit

    # Open the "Weather Agent" configuration directly in the editor
    aurite edit "Weather Agent"
    ```

---

#### Global Options

These options can be used with the base `aurite` command.

| Option                 | Description                                                           |
| ---------------------- | --------------------------------------------------------------------- |
| `--install-completion` | Installs shell completion for the `aurite` command.                   |
| `--show-completion`    | Displays the shell completion script to be sourced or saved manually. |
| `--help`               | Shows the main help message listing all commands.                     |

### TUI Guide

The Aurite framework includes two powerful Textual User Interfaces (TUIs) to enhance your development experience directly in the terminal: the **Interactive Chat TUI** and the **Configuration Editor TUI**.

---

#### TUI Interfaces

=== ":material-chat-processing: Interactive Chat TUI"

    The Chat TUI provides a rich, interactive environment for conversing with your agents, viewing tool calls in real-time, and managing conversation history.

    !!! info "How to Launch"
        The Chat TUI is launched using the `aurite run` command when you specify an agent's name **without** providing a user message.

        ```bash
        # Launch a new chat session with an agent
        aurite run my_chat_agent

        # Continue a previous conversation
        aurite run my_chat_agent --session-id "some-previous-session-id"
        ```

    **Interface Overview:**

    1.  **Header:** Displays the agent name and the current session ID.
    2.  **Agent Info Panel:** Shows key details about the agent (system prompt, LLM, etc.).
    3.  **Chat History:** The main panel displaying the conversation, including user messages, agent responses, and tool calls.
    4.  **User Input:** The text area at the bottom for composing messages.
    5.  **Footer:** Displays key bindings.

    !!! tip "Key Bindings"
        -   **`Ctrl+Enter`**: Send the message to the agent.
        -   **`Ctrl+C`**: Exit the chat application.

=== ":material-file-edit: Configuration Editor TUI"

    The Configuration Editor TUI (`aurite edit`) is a powerful tool for creating, viewing, and modifying all your component configurations without manually editing JSON or YAML files.

    !!! info "How to Launch"
        You can launch the editor in two ways:

        ```bash
        # General Mode: Browse all configurations
        aurite edit

        # Direct Edit Mode: Open a specific component
        aurite edit my_agent
        ```

    **Interface Overview:**

    The editor uses a three-pane layout for efficient navigation:

    1.  **Navigation Tree (Left):** A tree of all component types (`agent`, `llm`, etc.).
    2.  **Component List (Middle):** A table listing all components of the selected type.
    3.  **Configuration Editor (Right):** An interactive form for editing the selected component's fields.

    !!! tip "How to Use"
        1.  **Navigate:** Use arrow keys to move between panes and select items.
        2.  **Edit:** Use `Tab` to move between fields in the editor. Press `Enter` on dropdowns or buttons to open them.
        3.  **Save:** Navigate to the "Save Configuration" button and press `Enter` to write your changes to the file.
        4.  **Exit:** Press `Ctrl+C` to exit the editor.

---

## Part 5: Practical Code Snippets & Examples

This section provides practical, copy-paste-ready code snippets demonstrating common use cases of the Aurite framework in a programmatic context, such as a Jupyter notebook or a custom Python script.

### Initializing the Framework

The first step is always to initialize the `Aurite` class.

```python
from aurite import Aurite

# Initialize Aurite. When working outside of a project context, it's good practice
# to disable file-based logging to keep the output clean.
aurite = Aurite(disable_logging=True)

# It's important to initialize the kernel to start background services like the MCPHost.
await aurite.initialize()

print("✅ Aurite initialized!")
```

### Programmatic Component Registration

In a notebook or script, it's often easiest to define and register components directly in Python.

#### Registering an LLM

```python
from aurite import LLMConfig

# Define a default LLM config for agents to use.
default_llm = LLMConfig(
    name="default_llm",
    provider="anthropic",
    model="claude-3-sonnet-20240229",
)

# Register the LLM so other components can reference it.
await aurite.register_llm(default_llm)
```

#### Registering an Agent

```python
from aurite import AgentConfig

# Create an agent configuration, linking it to the LLM.
agent_config = AgentConfig(
    name="My First Agent",
    llm_config_id="default_llm",
    system_prompt="You are a helpful assistant."
)

# Register the agent with Aurite.
await aurite.register_agent(agent_config)
```

#### Registering an MCP Server (Tool Server)

```python
from aurite import ClientConfig

# This config points to a local Python script that acts as a tool server.
weather_server_config = ClientConfig(
    name="weather_server",
    server_path="path/to/your/weather_server.py",
    capabilities=["tools"],
)

await aurite.register_mcp_server(weather_server_config)

# You can then create an agent that uses this server:
weather_agent_config = AgentConfig(
    name="My Weather Agent",
    llm_config_id="default_llm",
    mcp_servers=["weather_server"]
)
await aurite.register_agent(weather_agent_config)
```

### Running an Agent

Once an agent is registered, you can execute it with a user message.

```python
user_message = "Hello! Can you tell me a joke?"

# Run the agent with the query
agent_result = await aurite.run_agent(
    agent_name="My First Agent",
    user_message=user_message
)

print("Agent Response:")
print(agent_result.primary_text)
```

### Enforcing Structured Output (JSON Schema)

You can force an agent to return a JSON object that conforms to a specific schema.

```python
# Define a JSON schema for the desired output
text_analysis_schema = {
    "type": "object",
    "properties": {
        "sentiment": {
            "type": "string",
            "enum": ["positive", "negative", "neutral"],
        },
        "key_topics": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["sentiment", "key_topics"]
}

# Create an agent with the schema
analysis_agent = AgentConfig(
    name="Text Analyzer",
    llm_config_id="default_llm",
    system_prompt="Analyze the user's text and return your analysis as a JSON object matching the provided schema.",
    config_validation_schema=text_analysis_schema
)
await aurite.register_agent(analysis_agent)

# Run the agent
analysis_result = await aurite.run_agent(
    agent_name="Text Analyzer",
    user_message="This new feature is amazing and so helpful!"
)

# The result will be a JSON string that can be parsed
import json
parsed_data = json.loads(analysis_result.primary_text)
print(parsed_data)
```

### Creating and Running a Linear Workflow

Chain multiple agents together to perform a multi-step task.

```python
from aurite import WorkflowConfig

# Assume 'Content Analyzer' and 'Recommendation Generator' agents are already registered.

# Create a workflow that chains the two agents
content_workflow = WorkflowConfig(
    name="Content Processing Workflow",
    steps=["Content Analyzer", "Recommendation Generator"],
    description="Analyzes content and generates improvement recommendations"
)

# Register the workflow
await aurite.register_workflow(content_workflow)

# Run the workflow
workflow_result = await aurite.run_workflow(
    workflow_name="Content Processing Workflow",
    initial_input="Some text to be analyzed and get recommendations for."
)

# The .final_message property contains the output from the last step
print("Final Workflow Message:")
print(workflow_result.final_message)
```

##### Workflow Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant Aurite
    participant Engine
    participant Workflow
    participant Agent

    User->>Aurite: run_linear_workflow(name, input)
    Aurite->>Engine: run_linear_workflow(name, input)
    Engine->>Engine: create_workflow_executor()
    Engine->>Workflow: execute(input, session_id)

    loop For each step
        Workflow->>Engine: run_agent(step_name, step_input)
        Engine->>Agent: execute_with_tools()
        Agent-->>Engine: step_result
        Engine-->>Workflow: step_result
    end

    Workflow-->>Engine: workflow_result
    Engine->>Engine: save_workflow_result()
    Engine-->>Aurite: LinearWorkflowExecutionResult
    Aurite-->>User: result
```
