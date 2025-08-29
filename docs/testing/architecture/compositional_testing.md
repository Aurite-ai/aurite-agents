# Compositional Testing

## Overview

Compositional testing is the core principle that enables efficient and thorough validation of AI systems. By recognizing that components build upon each other, we can eliminate redundant testing and focus efforts on integration points.

## The Composition Hierarchy

### Foundation Layer: LLMs and MCP Servers

These components are tested independently as they have no dependencies:

```
LLM Testing                    MCP Server Testing
├── Quality                    ├── Quality
│   ├── Coherence              │   ├── API Compliance
│   ├── Instruction Following  │   ├── Performance
│   └── Format Compliance      │   └── Error Handling
└── Security                   └── Security
    ├── Prompt Injection           ├── Authentication
    ├── Content Safety             ├── Input Validation
    └── Data Leakage               └── Rate Limiting
```

### Integration Layer: Agents

Agents combine LLMs and MCP servers, inheriting their test results:

```
Agent = LLM + MCP Servers + Agent Logic

Agent Testing
├── Inherited from LLM
│   ├── ✓ Language capabilities (assumed valid)
│   └── ✓ Security boundaries (pre-validated)
├── Inherited from MCP
│   ├── ✓ Tool availability (confirmed working)
│   └── ✓ API performance (already measured)
└── New Agent-Specific Tests
    ├── Tool Selection Accuracy
    ├── Multi-turn Coherence
    └── Goal Achievement
```

### Business Layer: Workflows

Workflows orchestrate multiple agents, inheriting all lower-level validations:

```
Workflow = Agent₁ + Agent₂ + ... + Orchestration Logic

Workflow Testing
├── Inherited from All Agents
│   ├── ✓ Individual agent capabilities
│   ├── ✓ Tool functionality
│   └── ✓ Security validations
└── New Workflow-Specific Tests
    ├── Inter-agent Communication
    ├── Business Logic Compliance
    └── End-to-end Performance
```

## Composition Patterns

### Pattern 1: Additive Composition

Each layer adds new tests without repeating lower-level validations:

```python
class AgentTester:
    def test_agent(self, agent_config):
        results = TestResults()

        # Get inherited results (don't re-test)
        results.llm_results = self.get_cached_llm_results(agent_config.llm)
        results.mcp_results = self.get_cached_mcp_results(agent_config.tools)

        # Only test agent-specific behavior
        results.agent_tests = {
            "tool_selection": self.test_tool_selection(agent_config),
            "goal_achievement": self.test_goal_achievement(agent_config),
            "efficiency": self.test_efficiency(agent_config)
        }

        # Aggregate scores
        results.composite_score = self.calculate_composite_score(results)
        return results
```

### Pattern 2: Conditional Composition

Higher-level tests only run if dependencies pass:

```python
def test_workflow(workflow_config):
    # Check all agent dependencies first
    for agent_id in workflow_config.agents:
        agent_result = get_agent_test_result(agent_id)
        if not agent_result.passed:
            return TestResult(
                status="BLOCKED",
                reason=f"Agent {agent_id} failed testing",
                blocking_component=agent_id
            )

    # All dependencies passed, proceed with workflow tests
    return execute_workflow_tests(workflow_config)
```

### Pattern 3: Degraded Composition

Partial failures allow testing with reduced confidence:

```python
def test_with_degradation(component):
    dependency_scores = []
    warnings = []

    for dep in component.dependencies:
        dep_result = get_test_result(dep)
        dependency_scores.append(dep_result.score)

        if dep_result.score < 0.8:
            warnings.append(f"{dep.name} has degraded score: {dep_result.score}")

    # Continue testing but with warnings
    component_result = test_component(component)
    component_result.confidence = min(dependency_scores) * component_result.score
    component_result.warnings = warnings

    return component_result
```

## Test Result Inheritance

### Inheritance Rules

1. **Quality Scores:** Multiply up the chain

   ```
   Agent Quality = LLM Quality × MCP Quality × Agent-Specific Quality
   ```

2. **Security Scores:** Take the minimum (weakest link)

   ```
   Agent Security = min(LLM Security, MCP Security, Agent-Specific Security)
   ```

3. **Performance Metrics:** Sum or take worst case
   ```
   Agent Latency = LLM Latency + MCP Latency + Agent Processing
   ```

### Inheritance Example

```json
{
  "workflow_test_result": {
    "workflow_id": "customer_support_workflow",
    "composite_scores": {
      "quality": 0.92,
      "security": 0.88,
      "performance": 0.95
    },
    "inherited_results": {
      "triage_agent": {
        "quality": 0.94,
        "inherited_from": {
          "gpt-4": { "quality": 0.96 },
          "crm_api": { "quality": 0.98 }
        }
      },
      "response_agent": {
        "quality": 0.9,
        "inherited_from": {
          "claude-3": { "quality": 0.95 },
          "email_api": { "quality": 0.95 }
        }
      }
    },
    "workflow_specific_tests": {
      "escalation_logic": "PASS",
      "sla_compliance": "PASS",
      "data_consistency": "PASS"
    }
  }
}
```

## Optimization Strategies

### 1. Cache and Reuse

```python
class TestResultCache:
    def __init__(self):
        self.cache = {}
        self.ttl = 3600  # 1 hour

    def get_or_test(self, component_id, test_func):
        if component_id in self.cache:
            cached_result, timestamp = self.cache[component_id]
            if time.time() - timestamp < self.ttl:
                return cached_result

        # Not in cache or expired, run test
        result = test_func()
        self.cache[component_id] = (result, time.time())
        return result
```

### 2. Parallel Testing with Dependencies

```python
async def test_with_dependencies(component):
    # Test independent dependencies in parallel
    dep_results = await asyncio.gather(*[
        test_component(dep) for dep in component.independent_deps
    ])

    # Test dependent components sequentially
    for dep in component.sequential_deps:
        dep_result = await test_component(dep)
        if not dep_result.passed:
            return early_termination(dep_result)

    # All dependencies tested, test this component
    return await test_component(component)
```

### 3. Incremental Testing

```python
def incremental_test(component, previous_result):
    # Identify what changed
    changes = detect_changes(component, previous_result.version)

    if changes.only_config:
        # Just rerun configuration tests
        return test_configuration(component)
    elif changes.only_prompts:
        # Rerun prompt-related tests
        return test_prompts(component)
    else:
        # Full retest needed
        return full_test(component)
```

## Composition Benefits

### 1. Efficiency Gains

- **50-70% reduction** in test execution time
- **No redundant validations** of foundation components
- **Parallel execution** where possible

### 2. Clear Attribution

- **Precise failure identification** - know exactly which component failed
- **Impact analysis** - understand downstream effects
- **Targeted fixes** - fix once, benefit everywhere

### 3. Confidence Building

- **Layered validation** provides defense in depth
- **Inherited trust** from validated components
- **Comprehensive coverage** without redundancy

## Real-World Example: Customer Support Workflow

### Component Structure

```
Customer Support Workflow
├── Triage Agent
│   ├── GPT-4 (LLM)
│   └── CRM API (MCP)
├── Response Agent
│   ├── Claude-3 (LLM)
│   └── Email API (MCP)
└── Escalation Agent
    ├── GPT-4 (LLM)
    └── Ticketing API (MCP)
```

### Testing Sequence

1. **Foundation Testing (Parallel)**

   - Test GPT-4: 2 minutes
   - Test Claude-3: 2 minutes
   - Test all APIs: 3 minutes
   - Total: 3 minutes (parallel)

2. **Agent Testing (Parallel, after foundations)**

   - Test Triage Agent: 1 minute (skips LLM/API tests)
   - Test Response Agent: 1 minute
   - Test Escalation Agent: 1 minute
   - Total: 1 minute (parallel)

3. **Workflow Testing (After agents)**
   - Test orchestration: 2 minutes
   - Total: 2 minutes

**Total Time: 6 minutes** (vs 15+ minutes without composition)

## Best Practices

### 1. Design for Composition

- Keep components loosely coupled
- Define clear interfaces
- Document dependencies explicitly

### 2. Maintain Test Independence

- Each layer's tests should be self-contained
- Don't rely on side effects from other tests
- Use mocks/stubs when testing in isolation

### 3. Version Compatibility

- Track component versions in test results
- Invalidate cache on version changes
- Maintain compatibility matrices

### 4. Progressive Enhancement

- Start with foundation tests
- Add integration tests incrementally
- Build confidence layer by layer

## Related Documentation

- [Test Inheritance](test_inheritance.md)
- [Testing Architecture](testing_architecture.md)
- [Component Testing Guides](../components/)
