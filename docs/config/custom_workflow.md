# Custom Workflow Configuration

When a `simple_workflow` isn't enough to capture your logic, you can implement a **Custom Workflow** directly in Python. This gives you complete control over the execution flow, allowing for conditional logic, branching, looping, and complex data manipulation between steps.

A custom workflow configuration is a JSON or YAML object with a `type` field set to `"custom_workflow"`. Its purpose is to link a component name to your Python code.

## How It Works

1.  **Configuration:** You create a configuration file that gives your custom workflow a `name` and points to the `module_path` and `class_name` of your Python implementation.
2.  **Implementation:** You write a Python class that inherits from the framework's base workflow class `CustomWorkflow`. This class must implement an `execute_workflow` method, which contains your custom logic.
3.  **Execution:** When you ask the framework to run your custom workflow by its `name`, the `ConfigManager` finds its configuration. The framework then dynamically loads the specified Python module, instantiates your class, and calls its `run` method.

This approach cleanly separates the configuration (the "what") from the implementation (the "how"), allowing you to manage your workflows as named components within the Aurite ecosystem while retaining the full power of Python for complex logic.

## Full Example

This example defines a custom workflow implemented in the `AdvancedDataPipeline` class inside the `data_pipeline.py` file.

```json
{
  "type": "custom_workflow",
  "name": "advanced-data-pipeline",
  "description": "A custom Python workflow for processing and validating data with complex business rules.",
  "module_path": "custom_workflows/data_pipeline.py",
  "class_name": "AdvancedDataPipeline"
}
```

## Core Fields

### `name`
**Type:** `string` (Required)
**Description:** A unique identifier for the custom workflow. This name is used to run the workflow from the framework's interfaces.

```json
{
  "name": "intelligent-routing-workflow"
}
```

### `description`
**Type:** `string` (Optional)
**Description:** A brief, human-readable description of what the custom workflow does.

```json
{
  "description": "A workflow that dynamically routes tasks to different agents based on input content."
}
```

## Python Code Linking

These fields tell the framework where to find and how to load your custom workflow implementation.

### `module_path`
**Type:** `string` (Required)
**Description:** The path to the Python file containing your workflow implementation. This path should be relative to the location of the `.aurite` file that defines its context.

**Important:** The framework resolves this path to an absolute path at runtime.

```json
{
  "module_path": "custom_workflows/my_routing_logic.py"
}
```

### `class_name`
**Type:** `string` (Required)
**Description:** The name of the class within the specified Python module that implements the workflow logic. This class must adhere to the framework's custom workflow interface.

```json
{
  "class_name": "MyRoutingWorkflow"
}
```