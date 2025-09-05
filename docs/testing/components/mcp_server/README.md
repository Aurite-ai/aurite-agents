# MCP Server Testing

## Overview

MCP (Model Context Protocol) servers are foundation components in the Kahuna Testing & Security Framework's compositional hierarchy. As 100% framework-agnostic components, MCP servers provide tools and resources through standardized interfaces that operate independently of any specific agent framework. This document describes how MCP servers are tested and how their test results enable efficient testing of higher-level components through inheritance.

### Position in Testing Hierarchy

```
Foundation Layer (100% Framework-Agnostic)
├── LLMs ─────────┐
│                 ├─→ Agents (inherit results) ─→ Workflows
└── MCP Servers ──┘
    ↑
    Our focus
```

MCP servers, alongside LLMs, form the foundation layer of our testing architecture. They:

- Have no dependencies on other components
- Are tested directly via the MCP protocol
- Provide inheritable test results to all agent frameworks
- Enable 85% reduction in redundant testing through result inheritance

## Architectural Principles

### 1. Framework Independence

MCP servers are completely framework-agnostic because they:

- Expose tools through the standardized MCP protocol
- Process requests and responses in a uniform format
- Operate as stateless services independent of calling context
- Maintain consistent behavior regardless of the agent framework

### 2. Direct API Testing

All MCP server tests bypass framework layers entirely:

```python
# Direct MCP protocol testing - no framework mediation
mcp_client = MCPClient(server_url)
response = mcp_client.call_tool("get_weather", {"city": "San Francisco"})
# Validate response directly
```

### 3. Test Result Inheritance

MCP test results are structured for maximum reusability:

- **Validated tool calls** become test patterns for agents
- **Performance baselines** set expectations for agent testing
- **Security validations** eliminate redundant security testing
- **Tool catalogs** inform agent tool selection tests

## Test Categories

### Quality Testing (60% of tests)

Quality tests ensure MCP servers meet functional and performance requirements:

| Test Type           | Description                   | Inheritable Data                 |
| ------------------- | ----------------------------- | -------------------------------- |
| **Tool Discovery**  | Validate tool enumeration     | Available tools list             |
| **Tool Invocation** | Test successful execution     | Request/response patterns        |
| **Error Handling**  | Verify proper error responses | Error scenarios                  |
| **Performance**     | Measure response times        | Baseline metrics (p50, p95, p99) |
| **API Compliance**  | Check MCP protocol adherence  | Protocol version compatibility   |

### Security Testing (40% of tests)

Security tests validate protection against threats and compliance:

| Test Type            | Description                    | Inheritable Data          |
| -------------------- | ------------------------------ | ------------------------- |
| **Authentication**   | Verify access controls         | Auth mechanisms validated |
| **Input Validation** | Test injection resistance      | Safe input patterns       |
| **Rate Limiting**    | Check request throttling       | Rate limit thresholds     |
| **Data Exposure**    | Prevent information leakage    | Security clearances       |
| **Authorization**    | Validate permission boundaries | Allowed operations        |

## Test Execution Model

### Development-Time Testing

Comprehensive validation before deployment:

```python
def test_mcp_server_development(server_config):
    """
    Full MCP server validation following architecture patterns
    """
    # 1. No dependency checking needed (foundation component)

    # 2. Run quality tests
    quality_results = {
        "tool_discovery": test_tool_discovery(server_config),
        "tool_invocation": test_tool_invocation(server_config),
        "error_handling": test_error_handling(server_config),
        "performance": test_performance_benchmarks(server_config),
        "api_compliance": test_mcp_compliance(server_config)
    }

    # 3. Run security tests
    security_results = {
        "authentication": test_authentication(server_config),
        "input_validation": test_input_validation(server_config),
        "rate_limiting": test_rate_limiting(server_config),
        "data_exposure": test_data_exposure(server_config),
        "authorization": test_authorization(server_config)
    }

    # 4. Structure for inheritance
    inheritable_data = {
        "validated_tool_calls": extract_tool_patterns(quality_results),
        "tool_catalog": build_tool_catalog(quality_results),
        "security_clearances": extract_security_validations(security_results),
        "performance_baselines": extract_performance_metrics(quality_results)
    }

    # 5. Cache in universal cache (24-hour TTL)
    cache_universal_results(server_config.id, {
        "quality_score": calculate_quality_score(quality_results),
        "security_score": calculate_security_score(security_results),
        "inheritable_data": inheritable_data,
        "ttl": 86400  # 24 hours
    })

    return test_results
```

### Runtime Monitoring

Selective validation in production:

```python
def monitor_mcp_server_runtime(server_id, request):
    """
    Lightweight runtime validation with caching
    """
    # 1. Check universal cache first
    cached = get_universal_cache(server_id)
    if cached and cached.is_valid():
        return cached.result

    # 2. Quick security check
    if not validate_input_safety(request):
        return block_request("Input validation failed")

    # 3. Performance monitoring (async)
    async_monitor_performance(server_id, request)

    # 4. Execute with monitoring
    return execute_with_monitoring(request)
```

## Test Result Structure

MCP test results are structured to maximize inheritance value:

```python
MCP_TEST_RESULT = {
    # Component identification
    "component_id": "weather_mcp_server",
    "component_type": "mcp_server",
    "version": "1.0.0",
    "timestamp": "2024-08-30T16:00:00Z",

    # Framework context (always universal for MCP)
    "framework": "universal",
    "is_agnostic": True,
    "cross_framework_validity": True,

    # Aggregate scores
    "quality_score": 0.95,
    "security_score": 0.98,

    # Detailed test results
    "test_results": {
        "quality": {
            "tool_discovery": {"status": "PASS", "tools_found": 3},
            "tool_invocation": {"status": "PASS", "success_rate": 0.98},
            "error_handling": {"status": "PASS", "coverage": 0.95},
            "performance": {"status": "PASS", "p95_ms": 150},
            "api_compliance": {"status": "PASS", "version": "1.0"}
        },
        "security": {
            "authentication": {"status": "PASS", "mechanism": "api_key"},
            "input_validation": {"status": "PASS", "blocked_injections": 10},
            "rate_limiting": {"status": "PASS", "limit": "100/min"},
            "data_exposure": {"status": "PASS", "leaks_found": 0},
            "authorization": {"status": "PASS", "boundaries_enforced": True}
        }
    },

    # Inheritable data for agents
    "inheritable_data": {
        "validated_tool_calls": [
            {
                "tool_name": "get_weather",
                "test_case": "valid_city",
                "request": {
                    "method": "tools/call",
                    "params": {
                        "name": "get_weather",
                        "arguments": {"city": "San Francisco"}
                    }
                },
                "response": {
                    "temperature": 65,
                    "conditions": "sunny",
                    "humidity": 70
                },
                "validation": {
                    "status": "PASS",
                    "response_time_ms": 145,
                    "security_checks": ["input_validated", "rate_limit_ok"]
                }
            }
            # Additional test cases...
        ],

        "tool_catalog": {
            "get_weather": {
                "available": True,
                "avg_response_time_ms": 150,
                "success_rate": 0.98,
                "security_validated": True,
                "test_coverage": ["valid_input", "invalid_input", "edge_cases"]
            },
            "get_forecast": {
                "available": True,
                "avg_response_time_ms": 200,
                "success_rate": 0.96,
                "security_validated": True,
                "test_coverage": ["valid_input", "date_ranges", "locations"]
            }
        },

        "performance_baselines": {
            "p50_ms": 100,
            "p95_ms": 150,
            "p99_ms": 300,
            "throughput_rps": 100
        },

        "security_clearances": {
            "injection_tested": True,
            "authentication_required": True,
            "rate_limits_enforced": True,
            "data_sanitization": True
        }
    },

    # Cache metadata
    "cache_ttl": 86400,  # 24 hours for foundation components
    "cache_key": "universal:mcp:weather_mcp_server:1.0.0",

    # Inheritance metadata
    "inherits_from": [],  # Empty - foundation component
    "inherited_by": ["agent", "workflow"],  # Components that will inherit
    "inheritance_benefit": "85% reduction in tool testing for agents"
}
```

## Inheritance Model

### How Agents Inherit MCP Test Results

When an agent is tested, it automatically inherits MCP validation:

```python
# Agent test leveraging MCP inheritance
AGENT_TEST_WITH_MCP_INHERITANCE = {
    "agent_id": "weather_assistant",

    # Inherited from MCP testing (no retesting needed)
    "inherited_validations": {
        "weather_mcp_server": {
            "quality_score": 0.95,  # Inherited
            "security_score": 0.98,  # Inherited
            "tools_validated": ["get_weather", "get_forecast"],
            "skip_tool_execution_tests": True,  # Don't retest tools
            "use_validated_patterns": True,  # Reuse test cases
            "performance_baseline": 150  # Inherited p95
        }
    },

    # Agent focuses on integration testing only
    "agent_specific_tests": {
        "tool_selection": {
            "test": "Does agent select correct tool for query?",
            "result": "PASS"
        },
        "response_synthesis": {
            "test": "Does agent format tool output appropriately?",
            "result": "PASS"
        }
    },

    # Time saved through inheritance
    "testing_metrics": {
        "tests_inherited": 10,
        "tests_executed": 2,
        "time_saved": "85%"
    }
}
```

### Cross-Framework Inheritance

MCP test results are valid across all agent frameworks:

| Framework     | Inheritance Usage           | Time Saved |
| ------------- | --------------------------- | ---------- |
| **Aurite**    | Direct inheritance (native) | 85%        |
| **LangChain** | Via adapter translation     | 85%        |
| **AutoGen**   | Via adapter translation     | 85%        |
| **CrewAI**    | Via adapter translation     | 85%        |
| **Custom**    | Via generic adapter         | 80-85%     |

## Caching Strategy

### Universal Cache Integration

MCP test results are stored in the universal cache for cross-framework sharing:

```python
CACHE_STRATEGY = {
    "cache_type": "universal",  # Shared across all frameworks
    "ttl": 86400,  # 24 hours
    "invalidation": "cascade",  # Invalidate dependent components
    "key_pattern": "universal:mcp:{server_id}:{version}",

    "benefits": {
        "cross_framework_reuse": True,
        "cache_hit_rate": 0.85,
        "redundant_test_elimination": 0.85
    }
}
```

### Cache Invalidation

When an MCP server is updated:

1. Universal cache entry is invalidated
2. All dependent agent test results are marked stale
3. Workflow test results are cascaded for invalidation
4. Next test run refreshes the cache

## Failure Handling

### Failure Impact Analysis

MCP server failures have significant upstream impact:

```
MCP Failure Impact:
├── Direct Impact
│   └── MCP server cannot be used
├── Agent Impact
│   ├── Agents using this MCP are blocked
│   └── Agent tests marked as "blocked by dependency"
└── Workflow Impact
    ├── Workflows using affected agents fail
    └── Business processes disrupted
```

### Failure Propagation Rules

1. **Critical Failures** (Security breaches, authentication failures)

   - Block all dependent components immediately
   - Require manual intervention to resolve

2. **Quality Failures** (Performance degradation, high error rates)

   - Allow degraded operation with warnings
   - Trigger alerts for investigation

3. **Partial Failures** (Some tools working, others failing)
   - Selective blocking of failed tools only
   - Agents can use working tools

## Getting Started

### Running MCP Server Tests

```bash
# Run all MCP server tests
aurite test mcp-server <server_id>

# Run quality tests only
aurite test mcp-server <server_id> --quality

# Run security tests only
aurite test mcp-server <server_id> --security

# Run with specific framework context (for comparison)
aurite test mcp-server <server_id> --framework langchain
```

### Viewing Test Results

```bash
# View latest test results
aurite test results mcp-server <server_id>

# View inherited impact
aurite test inheritance <server_id>

# View cache status
aurite cache status mcp-server <server_id>
```

## Related Documentation

- [Test Patterns](test_patterns.md) - Reusable test patterns and validated tool calls
- [Testing Architecture](../../architecture/testing_architecture.md) - Overall testing framework architecture
- [Test Inheritance](../../architecture/test_inheritance.md) - How test results flow through the hierarchy
- [Framework-Agnostic Testing](../../architecture/framework_agnostic_testing.md) - Cross-framework testing approach
- [Kahuna Testing Framework](../../README.md) - Main testing framework documentation
