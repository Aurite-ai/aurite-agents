# :material-clipboard-check: Evaluation Configuration

Evaluations are components that test and validate the performance of agents, workflows, and other components in the Aurite framework. An evaluation configuration defines what component(s) to test, the test cases to run, and the expected output criteria.

An evaluation configuration is a JSON or YAML object with a `type` field set to `"evaluation"`.

!!! tip "Configuration Location"

    Evaluation configurations can be placed in any directory specified in your project's `.aurite` file (e.g., `config/evaluations/`, `config/testing/`). The framework will automatically discover them.

---

## Schema

The `EvaluationConfig` defines the structure for an evaluation configuration. Below are the available fields, categorized for clarity.

=== ":material-format-list-bulleted-type: Core Fields"

    These fields define the fundamental properties of the evaluation.

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `name` | `string` | Yes | A unique identifier for the evaluation. This name is used to reference the evaluation in commands and reports. |
    | `description` | `string` | No | A brief, human-readable description of what the evaluation tests. |
    | `component_type` | `string` | No | The type of component being evaluated. Must be one of: `"agent"`, `"linear_workflow"`, `"custom_workflow"`, `"graph_workflow"`, or `"mcp_server"`. |
    | `component_refs` | `array` | No | A list of component names to evaluate. Used for testing multiple components with the same test cases. |
    | `component_config` | `object` | No | Direct configuration of the component being tested (alternative to using `component_refs`). |

=== ":material-test-tube: Test Configuration"

    These fields define the test cases and evaluation criteria.

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `test_cases` | `array` | Yes | A list of test cases to run against the component(s). Each test case contains input and expectations. |
    | `review_llm` | `string` | No | The name of an LLM configuration to use for automated review of the component's output against expectations. |
    | `expected_schema` | `object` | No | A JSON schema that the component's output is expected to conform to. Used for structured output validation. |

=== ":material-cog: Advanced Configuration"

    These fields provide advanced customization options.

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `run_agent` | `function\|string` | No | A custom function or filepath to a Python file for running the component. The file should contain a `run` function. If not provided, uses the built-in runner. |
    | `run_agent_kwargs` | `object` | No | Additional keyword arguments to pass to the `run_agent` function beyond the input string. |

=== ":material-cached: Caching Configuration"

    These fields control result caching behavior.

    | Field | Type | Required | Default | Description |
    | --- | --- | --- | --- | --- |
    | `use_cache` | `boolean` | No | `true` | Whether to use cached results for test cases that have been evaluated before. |
    | `cache_ttl` | `integer` | No | `3600` | Time-to-live for cached results in seconds (default: 1 hour). |
    | `force_refresh` | `boolean` | No | `false` | Force re-execution of all test cases, bypassing cache. |
    | `evaluation_config_id` | `string` | No | Auto-generated | ID of the evaluation configuration (used for cache key generation). |

=== ":material-list-box: Test Case Structure"

    Each test case in the `test_cases` array has the following structure:

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `id` | `string` | No | A unique identifier for the test case. Auto-generated UUID if not provided. |
    | `name` | `string` | No | A user-friendly name for the test case (e.g., "weather_planning_sf"). |
    | `input` | `string` | Yes | The user input message that will be fed to the component being evaluated. |
    | `output` | `any` | No | Pre-recorded output for this test case. If not provided, the component will be run to generate output. |
    | `expectations` | `array` | Yes | A list of string descriptions of what is expected from the output (e.g., "The output contains temperature in Celsius", "The get_weather tool was called"). |

---

## :material-code-json: Configuration Examples

Here are practical examples of evaluation configurations using the updated structure.

=== "Single Agent Evaluation"

    An evaluation that tests a single weather agent's ability to provide temperature information.

    ```json
    {
      "name": "single_weather_agent_evaluation",
      "type": "evaluation",
      "component_type": "agent",
      "component_refs": [
        "Average Weather Agent"
      ],
      "review_llm": null,
      "test_cases": [
        {
          "name": "weather_planning_sf",
          "input": "What's the weather in San Francisco and create a plan for outdoor activities",
          "expectations": [
            "The response uses the weather_lookup tool to get San Francisco weather",
            "The response provides temperature information",
            "The response creates a structured plan based on weather conditions",
            "The response uses planning tools to save the plan"
          ]
        },
        {
          "name": "weather_comparison",
          "input": "Check the weather in London and Tokyo, then compare them",
          "expectations": [
            "The response uses weather_lookup for both London and Tokyo",
            "The response provides temperature for both cities",
            "The response compares the weather conditions between cities",
            "The response is well-structured and informative"
          ]
        }
      ]
    }
    ```

=== "Multiple Agent Evaluation"

    An evaluation that tests multiple agents with the same test cases for comparison.

    ```json
    {
      "name": "weather_agents_evaluation",
      "type": "evaluation",
      "component_type": "agent",
      "component_refs": [
        "Good Weather Agent",
        "Average Weather Agent",
        "Poor Weather Agent"
      ],
      "review_llm": null,
      "test_cases": [
        {
          "name": "weather_planning_sf",
          "input": "What's the weather in San Francisco and create a plan for outdoor activities",
          "expectations": [
            "The response uses the weather_lookup tool to get San Francisco weather",
            "The response provides temperature information",
            "The response creates a structured plan based on weather conditions",
            "The response uses planning tools to save the plan"
          ]
        },
        {
          "name": "comprehensive_travel",
          "input": "Create a comprehensive travel plan based on weather in three cities",
          "expectations": [
            "The response uses weather tools to get weather data for multiple cities",
            "The response uses planning tools to create and save a structured plan",
            "The response provides detailed recommendations for all three cities",
            "The response demonstrates coordination between weather and planning tools"
          ]
        }
      ],
      "metadata": {
        "description": "Unified evaluation for all weather agents - tests good, average, and poor quality agents with the same test cases",
        "expected_performance": "varied",
        "tool_requirements": ["weather_lookup", "current_time", "create_plan", "save_plan"]
      }
    }
    ```

=== "Custom Function Evaluation"

    An evaluation that uses a custom function to run the component, allowing for specialized testing scenarios.

    ```json
    {
      "name": "function_weather_agents_evaluation",
      "type": "evaluation",
      "component_type": "agent",
      "run_agent": "tests/fixtures/workspace/shared_configs/evaluation/run_function/test_weather_agent_function.py",
      "run_agent_kwargs": {},
      "review_llm": null,
      "test_cases": [
        {
          "name": "weather_planning_sf_good",
          "input": "What's the weather in San Francisco and create a plan for outdoor activities",
          "expectations": [
            "The response uses the weather_lookup tool to get San Francisco weather",
            "The response provides temperature information",
            "The response creates a structured plan based on weather conditions",
            "The response uses planning tools to save the plan"
          ]
        },
        {
          "name": "weather_comparison_good",
          "input": "Check the weather in London and Tokyo, then compare them",
          "expectations": [
            "The response uses weather_lookup for both London and Tokyo",
            "The response provides temperature for both cities",
            "The response compares the weather conditions between cities",
            "The response is well-structured and informative"
          ]
        }
      ],
      "force_refresh": true,
      "metadata": {
        "description": "Function-based evaluation for weather agents - tests custom run function with different quality levels",
        "evaluation_type": "run_function",
        "quality_levels": ["good", "average", "poor"]
      }
    }
    ```

=== "Workflow Evaluation"

    An evaluation that tests different types of workflows.

    ```json
    [
      {
        "name": "weather_workflow_evaluation",
        "type": "evaluation",
        "component_type": "linear_workflow",
        "component_refs": [
          "test_weather_workflow"
        ],
        "review_llm": null,
        "test_cases": [
          {
            "name": "weather_planning_sf",
            "input": "What's the weather in San Francisco",
            "expectations": [
              "The first agent uses a tool to look up the weather in San Francisco",
              "This weather information is relayed in detail to the second agent",
              "The second agent creates a plan of what to wear based on this weather information",
              "The plan is stored using a tool by the second agent"
            ]
          }
        ]
      },
      {
        "name": "weather_custom_workflow_evaluation",
        "type": "evaluation",
        "component_type": "custom_workflow",
        "component_refs": [
          "ExampleCustomWorkflow"
        ],
        "review_llm": null,
        "test_cases": [
          {
            "name": "weather_planning_sf",
            "input": "What's the weather in San Francisco",
            "expectations": [
              "The workflow runs successfully",
              "The workflow creates a plan based on the weather conditions in San Francisco"
            ]
          }
        ]
      },
      {
        "name": "weather_graph_workflow_evaluation",
        "type": "evaluation",
        "component_type": "graph_workflow",
        "component_refs": [
          "Parallel Weather Graph Workflow"
        ],
        "review_llm": null,
        "test_cases": [
          {
            "name": "weather_planning_sf",
            "input": "What's the weather in San Francisco",
            "expectations": [
              "The workflow runs successfully",
              "The workflow's fahrenheit agent outputs the temperature in fahrenheit",
              "The workflow's celcius agent outputs the temperature in celcius"
            ]
          }
        ]
      }
    ]
    ```

=== "MCP Server Evaluation"

    An evaluation that tests MCP server functionality.

    ```json
    {
      "name": "weather_mcp_evaluation",
      "type": "evaluation",
      "component_type": "mcp_server",
      "component_refs": [
        "weather_server"
      ],
      "review_llm": null,
      "test_cases": [
        {
          "name": "weather_planning_sf",
          "input": "What's the weather in San Francisco",
          "expectations": [
            "The weather_lookup tool is called once with the input of San Francisco",
            "The response from the tool provides temperature information"
          ]
        }
      ]
    }
    ```

=== "Structured Output with Schema Validation"

    An evaluation that validates structured output against a JSON schema.

    ```json
    {
      "name": "structured-weather-test",
      "type": "evaluation",
      "component_type": "agent",
      "component_refs": ["Structured Output Weather Agent"],
      "test_cases": [
        {
          "name": "london_weather",
          "input": "What's the weather in London?",
          "expectations": [
            "The output contains temperature information in celsius",
            "The output follows the required JSON structure",
            "The output includes weather recommendations"
          ]
        }
      ],
      "review_llm": "anthropic_claude_3_haiku",
      "expected_schema": {
        "type": "object",
        "properties": {
          "weather_summary": {
            "type": "string",
            "description": "A brief summary of the weather conditions."
          },
          "temperature": {
            "type": "object",
            "properties": {
              "value": {
                "type": "number"
              },
              "unit": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"]
              }
            },
            "required": ["value", "unit"]
          },
          "recommendations": {
            "type": "array",
            "items": {
              "type": "string"
            },
            "description": "Recommendations based on the weather."
          }
        },
        "required": ["weather_summary", "temperature", "recommendations"]
      }
    }
    ```

---

## :material-lightbulb: Usage Tips

### Component Selection

- Use `component_refs` to test one or more existing components by name
- Use `component_config` to define a component configuration inline
- Use `component_type` to specify what type of component you're testing

### Custom Run Functions

When using `run_agent` with a file path:

1. The file should contain a `run` function that takes the input string as the first parameter
2. Additional parameters can be passed via `run_agent_kwargs`
3. The function should return the component's output

Example custom run function:

```python
# custom_runner.py
async def run(input_text: str, **kwargs) -> str:
    # Custom logic to run your component
    # Return the component's output
    return result
```

### Caching Behavior

- Set `use_cache: false` to always run fresh evaluations
- Use `force_refresh: true` to bypass cache for a single run
- Adjust `cache_ttl` to control how long results are cached
- The `evaluation_config_id` is used as part of the cache key

### Test Case Design

- Write clear, specific expectations that can be automatically evaluated
- Use descriptive `name` fields for test cases to make results easier to understand
- Include both positive expectations (what should happen) and negative ones (what shouldn't happen)
- Test edge cases and error conditions alongside happy path scenarios
