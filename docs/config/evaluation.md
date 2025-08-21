# :material-clipboard-check: Evaluation Configuration

Evaluations are components that test and validate the performance of agents, workflows, and other components in the Aurite framework. An evaluation configuration defines what component to test, the input to provide, and the expected output criteria.

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
    | `eval_name` | `string` | Yes | The name of the component being evaluated (must match an existing agent, workflow, etc.). |
    | `eval_type` | `string` | Yes | The type of component being evaluated. Must be one of: `"agent"`, `"linear_workflow"`, or `"custom_workflow"`. |

=== ":material-test-tube: Test Configuration"

    These fields define the test inputs and expected outcomes.

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `user_input` | `string` | Yes | The user input message that will be fed to the component being evaluated. |
    | `expected_output` | `string` | Yes | A description of the expected output or behavior from the component. This is used to validate the component's performance. |
    | `review_llm` | `string` | No | The name of an LLM configuration to use for automated review of the component's output against the expected output. If not specified, it will default to a config using gpt-3.5-turbo. |

---

## :material-code-json: Configuration Example

Here is a practical example of an evaluation configuration.

=== "Agent Evaluation"

    An evaluation that tests a code refactoring agent's ability to improve Python code quality.

    ```json
    {
      "type": "evaluation",
      "name": "code-refactor-test",
      "description": "Tests the code refactoring agent's ability to improve Python code readability",
      "eval_name": "code-refactor-agent",
      "eval_type": "agent",
      "user_input": "Please refactor this Python function to improve readability: def calc(x,y,z): return x*2+y/3-z**2 if x>0 else 0",
      "expected_output": "The agent should provide a refactored version with proper variable names, spacing, and potentially break down the complex expression for better readability",
      "review_llm": "claude-3-opus"
    }
