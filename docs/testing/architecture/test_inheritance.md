# Test Inheritance

## Overview

Test inheritance is the mechanism by which higher-level components automatically benefit from the validation of their dependencies. This document details how test results flow through the component hierarchy and how to implement efficient inheritance patterns.

## Inheritance Principles

### 1. Once Tested, Always Trusted

When a foundation component passes testing, all components using it can trust those results without retesting:

```
LLM passes prompt injection test at 10:00 AM
  ↓
Agent A using this LLM at 10:30 AM → Inherits "PASS" for prompt injection
Agent B using this LLM at 10:45 AM → Inherits "PASS" for prompt injection
  ↓
No need to retest prompt injection for either agent
```

### 2. Weakest Link Security

Security scores propagate using the minimum value principle:

```
Workflow Security Score = MIN(
    Agent1 Security,
    Agent2 Security,
    Workflow-Specific Security
)

Where each Agent Security = MIN(
    LLM Security,
    MCP Security,
    Agent-Specific Security
)
```

### 3. Composite Quality

Quality scores combine multiplicatively to reflect cumulative degradation:

```
Workflow Quality =
    (Agent1 Quality × Weight1) +
    (Agent2 Quality × Weight2) +
    (Workflow Quality × Weight3)

Where weights sum to 1.0
```

## Inheritance Data Model

### Test Result Structure

```python
@dataclass
class TestResult:
    """Base test result with inheritance support"""
    component_id: str
    component_type: str
    timestamp: datetime
    version: str

    # Direct test results
    direct_tests: Dict[str, TestScore]

    # Inherited results
    inherited_results: Dict[str, InheritedResult]

    # Composite scores
    composite_scores: CompositeScores

    # Metadata
    dependencies: List[ComponentDependency]
    inheritance_chain: List[str]
    confidence_level: float

@dataclass
class InheritedResult:
    """Represents an inherited test result"""
    source_component: str
    source_version: str
    original_timestamp: datetime
    test_name: str
    score: float
    status: str
    ttl_remaining: int  # Time-to-live in seconds

@dataclass
class CompositeScores:
    """Aggregated scores with inheritance"""
    quality: float
    security: float
    performance: float
    reliability: float

    # Breakdown by source
    quality_breakdown: Dict[str, float]
    security_breakdown: Dict[str, float]
```

## Inheritance Patterns

### Pattern 1: Direct Inheritance

Simple pass-through of test results from dependency to dependent:

```python
class DirectInheritance:
    def inherit_results(self, component, dependency_results):
        inherited = {}

        for dep_id, dep_result in dependency_results.items():
            # Direct inheritance of applicable tests
            for test_name, test_score in dep_result.direct_tests.items():
                if self.is_inheritable(test_name, component.type):
                    inherited[f"{dep_id}.{test_name}"] = InheritedResult(
                        source_component=dep_id,
                        source_version=dep_result.version,
                        original_timestamp=dep_result.timestamp,
                        test_name=test_name,
                        score=test_score.value,
                        status=test_score.status,
                        ttl_remaining=self.calculate_ttl(dep_result)
                    )

        return inherited
```

### Pattern 2: Filtered Inheritance

Selective inheritance based on relevance:

```python
class FilteredInheritance:
    # Define what each component type inherits
    INHERITANCE_RULES = {
        "agent": {
            "from_llm": [
                "prompt_injection_resistance",
                "content_safety",
                "output_format_compliance"
            ],
            "from_mcp": [
                "api_availability",
                "authentication_status",
                "rate_limit_compliance"
            ]
        },
        "workflow": {
            "from_agent": [
                "goal_achievement_rate",
                "tool_usage_efficiency",
                "security_compliance"
            ]
        }
    }

    def inherit_filtered(self, component_type, source_type, test_results):
        rules = self.INHERITANCE_RULES.get(component_type, {})
        inheritable_tests = rules.get(f"from_{source_type}", [])

        return {
            test: result
            for test, result in test_results.items()
            if test in inheritable_tests
        }
```

### Pattern 3: Transformed Inheritance

Modify inherited scores based on context:

```python
class TransformedInheritance:
    def inherit_with_transformation(self, component, dependency_results):
        inherited = {}

        for dep_id, dep_result in dependency_results.items():
            # Apply transformation based on dependency importance
            importance = self.get_dependency_importance(component, dep_id)

            for test_name, score in dep_result.items():
                # Transform score based on importance
                transformed_score = self.transform_score(
                    score,
                    importance,
                    component.risk_profile
                )

                inherited[f"{dep_id}.{test_name}"] = transformed_score

        return inherited

    def transform_score(self, original_score, importance, risk_profile):
        if risk_profile == "high":
            # More conservative for high-risk components
            return original_score * 0.9 * importance
        elif risk_profile == "low":
            # More lenient for low-risk components
            return min(1.0, original_score * 1.1 * importance)
        else:
            return original_score * importance
```

## Inheritance Lifecycle

### 1. Test Execution Phase

```python
async def execute_with_inheritance(component):
    # Step 1: Gather dependency results
    dep_results = await gather_dependency_results(component.dependencies)

    # Step 2: Check if dependencies passed
    if not all_dependencies_passed(dep_results):
        return blocked_result(component, dep_results)

    # Step 3: Inherit applicable results
    inherited = inherit_results(component, dep_results)

    # Step 4: Run component-specific tests
    direct_tests = await run_direct_tests(component)

    # Step 5: Combine results
    return combine_results(inherited, direct_tests)
```

### 2. Result Aggregation Phase

```python
def aggregate_inherited_results(inherited_results, direct_results):
    aggregated = {
        "quality": calculate_quality_score(inherited_results, direct_results),
        "security": calculate_security_score(inherited_results, direct_results),
        "performance": calculate_performance_score(inherited_results, direct_results)
    }

    # Add confidence based on inheritance freshness
    aggregated["confidence"] = calculate_confidence(inherited_results)

    return aggregated

def calculate_confidence(inherited_results):
    """Calculate confidence based on age and version of inherited results"""
    confidence = 1.0

    for result in inherited_results.values():
        age_factor = 1.0 - (time_since(result.original_timestamp) / MAX_AGE)
        version_factor = 1.0 if result.source_version == CURRENT_VERSION else 0.8

        confidence *= (age_factor * version_factor)

    return max(0.5, confidence)  # Minimum 50% confidence
```

### 3. Cache Management Phase

```python
class InheritanceCache:
    def __init__(self):
        self.cache = {}
        self.version_map = {}

    def store_result(self, component_id, result):
        """Store result with version tracking"""
        self.cache[component_id] = {
            "result": result,
            "timestamp": datetime.now(),
            "version": result.version,
            "inheritable_until": datetime.now() + timedelta(hours=1)
        }

        # Track version for invalidation
        self.version_map[component_id] = result.version

    def get_inheritable_result(self, component_id):
        """Get result if still valid for inheritance"""
        if component_id not in self.cache:
            return None

        cached = self.cache[component_id]

        # Check if still inheritable
        if datetime.now() > cached["inheritable_until"]:
            return None

        # Check version validity
        if self.version_map[component_id] != cached["version"]:
            return None

        return cached["result"]

    def invalidate_cascade(self, component_id):
        """Invalidate component and all dependents"""
        # Remove from cache
        if component_id in self.cache:
            del self.cache[component_id]

        # Find and invalidate dependents
        dependents = self.find_dependents(component_id)
        for dep in dependents:
            self.invalidate_cascade(dep)
```

## Inheritance Rules by Component Type

### LLM Inheritance Rules

LLMs are foundation components and don't inherit:

```python
LLM_INHERITANCE = {
    "inherits_from": [],
    "provides_to": ["agent"],
    "inheritable_tests": [
        "prompt_injection_resistance",
        "content_safety_score",
        "hallucination_rate",
        "instruction_following_accuracy",
        "output_format_compliance"
    ]
}
```

### MCP Server Inheritance Rules

MCP Servers are foundation components and don't inherit:

```python
MCP_INHERITANCE = {
    "inherits_from": [],
    "provides_to": ["agent"],
    "inheritable_tests": [
        "api_availability",
        "response_time_p95",
        "error_rate",
        "authentication_validity",
        "rate_limit_compliance"
    ]
}
```

### Agent Inheritance Rules

Agents inherit from both LLMs and MCP Servers:

```python
AGENT_INHERITANCE = {
    "inherits_from": ["llm", "mcp_server"],
    "provides_to": ["workflow"],
    "inheritable_tests": [
        "goal_achievement_rate",
        "tool_selection_accuracy",
        "multi_turn_coherence",
        "resource_efficiency",
        "security_compliance"
    ],
    "inheritance_weights": {
        "llm": 0.4,
        "mcp_server": 0.3,
        "agent_specific": 0.3
    }
}
```

### Workflow Inheritance Rules

Workflows inherit from all constituent agents:

```python
WORKFLOW_INHERITANCE = {
    "inherits_from": ["agent"],
    "provides_to": [],
    "inheritable_tests": [
        "end_to_end_success_rate",
        "business_logic_compliance",
        "sla_adherence",
        "data_consistency",
        "audit_completeness"
    ],
    "inheritance_weights": "dynamic"  # Based on agent importance in workflow
}
```

## Inheritance Validation

### Ensuring Inheritance Integrity

```python
class InheritanceValidator:
    def validate_inheritance_chain(self, component_result):
        """Validate that inheritance chain is complete and valid"""
        issues = []

        # Check all required dependencies are present
        for dep in component_result.dependencies:
            if dep.id not in component_result.inherited_results:
                issues.append(f"Missing inheritance from {dep.id}")

        # Check inheritance freshness
        for inherited in component_result.inherited_results.values():
            if inherited.ttl_remaining <= 0:
                issues.append(f"Expired inheritance from {inherited.source_component}")

        # Check version compatibility
        for inherited in component_result.inherited_results.values():
            if not self.is_version_compatible(inherited.source_version):
                issues.append(f"Incompatible version from {inherited.source_component}")

        return issues
```

## Best Practices

### 1. Clear Inheritance Boundaries

- Document what each component inherits
- Specify which tests are inheritable
- Define inheritance weights explicitly

### 2. Version Management

- Track component versions in test results
- Invalidate inheritance on version changes
- Maintain version compatibility matrix

### 3. Time-Based Validity

- Set appropriate TTL for inherited results
- Refresh inheritance periodically
- Alert on stale inheritance

### 4. Audit Trail

- Log all inheritance decisions
- Track inheritance chain
- Enable inheritance debugging

## Example: Complete Inheritance Flow

```python
# 1. LLM Testing (Foundation)
llm_result = {
    "component_id": "gpt-4",
    "direct_tests": {
        "prompt_injection": 0.95,
        "content_safety": 0.98
    }
}

# 2. MCP Testing (Foundation)
mcp_result = {
    "component_id": "crm_api",
    "direct_tests": {
        "availability": 0.99,
        "performance": 0.94
    }
}

# 3. Agent Testing (Inherits from LLM + MCP)
agent_result = {
    "component_id": "support_agent",
    "inherited_results": {
        "gpt-4.prompt_injection": 0.95,
        "gpt-4.content_safety": 0.98,
        "crm_api.availability": 0.99,
        "crm_api.performance": 0.94
    },
    "direct_tests": {
        "tool_selection": 0.92,
        "goal_achievement": 0.89
    },
    "composite_scores": {
        "quality": 0.91,  # Weighted combination
        "security": 0.95  # Minimum of all security scores
    }
}

# 4. Workflow Testing (Inherits from Agent)
workflow_result = {
    "component_id": "support_workflow",
    "inherited_results": {
        "support_agent.quality": 0.91,
        "support_agent.security": 0.95
    },
    "direct_tests": {
        "business_logic": 0.96,
        "end_to_end": 0.93
    },
    "composite_scores": {
        "quality": 0.92,
        "security": 0.95,
        "business_compliance": 0.94
    }
}
```

## Related Documentation

- [Compositional Testing](compositional_testing.md)
- [Testing Architecture](testing_architecture.md)
- [Component Testing Guides](../components/)
