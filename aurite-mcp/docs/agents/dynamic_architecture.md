# Aurite Dynamic Agent Architecture

This document outlines the architecture for dynamic agents in the Aurite agent framework, specifically focusing on the implementation of the `BaseAgent` class for autonomous tool selection and execution.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Dynamic Agent Execution Model](#dynamic-agent-execution-model)
4. [Planning and Goal Management](#planning-and-goal-management)
5. [Tool Selection and Adaptation](#tool-selection-and-adaptation)
6. [Memory and State Management](#memory-and-state-management)
7. [Error Handling and Resilience](#error-handling-and-resilience)
8. [Extension Points](#extension-points)
9. [Integration with Host System](#integration-with-host-system)
10. [Reused Components](#reused-components)

## Architecture Overview

The dynamic agent architecture represents the high-autonomy end of the Agency Spectrum, providing agents with the ability to:

1. **Autonomously select tools** based on goals and context
2. **Plan their own execution path** without a predefined sequence
3. **Adapt to changing information** during execution
4. **Manage their own memory** across execution steps
5. **Execute tools in parallel** when appropriate

Unlike workflow agents which follow a fixed sequence of steps, dynamic agents choose their own path through a goal-directed planning process:

```
┌─────────────────────────────────────────────────────────────┐
│                      BaseAgent                              │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                  Planning Cycle                        │  │
│  │                                                        │  │
│  │  ┌───────────┐      ┌───────────┐      ┌───────────┐  │  │
│  │  │ Analyze   │ ───> │  Plan     │ ───> │ Execute   │  │  │
│  │  │ Context   │      │  Actions  │      │ Actions   │  │  │
│  │  └───────────┘      └───────────┘      └───────────┘  │  │
│  │        │                                     │        │  │
│  │        └─────────────────────────────────────┘        │  │
│  │                     (feedback)                        │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                 AgentContext                           │  │
│  │  ┌───────────────┐  ┌───────────────────────────────┐ │  │
│  │  │   Data Model  │  │    Action Results             │ │  │
│  │  └───────────────┘  └───────────────────────────────┘ │  │
│  │  ┌───────────────┐  ┌───────────────────────────────┐ │  │
│  │  │   Memory      │  │    Tool Manager Reference     │ │  │
│  │  └───────────────┘  └───────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### BaseAgent (`base_agent.py`)

The `BaseAgent` class serves as the foundation for dynamic agents and contains several key components:

1. **Planning Capabilities**: For determining what actions to take
2. **Memory Management**: For short and long-term memory across actions
3. **Tool Selection**: For choosing appropriate tools based on goals
4. **Action Execution**: For running selected tools with proper arguments
5. **Context Management**: For maintaining state during execution
6. **Hook System**: For extensions and customization

Key implementation sketch:

```python
class BaseAgent:
    """Base class for implementing dynamic agents with autonomous tool selection"""
    
    def __init__(self, host, name="unnamed_agent"):
        self.host = host
        self.name = name
        self.tool_manager = host._tool_manager
        self.memory = AgentMemory()
        
        # Hook points for customization
        self.before_execution_hooks = []
        self.after_execution_hooks = []
        self.before_action_hooks = []
        self.after_action_hooks = []
        self.planning_hooks = []
        
    async def execute(self, input_data, metadata=None):
        """Execute the agent with the given input"""
        # Create agent context
        context = self._create_context(input_data, metadata)
        
        # Run planning cycle
        while not self._is_goal_complete(context):
            # Analyze current state
            state = self._analyze_context(context)
            
            # Plan next actions
            actions = await self._plan_actions(state, context)
            
            # Execute actions (potentially in parallel)
            await self._execute_actions(actions, context)
            
            # Update memory and context
            self._update_memory(context)
            
        # Return final context
        return context
```

### AgentMemory

The `AgentMemory` class provides structured storage for:

1. **Short-term memory**: For the current execution cycle
2. **Working memory**: For the overall execution session
3. **Long-term memory**: For persistent knowledge across sessions

Key implementation sketch:

```python
class AgentMemory:
    """Memory for dynamic agents"""
    
    def __init__(self):
        self.short_term = {}  # Current cycle memory
        self.working = {}     # Current session memory
        self.long_term = {}   # Persistent memory
        
    def add(self, key, value, memory_type="working"):
        """Add an item to memory"""
        if memory_type == "short_term":
            self.short_term[key] = value
        elif memory_type == "working":
            self.working[key] = value
        elif memory_type == "long_term":
            self.long_term[key] = value
            
    def get(self, key, memory_type="working", default=None):
        """Get an item from memory"""
        if memory_type == "short_term":
            return self.short_term.get(key, default)
        elif memory_type == "working":
            return self.working.get(key, default)
        elif memory_type == "long_term":
            return self.long_term.get(key, default)
        return default
    
    def clear_short_term(self):
        """Clear short-term memory after a cycle"""
        self.short_term = {}
```

### ActionResult

The `ActionResult` class tracks the outcome of dynamic actions:

```python
@dataclass
class ActionResult:
    """Result of a dynamic agent action"""
    action_id: str
    tool_name: str
    status: ActionStatus
    result: Any = None
    error: Optional[Exception] = None
    execution_time: float = 0.0
    arguments: Dict[str, Any] = field(default_factory=dict)
```

## Dynamic Agent Execution Model

The dynamic agent execution follows a cyclic model:

1. **Initialization**: Setting up the agent and context
2. **Analysis**: Analyzing the current context and goal state
3. **Planning**: Determining the next actions to take
4. **Execution**: Running the planned actions (potentially in parallel)
5. **Update**: Incorporating results into memory and context
6. **Evaluation**: Checking if the goal has been achieved
7. **Iteration**: Repeating the cycle until goal completion or failure

This represents a significant departure from the sequential workflow model, enabling more flexible and adaptive behavior.

## Planning and Goal Management

Dynamic agents rely on a planning component to determine their course of action:

1. **Goal Representation**: Explicit or implicit representation of the target state
2. **State Analysis**: Assessment of the current state vs. the target state
3. **Action Selection**: Choosing actions that reduce the distance to the goal
4. **Plan Formation**: Creating a coherent sequence or set of parallel actions

The planning process may be implemented through:

1. **Rule-based planning**: Simple if-then rules for action selection
2. **Search-based planning**: Searching for paths to the goal state
3. **LLM-assisted planning**: Using language models to generate plans
4. **Hybrid approaches**: Combining multiple planning strategies

## Tool Selection and Adaptation

Dynamic agents select tools based on their capabilities and the current goal:

1. **Capability Matching**: Matching tool capabilities to task requirements
2. **Context-Aware Selection**: Considering the current state in tool selection
3. **Adaptation**: Adjusting parameters based on previous results
4. **Discovery**: Dynamically discovering available tools

The tool selection process works with the tool manager:

```python
async def _select_tools_for_task(self, task, context):
    """Select appropriate tools for a given task"""
    # Get all available tools
    available_tools = await self.tool_manager.list_tools()
    
    # Filter based on capabilities needed for the task
    required_capabilities = self._identify_required_capabilities(task)
    
    matching_tools = []
    for tool in available_tools:
        tool_caps = await self.tool_manager.get_tool_capabilities(tool.name)
        if all(cap in tool_caps for cap in required_capabilities):
            matching_tools.append(tool)
    
    # Consider context and preferences
    return self._prioritize_tools(matching_tools, context)
```

## Memory and State Management

Dynamic agents require a more sophisticated memory model than workflows:

1. **Memory Types**: Short-term, working, and long-term memory
2. **State Tracking**: Maintaining awareness of the current state
3. **History Management**: Recording action history and results
4. **Knowledge Integration**: Incorporating new information into memory

The memory system allows agents to:

1. Remember previous actions and outcomes
2. Maintain context across planning cycles
3. Learn from experience
4. Avoid repeating failed approaches

## Error Handling and Resilience

Dynamic agents need robust error handling due to their autonomous nature:

1. **Action-level retries**: Retrying individual actions when they fail
2. **Plan adaptation**: Adjusting plans when actions fail repeatedly
3. **Recovery strategies**: Alternative approaches when primary paths fail
4. **Health monitoring**: Detecting and addressing deteriorating conditions

The retry mechanism leverages the existing utils:

```python
# Decorate the execute function with retry logic
decorated_execute = with_retries(
    max_retries=3,
    retry_delay=1.0,
    exponential_backoff=True,
    on_retry=lambda e, a: self._on_action_retry(action, e, a),
)(self._execute_action)

# Execute with retries
result = await decorated_execute(action, context)
```

## Extension Points

The dynamic agent provides several extension points:

1. **Hooks**: Before/after hooks for execution and actions
2. **Custom planners**: Ability to provide custom planning logic
3. **Memory extensions**: Custom memory implementations
4. **Custom action types**: Support for different types of actions
5. **Tool adapters**: Specialized tool interaction patterns

Hooks are implemented similarly to the workflow framework:

```python
# Adding hooks to an agent
agent.add_before_execution_hook(async_hook_function)
agent.add_after_action_hook(async_hook_function)

# Hook implementation example
async def my_planning_hook(state, context):
    # Influence the planning process
    # ...
    return modified_state
```

## Integration with Host System

The dynamic agent integrates with the MCP Host system through the same interfaces as workflows:

1. **ToolManager Reference**: Access to tools through the host's tool manager
2. **Host Reference**: Direct access to the host for system-level operations
3. **Context Integration**: Using AgentContext for data management

This integration allows dynamic agents to leverage the same underlying infrastructure as workflows, just with more autonomy in their operation.

## Reused Components

The dynamic agent architecture reuses several components from the workflow framework:

1. **AgentContext**: For state management during execution
2. **Retry Mechanism**: The `with_retries` decorator for resilient execution
3. **Hook Execution**: The `run_hooks_with_error_handling` utility for consistent hook handling
4. **Context Data Access**: Methods for uniform data access regardless of underlying structure
5. **Result Summarization**: The `summarize_execution_results` function for consistent reporting

By reusing these components, we ensure consistency across the Agency Spectrum while building on the solid foundation established in the workflow framework.

## Conclusion

The dynamic agent architecture represents the high-autonomy end of the Agency Spectrum, providing flexible, goal-directed behavior through autonomous planning and tool selection. By reusing core components from the workflow framework while introducing new capabilities for planning and memory management, we maintain a consistent architecture while enabling more sophisticated agent behaviors.

Key differences from workflows include:

1. **Planning vs. Sequencing**: Dynamic agents plan their steps rather than following a preset sequence
2. **Tool Selection**: Dynamic agents choose tools based on tasks rather than having fixed tool assignments
3. **Memory Management**: Dynamic agents maintain more sophisticated memory across planning cycles
4. **Parallel Execution**: Dynamic agents can execute multiple actions in parallel when appropriate
5. **Adaptation**: Dynamic agents can change their approach based on emerging information

These differences enable dynamic agents to handle more open-ended, complex tasks while maintaining the reliability and security guarantees of the overall Aurite framework.