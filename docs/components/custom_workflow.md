# Custom Workflow Configurations (CustomWorkflowConfig)

Custom Workflows provide the ultimate flexibility for orchestrating components within the Aurite Agents framework. Unlike Simple Workflows which execute a linear sequence of agents, Custom Workflows allow you to define complex logic, conditional branching, parallel execution (if your Python code implements it), and intricate interactions between Agents, other Simple Workflows, or even other Custom Workflows using custom Python classes.

This document details the `CustomWorkflowConfig` model, which points to your Python module and class that implements the custom orchestration logic. The `CustomWorkflowConfig` model is defined in `src/aurite/config/config_models.py`.

## Quickstart Example

A Custom Workflow configuration primarily needs a `name`, a `module_path` pointing to your Python file, and the `class_name` within that file that implements the workflow logic.

```json
{
  "name": "MyAdvancedOrchestrator",
  "description": "A custom workflow for complex task management.",
  "module_path": "src/my_custom_workflows/advanced_orchestrator.py", // Path relative to project root
  "class_name": "AdvancedTaskOrchestratorWorkflow"
}
```

-   **`name`**: A unique name for this custom workflow.
-   **`description`** (optional): A brief explanation of what the workflow does.
-   **`module_path`**: The file path (relative to your project root, where `aurite_config.json` or your `PROJECT_CONFIG_PATH` points) to the Python file containing your custom workflow class.
-   **`class_name`**: The name of the Python class within the specified `module_path` file that implements the custom workflow logic.

## Detailed Configuration Fields (CustomWorkflowConfig)

A Custom Workflow configuration is a JSON object with the following fields:

| Field         | Type   | Default  | Description                                                                                                                                                              |
|---------------|--------|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `name`        | string | Required | A unique identifier for this custom workflow configuration. This name is used to execute the workflow.                                                                   |
| `module_path` | string (Path) | Required | The file path to the Python module (`.py` file) containing the custom workflow class. This path is resolved relative to the root of your Aurite project.                 |
| `class_name`  | string | Required | The name of the Python class within the specified `module_path` that implements the custom workflow's execution logic.                                                     |
| `description` | string | `null`   | An optional, human-readable description of what the custom workflow accomplishes and its intended use.                                                                     |

## Implementing a Custom Workflow Class

The Python class specified in `class_name` must adhere to a specific interface to be executable by the Aurite framework. It needs an `execute_workflow` asynchronous method.

**Required Method Signature:**

```python
from typing import Any, Optional
# Forward reference for ExecutionFacade if type hinting in the same file or for clarity
# from src.aurite.execution.facade import ExecutionFacade # Actual import if needed

class MyCustomWorkflowClass:
    async def execute_workflow(
        self,
        initial_input: Any,
        executor: "ExecutionFacade", # Instance of ExecutionFacade passed by the system
        session_id: Optional[str] = None # Optional session_id for context
    ) -> Any:
        """
        This method contains your custom orchestration logic.

        Args:
            initial_input: The initial data or message to start the workflow.
            executor: An instance of ExecutionFacade, allowing this workflow
                      to call other agents, simple workflows, or custom workflows.
            session_id: An optional session ID for maintaining context across calls.

        Returns:
            The final result of the workflow's execution.
        """
        # --- Your custom Python orchestration logic here ---
        # Example: Call an agent
        agent_result = await executor.run_agent(
            agent_name="MyProcessingAgent", # Ensure this agent is defined in your project
            user_message=str(initial_input), # Ensure message is a string
            session_id=session_id
        )
        processed_data = agent_result.primary_text

        # Example: Conditional logic
        if "error" in processed_data.lower():
            # Handle error or call a different component
            error_handling_result = await executor.run_agent(
                agent_name="ErrorHandlingAgent",
                user_message=processed_data,
                session_id=session_id
            )
            return {"status": "error", "details": error_handling_result.final_response.content[0].text}

        # Example: Call a simple workflow
        simple_workflow_result = await executor.run_simple_workflow(
            workflow_name="MyFollowUpWorkflow", # Ensure this simple workflow is defined
            initial_input=processed_data,
            session_id=session_id
        )
        # Assuming simple_workflow_result is a dict with a 'final_message' key
        final_output = simple_workflow_result.get("final_message", "Workflow completed.")

        return {"status": "success", "output": final_output}

```

**Key points for implementation:**
1.  **Asynchronous:** The `execute_workflow` method must be `async def`.
2.  **`executor` Argument:** The framework will pass an instance of `ExecutionFacade` as the `executor` argument. Use this object to run other agents (`executor.run_agent(...)`), simple workflows (`executor.run_simple_workflow(...)`), or even other custom workflows (`executor.run_custom_workflow(...)`).
3.  **`initial_input`:** This is the data passed when the custom workflow is first invoked.
4.  **`session_id`:** Optional Variable. Use this to maintain conversational context if your workflow involves multiple turns with stateful agents.
5.  **Return Value:** The method should return the final result of the workflow's execution. The structure of this return value is up to you.

## Example CustomWorkflowConfig File

Custom Workflow configurations are typically stored in JSON files (e.g., `config/custom_workflows/my_custom_logic.json`) and referenced by name in the main project configuration. A file can contain a single `CustomWorkflowConfig` object or a list of them.

**Example: `config/custom_workflows/orchestrators.json`**
```json
[
  {
    "name": "ComplexDecisionFlow",
    "description": "A workflow that makes decisions based on initial input and routes to different agents.",
    "module_path": "src/my_workflows/decision_engine.py",
    "class_name": "DecisionEngineWorkflow"
  },
  {
    "name": "IterativeRefinementProcess",
    "description": "Iteratively calls an agent to refine a document until a condition is met.",
    "module_path": "src/my_workflows/refinement_loop.py",
    "class_name": "DocumentRefinerWorkflow"
  }
]
```
*(Ensure the Python files like `src/my_workflows/decision_engine.py` exist and contain the specified classes with the correct `execute_workflow` method.)*

## How Custom Workflows are Used

Custom Workflows are executed by their `name`. The `HostManager` (via the `ExecutionFacade`) loads your Python module, instantiates your custom class, and calls its `execute_workflow` method.

They can be invoked via:
-   The API (e.g., `/execute/custom-workflow/{workflow_name}`).
-   The CLI (`run-cli execute custom-workflow <workflow_name> '<json_initial_input>'`). Note that the input for CLI must be a valid JSON string.
-   From within another Custom Workflow.
-   From the Aurite class (mainly for packaged verison of the framework)

## Component Documentation Links

-   [Agent Configurations (AgentConfig)](./agent.md)
-   [Simple Workflow Configurations (WorkflowConfig)](./simple_workflow.md)
-   [Project Configurations (ProjectConfig)](./PROJECT.md): Custom Workflows are included in a project.
-   The `ExecutionFacade` class (`src/aurite/execution/facade.py`) documentation would be relevant for understanding how to use the `executor` object.
