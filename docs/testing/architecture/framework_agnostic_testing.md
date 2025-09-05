# Framework-Agnostic Testing Architecture

## Overview

The Framework-Agnostic Testing Architecture extends the Kahuna Testing & Security Framework to enable testing of AI components across multiple agent frameworks, not just Aurite Agents. This architecture introduces a third dimension to our testing matrix, allowing us to distinguish between tests that are universal across all frameworks and those that are specific to individual framework implementations.

### Purpose and Philosophy

Framework-agnostic testing recognizes that certain AI components and behaviors can be validated independently of the framework that orchestrates them. By separating universal testing concerns from framework-specific ones, we can:

- **Maximize test reusability** across different agent frameworks
- **Establish universal quality and security standards** for AI components
- **Enable cross-framework performance comparisons**
- **Reduce redundant testing effort** when components are used in multiple frameworks
- **Provide a common testing language** for heterogeneous AI systems

### The Third Dimension

Our testing framework now operates in three dimensions:

```
Testing Matrix:
├── Dimension 1: Testing Categories
│   ├── Quality Assurance (QA)
│   └── Security Testing
├── Dimension 2: Testing Phases
│   ├── Development-Time Testing
│   └── Runtime Monitoring
└── Dimension 3: Framework Scope (NEW)
    ├── Framework-Agnostic
    └── Framework-Specific
```

This creates combinations such as:

- Framework-Agnostic Security Runtime LLM Test
- Framework-Specific QA Development-Time Workflow Test
- Framework-Agnostic Quality Development-Time MCP Server Test

## Testing Scope Classification

### Framework-Agnostic Components

Framework-agnostic testing applies to components and behaviors that operate independently of any specific agent framework:

**Characteristics:**

- Direct API interaction without framework mediation
- Standardized input/output formats
- Universal evaluation criteria
- Consistent behavior across frameworks
- No dependency on framework-specific features

**Testing Capabilities:**

- Direct component invocation
- Standardized performance metrics
- Universal security validation
- Cross-framework result comparison
- Cached interaction replay

### Framework-Specific Components

Framework-specific testing addresses behaviors and features unique to individual frameworks:

**Characteristics:**

- Framework-injected system prompts
- Proprietary orchestration patterns
- Custom state management
- Framework-specific configuration
- Unique error handling mechanisms

**Testing Requirements:**

- Framework context awareness
- Adapter-based translation
- Framework-specific metrics
- Custom evaluation criteria
- Native execution environment

## Component Testing Breakdown

### LLM Testing (100% Framework-Agnostic)

Language models operate as stateless services that process text input and generate text output, making them completely framework-independent.

**Framework-Agnostic Aspects:**

- Prompt injection resistance
- Content safety validation
- Response quality metrics
- Instruction following accuracy
- Output format compliance
- Hallucination detection
- Performance benchmarking
- Token usage analysis

**Why Fully Agnostic:**

- LLMs are accessed via standardized APIs (OpenAI, Anthropic, etc.)
- Input/output is pure text, regardless of calling framework
- Security and quality concerns are universal
- No framework can alter core LLM behavior

### MCP Server Testing (100% Framework-Agnostic)

Model Context Protocol servers provide tools and resources through standardized interfaces, making them inherently framework-independent.

**Framework-Agnostic Aspects:**

- API compliance verification
- Tool invocation testing
- Performance benchmarking
- Error handling validation
- Authentication and authorization
- Rate limiting compliance
- Input validation
- Resource availability

**Why Fully Agnostic:**

- MCP defines a standard protocol for tool interaction
- Tools operate independently of calling context
- Security and reliability requirements are universal
- Direct testing bypasses framework layers entirely

### Agent Testing (Hybrid: 60% Agnostic, 40% Specific)

Agents combine LLMs and tools with framework-specific orchestration, creating a hybrid testing scenario.

**Framework-Agnostic Aspects (60%):**

- Tool selection accuracy
- Goal achievement metrics
- Multi-turn conversation coherence
- Cost efficiency analysis
- Security boundary validation
- Resource usage patterns
- Decision-making quality
- Task completion rates

**Framework-Specific Aspects (40%):**

- System prompt handling and injection
- Memory and context management
- State persistence mechanisms
- Framework-specific tool integration
- Error recovery patterns
- Conversation history management
- Variable naming and scoping
- Framework-specific optimizations

### Workflow Testing (20% Agnostic, 80% Specific)

Workflows are heavily dependent on framework orchestration capabilities, making them predominantly framework-specific.

**Framework-Agnostic Aspects (20%):**

- Business logic validation
- End-to-end success metrics
- Data flow integrity
- Output quality assessment
- Total cost analysis
- Compliance verification

**Framework-Specific Aspects (80%):**

- Agent orchestration patterns
- Inter-agent communication protocols
- State management across agents
- Parallel execution strategies
- Error propagation and recovery
- Conditional branching logic
- Framework-specific optimizations
- Native integration patterns

## Aurite as the Universal Standard

### Standardization Philosophy

Aurite Agents serves as the canonical format and reference implementation for framework-agnostic testing. This design decision is based on several key principles:

**Canonical Data Structures:**

- Aurite's configuration formats become the universal language
- All frameworks translate to/from Aurite's representations
- Test cases and results use Aurite's data models
- Standardized metrics and scoring systems

**Reference Implementation:**

- Aurite provides the baseline for expected behavior
- Other frameworks are compared against Aurite's results
- Performance benchmarks use Aurite as the standard
- Security validations follow Aurite's patterns

**Benefits of Standardization:**

- Single source of truth for test definitions
- Consistent evaluation criteria across frameworks
- Simplified cross-framework comparisons
- Reduced complexity in multi-framework environments

### Adapter Pattern Architecture

The adapter pattern enables translation between framework-specific formats and Aurite's standard:

**Abstract Adapter Interface:**

```
Framework Adapter
├── Configuration Translation
│   ├── To Aurite Format
│   └── From Aurite Format
├── Execution Translation
│   ├── Request Adaptation
│   └── Response Normalization
├── Context Extraction
│   ├── System Prompts
│   ├── Framework Variables
│   └── State Information
└── Feature Mapping
    ├── Supported Features
    ├── Unsupported Features
    └── Feature Compatibility
```

**Bidirectional Translation Requirements:**

- Configuration mapping (both directions)
- Request/response format conversion
- Error message standardization
- Metric normalization
- Result aggregation

**Framework Detection and Classification:**

- Automatic framework identification from configuration
- Version compatibility checking
- Feature capability assessment
- Optimization opportunity detection

## Three-Dimensional Testing Matrix

### Matrix Integration

The framework scope dimension integrates with existing testing categories and phases:

```
Complete Testing Combinations:
├── Framework-Agnostic
│   ├── Quality Assurance
│   │   ├── Development-Time
│   │   └── Runtime
│   └── Security
│       ├── Development-Time
│       └── Runtime
└── Framework-Specific
    ├── Quality Assurance
    │   ├── Development-Time
    │   └── Runtime
    └── Security
        ├── Development-Time
        └── Runtime
```

### Test Inheritance Across Frameworks

Test inheritance now operates across framework boundaries:

**Inheritance Rules:**

1. Framework-agnostic test results are inherited by all framework-specific tests
2. LLM and MCP test results apply universally
3. Framework-specific agent tests inherit agnostic agent test results

**Inheritance Benefits:**

- Eliminate redundant testing across frameworks
- Accelerate multi-framework validation
- Ensure consistent security standards
- Enable rapid framework migration testing

### Cross-Framework Comparison

The three-dimensional matrix enables sophisticated comparisons:

**Comparison Capabilities:**

- Performance benchmarking across frameworks
- Security posture comparison
- Cost efficiency analysis
- Feature parity assessment
- Migration readiness evaluation

## Integration with Existing Architecture

### Relationship to Compositional Testing

Framework-agnostic testing extends the compositional testing model:

```
Extended Hierarchy:
Universal Foundation (Framework-Agnostic)
├── LLMs (100% Agnostic)
├── MCP Servers (100% Agnostic)
└── Core Agent Behaviors (60% Agnostic)
    └── Framework Layer (Framework-Specific)
        ├── Agent Orchestration (40% Specific)
        └── Workflows (80% Specific)
```

### Extension of Test Inheritance

The existing test inheritance patterns extend naturally:

**Original Inheritance:**

- LLM → Agent → Workflow (within framework)

**Extended Inheritance:**

- Universal LLM → Any Framework's Agent
- Universal MCP → Any Framework's Agent
- Agnostic Agent Tests → Specific Agent Tests
- Cross-Framework Workflow Composition

### API Exposure

The Aurite API becomes the universal testing service:

**Service Endpoints:**

- `/test/agnostic/llm` - Universal LLM testing
- `/test/agnostic/mcp` - Universal MCP testing
- `/test/agnostic/agent` - Core agent behavior testing
- `/test/framework/{framework}/agent` - Framework-specific agent testing
- `/test/compare` - Cross-framework comparison

## Framework Categories

### Native Frameworks

Frameworks with direct integration and full support:

**Characteristics:**

- Built-in adapter implementation
- Full feature compatibility
- Optimized translation layer
- Native performance

**Examples:**

- Aurite Agents (reference implementation)
- Frameworks with official adapters

### Compatible Frameworks

Frameworks that can be integrated via adapters:

**Characteristics:**

- Adapter-based integration
- Most features supported
- Some translation overhead
- Good compatibility

**Examples:**

- LangChain
- AutoGen
- CrewAI
- Custom enterprise frameworks

### Legacy Frameworks

Older or incompatible frameworks with limited support:

**Characteristics:**

- Basic adapter support only
- Limited feature compatibility
- Significant translation overhead
- Partial testing coverage

**Examples:**

- Deprecated framework versions
- Proprietary closed systems
- Highly customized implementations

## Testing Service Architecture

### Aurite as a Testing Service Provider

Aurite Agents provides testing services to other frameworks:

**Service Model:**

```
Testing Service Architecture:
├── API Gateway
│   ├── Authentication
│   ├── Rate Limiting
│   └── Request Routing
├── Test Orchestrator
│   ├── Framework Detection
│   ├── Adapter Selection
│   └── Test Scheduling
├── Execution Engine
│   ├── Agnostic Tests
│   ├── Specific Tests
│   └── Comparison Tests
└── Result Aggregator
    ├── Standardization
    ├── Scoring
    └── Reporting
```

### Framework-Agnostic API Endpoints

Universal testing endpoints that work across all frameworks:

**Core Endpoints:**

- Component registration
- Test execution
- Result retrieval
- Metric aggregation
- Comparison analysis

**Authentication & Authorization:**

- API key-based access
- Framework-specific credentials
- Rate limiting per framework
- Usage tracking and billing

### Standardized Result Formats

All test results follow Aurite's standard format:

**Result Structure:**

```
TestResult:
├── Metadata
│   ├── Framework
│   ├── Component Type
│   ├── Test Category
│   └── Timestamp
├── Scores
│   ├── Overall Score
│   ├── Category Scores
│   └── Detailed Metrics
├── Issues
│   ├── Failures
│   ├── Warnings
│   └── Recommendations
└── Comparison
    ├── Baseline Comparison
    ├── Cross-Framework Analysis
    └── Historical Trends
```

## Implementation Roadmap

### Phase 1: Foundation (Framework-Agnostic Components)

- Establish LLM testing services
- Implement MCP server testing
- Define standard data formats
- Create base adapter interface

### Phase 2: Hybrid Components (Agent Testing)

- Separate agnostic vs specific agent tests
- Implement agent simulation engine
- Create framework detection system
- Build adapter for one additional framework

### Phase 3: Framework Integration

- Develop adapters for major frameworks
- Implement cross-framework comparison
- Create migration testing tools
- Establish performance baselines

### Phase 4: Service Deployment

- Deploy testing API services
- Implement authentication and billing
- Create developer documentation
- Build testing dashboard

## Benefits and Impact

### For Developers

- Test once, validate everywhere
- Simplified multi-framework development
- Consistent quality standards
- Reduced testing overhead

### For Organizations

- Framework vendor independence
- Simplified compliance validation
- Reduced testing costs
- Accelerated framework adoption

### For the Ecosystem

- Universal quality standards
- Cross-framework interoperability
- Shared security baselines
- Industry-wide best practices

## Related Documentation

- [Testing Hierarchy](testing_hierarchy.md) - Complete testing hierarchy and flow
- [Testing Architecture](testing_architecture.md) - Core architectural principles
- [Test Inheritance](test_inheritance.md) - Test result inheritance patterns
- [Kahuna Testing & Security Framework](../README.md) - Framework overview
