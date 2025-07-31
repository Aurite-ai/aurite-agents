# Design Document: ToolHost and Tool Providers

**Status:** Proposed

## 1. Goal & Motivation

To create a unified, extensible architecture for managing and executing tools within the Aurite framework. This design introduces a `ToolHost` that can handle both existing MCP-based tools and new categories of custom, in-process tools (like in-memory storage or agent-to-agent communication). The primary motivation is to enable seamless integration of diverse tool types while maintaining a clean, decoupled, and scalable architecture.

## 2. Core Concepts

- **`ToolHost`**: A central router class that serves as the single gateway for all tool-related operations. It owns the `MCPHost` and manages a collection of `ToolProvider` instances. It abstracts the complexity of where a tool's logic resides from the rest of the application.
- **`BaseToolProvider`**: A Python abstract base class that defines a strict interface for any class that wishes to provide a set of custom, non-MCP tools. This ensures pluggability and consistency.
- **Concrete Tool Providers**: Specific implementations of `BaseToolProvider` that encapsulate the logic for a particular category of custom tools (e.g., `StorageToolProvider`, `OrchestrationToolProvider`).
- **Instance-Specific Tool Naming**: A robust naming convention, **`{component_name}-{tool_name}`**, used to create a unique, unambiguous namespace for every tool provided by a component instance. This is the key to routing and disambiguation.

## 3. Detailed Architecture

### 3.1 `BaseToolProvider` Interface

A new interface will be defined to ensure any custom tool provider can integrate with the `ToolHost`.

**Location:** `src/aurite/host/base_provider.py`

```python
from abc import ABC, abstractmethod
from typing import Any, List, Dict
import mcp.types as types

class BaseToolProvider(ABC):
    """
    An interface for a class that provides a set of custom, non-MCP tools.
    """
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the unique name of this provider (e.g., 'storage')."""
        pass

    @abstractmethod
    async def register_component(self, config: Any):
        """
        Registers a component configuration (e.g., StorageConfig) and prepares
        its tools, including their schemas and handlers.
        """
        pass

    @abstractmethod
    def get_tool_schemas(self) -> List[types.Tool]:
        """Returns the schemas of all tools currently managed by this provider."""
        pass

    @abstractmethod
    def can_handle(self, tool_name: str) -> bool:
        """Returns True if this provider is responsible for the given tool name."""
        pass

    @abstractmethod
    async def call_tool(self, name: str, args: dict) -> types.CallToolResult:
        """Executes the specified tool by its unique name."""
        pass
```

### 3.2 `ToolHost` - The Central Router

The `ToolHost` becomes a lean router, delegating all complex logic to its registered providers or the `MCPHost`.

**Location:** `src/aurite/host/tool_host.py`

```python
class ToolHost:
    def __init__(self, mcp_host: MCPHost):
        self._mcp_host = mcp_host
        self._providers: Dict[str, BaseToolProvider] = {}

    def register_provider(self, provider: BaseToolProvider):
        """Adds a custom tool provider to the host."""
        self._providers[provider.provider_name()] = provider

    async def register_component(self, component_type: str, config: Any):
        """Finds the right provider and registers a component with it."""
        if component_type in self._providers:
            provider = self._providers[component_type]
            await provider.register_component(config)
        else:
            raise ValueError(f"No tool provider registered for component type '{component_type}'")

    def get_formatted_tools(self, agent_config: AgentConfig) -> List[Dict[str, Any]]:
        """Gathers tool schemas from all providers and MCPHost into a single list."""
        all_tools = list(self._mcp_host.tools.values())
        for provider in self._providers.values():
            all_tools.extend(provider.get_tool_schemas())

        formatted_tools = [tool.model_dump() for tool in all_tools]
        # Final filtering is applied to the unified list
        return self._filtering_manager.filter_component_list(formatted_tools, agent_config)

    async def call_tool(self, name: str, args: dict) -> types.CallToolResult:
        """Routes a tool call to the correct provider or defaults to MCPHost."""
        for provider in self._providers.values():
            if provider.can_handle(name):
                return await provider.call_tool(name, args)

        return await self._mcp_host.call_tool(name, args)
```

### 3.3 Concrete Provider Example: `StorageToolProvider`

This class implements the `BaseToolProvider` interface and handles all logic for storage-related tools.

**Location:** `src/aurite/host/storage_provider.py`

```python
class StorageToolProvider(BaseToolProvider):
    def __init__(self):
        self._tools: Dict[str, types.Tool] = {}
        self._handlers: Dict[str, Callable] = {}
        self._datastores: Dict[str, Any] = {} # e.g., {"my_mem_db": {}}

    def provider_name(self) -> str:
        return "storage"

    async def register_component(self, config: StorageConfig):
        # 1. Check if it's a native tool type (e.g., memory)
        if config.storage_type == "memory":
            # 2. Create the backend datastore for this instance
            self._datastores[config.name] = {}

            # 3. Generate unique tool name and description
            tool_name = f"{config.name}-write"
            description = f"Writes a value to a key in the '{config.name}' in-memory store."

            # 4. Create schema and handler, linking them via the unique name
            schema = types.Tool(name=tool_name, description=description, ...)
            handler = self._create_write_handler(config.name) # Returns a function bound to the correct datastore

            self._tools[tool_name] = schema
            self._handlers[tool_name] = handler

        elif config.storage_type == "postgresql":
            # This type would be handled by an MCP Server. The registration logic
            # for its corresponding ClientConfig would live elsewhere, likely
            # orchestrated by the ExecutionFacade which would call MCPHost directly.
            # This provider would do nothing for this storage_type.
            pass

    # ... implementation of get_tool_schemas, can_handle, call_tool ...
```

## 4. End-to-End Workflow

1.  **Initialization**: The `ExecutionFacade` is initialized with a `ToolHost`. The `ToolHost` is initialized with an `MCPHost` and registers all available `ToolProvider` implementations (e.g., `StorageToolProvider`).
2.  **Component Registration**: When an agent run begins, the `ExecutionFacade` iterates through its required components.
    - If it's an `mcp_server`, it calls `self._mcp_host.register_client(...)`.
    - If it's a `storage` component, it calls `self._tool_host.register_component("storage", storage_config)`.
3.  **Tool Discovery**: The `Agent` calls `self._tool_host.get_formatted_tools()`. The `ToolHost` gathers schemas from `MCPHost` and all registered providers, creating a single, unified list of tools with unique, instance-specific names.
4.  **LLM Call**: The LLM receives the clear, unambiguous list of tools (e.g., `my_mem_db-read`, `postgresql_server-query`) and makes a function call to a specific tool.
5.  **Tool Execution**: The `AgentTurnProcessor` calls `self._tool_host.call_tool(...)` with the unique tool name. The `ToolHost` finds the provider that `can_handle()` the tool name and delegates the call. If no provider claims it, it defaults to the `MCPHost`.

This architecture provides a robust, decoupled, and highly extensible system for managing all current and future tool capabilities of the framework.
