# Aurite Architecture Overview

This document provides a high-level overview of the Aurite architecture, focusing on the relationship between the MCP Host system and the Agent Framework.

## System Architecture

Aurite is built on a layered architecture that provides a clear separation of concerns while enabling powerful agent capabilities:

```mermaid
graph TD
    Users["Users/Applications"] --> L4["Layer 4: Agent Framework"]
    L4 --> L3["Layer 3: Resource Management"]
    L3 --> L2["Layer 2: Communication and Routing"]
    L2 --> L1["Layer 1: Security and Foundation"]
    L1 --> Servers["Tool Servers & External Systems"]

    classDef layer fill:#f9f9f9,stroke:#333,stroke-width:2px;
    class L1,L2,L3,L4 layer;
```

### Layer 1: Security and Foundation

The foundation layer establishes security boundaries and access control:

- **Security Manager**: Manages credentials, authentication, and authorization
- **Root Manager**: Controls access to URI roots and resources

### Layer 2: Communication and Routing

The communication layer handles message flow:

- **Transport Manager**: Creates and manages communication channels
- **Message Router**: Directs requests to appropriate tool servers

### Layer 3: Resource Management

The resource management layer provides access to data and services:

- **Tool Manager**: Manages tool registration, discovery, and execution across servers
- **Prompt Manager**: Manages system prompts and their execution
- **Resource Manager**: Manages access to files and external resources
- **Storage Manager**: Manages database connections and queries

The Tool Manager provides a unified interface for:
- Tool registration and discovery
- Tool execution with routing
- Capability-based tool selection
- Access control validation through the Root Manager

```mermaid
graph TD
    TM[Tool Manager] --> MR[Message Router]
    TM --> RM[Root Manager]
    TM --> TC[Tool Clients]

    MR --> SR[Server Registry]
    MR --> TR[Tool Registry]

    TC --> T1[Tool Server 1]
    TC --> T2[Tool Server 2]

    classDef manager fill:#f9f9f9,stroke:#333,stroke-width:2px;
    class TM,MR,RM manager;
```

### Layer 4: Agent Framework

The agent framework provides the building blocks for AI agents:

- **Workflow Manager**: Manages workflow registration, execution, and lifecycle
  - Workflow registration and configuration
  - Workflow execution orchestration
  - Resource allocation and lifecycle management
  - Centralized workflow control from the host

- **BaseWorkflow**: Sequential workflow execution with fixed tools
  - Type-safe context management
  - Composable workflow steps
  - Error handling and retries
  - Middleware hooks for extensibility
  
- **BaseAgent**: Dynamic agent execution with autonomous tool selection

- **Hybrid Implementations**: Combined workflow and dynamic behaviors

The BaseWorkflow implementation follows a pipeline pattern:

```mermaid
graph LR
    WM[Workflow Manager] --> |"Register"| WF[Workflow]
    WM --> |"Execute"| WF
    
    Input[Input Data] --> Context[Agent Context]
    Context --> Steps[Workflow Steps]
    Steps --> Composite[Composite Steps]
    Steps --> Simple[Simple Steps]
    Composite --> ToolMgr[Tool Manager]
    Simple --> ToolMgr
    ToolMgr --> Tools[Tool Execution]
    Tools --> Results[Step Results]
    Results --> Output[Output Data]

    subgraph Host System
        WM
        ToolMgr
    end
    
    subgraph Agent Framework
        WF
        Context
        Steps
        Composite
        Simple
        Results
    end

    style WM fill:#d4f0c4,stroke:#333,stroke-width:2px
    style ToolMgr fill:#d4f0c4,stroke:#333,stroke-width:2px
    style Context fill:#e6f3ff,stroke:#333,stroke-width:2px
    style Steps fill:#fff2e6,stroke:#333,stroke-width:2px
    style Tools fill:#e6ffe6,stroke:#333,stroke-width:2px
    style WF fill:#e6f3ff,stroke:#333,stroke-width:2px
```

## The Agency Spectrum

A central concept in Aurite is the Agency Spectrum, which describes the level of autonomy given to AI agents:

```mermaid
graph LR
    A["Sequential/Workflow
    • Fixed steps & tools
    • Predictable execution
    • High reliability"]

    B["Hybrid
    • Decision points
    • Conditional branching
    • Controlled autonomy"]

    C["Dynamic/Parallel
    • Autonomous tool selection
    • Goal-oriented behavior
    • Self-directed planning"]

    A --> B --> C

    style A fill:#e6f3ff,stroke:#333,stroke-width:2px
    style B fill:#fff2e6,stroke:#333,stroke-width:2px
    style C fill:#e6ffe6,stroke:#333,stroke-width:2px
```

Each type of agent serves different use cases:

- **Workflow Agents**: For predictable, repeatable processes with high reliability needs
- **Hybrid Agents**: For processes with decision points that benefit from some autonomy
- **Dynamic Agents**: For complex, open-ended tasks requiring adaptive behavior

## Core Components

The Aurite system is organized around two main components:

### 1. MCP Host System (`host.py`)

The orchestration layer that:
- Manages connections to tool servers
- Initializes and coordinates all managers
- Provides APIs for tool execution, workflow management, and resource access
- Enforces security policies and access control
- Provides centralized workflow registration and execution

### 2. Agent Framework

The agent implementation layer that:
- Provides base classes for different agent types
- Implements workflow and planning capabilities
- Manages memory and context
- Defines workflow steps and composition patterns
- Interfaces with the host through the Tool Manager

## Implementation Status

Current implementation status:

- **Layer 1**: ✅ Implemented (Security Manager, Root Manager)
- **Layer 2**: ✅ Implemented (Transport Manager, Message Router)
- **Layer 3**: ✅ Implemented
  - ✅ Tool Manager
  - ✅ Prompt Manager
  - ✅ Resource Manager
  - ✅ Storage Manager
- **Layer 4**: 🔄 In Progress
  - ✅ Workflow Manager
    - ✅ Workflow registration and discovery
    - ✅ Execution orchestration
    - ✅ Lifecycle management
  - ✅ BaseWorkflow implementation
    - ✅ Context management
    - ✅ Step composition
    - ✅ Error handling
    - ✅ Hook system
    - ✅ Tool Manager integration
  - ⏳ BaseAgent implementation (planned)
  - ⏳ Hybrid Agent implementation (planned)

## Roadmap

Future development plans:

### Short-term
1. **Enhance workflow management capabilities**
   - Workflow composition and chaining
   - Adding metadata and filtering features
   - Performance monitoring and metrics
   - Parallel workflow execution support

2. **Complete agent examples and demos**
   - Document processor example
   - Research assistant example
   - Financial analysis example

3. **Create example applications using the host**
   - CLI application for running workflows
   - Web API for workflow registration and execution
   - Dashboard for workflow monitoring

### Medium-term
1. **Implement hybrid agent capabilities**
   - Decision point framework
   - Controlled transitions between modes
   - Context sharing between sequential and dynamic components

2. **Enhance memory and planning**
   - Advanced memory capabilities for BaseAgent
   - More sophisticated planning strategies
   - Learning from execution history

### Long-term
1. **Multi-agent coordination**
   - Agent-to-agent communication
   - Task delegation and collaboration
   - Shared knowledge and resources

2. **Specialized agent types**
   - Task-specific agent implementations
   - Domain-specific knowledge integration
   - Custom tool development

## Development Approach

When developing within the Aurite architecture:

1. **Respect layer boundaries**: Higher layers should only depend on lower layers, not vice versa
2. **Follow the manager pattern**: New functionality should be encapsulated in specialized managers
3. **Validate security**: All operations should be validated against security policies
4. **Maintain asyncio consistency**: All APIs should be async/await compatible
5. **Design for extensibility**: Components should be designed for extension and customization
6. **Use dependency injection**: Components should receive their dependencies rather than creating them
7. **Limit coupling**: Each component should only depend on the interfaces it actually uses
8. **Centralize management**: Higher-level components should be managed by the host through dedicated managers

## Conclusion

The Aurite architecture provides a comprehensive framework for building AI agents with varying levels of autonomy. By organizing functionality into clear layers and providing specialized components for different concerns, it enables the development of powerful, secure, and reliable agent systems.