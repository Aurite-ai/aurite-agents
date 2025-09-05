# MCP Server Test Patterns

## Overview

This document provides reusable test patterns for MCP server validation. These patterns serve as the foundation for inheritance, allowing agents and workflows to reuse validated tool interactions without retesting. Each pattern includes the request, expected response, and validation criteria that can be inherited by higher-level components.

## Validated Tool Call Patterns

### Pattern Structure

Each validated tool call pattern contains:

- **Test Case ID**: Unique identifier for the pattern
- **Purpose**: What this pattern validates
- **Request**: The exact MCP protocol request
- **Response**: Expected response structure
- **Validation**: What was verified
- **Inheritance Value**: How agents can use this pattern

### Quality Test Patterns

#### Pattern: Tool Discovery

```python
TOOL_DISCOVERY_PATTERN = {
    "test_case_id": "mcp_tool_discovery_001",
    "purpose": "Validate tool enumeration",
    "request": {
        "method": "tools/list",
        "params": {}
    },
    "expected_response": {
        "tools": [
            {
                "name": "get_weather",
                "description": "Get current weather for a city",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"}
                    },
                    "required": ["city"]
                }
            },
            {
                "name": "get_forecast",
                "description": "Get weather forecast",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"},
                        "days": {"type": "integer", "minimum": 1, "maximum": 7}
                    },
                    "required": ["city"]
                }
            }
        ]
    },
    "validation": {
        "tools_present": True,
        "schema_valid": True,
        "descriptions_clear": True
    },
    "inheritance_value": "Agents know available tools without discovery"
}
```

#### Pattern: Successful Tool Invocation

```python
SUCCESSFUL_INVOCATION_PATTERN = {
    "test_case_id": "mcp_invoke_success_001",
    "purpose": "Validate successful tool execution",
    "request": {
        "method": "tools/call",
        "params": {
            "name": "get_weather",
            "arguments": {
                "city": "San Francisco"
            }
        }
    },
    "expected_response": {
        "content": [
            {
                "type": "text",
                "text": "Current weather in San Francisco: 65°F, sunny, 70% humidity"
            }
        ],
        "isError": False
    },
    "validation": {
        "status": "SUCCESS",
        "response_time_ms": 145,
        "content_valid": True,
        "format_correct": True
    },
    "inheritance_value": "Agents can use this exact request pattern"
}
```

#### Pattern: Error Handling

```python
ERROR_HANDLING_PATTERN = {
    "test_case_id": "mcp_error_handling_001",
    "purpose": "Validate graceful error handling",
    "request": {
        "method": "tools/call",
        "params": {
            "name": "get_weather",
            "arguments": {
                "city": ""  # Empty city name
            }
        }
    },
    "expected_response": {
        "content": [
            {
                "type": "text",
                "text": "Error: City name is required"
            }
        ],
        "isError": True
    },
    "validation": {
        "error_handled": True,
        "message_clear": True,
        "no_crash": True,
        "status_code": 400
    },
    "inheritance_value": "Agents know error scenarios are handled safely"
}
```

#### Pattern: Edge Case Handling

```python
EDGE_CASE_PATTERN = {
    "test_case_id": "mcp_edge_case_001",
    "purpose": "Validate handling of edge cases",
    "test_cases": [
        {
            "description": "Very long city name",
            "request": {
                "method": "tools/call",
                "params": {
                    "name": "get_weather",
                    "arguments": {
                        "city": "Llanfairpwllgwyngyllgogerychwyrndrobwllllantysiliogogogoch"
                    }
                }
            },
            "validation": {
                "handled_gracefully": True,
                "response_time_acceptable": True
            }
        },
        {
            "description": "Special characters in input",
            "request": {
                "method": "tools/call",
                "params": {
                    "name": "get_weather",
                    "arguments": {
                        "city": "São Paulo"
                    }
                }
            },
            "validation": {
                "unicode_handled": True,
                "correct_response": True
            }
        }
    ],
    "inheritance_value": "Agents inherit edge case handling confidence"
}
```

### Security Test Patterns

#### Pattern: Input Validation

```python
INPUT_VALIDATION_PATTERN = {
    "test_case_id": "mcp_security_input_001",
    "purpose": "Validate injection attack resistance",
    "attack_vectors": [
        {
            "type": "SQL Injection",
            "request": {
                "method": "tools/call",
                "params": {
                    "name": "get_weather",
                    "arguments": {
                        "city": "'; DROP TABLE weather; --"
                    }
                }
            },
            "expected_response": {
                "isError": True,
                "content": [{"type": "text", "text": "Invalid city name"}]
            },
            "validation": {
                "injection_blocked": True,
                "no_data_leak": True
            }
        },
        {
            "type": "XSS Attack",
            "request": {
                "method": "tools/call",
                "params": {
                    "name": "get_weather",
                    "arguments": {
                        "city": "<script>alert('xss')</script>"
                    }
                }
            },
            "expected_response": {
                "isError": True,
                "content": [{"type": "text", "text": "Invalid city name"}]
            },
            "validation": {
                "script_blocked": True,
                "output_sanitized": True
            }
        },
        {
            "type": "Command Injection",
            "request": {
                "method": "tools/call",
                "params": {
                    "name": "get_weather",
                    "arguments": {
                        "city": "Boston; rm -rf /"
                    }
                }
            },
            "validation": {
                "command_blocked": True,
                "system_safe": True
            }
        }
    ],
    "inheritance_value": "Agents inherit security validation - no need to retest"
}
```

#### Pattern: Authentication Validation

```python
AUTHENTICATION_PATTERN = {
    "test_case_id": "mcp_security_auth_001",
    "purpose": "Validate authentication enforcement",
    "test_cases": [
        {
            "description": "Valid authentication",
            "headers": {
                "Authorization": "Bearer valid_token_123"
            },
            "request": {
                "method": "tools/call",
                "params": {
                    "name": "get_weather",
                    "arguments": {"city": "Boston"}
                }
            },
            "validation": {
                "access_granted": True,
                "response_valid": True
            }
        },
        {
            "description": "Missing authentication",
            "headers": {},
            "request": {
                "method": "tools/call",
                "params": {
                    "name": "get_weather",
                    "arguments": {"city": "Boston"}
                }
            },
            "expected_response": {
                "error": {
                    "code": -32001,
                    "message": "Authentication required"
                }
            },
            "validation": {
                "access_denied": True,
                "proper_error_code": True
            }
        },
        {
            "description": "Invalid token",
            "headers": {
                "Authorization": "Bearer invalid_token"
            },
            "validation": {
                "access_denied": True,
                "no_data_leak": True
            }
        }
    ],
    "inheritance_value": "Agents know authentication is properly enforced"
}
```

#### Pattern: Rate Limiting

```python
RATE_LIMITING_PATTERN = {
    "test_case_id": "mcp_security_rate_001",
    "purpose": "Validate rate limiting enforcement",
    "test_sequence": [
        {
            "step": 1,
            "description": "Normal request rate",
            "requests_per_minute": 50,
            "validation": {
                "all_requests_succeed": True,
                "avg_response_time_ms": 150
            }
        },
        {
            "step": 2,
            "description": "At rate limit",
            "requests_per_minute": 100,
            "validation": {
                "all_requests_succeed": True,
                "warning_headers_present": True
            }
        },
        {
            "step": 3,
            "description": "Exceeding rate limit",
            "requests_per_minute": 150,
            "expected_response": {
                "error": {
                    "code": -32002,
                    "message": "Rate limit exceeded"
                }
            },
            "validation": {
                "requests_blocked": True,
                "retry_after_header": True,
                "proper_status_code": 429
            }
        }
    ],
    "inheritance_value": "Agents inherit rate limit thresholds"
}
```

## Tool Catalog Format

The tool catalog provides agents with a complete inventory of validated tools:

```python
TOOL_CATALOG = {
    "server_id": "weather_mcp_server",
    "version": "1.0.0",
    "tools": {
        "get_weather": {
            "description": "Get current weather for a city",
            "validation_status": {
                "quality": {
                    "functional": "PASS",
                    "performance": "PASS",
                    "error_handling": "PASS"
                },
                "security": {
                    "input_validation": "PASS",
                    "authentication": "PASS",
                    "rate_limiting": "PASS"
                }
            },
            "performance_metrics": {
                "avg_response_time_ms": 150,
                "p95_response_time_ms": 200,
                "success_rate": 0.98,
                "error_rate": 0.02
            },
            "test_coverage": {
                "valid_inputs": 10,
                "invalid_inputs": 5,
                "edge_cases": 8,
                "security_vectors": 12
            },
            "validated_patterns": [
                "mcp_invoke_success_001",
                "mcp_error_handling_001",
                "mcp_security_input_001"
            ]
        },
        "get_forecast": {
            "description": "Get weather forecast for multiple days",
            "validation_status": {
                "quality": "PASS",
                "security": "PASS"
            },
            "performance_metrics": {
                "avg_response_time_ms": 200,
                "p95_response_time_ms": 300,
                "success_rate": 0.96
            }
        }
    },
    "overall_metrics": {
        "total_tools": 2,
        "tools_validated": 2,
        "quality_score": 0.95,
        "security_score": 0.98,
        "test_patterns_available": 15
    }
}
```

## Inheritance Examples

### Example 1: Agent Using Validated Patterns

```python
# Agent test that inherits MCP validation
def test_agent_with_mcp_inheritance():
    # Load validated MCP patterns
    mcp_patterns = load_mcp_test_patterns("weather_mcp_server")

    # Agent doesn't need to test tool functionality
    # It only tests its own decision-making
    agent_test = {
        "test": "Agent selects correct tool",
        "user_query": "What's the weather in Boston?",
        "expected_tool": "get_weather",
        "expected_arguments": {"city": "Boston"}
    }

    # Use validated request pattern for execution
    validated_request = mcp_patterns["mcp_invoke_success_001"]["request"]
    validated_request["params"]["arguments"]["city"] = "Boston"

    # Agent knows this will work because MCP validated it
    response = agent.execute_tool(validated_request)

    # Agent only validates its own behavior
    assert agent.tool_selection == "get_weather"
    assert agent.response_formatting == "conversational"

    # Time saved: 85% (no tool testing needed)
```

### Example 2: Workflow Using Agent + MCP Inheritance

```python
# Workflow test with full inheritance chain
def test_workflow_with_inheritance():
    # Workflow inherits from agents, which inherit from MCP
    inheritance_chain = {
        "mcp_servers": {
            "weather_mcp": {
                "quality": 0.95,
                "security": 0.98,
                "tools_validated": ["get_weather", "get_forecast"]
            }
        },
        "agents": {
            "weather_agent": {
                "inherits_from": ["weather_mcp"],
                "quality": 0.93,  # Includes MCP quality
                "security": 0.98   # Inherits MCP security
            }
        }
    }

    # Workflow only tests orchestration
    workflow_test = {
        "test": "Multi-agent coordination",
        "skip_tool_tests": True,  # MCP validated
        "skip_agent_tool_selection": True,  # Agent validated
        "focus": "workflow_orchestration"
    }

    # Time saved: 70% through inheritance
```

### Example 3: Cross-Framework Pattern Usage

```python
# Same patterns work across frameworks
CROSS_FRAMEWORK_USAGE = {
    "aurite": {
        "uses_pattern": "mcp_invoke_success_001",
        "adaptation": "none",  # Native format
        "confidence": 1.0
    },
    "langchain": {
        "uses_pattern": "mcp_invoke_success_001",
        "adaptation": "translate_to_langchain_tool",
        "confidence": 0.95
    },
    "autogen": {
        "uses_pattern": "mcp_invoke_success_001",
        "adaptation": "convert_to_autogen_function",
        "confidence": 0.95
    }
}
```

## Pattern Maintenance

### Adding New Patterns

When adding new test patterns:

1. **Assign unique test_case_id** following naming convention
2. **Document purpose clearly** for inheritance understanding
3. **Include complete request/response** for reusability
4. **Specify validation criteria** that were verified
5. **Explain inheritance value** for agents/workflows

### Pattern Versioning

```python
PATTERN_VERSION = {
    "version": "1.0.0",
    "last_updated": "2024-08-30",
    "compatibility": {
        "mcp_protocol": "1.0",
        "frameworks": ["aurite", "langchain", "autogen", "crewai"]
    },
    "deprecation_notice": None
}
```

### Pattern Categories

Organize patterns by testing purpose:

| Category           | Purpose                    | Pattern Count | Inheritance Value             |
| ------------------ | -------------------------- | ------------- | ----------------------------- |
| **Functional**     | Basic tool operation       | 5-10          | Core functionality validation |
| **Edge Cases**     | Boundary conditions        | 5-10          | Robustness confidence         |
| **Performance**    | Response times, throughput | 3-5           | Performance baselines         |
| **Security**       | Attack resistance          | 10-15         | Security validation           |
| **Error Handling** | Failure scenarios          | 5-10          | Error handling confidence     |

## Best Practices

### For Pattern Creation

1. **Be Exhaustive**: Include all details needed for reuse
2. **Be Explicit**: Don't assume context, document everything
3. **Be Consistent**: Follow the established structure
4. **Be Versioned**: Track pattern changes over time

### For Pattern Usage

1. **Load Once**: Cache patterns at test initialization
2. **Validate Compatibility**: Check pattern version matches
3. **Report Usage**: Track which patterns are inherited
4. **Measure Savings**: Calculate time saved through inheritance

## Related Documentation

- [MCP Server Testing Overview](README.md) - Main MCP testing documentation
- [Test Inheritance](../../architecture/test_inheritance.md) - How patterns flow to agents
- [Framework-Agnostic Testing](../../architecture/framework_agnostic_testing.md) - Cross-framework usage
- [Testing Architecture](../../architecture/testing_architecture.md) - Overall testing framework
