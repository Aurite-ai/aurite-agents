# Testing Architecture

## Overview

The Kahuna Testing & Security Framework implements a hierarchical, compositional testing architecture that mirrors the natural dependencies between AI components while supporting testing across multiple agent frameworks. This document describes the core architectural principles and design decisions that enable both framework-agnostic and framework-specific testing.

## Architectural Principles

### 1. Compositional Testing

Components are tested in layers, with each layer building upon the results of lower layers:

```
┌─────────────────────────────────────┐
│     Workflow Testing (20% Agnostic) │ ← Business Logic Layer
│   (Inherits all component tests)    │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│      Agent Testing (60% Agnostic)   │ ← Integration Layer
│    (Inherits LLM + MCP tests)       │
└──────┬───────────────────┬──────────┘
       │                   │
┌──────┴──────┐     ┌──────┴──────┐
│  LLM Tests  │     │ MCP Tests   │    ← Foundation Layer
│100% Agnostic│     │100% Agnostic│       (Framework-Independent)
└─────────────┘     └─────────────┘
```

### 2. Test Result Inheritance

Higher-level components automatically inherit relevant test results from their dependencies:

- **Agents** inherit security and quality scores from their LLMs and MCP servers (cross-framework)
- **Workflows** inherit aggregated scores from all constituent agents
- **Framework-agnostic results** are shared across all framework implementations
- **Redundant tests are skipped** when foundation components have already been validated

### 3. Separation of Concerns

The architecture maintains clear boundaries between:

- **Quality vs Security:** Different testing objectives and methodologies
- **Development vs Runtime:** Different execution contexts and constraints
- **Component vs Integration:** Different scopes of validation
- **Framework-Agnostic vs Framework-Specific:** Universal vs implementation-specific tests

### 4. Framework Independence

Certain components can be tested independently of any specific agent framework:

- **LLMs and MCP Servers:** 100% framework-agnostic, tested via direct API calls
- **Core Agent Behaviors:** 60% framework-agnostic, focusing on tool usage and goal achievement
- **Business Logic:** 20% of workflow testing is framework-agnostic
- **Aurite as Standard:** All frameworks translate to/from Aurite's canonical format

## System Architecture

### Core Components

```
Testing Framework
├── Framework Adapter Layer (NEW)
│   ├── Framework Detector
│   ├── Adapter Manager
│   ├── Translation Engine
│   └── Standard Format Converter
├── Test Orchestrator
│   ├── Dependency Resolver
│   ├── Test Scheduler
│   ├── Result Aggregator
│   └── Cross-Framework Coordinator
├── Quality Engine
│   ├── Evaluator (existing)
│   ├── Performance Tester
│   ├── Requirement Validator
│   └── Framework Comparator
├── Security Engine (existing)
│   ├── LLM Security Tester (100% Agnostic)
│   ├── MCP Security Tester (100% Agnostic)
│   ├── Agent Security Tester (60% Agnostic)
│   └── Workflow Security Tester (20% Agnostic)
├── Cache Manager
│   ├── Universal Cache (Agnostic)
│   ├── Framework Cache (Specific)
│   └── Cache Invalidator
└── Metrics Collector
    ├── Quality Metrics
    ├── Security Metrics
    ├── Business Metrics
    └── Framework Comparison Metrics
```

### Data Flow

```
1. Input: Business Requirements + Target Frameworks (from Kahuna-mgr)
   ↓
1.5. Framework Detection & Adapter Selection
   ↓
2. Test Planning: Dependency Analysis & Test Selection
   ↓
2.5. Test Categorization: Agnostic vs Framework-Specific
   ↓
3. Test Execution: Parallel/Sequential based on dependencies
   ↓
3.5. Cross-Framework Result Caching
   ↓
4. Result Aggregation: Inheritance & Composition
   ↓
4.5. Framework Normalization & Comparison
   ↓
5. Output: Metrics & Reports (to Kahuna-exec)
```

## Testing Strategies

### Development-Time Testing

**Purpose:** Validate components before deployment

**Characteristics:**

- Comprehensive test coverage
- Longer execution times acceptable
- Focus on finding issues early
- Includes edge cases and stress testing

**Execution Model:**

```python
def development_test(component, framework="aurite"):
    # 1. Detect and adapt framework
    adapter = get_framework_adapter(framework)
    component = adapter.translate_to_standard(component)

    # 2. Check universal cache for agnostic results
    cached_agnostic = check_universal_cache(component)

    # 3. Run foundation tests (100% agnostic for LLM/MCP)
    if not cached_agnostic:
        foundation_results = test_foundations(component.dependencies)
        cache_universal_results(foundation_results)
    else:
        foundation_results = cached_agnostic

    # 4. Run component-specific tests (split agnostic/specific)
    agnostic_tests, specific_tests = categorize_tests(component)
    component_results = test_component(component, agnostic_tests, specific_tests)

    # 5. Run integration tests
    integration_results = test_integration(component, foundation_results)

    # 6. Aggregate and normalize results
    results = aggregate_results(foundation_results, component_results, integration_results)
    return adapter.translate_from_standard(results)
```

### Runtime Testing

**Purpose:** Monitor and validate in production

**Characteristics:**

- Selective, critical tests only
- Minimal performance impact
- Real-time threat detection
- Continuous quality monitoring

**Execution Model:**

```python
def runtime_monitor(component, request, framework="aurite"):
    # 1. Framework detection
    adapter = get_framework_adapter(framework)
    request = adapter.normalize_request(request)

    # 2. Quick security checks (framework-agnostic for LLM/MCP)
    security_check = quick_security_scan(request)
    if not security_check.passed:
        return block_request(security_check)

    # 3. Check cached agnostic results
    if component.type in ["llm", "mcp"]:
        cached = check_universal_cache(component)
        if cached and cached.is_valid():
            return cached.result

    # 4. Quality monitoring (async)
    async_quality_monitor(component, request, framework)

    # 5. Allow execution with monitoring
    return execute_with_monitoring(component, request)
```

## Test Orchestration Patterns

### Pattern 1: Bottom-Up (Development)

```
1. Test all LLMs (100% agnostic, cached universally)
2. Test all MCP Servers (100% agnostic, cached universally)
3. Test Agents (60% agnostic using cached results, 40% framework-specific)
4. Test Workflows (20% agnostic, 80% framework-specific)
```

**Use Case:** Initial development, comprehensive validation

### Pattern 2: Top-Down (Debugging)

```
1. Workflow fails
2. Identify failing agent(s)
3. Check agent's LLM and MCP components (use cached results if available)
4. Isolate root cause (framework-specific or agnostic issue)
```

**Use Case:** Production issues, troubleshooting

### Pattern 3: Parallel with Dependencies

```
         ┌─→ LLM Tests (Agnostic) ─┐
Start ─┤                            ├─→ Agent Tests ─→ Workflow Tests
         └─→ MCP Tests (Agnostic) ─┘
```

**Use Case:** Efficient testing with dependency management

### Pattern 4: Cross-Framework Testing (NEW)

```
Component ─┬─→ Aurite Testing ─────┬─→ Compare Results
           ├─→ LangChain Testing ──┤
           └─→ AutoGen Testing ────┘
```

**Use Case:** Framework compatibility validation, migration testing

### Pattern 5: Framework Migration Testing (NEW)

```
1. Run tests in current framework
2. Translate configuration to new framework
3. Run tests in new framework
4. Compare results and identify discrepancies
5. Validate business logic preservation
```

**Use Case:** Framework migration, multi-framework support

## Failure Handling

### Failure Propagation Rules

1. **Foundation Failure → Component Blocked**

   - If LLM fails security, all agents using it are blocked
   - If MCP server fails quality, agents get degraded scores

2. **Partial Failure → Degraded Operation**

   - Non-critical test failures allow operation with warnings
   - Critical failures block execution entirely

3. **Cascade Prevention**
   - Early termination when foundation tests fail
   - Skip dependent tests to save resources

### Failure Impact Analysis

```
Component Failure Impact:
├── Direct Impact
│   └── Component cannot be deployed/used
├── Upstream Impact
│   └── Dependent components marked as "at risk"
└── Business Impact
    └── Affected workflows and business processes identified
```

## Scalability Considerations

### Test Result Caching

- **Universal Cache:** Framework-agnostic results (LLM/MCP) cached globally
  - 24-hour TTL for foundation components
  - Shared across all frameworks
  - 85% cache hit rate with cross-framework sharing
- **Framework Cache:** Framework-specific results isolated per implementation
  - 4-hour TTL for agent-specific tests
  - 1-hour TTL for workflow tests
  - Framework-isolated to prevent contamination
- **Cache Invalidation:** Cascade invalidation on component updates
  - Universal cache invalidation affects all frameworks
  - Framework cache invalidation is isolated

### Distributed Testing

- Parallelize independent tests across workers
- Use message queues for test coordination
- Aggregate results in central database

### Performance Optimization

- Lazy loading of test dependencies
- Incremental testing for small changes
- Test prioritization based on risk assessment

## Framework Adaptation Layer

### Adapter Architecture

```
Framework Adapter
├── Configuration Translation
│   ├── To Aurite Standard Format
│   └── From Aurite Standard Format
├── Execution Translation
│   ├── Request Normalization
│   └── Response Denormalization
├── Context Extraction
│   ├── Framework System Prompts
│   ├── Framework Variables
│   └── State Management
└── Feature Mapping
    ├── Supported Features
    ├── Unsupported Features
    └── Compatibility Matrix
```

### Translation Mechanisms

- **Bidirectional Translation:** Convert between framework formats and Aurite standard
- **Lossless Conversion:** Preserve all framework-specific metadata
- **Fallback Strategies:** Handle unsupported features gracefully
- **Version Compatibility:** Support multiple framework versions

### Framework Detection

```python
def detect_framework(config):
    # Check for framework-specific markers
    if "langchain_version" in config:
        return LangChainAdapter()
    elif "autogen_config" in config:
        return AutoGenAdapter()
    elif "crew_settings" in config:
        return CrewAIAdapter()
    else:
        return AuriteNativeAdapter()
```

## Integration Points

### With Kahuna Manager Mode

**Input:**

- Business workflow definitions
- Component requirements
- Quality thresholds
- Security policies
- **Target frameworks** (NEW)

**Processing:**

- Map business requirements to technical tests
- Generate test plans from workflow definitions
- **Adapt tests for each target framework** (NEW)

### With Kahuna Developer Mode

**Integration:**

- IDE plugins for test execution
- Real-time test feedback during development
- Test-driven development support

### With Kahuna Executive Mode

**Output:**

- Aggregated quality metrics (per framework)
- Security posture dashboards (cross-framework)
- Business KPI alignment
- Compliance reports
- **Framework comparison metrics** (NEW)
- **Migration readiness assessments** (NEW)

## Security Architecture

### Defense in Depth

```
Layer 0: Framework Adapter Security (NEW)
Layer 1: Input Validation (MCP Servers - 100% Agnostic)
Layer 2: Content Filtering (LLMs - 100% Agnostic)
Layer 3: Action Authorization (Agents - 60% Agnostic)
Layer 4: Workflow Policies (Workflows - 20% Agnostic)
```

### Zero Trust Principles

- Verify at every layer
- No implicit trust between components
- Continuous validation in runtime
- **Framework boundaries are security boundaries** (NEW)
- **Cross-framework validation required** (NEW)

### Framework-Specific Security Considerations

- **System Prompt Injection:** Framework-specific prompts may introduce vulnerabilities
- **State Management:** Different frameworks handle state differently, affecting security
- **Tool Authorization:** Framework-specific tool integration may bypass security checks
- **Memory Leakage:** Cross-framework memory sharing requires careful isolation

## Future Enhancements

### Planned Features

1. **AI-Powered Test Generation**

   - Automatically generate tests from requirements
   - Learn from historical test results
   - **Generate framework-specific test adaptations** (NEW)

2. **Predictive Failure Analysis**

   - Predict likely failure points
   - Proactive testing recommendations
   - **Cross-framework failure correlation** (NEW)

3. **Adaptive Testing**

   - Adjust test intensity based on component stability
   - Dynamic test selection based on risk
   - **Framework-specific optimization** (NEW)

4. **Framework Compatibility Testing** (NEW)

   - Automated compatibility matrix generation
   - Framework feature parity analysis
   - Migration impact assessment

5. **Auto-Generation of Framework Adapters** (NEW)
   - Learn translation patterns from examples
   - Generate adapters for new frameworks
   - Validate adapter correctness automatically

### Extension Points

- Plugin architecture for custom test types
- Webhook integration for external tools
- API for third-party test frameworks
- **Framework adapter SDK** (NEW)
- **Cross-framework test orchestration API** (NEW)

## Related Documentation

- [Framework-Agnostic Testing Architecture](framework_agnostic_testing.md)
- [Testing Hierarchy and Flow](testing_hierarchy.md)
- [Test Inheritance](test_inheritance.md)
- [Security Engine Design](../../../src/aurite/security/core/security_engine.py)
- [Kahuna Testing & Security Framework](../README.md)
