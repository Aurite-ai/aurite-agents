# Test Inheritance

## Overview

Test inheritance is the mechanism by which higher-level components automatically benefit from the validation of their dependencies, both within a single framework and across multiple agent frameworks. This document details how test results flow through the component hierarchy and how to implement efficient inheritance patterns that maximize test reuse through framework-agnostic validation.

## Inheritance Principles

### 1. Once Tested, Always Trusted

When a foundation component passes testing, all components using it can trust those results without retesting. For framework-agnostic components (LLMs and MCP Servers), this trust extends across ALL frameworks:

```
LLM passes prompt injection test at 10:00 AM (via Aurite framework)
  ↓
Agent A using this LLM at 10:30 AM (LangChain) → Inherits "PASS"
Agent B using this LLM at 10:45 AM (AutoGen) → Inherits "PASS"
Agent C using this LLM at 11:00 AM (Aurite) → Inherits "PASS"
  ↓
No need to retest prompt injection for any agent in any framework
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
    LLM Security (100% agnostic),
    MCP Security (100% agnostic),
    Agent-Specific Security (40% framework-specific)
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

### 4. Cross-Framework Inheritance

Framework-agnostic test results are inherited across all framework implementations:

```
Component Agnostic % → Cross-Framework Inheritance
LLM: 100% → All results shared across frameworks
MCP: 100% → All results shared across frameworks
Agent: 60% → Core behavior results shared
Workflow: 20% → Business logic results shared
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

    # Framework context
    framework: str  # Framework that ran the test
    is_agnostic: bool  # Whether results are framework-agnostic
    cross_framework_validity: bool  # Can be shared across frameworks

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
    framework_confidence: Dict[str, float]  # Confidence per framework

@dataclass
class InheritedResult:
    """Represents an inherited test result"""
    source_component: str
    source_version: str
    source_framework: str  # Framework that originally ran the test
    original_timestamp: datetime
    test_name: str
    score: float
    status: str
    ttl_remaining: int  # Time-to-live in seconds
    is_universal: bool  # True for framework-agnostic results
    inheritance_type: str  # "direct", "cross-framework", "transformed"

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

Simple pass-through of test results from dependency to dependent within the same framework:

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

### Pattern 4: Universal Inheritance

Framework-agnostic results that propagate across all frameworks:

```python
class UniversalInheritance:
    def inherit_universal(self, component, dependency_results, target_framework):
        inherited = {}

        for dep_id, dep_result in dependency_results.items():
            # Check if results are framework-agnostic
            if dep_result.is_agnostic or dep_result.component_type in ["llm", "mcp"]:
                for test_name, test_score in dep_result.direct_tests.items():
                    inherited[f"{dep_id}.{test_name}"] = InheritedResult(
                        source_component=dep_id,
                        source_version=dep_result.version,
                        source_framework=dep_result.framework,
                        original_timestamp=dep_result.timestamp,
                        test_name=test_name,
                        score=test_score.value,
                        status=test_score.status,
                        ttl_remaining=self.calculate_universal_ttl(dep_result),
                        is_universal=True,
                        inheritance_type="cross-framework"
                    )

        return inherited
```

### Pattern 5: Framework Boundary Inheritance

Handle inheritance when components use different frameworks:

```python
class FrameworkBoundaryInheritance:
    def inherit_across_frameworks(self, component, dependency_results):
        inherited = {}
        adapter = self.get_framework_adapter(component.framework)

        for dep_id, dep_result in dependency_results.items():
            # Determine what can be inherited
            if dep_result.framework != component.framework:
                # Only inherit agnostic results across framework boundaries
                agnostic_percentage = self.get_agnostic_percentage(dep_result.component_type)

                for test_name, test_score in dep_result.direct_tests.items():
                    if self.is_agnostic_test(test_name, dep_result.component_type):
                        # Translate and inherit
                        translated_result = adapter.translate_result(test_score)
                        inherited[f"{dep_id}.{test_name}"] = translated_result
            else:
                # Same framework - inherit everything
                inherited.update(self.inherit_direct(dep_id, dep_result))

        return inherited
```

## Inheritance Lifecycle

### 1. Test Execution Phase

```python
async def execute_with_inheritance(component, framework="aurite"):
    # Step 1: Check universal cache for agnostic results
    universal_results = await check_universal_cache(component.dependencies)

    # Step 2: Gather framework-specific dependency results
    dep_results = await gather_dependency_results(component.dependencies, framework)

    # Step 3: Merge universal and framework-specific results
    all_results = merge_results(universal_results, dep_results)

    # Step 4: Check if dependencies passed
    if not all_dependencies_passed(all_results):
        return blocked_result(component, all_results)

    # Step 5: Inherit applicable results (both agnostic and specific)
    inherited = inherit_results(component, all_results, framework)

    # Step 6: Run component-specific tests
    agnostic_tests, specific_tests = categorize_tests(component)
    direct_tests = await run_direct_tests(component, agnostic_tests, specific_tests)

    # Step 7: Combine and cache results
    final_results = combine_results(inherited, direct_tests)
    cache_results(final_results, framework)

    return final_results
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
        self.universal_cache = {}  # Framework-agnostic results
        self.framework_cache = {}  # Framework-specific results
        self.version_map = {}

    def store_result(self, component_id, result, framework="aurite"):
        """Store result with framework context"""
        cache_entry = {
            "result": result,
            "timestamp": datetime.now(),
            "version": result.version,
            "framework": framework,
            "inheritable_until": self.calculate_ttl(result)
        }

        # Store in appropriate cache
        if result.is_agnostic or result.component_type in ["llm", "mcp"]:
            self.universal_cache[component_id] = cache_entry
            cache_entry["inheritable_until"] = datetime.now() + timedelta(hours=24)
        else:
            if framework not in self.framework_cache:
                self.framework_cache[framework] = {}
            self.framework_cache[framework][component_id] = cache_entry

        # Track version for invalidation
        self.version_map[component_id] = result.version

    def get_inheritable_result(self, component_id, framework="aurite"):
        """Get result from universal or framework cache"""
        # Check universal cache first
        if component_id in self.universal_cache:
            cached = self.universal_cache[component_id]
            if self.is_valid_cache(cached):
                return cached["result"]

        # Check framework-specific cache
        if framework in self.framework_cache:
            if component_id in self.framework_cache[framework]:
                cached = self.framework_cache[framework][component_id]
                if self.is_valid_cache(cached):
                    return cached["result"]

        return None

    def is_valid_cache(self, cached):
        """Check if cached result is still valid"""
        if datetime.now() > cached["inheritable_until"]:
            return False
        if self.version_map.get(cached["result"].component_id) != cached["version"]:
            return False
        return True

    def invalidate_cascade(self, component_id, framework=None):
        """Invalidate component and all dependents"""
        # Remove from universal cache
        if component_id in self.universal_cache:
            del self.universal_cache[component_id]
            # Universal invalidation affects all frameworks
            for fw in self.framework_cache.values():
                if component_id in fw:
                    del fw[component_id]

        # Remove from specific framework cache
        elif framework and framework in self.framework_cache:
            if component_id in self.framework_cache[framework]:
                del self.framework_cache[framework][component_id]

        # Find and invalidate dependents
        dependents = self.find_dependents(component_id)
        for dep in dependents:
            self.invalidate_cascade(dep, framework)

    def calculate_ttl(self, result):
        """Calculate TTL based on component type and framework scope"""
        ttl_map = {
            "llm": timedelta(hours=24),      # 100% agnostic
            "mcp": timedelta(hours=24),      # 100% agnostic
            "agent": timedelta(hours=12),    # 60% agnostic
            "workflow": timedelta(hours=1)   # 20% agnostic
        }
        return datetime.now() + ttl_map.get(result.component_type, timedelta(hours=4))
```

## Inheritance Rules by Component Type

### LLM Inheritance Rules

LLMs are foundation components and don't inherit:

```python
LLM_INHERITANCE = {
    "inherits_from": [],
    "provides_to": ["agent"],
    "framework_agnostic": True,  # 100% agnostic
    "cross_framework_inheritance": 1.0,  # All results shared
    "inheritable_tests": [
        "prompt_injection_resistance",
        "content_safety_score",
        "hallucination_rate",
        "instruction_following_accuracy",
        "output_format_compliance"
    ],
    "cache_ttl": 24  # Hours - longer for agnostic components
}
```

### MCP Server Inheritance Rules

MCP Servers are foundation components and don't inherit:

```python
MCP_INHERITANCE = {
    "inherits_from": [],
    "provides_to": ["agent"],
    "framework_agnostic": True,  # 100% agnostic
    "cross_framework_inheritance": 1.0,  # All results shared
    "inheritable_tests": [
        "api_availability",
        "response_time_p95",
        "error_rate",
        "authentication_validity",
        "rate_limit_compliance"
    ],
    "cache_ttl": 24  # Hours - longer for agnostic components
}
```

### Agent Inheritance Rules

Agents inherit from both LLMs and MCP Servers:

```python
AGENT_INHERITANCE = {
    "inherits_from": ["llm", "mcp_server"],
    "provides_to": ["workflow"],
    "framework_agnostic": False,  # Hybrid
    "cross_framework_inheritance": 0.6,  # 60% agnostic
    "inheritable_tests": {
        "agnostic": [  # Cross-framework tests
            "goal_achievement_rate",
            "tool_selection_accuracy"
        ],
        "specific": [  # Framework-specific tests
            "multi_turn_coherence",
            "resource_efficiency",
            "security_compliance"
        ]
    },
    "inheritance_weights": {
        "llm": 0.4,
        "mcp_server": 0.3,
        "agent_specific": 0.3
    },
    "cache_ttl": {
        "agnostic": 12,  # Hours for agnostic results
        "specific": 4    # Hours for specific results
    }
}
```

### Workflow Inheritance Rules

Workflows inherit from all constituent agents:

```python
WORKFLOW_INHERITANCE = {
    "inherits_from": ["agent"],
    "provides_to": [],
    "framework_agnostic": False,  # Mostly specific
    "cross_framework_inheritance": 0.2,  # 20% agnostic
    "inheritable_tests": {
        "agnostic": [  # Cross-framework tests
            "business_logic_compliance",
            "end_to_end_success_rate"
        ],
        "specific": [  # Framework-specific tests
            "sla_adherence",
            "data_consistency",
            "audit_completeness"
        ]
    },
    "inheritance_weights": "dynamic",  # Based on agent importance
    "cache_ttl": {
        "agnostic": 4,   # Hours for agnostic results
        "specific": 1    # Hour for specific results
    }
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

## Framework Adaptation in Inheritance

### Cross-Framework Confidence Scoring

```python
def calculate_cross_framework_confidence(inherited_result, target_framework):
    """Calculate confidence when inheriting across frameworks"""
    base_confidence = inherited_result.confidence_level

    # Adjust confidence based on framework compatibility
    if inherited_result.is_universal:
        # Universal results maintain high confidence
        return base_confidence * 0.95
    elif inherited_result.source_framework == target_framework:
        # Same framework maintains full confidence
        return base_confidence
    else:
        # Cross-framework inheritance reduces confidence
        agnostic_ratio = get_agnostic_ratio(inherited_result.component_type)
        return base_confidence * agnostic_ratio * 0.9
```

### Framework Migration Inheritance

```python
def migrate_inheritance(component, old_framework, new_framework):
    """Handle inheritance during framework migration"""
    migration_results = {}

    # Get existing results from old framework
    old_results = get_cached_results(component, old_framework)

    for test_name, result in old_results.items():
        if is_agnostic_test(test_name, component.type):
            # Agnostic tests transfer directly
            migration_results[test_name] = result
            migration_results[test_name].framework = new_framework
        else:
            # Framework-specific tests need re-execution
            migration_results[test_name] = {
                "status": "pending_retest",
                "reason": "framework_migration",
                "old_result": result
            }

    return migration_results
```

## Best Practices

### 1. Clear Inheritance Boundaries

- Document what each component inherits
- Specify which tests are inheritable
- Define inheritance weights explicitly
- **Distinguish framework-agnostic from framework-specific tests**

### 2. Version Management

- Track component versions in test results
- Invalidate inheritance on version changes
- Maintain version compatibility matrix
- **Track framework versions for cross-framework compatibility**

### 3. Time-Based Validity

- Set appropriate TTL for inherited results
- Refresh inheritance periodically
- Alert on stale inheritance
- **Use longer TTLs for framework-agnostic results**

### 4. Audit Trail

- Log all inheritance decisions
- Track inheritance chain
- Enable inheritance debugging
- **Record cross-framework inheritance paths**

### 5. Cross-Framework Validation

- **Validate inherited results when crossing framework boundaries**
- **Maintain confidence scores for cross-framework inheritance**
- **Document framework-specific adaptations**
- **Test inheritance integrity across frameworks**

### 6. Universal Cache Management

- **Prioritize universal cache for agnostic components**
- **Implement cache warming for frequently used components**
- **Monitor cache hit rates across frameworks**
- **Optimize TTLs based on component stability**

## Example: Complete Inheritance Flow

```python
# 1. LLM Testing (Foundation - 100% Agnostic)
llm_result = {
    "component_id": "gpt-4",
    "framework": "aurite",  # Tested via Aurite
    "is_agnostic": True,
    "cross_framework_validity": True,
    "direct_tests": {
        "prompt_injection": 0.95,
        "content_safety": 0.98
    }
}

# 2. MCP Testing (Foundation - 100% Agnostic)
mcp_result = {
    "component_id": "crm_api",
    "framework": "langchain",  # Tested via LangChain
    "is_agnostic": True,
    "cross_framework_validity": True,
    "direct_tests": {
        "availability": 0.99,
        "performance": 0.94
    }
}

# 3. Agent Testing (Inherits cross-framework - 60% Agnostic)
agent_result = {
    "component_id": "support_agent",
    "framework": "autogen",  # Running in AutoGen
    "is_agnostic": False,  # Hybrid component
    "cross_framework_validity": 0.6,  # 60% shareable
    "inherited_results": {
        # Universal inheritance from different frameworks
        "gpt-4.prompt_injection": {
            "score": 0.95,
            "source_framework": "aurite",
            "is_universal": True
        },
        "gpt-4.content_safety": {
            "score": 0.98,
            "source_framework": "aurite",
            "is_universal": True
        },
        "crm_api.availability": {
            "score": 0.99,
            "source_framework": "langchain",
            "is_universal": True
        },
        "crm_api.performance": {
            "score": 0.94,
            "source_framework": "langchain",
            "is_universal": True
        }
    },
    "direct_tests": {
        "tool_selection": 0.92,  # Agnostic test
        "goal_achievement": 0.89,  # Agnostic test
        "memory_management": 0.87  # Framework-specific
    },
    "composite_scores": {
        "quality": 0.91,
        "security": 0.95,
        "framework_confidence": {
            "aurite": 0.95,
            "langchain": 0.93,
            "autogen": 1.0
        }
    }
}

# 4. Workflow Testing (Mixed framework - 20% Agnostic)
workflow_result = {
    "component_id": "support_workflow",
    "framework": "aurite",  # Workflow in Aurite
    "is_agnostic": False,
    "cross_framework_validity": 0.2,  # 20% shareable
    "inherited_results": {
        # Inheriting from AutoGen agent
        "support_agent.quality": {
            "score": 0.91,
            "source_framework": "autogen",
            "is_universal": False,
            "confidence": 0.85  # Reduced confidence across frameworks
        },
        "support_agent.security": {
            "score": 0.95,
            "source_framework": "autogen",
            "is_universal": False,
            "confidence": 0.90
        }
    },
    "direct_tests": {
        "business_logic": 0.96,  # Agnostic
        "end_to_end": 0.93,  # Agnostic
        "orchestration": 0.91  # Framework-specific
    },
    "composite_scores": {
        "quality": 0.92,
        "security": 0.95,
        "business_compliance": 0.94,
        "cross_framework_confidence": 0.88
    }
}
```

## Related Documentation

- [Framework-Agnostic Testing Architecture](framework_agnostic_testing.md)
- [Testing Architecture](testing_architecture.md)
- [Testing Hierarchy and Flow](testing_hierarchy.md)
- [Component Testing Guides](../components/)
- [Kahuna Testing & Security Framework](../README.md)
