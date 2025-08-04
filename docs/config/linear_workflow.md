# :material-chart-timeline-variant: Linear Workflow Configuration

Linear workflows provide a straightforward way to execute a series of components in a predefined, sequential order. They are perfect for tasks that follow a linear process, such as "first run the data-ingestion agent, then run the analysis agent."

A linear workflow configuration is a JSON or YAML object with a `type` field set to `"linear_workflow"`.

<!-- prettier-ignore -->
!!! info "How It Works"
    When you execute a linear workflow, the framework iterates through the `steps` list in order. The output from one step is passed as the input to the next, allowing you to chain components together to create a processing pipeline.

---

## Schema

The `WorkflowConfig` defines the structure for a linear workflow.

=== ":material-format-list-bulleted-type: Core Fields"

    These fields define the fundamental properties of the workflow.

    | Field             | Type                     | Required | Description                                                                                                                         |
    | ----------------- | ------------------------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------- |
    | `name`            | `string`                 | Yes      | A unique identifier for the workflow. This name is used to run the workflow from the CLI or API.                                    |
    | `description`     | `string`                 | No       | A brief, human-readable description of what the workflow accomplishes.                                                              |
    | `steps`           | `list[string or object]` | Yes      | An ordered list of the components to execute. See "Steps Configuration" below for details.                                          |
    | `include_history` | `boolean`                | `None`   | If set, overrides the `include_history` setting for all agents in the workflow, forcing them all to either save or discard history. |

=== ":material-step-forward: Steps Configuration"

    The core of a linear workflow is the `steps` list. Each item in the list can be either a simple string (the component name) or a detailed object.

    **Simple Step (by Name)**

    The easiest way to define a step is to provide the `name` of the component.

    ```json
    "steps": ["fetch-data-agent", "process-data-agent"]
    ```

    **Detailed Step (by Object)**

    For more clarity, you can specify the component `type` along with its `name`. This is useful if you have components of different types with the same name.

    ```json
    "steps": [
      { "name": "fetch-data-agent", "type": "agent" },
      { "name": "analysis-pipeline", "type": "linear_workflow" }
    ]
    ```

    The `type` can be `"agent"`, `"linear_workflow"`, or `"custom_workflow"`.

---

## :material-code-json: Configuration Examples

=== "Simple Pipeline"

    This example defines a two-step workflow for processing customer feedback.

    ```json
    {
      "type": "linear_workflow",
      "name": "customer-feedback-pipeline",
      "description": "Fetches customer feedback, analyzes sentiment, and saves the result.",
      "steps": ["fetch-feedback-agent", "analyze-sentiment-agent"]
    }
    ```

=== "Workflow with History Override"

    This workflow forces all agents within it to maintain conversation history, which is useful for debugging or creating a continuous conversational experience across multiple agents.

    ```json
    {
      "type": "linear_workflow",
      "name": "stateful-support-flow",
      "description": "A multi-agent support flow that remembers the conversation.",
      "include_history": true,
      "steps": ["greeting-agent", "support-agent", "followup-agent"]
    }
    ```

=== "Nested Workflow"

    This example shows how a linear workflow can include another workflow as one of its steps.

    ```json
    {
      "type": "linear_workflow",
      "name": "daily-reporting-process",
      "description": "A top-level workflow that orchestrates other workflows and agents.",
      "steps": [
        { "name": "ingestion-workflow", "type": "linear_workflow" },
        { "name": "analysis-agent", "type": "agent" },
        { "name": "distribution-workflow", "type": "custom_workflow" }
      ]
    }
    ```
