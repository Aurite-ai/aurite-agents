# Kahuna Testing & Security Framework

## Overview

The Kahuna Testing & Security Framework provides comprehensive quality assurance and security validation for AI agents and workflows in enterprise environments. This framework is designed to bridge business requirements from Kahuna Manager Mode with development practices in Kahuna Developer Mode, ultimately providing metrics and insights to Kahuna Executive Mode.

## Core Philosophy

Our testing approach recognizes that AI components build upon each other in a hierarchical manner:

```
LLMs ─┐
      ├─→ Agents ─→ Workflows
MCP ──┘
```

This compositional nature allows us to:

- **Inherit** test results from foundation components
- **Focus** testing efforts on integration points
- **Avoid** redundant validation
- **Accelerate** the testing process

## Framework Organization

The testing framework is organized into two primary dimensions:

### 1. Testing Categories

- **Quality Assurance (QA):** Ensures components meet performance, accuracy, and business requirements
- **Security Testing:** Validates safety, compliance, and protection against threats

### 2. Testing Phases

- **Development-Time Testing:** Pre-deployment validation in development environments
- **Runtime Monitoring:** Continuous validation in production environments

## Component Hierarchy

### Foundation Components

- **[LLMs](components/llm/):** Language model testing for quality and security
- **[MCP Servers](components/mcp_server/):** Tool and API testing

### Composite Components

- **[Agents](components/agent/):** Combined LLM + MCP testing with agent-specific validation
- **[Workflows](components/workflow/):** End-to-end business process validation

## Testing Matrix

| Component      | Quality Testing                                                        | Security Testing                                                       | Inheritance              |
| -------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------------- | ------------------------ |
| **LLM**        | • Response coherence<br>• Instruction following<br>• Output formatting | • Prompt injection<br>• Content safety<br>• Data leakage               | None (foundation)        |
| **MCP Server** | • API compliance<br>• Performance<br>• Error handling                  | • Authentication<br>• Input validation<br>• Rate limiting              | None (foundation)        |
| **Agent**      | • Tool selection<br>• Goal achievement<br>• Efficiency                 | • Permission boundaries<br>• Action authorization<br>• Resource limits | Inherits from LLM + MCP  |
| **Workflow**   | • Business compliance<br>• End-to-end success<br>• Performance         | • Cross-agent security<br>• Data isolation<br>• Audit completeness     | Inherits from all agents |

## Key Concepts

### Test Result Inheritance

Higher-level components inherit test results from their dependencies:

```
Workflow Test Result = {
    workflow_specific_tests: { ... },
    agent_results: {
        agent_1: {
            agent_specific_tests: { ... },
            inherited_llm_results: { ... },
            inherited_mcp_results: { ... }
        }
    },
    aggregated_metrics: { ... }
}
```

### Smart Test Optimization

The framework optimizes testing through:

1. **Skip Redundant Tests:** If an LLM passes security tests, agents using it don't retest the same vectors
2. **Focus on Integration:** Agent tests focus on tool usage, not language capabilities
3. **Efficient Regression:** Component updates trigger only affected downstream tests

### Failure Propagation

When foundation components fail:

- Dependent components are marked as "pending" or "blocked"
- Impact analysis shows the full dependency chain
- Developers can see exactly what needs fixing

## Getting Started

### For Developers

1. **Component Testing:** Navigate to the specific component folder in [`components/`](components/)
2. **Development Testing:** See the [Development Testing Guide](guides/development_testing.md)
3. **Custom Compliance:** Define your own requirements using the [Compliance Framework](guides/compliance_framework.md)

### For DevOps

1. **Runtime Monitoring:** Configure production monitoring with the [Runtime Monitoring Guide](guides/runtime_monitoring.md)
2. **Metrics Export:** Set up dashboards for Kahuna Executive Mode

### For Architects

1. **Architecture Overview:** Understand the design in [`architecture/`](architecture/)
2. **Integration Patterns:** Learn about test composition in [Compositional Testing](architecture/compositional_testing.md)

## Integration with Kahuna Ecosystem

### Input: Project Context (from Kahuna-mgr)

- Business workflow requirements
- Component specifications
- Quality thresholds
- Security policies

### Process: Testing & Validation

- Development-time testing
- Security assessment
- Quality assurance
- Compliance verification

### Output: Metrics & Reports (to Kahuna-exec)

- Quality scores
- Security assessments
- Business KPI achievement
- Compliance status

## Documentation Structure

```
docs/testing/
├── README.md                          # This file
├── architecture/                      # System design and patterns
│   ├── testing_architecture.md        # Overall framework design
│   ├── compositional_testing.md       # Component composition patterns
│   └── test_inheritance.md            # Result reuse strategies
├── components/                        # Component-specific testing
│   ├── llm/                          # LLM testing documentation
│   ├── mcp_server/                   # MCP server testing
│   ├── agent/                        # Agent testing
│   └── workflow/                     # Workflow testing
├── guides/                           # Practical guides
│   ├── development_testing.md        # Development-time testing
│   ├── runtime_monitoring.md         # Production monitoring
│   └── compliance_framework.md       # Custom compliance definition
└── user_security/                    # User access and RBAC
    └── access_control.md             # User security documentation
```

## Quick Links

- **Start Testing:** [Development Testing Guide](guides/development_testing.md)
- **Component Tests:** [Components Directory](components/)
- **Architecture:** [Testing Architecture](architecture/testing_architecture.md)
- **Security:** [User Security](user_security/access_control.md)

## Contributing

When adding new test types or components:

1. Follow the compositional testing principles
2. Document inheritance relationships
3. Specify development vs. runtime applicability
4. Update the testing matrix in this README

## Related Documentation

- [Kahuna Developer Mode](../Kahuna%20Developer%20Mode.md)
- [Aurite Agents Framework](../../README.md)
- [Security Framework](../../src/aurite/security/)
