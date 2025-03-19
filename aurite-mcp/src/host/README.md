# MCP Host System

The MCP Host System is a modular, layered architecture for managing agent-based workflows, tools, and resources. It features a robust configuration management system that enables consistent handling of settings across all components.

## Architecture Overview

The system is organized into four primary layers:

1. **Foundation Layer**
   - Security Manager: Handles encryption and permissions
   - Root Manager: Manages filesystem roots and access control

2. **Communication Layer**
   - Transport Manager: Handles client-server communication
   - Message Router: Routes messages between components

3. **Resource Management Layer**
   - Storage Manager: Database connection management
   - Tool Manager: Tool discovery and execution
   - Prompt Manager: LLM prompt management
   - Resource Manager: Resource access and caching

4. **Agent Layer**
   - Workflow Manager: Workflow registration and execution
   - Agent Manager: Agent configuration and LLM interactions

## Configuration Management

The system uses a unified configuration management approach based on dataclass models and JSON files:

### Base Configuration Classes

```python
@dataclass
class BaseConfig:
    metadata: Dict[str, Any]

@dataclass
class ConnectionConfig(BaseConfig):
    connections: Dict[str, Dict[str, Any]]

@dataclass
class AgentConfig(BaseConfig):
    agents: List[ClientConfig]

@dataclass
class WorkflowConfig(BaseConfig):
    workflows: List[Dict[str, Any]]
```

### Configuration Directory Structure

```
config/
├── host.json              # Main host configuration
├── agents/
│   └── aurite_agents.json # Agent configurations
├── storage/
│   └── connections.json   # Database connections
├── workflows/
│   └── aurite_workflows.json # Workflow configurations
├── prompts/               # Prompt templates
└── resources/            # Shared resources
```

### Configurable Manager Pattern

All managers that require configuration inherit from the `ConfigurableManager` base class:

```python
class ConfigurableManager[T](Generic[T], ABC):
    def __init__(self, config_type: str):
        self._config_type = config_type
        self._config: Optional[T] = None

    @abstractmethod
    def _config_model_class(self) -> Type[T]:
        pass

    @abstractmethod
    def _validate_config_structure(self, config: Dict[str, Any]) -> bool:
        pass
```

## Key Features

1. **Standardized Configuration**
   - Type-safe configuration models
   - Consistent JSON serialization/deserialization
   - Centralized validation logic

2. **Modular Design**
   - Each manager handles specific functionality
   - Clear separation of concerns
   - Easy to extend and maintain

3. **Secure Operations**
   - Encrypted sensitive data
   - Permission-based access control
   - Secure database connection management

4. **Workflow Management**
   - Registration and execution of workflows
   - Configuration-driven workflow setup
   - Integration with LLM agents

5. **Resource Management**
   - Database connection pooling
   - Tool discovery and execution
   - Prompt template management

## Usage Examples

### Initializing the Host

```python
from host import MCPHost
from host.config import HostConfig

# Create and initialize host
host = MCPHost(config=HostConfig(clients=[]))
await host.initialize()
```

### Registering a Workflow

```python
# Register a workflow with configuration
workflow_name = await host.register_workflow(
    PlanningWorkflow,
    name="planning_workflow",
    workflow_config=planning_config
)
```

### Managing Database Connections

```python
# Create a database connection
conn_id, metadata = await host.storage.create_db_connection({
    "type": "postgresql",
    "host": "localhost",
    "database": "mydb",
    "username": "user",
    "password": "pass"
})
```

### Executing Prompts with Tools

```python
result = await host.execute_prompt_with_tools(
    prompt_name="create_plan",
    prompt_arguments={},
    client_id="planning",
    user_message="Create a new plan",
    tool_names=["save_plan"]
)
```

## Best Practices

1. **Configuration Management**
   - Keep sensitive data in environment variables
   - Use type hints for configuration models
   - Validate configurations at startup

2. **Error Handling**
   - Implement proper error handling in managers
   - Log errors with appropriate context
   - Provide meaningful error messages

3. **Resource Cleanup**
   - Always call shutdown() when done
   - Clean up database connections
   - Release system resources

4. **Security**
   - Use encryption for sensitive data
   - Implement proper access control
   - Validate client permissions

## Contributing

When adding new functionality:

1. Create appropriate configuration models
2. Inherit from ConfigurableManager
3. Implement required abstract methods
4. Add configuration validation
5. Update documentation

## License

This project is licensed under the MIT License - see the LICENSE file for details.