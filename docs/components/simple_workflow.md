# Simple Workflow Configurations (WorkflowConfig)

Simple Workflows in the Aurite Agents framework define a sequential execution of other components, which can include Agents, other Simple Workflows, or even Custom Workflows. They are designed for straightforward, multi-step tasks where the output of one step can become the input for the next.

This document outlines the structure and usage of `WorkflowConfig` objects, which are used to define these simple workflows. The `WorkflowConfig` model is defined in `src/aurite/config/config_models.py`.

## Quickstart Example

A basic Simple Workflow requires a `name` and a list of `steps`. Each step is typically the name of an Agent to be executed in sequence, but can also be the name of another Simple Workflow or a Custom Workflow.

```json
{
  "name": "TwoStepGreetingProcess",
  "description": "A simple workflow that first greets and then offers assistance.",
  "steps": [
    "GreetingAgent", // Name of the first AgentConfig
    "OfferHelpAgent"   // Name of the second AgentConfig
  ]
}
```

-   **`name`**: A unique name for this simple workflow.
-   **`description`** (optional): A brief explanation of what the workflow does.
-   **`steps`**: An ordered list of component names (usually Agent names) that will be executed sequentially.

## Detailed Configuration Fields (WorkflowConfig)

A Simple Workflow configuration is a JSON object with the following fields:

| Field         | Type                                     | Default  | Description                                                                                                                                                                                                                            |
|---------------|------------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `name`        | string                                   | Required | A unique identifier for this simple workflow configuration. This name is used to execute the workflow.                                                                                                                                   |
| `steps`       | array of (string or `WorkflowComponent`) | Required | An ordered list defining the sequence of execution. Each item can be:<br/>- A `string`: The name of an Agent, Simple Workflow, or Custom Workflow to execute. The framework attempts to infer the type based on available component names.<br/>- A `WorkflowComponent` object: For explicit step definition, especially useful for disambiguation if component names clash across types (see details below). |
| `description` | string                                   | `null`   | An optional, human-readable description of what the workflow accomplishes.                                                                                                                                                             |

### WorkflowComponent Object

While often just providing a component name as a string in the `steps` array is sufficient (the framework will try to infer its type), you can use a `WorkflowComponent` object for more explicit control. This is particularly useful if there's a naming conflict (e.g., an Agent and a Simple Workflow both named "DataProcessor").

| Field  | Type                                                       | Description                                                                                                                                                              |
|--------|------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `name` | string                                                     | The name of the component to execute (e.g., an Agent's name, another Simple Workflow's name, or a Custom Workflow's name).                                              |
| `type` | string (`"agent"`, `"simple_workflow"`, `"custom_workflow"`) | The explicit type of the component being executed in this step. Use this to resolve ambiguity if a component `name` could refer to multiple component types. |

**Example of a step using `WorkflowComponent` for disambiguation:**
```json
{
  "name": "MyWorkflowWithSpecificStepTypes",
  "steps": [
    "InitialGatherer", // Assumed to be an Agent if only one component has this name
    { "name": "DataProcessor", "type": "simple_workflow" }, // Explicitly run the Simple Workflow named "DataProcessor"
    { "name": "FinalReport", "type": "agent" } // Explicitly run the Agent named "FinalReport"
  ]
}
```
In most cases where component names are unique across types, simply listing the names as strings in the `steps` array is adequate. The framework defaults to interpreting string steps as agent names if not otherwise specified or uniquely identifiable as another workflow type.

## Example WorkflowConfig File

Simple Workflow configurations are typically stored in JSON files (e.g., `config/workflows/my_workflow.json`) and referenced by name in the main project configuration. A file can contain a single `WorkflowConfig` object or a list of them. Like all components, Simple Workflows can also be defined directly in a project configuration file (`aurite_config.json`)

**Example: `config/workflows/data_processing_sequence.json`**
```json
[
  {
    "name": "StandardDataProcessing",
    "description": "Fetches data, processes it, and then summarizes.",
    "steps": [
      "FetchDataSourceAgent",
      "CleanDataAgent",
      "AnalyzeDataAgent",
      "GenerateSummaryAgent"
    ]
  },
  {
    "name": "QuickReportWorkflow",
    "description": "A shorter workflow for generating a quick report.",
    "steps": [
      "FetchQuickDataAgent",
      "QuickSummaryAgent"
    ]
  }
]
```

## How Simple Workflows are Used

Simple Workflows are executed by their `name`. The `HostManager` (via the `ExecutionFacade`) orchestrates the execution, calling each component (Agent, Simple Workflow, or Custom Workflow) in the `steps` list in order. The output from one component is typically passed as the initial input to the next component in the sequence.

They can be invoked via:
-   The API (e.g., `/execute/workflow/{workflow_name}`).
-   The CLI (`run-cli execute workflow <workflow_name> "<initial_input>"`).
-   From within a Custom Workflow.

## Component Documentation Links

-   [Agent Configurations (AgentConfig)](./agent.md)
-   [Custom Workflow Configurations (CustomWorkflowConfig)](./custom_workflow.md)
-   [Project Configurations (ProjectConfig)](./PROJECT.md): Simple Workflows are included in a project.
