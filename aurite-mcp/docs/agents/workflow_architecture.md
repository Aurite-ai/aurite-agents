# Aurite Workflow Architecture

This document provides an architectural overview of the Aurite agent workflow framework, detailing how different components interact to create a flexible, modular system for building AI agents with varying levels of autonomy.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Workflow Execution Model](#workflow-execution-model)
4. [Tool Integration](#tool-integration)
5. [Error Handling and Resilience](#error-handling-and-resilience)
6. [Extension Points](#extension-points)
7. [Implementation Patterns](#implementation-patterns)
8. [Integration with Host System](#integration-with-host-system)
9. [DRY Utility Components](#dry-utility-components)

## Architecture Overview

The Aurite workflow architecture is part of a broader layered design that integrates with the MCP Host system. The architecture is built around the following key principles:

1. **Separation of concerns**: Each component has a well-defined responsibility
2. **Composition over inheritance**: Components are designed to be composable
3. **Typed interfaces**: Pydantic models provide type safety
4. **Extensibility**: Hook points allow customization without subclassing
5. **Tool abstraction**: Tools are managed separately from workflow logic

The overall MCP Host system architecture consists of four logical layers, with the workflow framework residing in Layer 4 (Agent Framework):

```
┌───────────────────────────────────────────────────────────┐
│               Layer 4: Agent Framework                    │
│                                                           │
│  ┌─────────────────┐  ┌────────────────┐  ┌────────────┐  │
│  │  BaseWorkflow   │  │  BaseAgent     │  │  Hybrid    │  │
│  │  (Sequential)   │  │  (Dynamic)     │  │  Agents    │  │
│  └─────────────────┘  └────────────────┘  └────────────┘  │
└───────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│           Layer 3: Resource Management                  │
│                                                         │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────┐  │
│  │  ToolManager    │  │  PromptManager │  │ Resource │  │
│  └─────────────────┘  └────────────────┘  │ Manager  │  │
│                                           └──────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│          Layer 2: Communication and Routing             │
│                                                         │
│  ┌─────────────────┐  ┌────────────────┐                │
│  │  MessageRouter  │  │ TransportMgr   │                │
│  └─────────────────┘  └────────────────┘                │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│            Layer 1: Security and Foundation             │
│                                                         │
│  ┌─────────────────┐  ┌────────────────┐                │
│  │  RootManager    │  │ SecurityMgr    │                │
│  └─────────────────┘  └────────────────┘                │
└─────────────────────────────────────────────────────────┘
```

The workflow implementation itself follows a compositional design pattern:

```
┌─────────────────────────────────────────────────────────┐
│                    BaseWorkflow                         │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │               Execution Pipeline                │    │
│  │                                                 │    │
│  │  ┌─────────┐  ┌─────────┐  ┌───────────────┐    │    │
│  │  │ Step 1  │→ │ Step 2  │→ │ CompositeStep │    │    │
│  │  └─────────┘  └─────────┘  │ ┌─────────┐   │    │    │
│  │                            │ │ Step 3A │   │    │    │
│  │                            │ └─────────┘   │    │    │
│  │                            │ ┌─────────┐   │    │    │
│  │                            │ │ Step 3B │   │    │    │
│  │                            │ └─────────┘   │    │    │
│  │                            └───────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
│                             │                           │
│                             ▼                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │               AgentContext                      │    │
│  │  ┌───────────────┐  ┌───────────────────────┐   │    │
│  │  │   Data Model  │  │    Step Results       │   │    │
│  │  └───────────────┘  └───────────────────────┘   │    │
│  │  ┌───────────────┐  ┌───────────────────────┐   │    │
│  │  │   Metadata    │  │    Tool Manager Ref   │   │    │
│  │  └───────────────┘  └───────────────────────┘   │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### AgentContext and Data Models (`base_models.py`)

The `AgentContext` class serves as the central data container for workflows and agents. It provides:

1. **Type-safe data storage**: Using Pydantic models for structured data
2. **State tracking**: For workflow execution
3. **Tool access**: Via the `tool_manager` reference
4. **Validation**: Through the `validate()` method

Key implementations:

```python
class AgentData(BaseModel):
    """Base model for agent context data"""
    model_config = ConfigDict(extra="allow")  # Allow extra fields

class AgentContext(Generic[T]):
    """Context for agent execution, designed to be reusable across all agent types"""
    def __init__(self, data: Optional[T] = None, metadata: Optional[Dict[str, Any]] = None,
                 required_fields: Optional[Set[str]] = None):
        # Data container - either a custom model or the base AgentData
        self.data = data or AgentData()
        # Metadata for execution tracking
        self.metadata: Dict[str, Any] = metadata or {}
        # Required fields for validation
        self.required_fields: Set[str] = required_fields or set()
        # Workflow tracking
        self.step_results: Dict[str, StepResult] = {}
        # Performance tracking
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None
        # Reference to the tool manager - set by the workflow
        self.tool_manager = None
```

### Workflow Steps (`base_workflow.py`)

The `WorkflowStep` class is the building block for workflows, defining:

1. **Input/output contracts**: Through required_inputs and provided_outputs
2. **Tool requirements**: Via required_tools
3. **Execution logic**: In the execute() method
4. **Condition logic**: Optional conditions for execution
5. **Composition support**: Through child steps

Key implementation:

```python
@dataclass
class WorkflowStep(ABC):
    """Abstract base class for workflow steps"""
    name: str
    description: str = ""
    required_inputs: Set[str] = field(default_factory=set)
    provided_outputs: Set[str] = field(default_factory=set)
    required_tools: Set[str] = field(default_factory=set)
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds
    timeout: float = 60.0  # seconds
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    _child_steps: List["WorkflowStep"] = field(default_factory=list)

    @abstractmethod
    async def execute(self, context: AgentContext, host: MCPHost) -> Dict[str, Any]:
        """Execute the step with the given context"""
        pass
```

The `CompositeStep` extends this to provide step composition:

```python
class CompositeStep(WorkflowStep):
    """A workflow step that executes a sequence of child steps"""
    async def execute(self, context: AgentContext, host: MCPHost) -> Dict[str, Any]:
        """Execute all child steps in sequence"""
        all_outputs = {}
        for step in self._child_steps:
            # Check condition
            if not await step.should_execute(context_data):
                continue
            # Execute step
            outputs = await step.execute(context, host)
            # Add outputs to accumulated outputs
            all_outputs.update(outputs)
        return all_outputs
```

### BaseWorkflow (`base_workflow.py`)

The `BaseWorkflow` class orchestrates the execution of steps, providing:

1. **Step sequencing**: Executing steps in order
2. **Error handling**: Through error handlers and retry logic
3. **Lifecycle management**: Initialization and shutdown
4. **Middleware hooks**: For extending behavior

Key implementation:

```python
class BaseWorkflow(ABC):
    """Base class for implementing strictly sequential workflow agents"""
    def __init__(self, host: MCPHost, name: str = "unnamed_workflow"):
        self.host = host
        self.name = name
        self.steps: List[WorkflowStep] = []
        self.error_handlers: Dict[str, Callable] = {}
        self.global_error_handler: Optional[Callable] = None
        self.tool_manager = host._tool_manager
        # Middleware hooks
        self.before_workflow_hooks: List[Callable] = []
        self.after_workflow_hooks: List[Callable] = []
        self.before_step_hooks: List[Callable] = []
        self.after_step_hooks: List[Callable] = []

    async def execute(self, input_data: Dict[str, Any], metadata: Dict[str, Any] = None) -> AgentContext:
        """Execute the workflow with the given input data"""
        agent_context = AgentContext(data=AgentData(**input_data), metadata=metadata or {})
        agent_context.tool_manager = self.tool_manager

        # Run before workflow hooks
        for hook in self.before_workflow_hooks:
            await hook(agent_context)

        # Execute each step in sequence
        for step in self.steps:
            # Check if step should be executed
            if not await step.should_execute(context_data):
                agent_context.add_step_result(step.name, StepResult(status=StepStatus.SKIPPED))
                continue

            # Run before step hooks
            for hook in self.before_step_hooks:
                await hook(step, agent_context)

            # Execute the step
            result = await self.execute_step(step, context_data)
            agent_context.add_step_result(step.name, result)

            # Run after step hooks
            for hook in self.after_step_hooks:
                await hook(step, agent_context, result)

            # If step failed, stop execution
            if result.status == StepStatus.FAILED:
                agent_context.complete()
                return agent_context

            # Update context with step outputs
            if result.status == StepStatus.COMPLETED:
                for key, value in result.outputs.items():
                    agent_context.set(key, value)

        # Complete the workflow
        agent_context.complete()

        # Run after workflow hooks
        for hook in self.after_workflow_hooks:
            await hook(agent_context)

        return agent_context
```

### Tool Management (`tools.py`)

The `ToolManager` class handles tool registration, discovery, and execution:

```python
class ToolManager:
    """Manages tool registration, discovery, and execution"""

    def __init__(self, root_manager: RootManager, message_router: MessageRouter):
        self._root_manager = root_manager
        self._message_router = message_router
        self._tools: Dict[str, types.Tool] = {}
        self._tool_metadata: Dict[str, Dict[str, Any]] = {}
        self._clients: Dict[str, Any] = {}
        self._active_requests: Dict[str, asyncio.Task] = {}

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Execute a tool with the given arguments"""
        # Validate tool exists
        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Get server for this tool
        server_id = await self._message_router.select_server_for_tool(tool_name)
        if not server_id:
            raise ValueError(f"No server found for tool: {tool_name}")

        # Get client session
        client = self._clients.get(server_id)
        if not client:
            raise ValueError(f"Client not found for server: {server_id}")

        # Validate access through root manager
        await self._root_manager.validate_access(client_id=server_id, tool_name=tool_name)

        # Execute the tool
        try:
            result = await client.call_tool(tool_name, arguments)
            # Process and return result
            # ...
        except Exception as e:
            logger.error(f"Tool execution failed - {tool_name}: {e}")
            raise
```

### Utility Functions (`base_utils.py`)

The `base_utils.py` module provides reusable utilities:

1. **Validation**: For inputs/outputs through `validate_required_fields()`
2. **Result summarization**: Via `summarize_execution_results()`
3. **Retry logic**: Through the `with_retries` decorator

Key implementation of the retry decorator:

```python
def with_retries(max_retries: int = 3, retry_delay: float = 1.0, exponential_backoff: bool = True):
    """Decorator for adding retry behavior to async functions"""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            attempts = 0
            last_exception = None

            while attempts <= max_retries:
                attempts += 1
                try:
                    # Execute function with timeout if provided
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    last_exception = e
                    # Check if should retry
                    if attempts > max_retries:
                        break
                    # Wait with backoff
                    current_delay = retry_delay * (2 ** (attempts - 1)) if exponential_backoff else retry_delay
                    await asyncio.sleep(current_delay)

            # All attempts failed
            if last_exception:
                raise last_exception
        return wrapper
    return decorator
```

### Host System (`host.py`)

The `MCPHost` class serves as the central orchestration component, integrating all four layers:

```python
class MCPHost:
    """The Model Context Protocol host"""
    def __init__(self, config: HostConfig, encryption_key: Optional[str] = None):
        # Layer 1: Foundation layer
        self._security_manager = SecurityManager(encryption_key=encryption_key)
        self._root_manager = RootManager()

        # Layer 2: Communication layer
        self._transport_manager = TransportManager()
        self._message_router = MessageRouter()

        # Layer 3: Resource management layer
        self._prompt_manager = PromptManager()
        self._resource_manager = ResourceManager()
        self._storage_manager = StorageManager()
        self._tool_manager = ToolManager(
            root_manager=self._root_manager, message_router=self._message_router
        )

        # State management
        self._config = config
        self._clients: Dict[str, ClientSession] = {}

    async def initialize(self):
        """Initialize the host and all configured clients"""
        # Initialize subsystems in layer order

        # Layer 1: Foundation layer
        await self._security_manager.initialize()
        await self._root_manager.initialize()

        # Layer 2: Communication layer
        await self._transport_manager.initialize()
        await self._message_router.initialize()

        # Layer 3: Resource management layer
        await self._prompt_manager.initialize()
        await self._resource_manager.initialize()
        await self._storage_manager.initialize()
        await self._tool_manager.initialize()

        # Initialize each configured client
        for client_config in self._config.clients:
            await self._initialize_client(client_config)
```

## Workflow Execution Model

The workflow execution follows a sequential model with these phases:

1. **Initialization**: Setting up the workflow and validating tools
2. **Execution preparation**: Creating the context and running pre-hooks
3. **Step execution**: For each step:
   - Check condition
   - Run pre-step hooks
   - Execute with retries
   - Run post-step hooks
   - Update context with outputs
4. **Finalization**: Completing the context and running post-hooks

The execution is controlled through the `BaseWorkflow.execute()` method, which orchestrates the entire process and returns the final context with execution results.

## Tool Integration

Tools are integrated into workflows through the `ToolManager` class. The key features of tool integration are:

1. **Dependency injection**: The tool_manager is injected into the context
2. **Access control**: Tools are validated against the root manager
3. **Dynamic routing**: Tools are routed to appropriate servers
4. **Capability matching**: Tools can be discovered by capability

Workflows interact with tools through the context's tool_manager:

```python
# In a workflow step:
async def execute(self, context: AgentContext, host: MCPHost) -> Dict[str, Any]:
    # Execute a tool
    result = await context.tool_manager.execute_tool(
        "tool_name",
        {"param1": "value1", "param2": "value2"}
    )
    # Process result
    return {"output_key": processed_result}
```

## Error Handling and Resilience

The framework provides several mechanisms for error handling and resilience:

1. **Step retries**: Steps are executed with retry logic
2. **Error handlers**: Per-step and global error handlers
3. **Step results**: Detailed execution results in the context
4. **Validation**: Input and output validation for each step
5. **Conditional execution**: Steps can be conditionally skipped

Steps are executed with the `with_retries` decorator:

```python
# In BaseWorkflow.execute_step:
decorated_execute = with_retries(
    max_retries=step.max_retries,
    retry_delay=step.retry_delay,
    exponential_backoff=True,
    timeout=step.timeout,
    on_retry=lambda e, a: asyncio.create_task(handle_error(e, a)),
)(execute_with_validation)

# Execute with retries
outputs = await decorated_execute()
```

## Extension Points

The framework provides several extension points:

1. **Hooks**: Before/after hooks for workflows and steps
2. **Error handlers**: Custom error handlers for specific steps
3. **Custom steps**: New step implementations
4. **Composition**: Steps can be composed into composite steps
5. **Custom contexts**: Context data can be extended with Pydantic models

Hooks allow extending behavior without subclassing:

```python
# Adding hooks to a workflow
workflow.add_before_workflow_hook(async_hook_function)
workflow.add_after_step_hook(async_hook_function)

# Hook implementation
async def my_before_workflow_hook(context: AgentContext):
    # Perform pre-workflow tasks
    context.metadata["workflow_start_time"] = time.time()
```

## Implementation Patterns

Several patterns are used throughout the framework:

1. **Composition pattern**: Steps can be composed into composite steps
2. **Strategy pattern**: Steps implement different execution strategies
3. **Decorator pattern**: with_retries wraps functionality with retry behavior
4. **Factory method**: AgentContext.create_model for creating custom contexts
5. **Pipeline pattern**: Sequential step execution in workflows

### Composition Example

```python
# Create a composite step
preparation_step = CompositeStep(
    name="data_preparation",
    description="Prepare data for analysis",
    steps=[
        DataLoadStep(),
        DataCleaningStep(),
        DataTransformationStep()
    ]
)

# Add to workflow
workflow.add_step(preparation_step)
```

### Factory Method Example

```python
# Create a custom context type
AnalysisContext = AgentContext.create_model(
    dataset_id=(str, ...),  # Required field
    analysis_type=str,
    include_visualization=bool
)

# Use the custom context
context = AnalysisContext(
    dataset_id="sales_data_2025",
    analysis_type="comprehensive",
    include_visualization=True
)
```

## Integration with Host System

The workflow architecture is fully integrated with the MCP Host system's layered architecture, residing in Layer 4 (Agent Framework). This integration provides several key benefits:

### Layer Dependencies

The BaseWorkflow class depends on components from lower layers:

1. **Layer 3 (Resource Management)**:
   - Uses `ToolManager` for tool execution
   - Indirectly uses `PromptManager` for system prompts
   - Can leverage `ResourceManager` for accessing resources

2. **Layer 2 (Communication)**:
   - Indirectly uses `MessageRouter` through ToolManager
   - Benefits from the communication infrastructure

3. **Layer 1 (Foundation)**:
   - Security validation through `RootManager`
   - Access control through `SecurityManager`

### Integration Points

The key integration points between the workflow framework and the host system are:

1. **ToolManager Reference**:
   ```python
   # In BaseWorkflow.__init__
   self.tool_manager = host._tool_manager
   ```

2. **Context Initialization**:
   ```python
   # In BaseWorkflow.execute
   agent_context.tool_manager = self.tool_manager
   ```

3. **Step Execution**:
   ```python
   # In BaseWorkflow.execute_step
   step_context.tool_manager = self.tool_manager
   outputs = await step.execute(step_context, self.host)
   ```

4. **Host Parameter**:
   ```python
   # In WorkflowStep.execute signature
   async def execute(self, context: AgentContext, host: MCPHost) -> Dict[str, Any]:
   ```

This tight integration with the host system ensures that workflows can leverage all capabilities of the underlying MCP infrastructure while maintaining a clean separation of concerns.

### Example Integration

Here's how the workflow system integrates with the host system in practice:

```python
# Create and initialize the host
host_config = HostConfig(clients=[...])
host = MCPHost(host_config)
await host.initialize()

# Create a workflow that uses the host
workflow = DataAnalysisWorkflow(host)
await workflow.initialize()

# Execute the workflow
results = await workflow.analyze_dataset(
    dataset_id="sales_data_2025",
    analysis_type="comprehensive"
)
```

## DRY Utility Components

The framework includes several utility components that promote DRY (Don't Repeat Yourself) principles:

### Context Data Access Utilities

The `AgentContext` class provides standardized methods for accessing data regardless of the underlying data structure:

```python
class AgentContext(Generic[T]):
    def get_data_dict(self) -> Dict[str, Any]:
        """Get the context data as a dictionary"""
        if isinstance(self.data, BaseModel):
            return self.data.model_dump()
        return self.data
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the context data with default fallback"""
        if isinstance(self.data, BaseModel):
            try:
                return getattr(self.data, key)
            except AttributeError:
                return default
        else:
            # Fallback for dict-like access
            return getattr(self.data, "get", lambda k, d: d)(key, default)
            
    def set(self, key: str, value: Any) -> None:
        """Set a value in the context data"""
        if isinstance(self.data, BaseModel):
            setattr(self.data, key, value)
        else:
            # Fallback for dict-like access
            if hasattr(self.data, "__setitem__"):
                self.data[key] = value
            else:
                setattr(self.data, key, value)
```

### Hook Execution Utilities

Standardized error handling for hooks is provided through:

```python
async def run_hooks_with_error_handling(
    hooks: List[Callable],
    hook_type: str,
    *args,
    **kwargs
) -> None:
    """Run a list of hooks with error handling"""
    for hook in hooks:
        try:
            # Check if the hook is awaitable
            if asyncio.iscoroutinefunction(hook):
                await hook(*args, **kwargs)
            else:
                hook(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {hook_type} hook: {e}")
```

This utility is used throughout the `BaseWorkflow` class to standardize hook execution:

```python
# Run before workflow hooks
await run_hooks_with_error_handling(
    self.before_workflow_hooks, "before workflow", agent_context
)

# Run before step hooks
await run_hooks_with_error_handling(
    self.before_step_hooks, f"before step {step.name}", step, agent_context
)

# Run after step hooks
await run_hooks_with_error_handling(
    self.after_step_hooks, f"after step {step.name}", step, agent_context, result
)
```

## Conclusion

The Aurite workflow architecture provides a flexible, modular framework for building AI agents across the Agency Spectrum. By integrating with the MCP Host system's layered architecture, it enables clear interfaces and extensibility without sacrificing type safety or simplicity.

The architecture follows DRY principles through:
1. Shared context models in base_models.py
2. Reusable utility functions in base_utils.py
3. Common workflow patterns in base_workflow.py
4. Centralized tool management in tools.py
5. Standardized hook execution with uniform error handling
6. Consistent context data access patterns

Key strengths of the architecture include:
1. **Clear layer responsibilities**: Each component has a well-defined role
2. **Composition over inheritance**: Workflows are built from composable steps
3. **Extensibility**: Multiple hook points for customization
4. **Type safety**: Pydantic models provide structured data handling
5. **Tool abstraction**: Clean separation between workflow logic and tool execution
6. **Error resilience**: Consistent error handling across the framework
7. **Simplified data access**: Uniform methods to access context data regardless of underlying storage

This design allows for easy creation of workflow-based agents while maintaining the flexibility to extend to more dynamic agent patterns through the same underlying infrastructure, positioning the Aurite framework as a comprehensive solution for the entire Agency Spectrum.