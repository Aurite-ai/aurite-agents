# Kahuna Testing & Security Framework

## Overview

The Kahuna Testing & Security Framework provides comprehensive quality assurance and security validation for AI agents and workflows across multiple agent frameworks in enterprise environments. This framework is designed to bridge business requirements from Kahuna Manager Mode with development practices in Kahuna Developer Mode, ultimately providing metrics and insights to Kahuna Executive Mode.

The framework now supports framework-agnostic testing, enabling validation of AI components independent of the specific agent framework being used, while also providing framework-specific testing for unique implementation details.

## Core Philosophy

Our testing approach recognizes two fundamental principles:

### 1. Compositional Hierarchy

AI components build upon each other in a hierarchical manner:

```
LLMs ─┐
      ├─→ Agents ─→ Workflows
MCP ──┘
```

### 2. Framework Independence

Certain AI components operate independently of any specific agent framework:

```
Framework-Agnostic (Universal)
├── LLMs (100% Agnostic)
├── MCP Servers (100% Agnostic)
└── Core Agent Behaviors (60% Agnostic)
    └── Framework-Specific Layer
        ├── Agent Orchestration (40% Specific)
        └── Workflows (80% Specific)
```

This dual nature allows us to:

- **Inherit** test results from foundation components
- **Reuse** tests across different agent frameworks
- **Focus** testing efforts on integration points
- **Avoid** redundant validation
- **Accelerate** the testing process
- **Enable** cross-framework comparisons

## Framework Organization

The testing framework operates in three dimensions:

### 1. Testing Categories

- **Quality Assurance (QA):** Ensures components meet performance, accuracy, and business requirements
- **Security Testing:** Validates safety, compliance, and protection against threats

### 2. Testing Phases

- **Development-Time Testing:** Pre-deployment validation in development environments
- **Runtime Monitoring:** Continuous validation in production environments

### 3. Framework Scope

- **Framework-Agnostic:** Universal tests that work across all agent frameworks
- **Framework-Specific:** Tests unique to individual framework implementations

This creates test combinations such as:

- Framework-Agnostic Security Runtime LLM Test
- Framework-Specific QA Development-Time Workflow Test
- Framework-Agnostic Quality Development-Time MCP Server Test

## Component Hierarchy

### Foundation Components (100% Framework-Agnostic)

- **[LLMs](components/llm/):** Language model testing for quality and security - completely independent of calling framework
- **[MCP Servers](components/mcp_server/):** Tool and API testing - operates through standardized protocols

### Hybrid Components

- **[Agents](components/agent/):** Combined LLM + MCP testing with agent-specific validation
  - 60% Framework-Agnostic: Core behaviors, tool usage, goal achievement
  - 40% Framework-Specific: System prompts, memory management, orchestration

### Framework-Dependent Components

- **[Workflows](components/workflow/):** End-to-end business process validation
  - 20% Framework-Agnostic: Business logic, data integrity
  - 80% Framework-Specific: Orchestration patterns, inter-agent communication

## Testing Matrix

| Component      | Quality Testing                                                        | Security Testing                                                       | Framework Scope              | Inheritance              |
| -------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------------- | ---------------------------- | ------------------------ |
| **LLM**        | • Response coherence<br>• Instruction following<br>• Output formatting | • Prompt injection<br>• Content safety<br>• Data leakage               | 100% Agnostic                | None (foundation)        |
| **MCP Server** | • API compliance<br>• Performance<br>• Error handling                  | • Authentication<br>• Input validation<br>• Rate limiting              | 100% Agnostic                | None (foundation)        |
| **Agent**      | • Tool selection<br>• Goal achievement<br>• Efficiency                 | • Permission boundaries<br>• Action authorization<br>• Resource limits | 60% Agnostic<br>40% Specific | Inherits from LLM + MCP  |
| **Workflow**   | • Business compliance<br>• End-to-end success<br>• Performance         | • Cross-agent security<br>• Data isolation<br>• Audit completeness     | 20% Agnostic<br>80% Specific | Inherits from all agents |

## Key Concepts

### Framework-Agnostic Testing

The framework supports testing AI components across multiple agent frameworks through:

- **Universal Standards:** LLMs and MCP Servers tested independently of framework
- **Adapter Pattern:** Translation between framework-specific and standard formats
- **Aurite as Standard:** Using Aurite Agents as the canonical testing format
- **Cross-Framework Comparison:** Benchmarking performance across different frameworks

For detailed architecture, see [Framework-Agnostic Testing Architecture](architecture/framework_agnostic_testing.md).

### Test Result Inheritance

Higher-level components inherit test results from their dependencies, now including cross-framework inheritance:

```
Workflow Test Result = {
    workflow_specific_tests: { ... },
    agent_results: {
        agent_1: {
            agent_specific_tests: { ... },
            inherited_llm_results: { ... },  // Framework-agnostic
            inherited_mcp_results: { ... }   // Framework-agnostic
        }
    },
    aggregated_metrics: { ... },
    framework_metadata: { ... }
}
```

### Smart Test Optimization

The framework optimizes testing through:

1. **Skip Redundant Tests:** If an LLM passes security tests, agents using it don't retest the same vectors
2. **Focus on Integration:** Agent tests focus on tool usage, not language capabilities
3. **Efficient Regression:** Component updates trigger only affected downstream tests
4. **Cross-Framework Reuse:** Framework-agnostic test results apply to all frameworks

### Failure Propagation

When foundation components fail:

- Dependent components are marked as "pending" or "blocked"
- Impact analysis shows the full dependency chain
- Developers can see exactly what needs fixing
- Framework-agnostic failures affect all framework implementations

## Integration with Kahuna Ecosystem

### Input: Project Context (from Kahuna-mgr)

- Business workflow requirements
- Component specifications
- Quality thresholds
- Security policies
- Target framework(s)

### Process: Testing & Validation

- Framework detection and adaptation
- Development-time testing (agnostic and specific)
- Security assessment
- Quality assurance
- Compliance verification
- Cross-framework comparison

### Output: Metrics & Reports (to Kahuna-exec)

- Quality scores (per framework)
- Security assessments
- Business KPI achievement
- Compliance status
- Framework comparison metrics

## Related Documentation

### Architecture Documents

- [Framework-Agnostic Testing](architecture/framework_agnostic_testing.md) - Multi-framework testing architecture
- [Testing Hierarchy](architecture/testing_hierarchy.md) - Complete testing hierarchy and flow
- [Testing Architecture](architecture/testing_architecture.md) - Core architectural principles
- [Test Inheritance](architecture/test_inheritance.md) - Test result inheritance patterns

### Component Testing Guides

- [LLM Testing](components/llm/) - Framework-agnostic LLM testing
- [MCP Server Testing](components/mcp_server/) - Framework-agnostic tool testing
- [Agent Testing](components/agent/) - Hybrid agent testing approach
- [Workflow Testing](components/workflow/) - Framework-specific workflow testing
