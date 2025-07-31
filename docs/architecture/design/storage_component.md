# Design Document: Storage Component

**Status:** Proposed

## 1. Goal & Motivation

To create a new `storage` sub-component that provides a standardized, extensible way to integrate various data storage backends (e.g., PostgreSQL, local file system, in-memory) into the Aurite framework. This will allow agents to persist, retrieve, and manage data seamlessly through the existing MCP tool mechanism, enhancing their ability to perform stateful operations.

## 2. Core Concepts

- **`StorageConfig`**: A new component configuration model that defines a specific storage instance. It will be a discriminated union to support multiple backend types with type safety.
- **`storage_type`**: A key field within each `StorageConfig` variant that determines the backend technology (e.g., `postgresql`, `local`, `memory`).
- **`StorageToolProvider`**: A dedicated class that implements the `BaseToolProvider` interface. It is responsible for managing all `storage` components, whether they are native in-process tools (like `memory`) or MCP-based tools (like `postgresql`).
- **Instance-Specific Naming**: Tools provided by a storage component will follow the `{component_name}-{tool_name}` convention (e.g., `my_mem_db-read`) to ensure they are unique and can be routed correctly by the `ToolHost`.

## 3. `StorageConfig` Model Design

We will use a **discriminated union** for the `StorageConfig` models in `src/aurite/config/config_models.py`. This provides the best combination of type safety, validation, and extensibility.

### 3.1 Pydantic Models

```python
# In src/aurite/config/config_models.py

from typing import Union, Literal, List, Optional
from pydantic import Field

# --- Base and Type-Specific Models ---

class BaseStorageConfig(BaseComponentConfig):
    """Base model for all storage configurations."""
    type: Literal["storage"] = "storage"

class LocalStorageConfig(BaseStorageConfig):
    """Configuration for local file system storage."""
    storage_type: Literal["local"] = "local"
    base_path: str = Field(description="The root directory for local storage.")

class PostgresStorageConfig(BaseStorageConfig):
    """Configuration for PostgreSQL storage."""
    storage_type: Literal["postgresql"] = "postgresql"
    host: str
    port: int = 5432
    username: str
    password: str # Note: Secure handling via env vars is recommended
    database: str

class MemoryStorageConfig(BaseStorageConfig):
    """Configuration for simple in-memory storage (primarily for testing and simple use cases)."""
    storage_type: Literal["memory"] = "memory"

# --- The Discriminated Union ---
# This allows Pydantic to automatically select the correct model based on `storage_type`.
StorageConfig = Union[LocalStorageConfig, PostgresStorageConfig, MemoryStorageConfig]

# --- Add to ProjectConfig ---
class ProjectConfig(BaseComponentConfig):
    # ... existing fields
    storage: List[StorageConfig] = Field(
        default_factory=list,
        description="Storage configurations available within this project.",
    )
```

## 4. `AgentConfig` Modification

The `AgentConfig` will be updated to include a list of storage component names it is authorized to use.

```python
# In src/aurite/config/config_models.py

class AgentConfig(BaseComponentConfig):
    # ... existing fields
    storage: Optional[List[str]] = Field(
        default_factory=list,
        description="List of storage component names this agent can use.",
    )
```

## 5. Implementation via `StorageToolProvider`

The `storage` component will be the first implementation of the new `ToolHost` and `ToolProvider` architecture. This design supersedes earlier concepts based on direct `MCPHost` interaction and connection management.

### 5.1 Role of the `StorageToolProvider`

A new `StorageToolProvider` class will be created that implements the `BaseToolProvider` interface. Its responsibilities include:

- Registering itself with the `ToolHost` under the provider name `"storage"`.
- Handling the registration of any `StorageConfig` component.
- Dynamically generating unique, instance-specific tool schemas and handlers based on the component's `name` (e.g., creating `my_mem_db-read` and `my_mem_db-write` tools for a `StorageConfig` named `my_mem_db`).
- Managing the internal state for each registered storage instance (e.g., maintaining a separate dictionary in memory for each `memory` storage component).
- Executing tool calls routed to it by the `ToolHost`.

### 5.2 Execution Flow

The end-to-end flow for a native in-process storage tool (like `memory`) will be:

1.  **Initialization**: The `ExecutionFacade` is initialized with a `ToolHost`, which has a registered `StorageToolProvider`.
2.  **Component Registration**: During an agent run, the `ExecutionFacade` finds a `StorageConfig` (e.g., for `my_mem_db`) and calls `tool_host.register_component("storage", storage_config)`.
3.  **Provider Handling**: The `ToolHost` routes this registration to the `StorageToolProvider`. The provider creates the tool schemas (`my_mem_db-read`, etc.) and their corresponding handlers, which are bound to the specific data store for `my_mem_db`.
4.  **Tool Discovery**: The `Agent` calls `tool_host.get_formatted_tools()`. The `ToolHost` returns a unified list including the newly created `my_mem_db-read` tool, which is then passed to the LLM.
5.  **Tool Execution**: The LLM calls the `my_mem_db-read` function. The `ToolHost` receives the call, sees that the `StorageToolProvider` `can_handle()` this tool name, and delegates the execution to it. The provider then runs the specific handler associated with the `my_mem_db` data store.

This architecture ensures that storage components are treated as first-class tool providers within the framework, offering a clean, scalable, and powerful way to manage state.
