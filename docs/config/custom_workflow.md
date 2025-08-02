# :material-language-python: Custom Workflow Configuration

When a `linear_workflow` isn't enough to capture your logic, you can implement a **Custom Workflow** directly in Python. This gives you complete control over the execution flow, allowing for conditional logic, branching, looping, and complex data manipulation between steps.

A custom workflow configuration is a JSON or YAML object with a `type` field set to `"custom_workflow"`. Its purpose is to link a component name to your Python code.

!!! info "How It Works" 1. **Configuration:** You create a config file that gives your workflow a `name` and points to the `module_path` and `class_name` of your Python code. 2. **Implementation:** You write a Python class that inherits from `BaseCustomWorkflow` and implements the `run` method. 3. **Execution:** When you run the workflow by its `name`, the framework dynamically loads your Python class, instantiates it, and calls its `run` method.

---

## Schema and Implementation

Configuring a custom workflow involves two parts: the configuration file and the Python implementation.

=== ":material-file-document-outline: Configuration Schema"

    The configuration file tells the framework where to find your Python code.

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `name` | `string` | Yes | A unique identifier for the custom workflow. |
    | `description` | `string` | No | A brief, human-readable description of what the workflow does. |
    | `module_path` | `string` | Yes | The path to the Python file containing your workflow class, relative to the `.aurite` file of its context. |
    | `class_name` | `string` | Yes | The name of the class within the module that implements the workflow. |

=== ":material-code-braces: Python Implementation"

    Your Python class must inherit from `BaseCustomWorkflow` and implement the `run` method.

    ```python
    from aurite.lib.models.config import BaseCustomWorkflow, AgentRunResult
    from typing import Any, Optional

    class MyWorkflow(BaseCustomWorkflow):
        async def run(self, initial_input: Any) -> Any:
            # Your custom logic goes here
            print(f"Workflow started with input: {initial_input}")

            # You can run agents using the helper method
            result: AgentRunResult = await self.run_agent(
                agent_name="my-agent",
                user_message="What is the weather in SF?"
            )

            return {"final_output": result.message_content}
    ```

    **Key Components:**
    -   **`BaseCustomWorkflow`**: The required base class.
    -   **`run(self, initial_input: Any) -> Any`**: The main entry point for your workflow's logic. This method must be implemented.
    -   **`run_agent(...)`**: A helper method provided by the base class to execute agents managed by the framework. It returns an `AgentRunResult` object.
    -   **`self.executor`**: An instance of the `AuriteEngine`, provided by the framework, which gives you access to core execution capabilities.

---

## :material-code-json: End-to-End Example

This example shows how to create a custom workflow that intelligently routes a task to one of two agents based on the input.

=== "1. Configuration File"
`config/workflows/routing_workflow.json`
`json
    {
      "type": "custom_workflow",
      "name": "intelligent-routing-workflow",
      "description": "A workflow that dynamically routes tasks to different agents based on input content.",
      "module_path": "custom_workflows/my_routing_logic.py",
      "class_name": "MyRoutingWorkflow"
    }
    `

=== "2. Python Implementation"
`custom_workflows/my_routing_logic.py`
```python
from aurite.lib.models.config import BaseCustomWorkflow, AgentRunResult
from typing import Any, Dict

    class MyRoutingWorkflow(BaseCustomWorkflow):
        """
        This workflow checks the input for keywords and routes the request
        to either a weather agent or a calculator agent.
        """
        async def run(self, initial_input: Dict[str, Any]) -> AgentRunResult:
            user_message = initial_input.get("message", "")

            if "weather" in user_message.lower():
                agent_to_run = "weather-agent"
            elif "calculate" in user_message.lower():
                agent_to_run = "calculator-agent"
            else:
                agent_to_run = "general-qa-agent"

            print(f"Routing to agent: {agent_to_run}")

            # Run the selected agent and return its result directly
            result = await self.run_agent(
                agent_name=agent_to_run,
                user_message=user_message
            )
            return result
