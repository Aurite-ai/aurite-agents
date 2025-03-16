# Aurite Agent Architecture

This document outlines the design for Aurite's agent framework, which implements AI agents across the Agency Spectrum as Layer 4 of the Aurite MCP architecture.

## Overview

Building on the layered architecture of the Aurite MCP Host system, the agent framework provides specialized classes for building AI agents with varying levels of autonomy, as defined in the Agency Spectrum:

```mermaid
graph LR
    subgraph "Agency Spectrum"
        A[Sequential/Workflow<br>Minimal Agency] -->|Increasing Autonomy| B[Hybrid<br>Mixed Agency]
        B -->|Increasing Autonomy| C[Dynamic/Parallel<br>Full Agency]
    end
    
    subgraph "Implementation Classes"
        D[BaseWorkflow] -.- A
        E[HybridAgent] -.- B
        F[BaseAgent] -.- C
    end
```

The agent framework includes three core architectural components:

1. `BaseWorkflow` - For sequential agents with minimal agency (predefined steps and tools)
2. `BaseAgent` - For dynamic agents with maximum agency (autonomous tool selection)
3. Future hybrid implementations that combine aspects of both approaches

## System Context

The agent framework operates as Layer 4 in the overall Aurite MCP architecture:

```mermaid
graph TB
    subgraph "Layer 4: Agent Framework"
        AgentFramework["Agent Framework (BaseWorkflow, BaseAgent, Hybrid)"]
    end
    
    subgraph "Layer 3: Resource Management"
        PromptManager["Prompt Manager"]
        ResourceManager["Resource Manager"]
        StorageManager["Storage Manager"]
    end
    
    subgraph "Layer 2: Communication and Routing"
        TransportManager["Transport Manager"]
        MessageRouter["Message Router"]
    end
    
    subgraph "Layer 1: Security and Foundation"
        SecurityManager["Security Manager"]
        RootManager["Root Manager"]
    end
    
    AgentFramework --> PromptManager
    AgentFramework --> ResourceManager
    AgentFramework --> StorageManager
    
    PromptManager --> TransportManager
    PromptManager --> MessageRouter
    ResourceManager --> TransportManager
    ResourceManager --> MessageRouter
    StorageManager --> TransportManager
    StorageManager --> MessageRouter
    
    TransportManager --> SecurityManager
    TransportManager --> RootManager
    MessageRouter --> SecurityManager
    MessageRouter --> RootManager
    
    MCPHost["MCP Host"] --> AgentFramework
    MCPHost --> PromptManager
    MCPHost --> ResourceManager
    MCPHost --> StorageManager
    MCPHost --> TransportManager
    MCPHost --> MessageRouter
    MCPHost --> SecurityManager
    MCPHost --> RootManager
    
    Applications["Client Applications"] --> AgentFramework
```

## BaseWorkflow Class

The `BaseWorkflow` class implements sequential agents with minimal agency.

### Architectural Characteristics

- **Sequential Execution**: Steps processed in a predefined order
- **Fixed Tool Selection**: Tools are pre-assigned to steps
- **Input/Output Contracts**: Strict data flow between steps
- **High Reliability**: Error handling and retry mechanisms
- **Predictable Execution**: Consistent behavior across runs

### Class Structure

```mermaid
classDiagram
    class BaseWorkflow {
        +host: MCPHost
        +name: str
        +steps: List[Union[WorkflowStep, ConditionalStep]]
        +error_handlers: Dict[str, Callable]
        +context_validators: List[Callable]
        +initialize()
        +execute(input_data: Dict) -> WorkflowContext
        +add_step(step: WorkflowStep, condition: Optional[Callable])
        +add_error_handler(step_name: str, handler: Callable)
        +validate_context(context: Dict) -> bool
        +shutdown()
    }
    
    class WorkflowStep {
        +name: str
        +description: str
        +required_inputs: Set[str]
        +provided_outputs: Set[str]
        +required_tools: Set[str]
        +max_retries: int
        +retry_delay: float
        +timeout: float
        +execute(context: Dict, host: MCPHost) -> Dict
        +validate_inputs(inputs: Dict) -> bool
        +validate_outputs(outputs: Dict) -> bool
    }
    
    class ConditionalStep {
        +step: WorkflowStep
        +condition: Callable
        +should_execute(context: Dict) -> bool
    }
    
    class WorkflowContext {
        +data: Dict[str, Any]
        +metadata: Dict[str, Any]
        +step_results: Dict[str, StepResult]
        +start_time: float
        +end_time: Optional[float]
        +add_step_result(step_name: str, result: StepResult)
        +get_step_result(step_name: str) -> StepResult
        +get_execution_time() -> float
        +complete()
    }
    
    class StepResult {
        +status: StepStatus
        +outputs: Dict[str, Any]
        +error: Optional[Exception]
        +execution_time: float
        +metrics: Dict[str, Any]
    }
    
    BaseWorkflow "1" *-- "many" WorkflowStep
    BaseWorkflow "1" *-- "many" ConditionalStep
    BaseWorkflow ..> WorkflowContext
    WorkflowContext "1" *-- "many" StepResult
    ConditionalStep "1" *-- "1" WorkflowStep
```

### Implementation Strategy

1. **Step Definition and Execution**
   - Each step is defined with required inputs and provided outputs
   - Steps execute in sequence with shared context
   - Steps can be conditional based on context state

2. **Context Management**
   - Context flows through steps and carries state
   - Each step validates inputs and validates outputs
   - Context validators ensure data consistency

3. **Error Handling**
   - Multiple retry mechanisms with exponential backoff
   - Step-specific error handlers
   - Global error handling policies

4. **Integration with Host System**
   - Uses host.call_tool() for fixed tool execution
   - Validates tool availability before workflow starts
   - Respects security boundaries from Layer 1

## BaseAgent Class

The `BaseAgent` class implements dynamic agents with maximum agency.

### Architectural Characteristics

- **Autonomous Operation**: Self-directed behavior based on goals
- **Dynamic Tool Selection**: Chooses appropriate tools based on task
- **Adaptive Planning**: Creates and modifies plans during execution
- **Memory and Context**: Maintains knowledge across interactions
- **Self-Evaluation**: Assesses results and learns from outcomes

### Class Structure

```mermaid
classDiagram
    class BaseAgent {
        +host: MCPHost
        +name: str
        +memory: AgentMemory
        +tool_registry: ToolRegistry
        +planner: AgentPlanner
        +active_plan: Optional[Plan]
        +execution_history: List[Dict]
        +initialize()
        +execute(task: str, context: Dict) -> AgentResult
        +select_tools(task: str, context: Dict) -> List[AgentTool]
        +evaluate_result(result: Any) -> Dict
        +shutdown()
    }
    
    class AgentMemory {
        +items: Dict[str, MemoryItem]
        +tags_index: Dict[str, Set[str]]
        +max_items: int
        +store(key: str, value: Any, tags: Set[str], ttl: Optional[float]) -> str
        +retrieve(key: str) -> Any
        +search_by_tags(tags: Set[str], match_all: bool) -> List[Tuple]
        +search_by_value(query: str, exact: bool) -> List[Tuple]
        +clear()
    }
    
    class ToolRegistry {
        +host: MCPHost
        +tools: Dict[str, AgentTool]
        +initialize()
        +discover_tools() -> List[AgentTool]
        +register_tool(tool: AgentTool)
        +get_tool(name: str) -> AgentTool
        +list_tools() -> List[AgentTool]
        +filter_tools(criteria: Dict) -> List[AgentTool]
    }
    
    class AgentPlanner {
        +host: MCPHost
        +create_plan(task: str, available_tools: List[AgentTool], context: Dict) -> Plan
        +update_plan(plan: Plan, observation: Any, available_tools: List[AgentTool]) -> Plan
    }
    
    class Plan {
        +steps: List[PlanStep]
        +goal: str
        +sub_goals: List[str]
        +context: Dict[str, Any]
        +current_step_index: int
        +get_current_step() -> PlanStep
        +advance()
        +is_complete() -> bool
    }
    
    class AgentResult {
        +success: bool
        +output: Any
        +execution_time: float
        +tool_calls: int
        +plan: Optional[Plan]
        +error: Optional[Exception]
        +metadata: Dict[str, Any]
    }
    
    BaseAgent "1" o-- "1" AgentMemory
    BaseAgent "1" o-- "1" ToolRegistry
    BaseAgent "1" o-- "1" AgentPlanner
    BaseAgent "1" o-- "1" Plan
    BaseAgent ..> AgentResult
    Plan "1" *-- "many" PlanStep
```

### Implementation Strategy

1. **Tool Management**
   - Dynamic tool discovery through host system
   - Capability-based tool filtering
   - Tool selection based on task requirements

2. **Memory System**
   - Short and long-term storage mechanisms
   - Tag-based and content-based retrieval
   - Time-to-live for ephemeral information

3. **Planning and Execution**
   - LLM-based plan generation
   - Step-by-step execution with fallbacks
   - Plan adaptation based on outcomes

4. **Integration with Host System**
   - Leverages all layers of the host architecture
   - Respects security boundaries from Layer 1
   - Uses prompts and resources from Layer 3

## Hybrid Agent Design

For agents in the middle of the Agency Spectrum, a hybrid approach is planned:

```mermaid
classDiagram
    BaseWorkflow <|-- HybridAgent
    BaseAgent <|-- HybridAgent
    
    class HybridAgent {
        +primary_workflow: BaseWorkflow
        +fallback_agent: BaseAgent
        +decision_points: List[DecisionPoint]
        +execute(input_data: Dict) -> Dict
        +handle_decision_point(point: DecisionPoint, context: Dict)
        +transition_to_dynamic_mode(context: Dict)
        +return_to_workflow(results: Dict, context: Dict)
    }
    
    class DecisionPoint {
        +condition: Callable
        +workflow_path: WorkflowStep
        +dynamic_action: Callable
        +evaluate(context: Dict) -> bool
    }
    
    HybridAgent "1" *-- "many" DecisionPoint
```

### Key Design Elements for Hybrid Agents

- **Structured Core**: Primary workflow defines main execution path
- **Decision Points**: Specific points where dynamic behavior is allowed
- **Mode Transitions**: Controlled switching between workflow and dynamic behavior
- **Shared Context**: Consistent state management across modes
- **Guardrails**: Safety mechanisms to prevent undesired behavior

## Example Implementations

The agent framework includes concrete examples that demonstrate its capabilities:

### Document Processor (Workflow Agent)

```python
class DocumentProcessorWorkflow(BaseWorkflow):
    """Workflow for processing and analyzing documents"""
    
    def __init__(self, host: MCPHost):
        super().__init__(host, name="document_processor")
        
        # Add the steps in sequence
        self.add_step(ClassificationStep())
        self.add_step(ExtractionStep())
        self.add_step(SentimentAnalysisStep())
        self.add_step(ReportGenerationStep())
```

### Research Assistant (Dynamic Agent)

```python
class ResearchAssistantAgent(BaseAgent):
    """Research assistant with autonomous capabilities"""
    
    def __init__(self, host: MCPHost):
        super().__init__(host, name="research_assistant")
        
        # Define tool preferences for different tasks
        self.preferred_tools = {
            "search": ["web_search", "document_search"],
            "analysis": ["extract_entities", "analyze_sentiment"],
            "generation": ["generate_text", "create_summary"]
        }
```

## Integration with MCP Host Layers

The agent framework integrates with all layers of the MCP Host architecture:

### Layer 1: Security and Foundation
- Respects access control policies
- Operates within established root boundaries
- Ensures secure tool execution

### Layer 2: Communication and Routing
- Uses transport mechanisms for tool communication
- Leverages message routing for optimal tool selection
- Handles communication failures appropriately

### Layer 3: Resource Management
- Utilizes system prompts for consistent behavior
- Accesses resources based on task requirements
- Manages database connections when needed

## Implementation Roadmap

The agent framework will be implemented in three phases:

### Phase 1: Core Classes
- [x] Implement BaseWorkflow with step execution
- [x] Implement BaseAgent with memory and planning
- [x] Create example implementations
- [x] Integration with MCP Host system

### Phase 2: Extended Capabilities
- [ ] Add advanced memory capabilities to BaseAgent
- [ ] Enhance planning with more sophisticated strategies
- [ ] Implement monitoring and observability
- [ ] Create additional tool integrations

### Phase 3: Hybrid and Advanced Features
- [ ] Implement HybridAgent class
- [ ] Develop decision point system
- [ ] Create transition mechanisms between modes
- [ ] Add learning capabilities for agent improvement

## Conclusion

The agent framework provides a comprehensive Layer 4 for the Aurite MCP architecture, enabling the creation of agents across the full Agency Spectrum. By building on the solid foundation of the layered architecture, these agent classes offer both flexibility and control, allowing developers to create agents with the precise level of autonomy needed for their use cases.