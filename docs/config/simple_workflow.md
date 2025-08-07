# Simple Workflow Configuration

Simple workflows provide a straightforward way to execute a series of components in a predefined, sequential order. They are perfect for tasks that follow a linear process, such as "first run the data-ingestion agent, then run the analysis agent."

A simple workflow configuration is a JSON or YAML object with a `type` field set to `"simple_workflow"`.

## How It Works

When you execute a simple workflow, the framework iterates through the `steps` list in order. For each step, it runs the specified component and waits for it to complete before moving on to the next one. The output or result from one step is passed as the input to the next, allowing you to chain components together to create a processing pipeline.

## Full Example

This example defines a two-step workflow for processing customer feedback.

```json
{
  "type": "simple_workflow",
  "name": "customer-feedback-pipeline",
  "description": "Fetches customer feedback, analyzes sentiment, and saves the result.",
  "steps": [
    "fetch-feedback-agent",
    "analyze-sentiment-agent"
  ]
}
```

## Core Fields

### `name`
**Type:** `string` (Required)
**Description:** A unique identifier for the workflow. This name is used to run the workflow from the command line or other interfaces.

```json
{
  "name": "daily-report-workflow"
}
```

### `type`
**Type:** `string` (Required)

**Description:** You must specify the component type as `simple_workflow` for the index's efficiency.
```json
  "type": "simple_workflow"
```

### `description`
**Type:** `string` (Optional)
**Description:** A brief, human-readable description of what the workflow accomplishes.

```json
{
  "description": "A workflow that generates and distributes a daily sales report."
}
```

## Steps Configuration

The core of a simple workflow is the `steps` list. This list defines the sequence of components to be executed.

### `steps`
**Type:** `list[string | object]` (Required)
**Description:** An ordered list of the components to execute. Each item in the list can be either a simple string (the name of the component) or a more detailed object.

#### Simple Step (by Name)

The easiest way to define a step is to simply provide the `name` of the component you want to run. The framework will look up the component in the configuration index.

```json
{
  "name": "simple-ingestion-workflow",
  "steps": [
    "fetch-data-agent",
    "process-data-agent",
    "save-results-agent"
  ]
}
```

#### Detailed Step (by Object)

For more clarity or to handle duplicate component names across component types, you can specify the component type. This object must include the `name` and `type` of the component.

-   `name` (string): The name of the component.
-   `type` (string): The type of the component. Must be one of `"agent"`, `"simple_workflow"`, or `"custom_workflow"`.

This more verbose format is functionally identical to the simple string format for now but may support additional step-specific parameters in the future.

```json
{
  "name": "detailed-ingestion-workflow",
  "steps": [
    {
      "name": "fetch-data-agent",
      "type": "agent"
    },
    {
      "name": "process-data-agent",
      "type": "agent"
    }
  ]
}
```