# :material-clipboard-check: Evaluation Configuration

Evaluations are components that test and validate the performance of agents, workflows, and other components in the Aurite framework. An evaluation configuration defines what component to test, the test cases to run, and the expected output criteria.

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
    | `eval_name` | `string` | No | The name of the component being evaluated (must match an existing agent, workflow, etc.). Required if no `run_agent` is provided. |
    | `eval_type` | `string` | No | The type of component being evaluated. Must be one of: `"agent"`, `"linear_workflow"`, or `"custom_workflow"`. Required if `eval_name` is provided. |

=== ":material-test-tube: Test Configuration"

    These fields define the test cases and evaluation criteria.

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `test_cases` | `array` | Yes | A list of test cases to run against the component. Each test case contains input and expectations. |
    | `review_llm` | `string` | No | The name of an LLM configuration to use for automated review of the component's output against expectations. If not specified, defaults to a basic LLM config. |
    | `expected_schema` | `object` | No | A JSON schema that the component's output is expected to conform to. Used for structured output validation. |

=== ":material-cog: Advanced Configuration"

    These fields provide advanced customization options.

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `run_agent` | `function\|string` | No | A custom function or filepath to a Python file for running the component. If not provided, uses the built-in runner based on `eval_name` and `eval_type`. |
    | `run_agent_kwargs` | `object` | No | Additional keyword arguments to pass to the `run_agent` function beyond the input string. |

=== ":material-list-box: Test Case Structure"

    Each test case in the `test_cases` array has the following structure:

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `id` | `string` | No | A unique identifier for the test case. Auto-generated if not provided. |
    | `input` | `string` | Yes | The user input message that will be fed to the component being evaluated. |
    | `output` | `any` | No | Pre-recorded output for this test case. If not provided, the component will be run to generate output. |
    | `expectations` | `array` | Yes | A list of string descriptions of what is expected from the output (e.g., "The output contains temperature in Celsius", "The get_weather tool was called"). |

---

## :material-code-json: Configuration Examples

Here are practical examples of evaluation configurations using the new test case format.

=== "Basic Agent Evaluation"

    An evaluation that tests a weather agent's ability to provide temperature information.

    ```json
    {
      "type": "evaluation",
      "name": "weather-agent-test",
      "description": "Tests the weather agent's ability to provide accurate temperature information",
      "eval_name": "Weather Agent",
      "eval_type": "agent",
      "test_cases": [
        {
          "input": "london",
          "expectations": [
            "The output contains temperature information in celsius"
          ]
        },
        {
          "input": "tokyo",
          "expectations": [
            "The output contains temperature information in celsius"
          ]
        },
        {
          "input": "What is the weather in San Francisco? Use Fahrenheit",
          "expectations": [
            "The output contains temperature information in fahrenheit"
          ]
        }
      ]
    }
    ```

=== "Structured Output Evaluation"

    An evaluation that tests structured output with JSON schema validation.

    ```json
    {
      "type": "evaluation",
      "name": "structured-weather-test",
      "description": "Tests structured output format for weather data",
      "eval_name": "Structured Output Weather Agent",
      "eval_type": "agent",
      "test_cases": [
        {
          "input": "london",
          "expectations": [
            "The output contains temperature information in celsius"
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

=== "Custom Workflow Evaluation"

    An evaluation that tests a custom workflow with structured output validation.

    ```json
    {
      "type": "evaluation",
      "name": "custom-workflow-test",
      "description": "Tests custom workflow with structured response format",
      "eval_name": "ExampleCustomWorkflow",
      "eval_type": "custom_workflow",
      "test_cases": [
        {
          "input": "london",
          "expectations": [
            "The output contains temperature information in celsius"
          ]
        }
      ],
      "review_llm": "anthropic_claude_3_haiku",
      "expected_schema": {
        "type": "object",
        "properties": {
          "status": {
            "type": "string",
            "enum": ["ok", "failed"]
          },
          "response": {
            "type": "string"
          },
          "error": {
            "type": "string"
          }
        },
        "required": ["status"],
        "additionalProperties": false
      }
    }
    ```
