# Execution Facade Architecture

This document explains the design and implementation of the Execution Facade, which provides a unified interface for executing agents and workflows in the Aurite Framework.

## Overview

The ExecutionFacade serves as the orchestration layer between the API endpoints and the core execution components (Agents, Workflows). It manages the complexity of component initialization, session management, and resource allocation while providing a simple interface for execution requests.

## Architecture Components

```
┌─────────────────┐
│  API Routes     │
│  /execution/*   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ ExecutionFacade │────▶│ ConfigManager    │     │ MCPHost          │
│                 │     │(Component Lookup)│     │ (Tool Registry)  │
└────────┬────────┘     └──────────────────┘     └──────────────────┘
         │
         ├─────────────────┬─────────────────┬─────────────────┐
         ▼                 ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────┐ ┌──────────────┐ ┌──────────────┐
│ Agent           │ │ Simple      │ │ Custom       │ │ Storage      │
│ Execution       │ │ Workflow    │ │ Workflow     │ │ Management   │
└─────────────────┘ └─────────────┘ └──────────────┘ └──────────────┘
```

## Core Responsibilities

### 1. Component Resolution
- Retrieves component configurations from ConfigManager
- Validates component existence and dependencies
- Handles missing configuration gracefully with fallbacks

### 2. Resource Management
- Manages LLM client instances
- Coordinates with MCPHost for tool availability
- Implements JIT (Just-In-Time) server registration

### 3. Session Management
- Loads conversation history for agents
- Persists conversation state after execution
- Provides abstraction over storage backends

### 4. Execution Orchestration
- Initializes components with proper configuration
- Manages execution lifecycle
- Handles both synchronous and streaming execution modes

## JIT MCP Server Registration

### Design Rationale

MCP servers provide tools that agents can use during execution. Rather than loading all servers at startup (which could be resource-intensive and slow), the ExecutionFacade implements Just-In-Time registration.

### Implementation Flow

```
┌─────────────────┐
│ Agent Execution │
│ Request         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ Load Agent      │────▶│ Check required   │
│ Configuration   │     │ mcp_servers list │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ For each server │────▶│ Is server        │
│ in mcp_servers  │     │ registered?      │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         │                       ├─ YES → Skip
         │                       │
         │                       └─ NO → Register
         ▼                                  │
┌─────────────────┐                         ▼
│ Execute Agent   │               ┌──────────────────┐
│ with all tools  │               │ Load server      │
│ available       │               │ config & register│
└─────────────────┘               └──────────────────┘
```

### Key Design Decisions

1. **Persistent Registration**: Servers remain registered after agent execution completes. This optimizes subsequent executions that need the same tools.

2. **Lazy Loading**: Servers are only loaded when actually needed by an agent, reducing startup time and memory usage.

3. **Graceful Failure**: If a required server cannot be loaded, the error is caught early before agent execution begins.

### Code Reference

```python
async def _prepare_agent_for_run(self, agent_name: str, ...):
    # ... load agent config ...

    # JIT Registration of MCP Servers
    if agent_config_for_run.mcp_servers:
        for server_name in agent_config_for_run.mcp_servers:
            if server_name not in self._host.registered_server_names:
                server_config_dict = self._config_manager.get_config("mcp_server", server_name)
                if not server_config_dict:
                    raise ConfigurationError(f"MCP Server '{server_name}' required by agent '{agent_name}' not found.")
                server_config = ClientConfig(**server_config_dict)
                await self._host.register_client(server_config)
                dynamically_registered_servers.append(server_name)
```

## Session Management Architecture

### Overview

Session management enables agents to maintain conversation context across multiple interactions. The system supports two storage backends with a unified interface.

### Storage Backend Design

```
┌─────────────────┐
│ ExecutionFacade │
└────────┬────────┘
         │
         ├─────────────────┬─────────────────┐
         ▼                 ▼                 │
┌─────────────────┐ ┌─────────────┐          │
│ StorageManager  │ │ CacheManager│          │
│ (Database)      │ │ (File-Based)│          │
└────────┬────────┘ └──────┬──────┘          │
         │                  │                │
         ▼                  ▼                │
┌─────────────────┐ ┌─────────────┐          │
│ PostgreSQL/     │ │ JSON Files  │          │
│ SQLite          │ │ + Memory    │          │
└─────────────────┘ └─────────────┘          │
```

### Storage Manager (Database Backend)

**Purpose**: Provides persistent storage for production environments.

**Features**:
- Full ACID compliance
- Efficient querying by agent_name and session_id
- Timestamp tracking for audit trails
- Scalable for large conversation histories

**Schema**:
```sql
AgentHistoryDB:
  - id: Integer (Primary Key)
  - agent_name: String (Indexed)
  - session_id: String (Indexed)
  - role: String
  - content_json: JSON
  - timestamp: DateTime
  - created_at: DateTime
```

### Cache Manager (File-Based Backend)

**Purpose**: Lightweight persistent storage for development and testing.

**Current Implementation**:
```python
class CacheManager:
    def __init__(self, cache_dir: Optional[Path] = None):
        self._cache_dir = cache_dir or Path(".aurite_cache")
        self._cache_dir.mkdir(exist_ok=True)
        self._history_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._load_cache()
```

**Features**:
- File-based persistence with JSON storage
- In-memory caching for performance
- Session metadata tracking (timestamps, agent name, message count)
- Automatic cache directory creation
- Safe session ID sanitization

**File Structure**:
```
.aurite_cache/
├── session-id-1.json
├── session-id-2.json
└── ...
```

**Session File Format**:
```json
{
  "session_id": "test-session-123",
  "conversation": [...],
  "created_at": "2025-01-09T19:08:48.959750",
  "last_updated": "2025-01-09T19:08:52.329089",
  "agent_name": "Weather Agent",
  "message_count": 4
}
```

### Session Flow

```
┌─────────────────┐
│ API Request     │
│ with session_id │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ Check if agent  │────▶│ include_history  │
│ configuration   │     │ = true?          │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         │                       ├─ NO → Skip history
         │                       │
         │                       └─ YES → Load history
         ▼                              │
┌─────────────────┐                     ▼
│ Add current     │     ┌──────────────────┐
│ user message    │     │ Load from        │
│ to history      │     │ storage backend  │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐
│ Execute Agent   │
│ with history    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Save complete   │
│ conversation    │
└─────────────────┘
```

### Key Design Decisions

1. **Immediate Cache Update**: The current user message is added to the cache immediately, ensuring it's available during agent execution.

2. **Full History Replacement**: On save, the entire conversation history replaces the previous version. This ensures consistency but may have performance implications for very long conversations.

3. **Backend Abstraction**: The ExecutionFacade doesn't know which storage backend is in use, allowing for easy swapping or enhancement.

## Streaming Architecture

### Event Translation Layer

The ExecutionFacade acts as a translator between the internal agent streaming events and the standardized API events.

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Agent Internal  │────▶│ ExecutionFacade  │────▶│ API SSE Events   │
│ Events          │     │ Translation      │     │                  │
└─────────────────┘     └──────────────────┘     └──────────────────┘

Internal Events:              Translated to:
- Raw LiteLLM chunks    →     - llm_response_start
- tool_complete         →     - llm_response
- tool_result           →     - llm_response_stop
- message_complete      →     - tool_call
- Errors                →     - tool_output
                              - error
```

### Stream State Management

The streaming implementation maintains state across turns:
- Tracks whether LLM has started responding
- Collects tool results for history updates
- Manages conversation history updates in real-time

## Error Handling Strategy

### Configuration Errors
- Caught early in the preparation phase
- Clear error messages indicating missing components
- Prevents partial execution with invalid configuration

### Execution Errors
- Wrapped with context about which component failed
- Original error preserved in the chain
- Graceful degradation where possible

### Streaming Errors
- Converted to error events in the stream
- Stream terminated cleanly
- Client can handle reconnection if needed

## Future Enhancements

### Enhanced Session Management

1. **Session Query APIs**
   - List sessions by agent
   - Search within conversations
   - Session analytics

### Performance Optimizations

1. **Connection Pooling**: Reuse LLM client connections
2. **Lazy History Loading**: Load only recent messages initially
3. **Streaming History Updates**: Update history incrementally during streaming

### Monitoring and Observability

1. **Execution Metrics**
   - Response times
   - Token usage
   - Error rates

2. **Session Analytics**
   - Active sessions
   - Average conversation length
   - Tool usage patterns

## Implementation References

- **Main Class**: `src/aurite/execution/facade.py`
- **Storage**: `src/aurite/storage/db_manager.py`, `src/aurite/storage/cache_manager.py`
- **Routes**: `src/aurite/bin/api/routes/facade_routes.py`
