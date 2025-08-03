# :material-language-python: Custom Workflow Configuration

When a `linear_workflow` isn't enough to capture your logic, you can implement a **Custom Workflow** directly in Python. This gives you complete control over the execution flow, allowing for conditional logic, branching, looping, and complex data manipulation between steps.

A custom workflow configuration is a JSON or YAML object with a `type` field set to `"custom_workflow"`. Its purpose is to link a component name to your Python code.

<!-- prettier-ignore -->
!!! info "How It Works"
    1. **Configuration:** You create a config file that gives your workflow a `name` and points to the `module_path` and `class_name` of your Python code.
    2. **Implementation:** You write a Python class that inherits from `aurite.BaseCustomWorkflow` and implements the `run` method.
    3. **Execution:** When you run the workflow by its `name`, the framework dynamically loads your Python class, instantiates it, and calls its `run` method, passing in the initial input and an execution engine.

---

## Schema and Implementation

Configuring a custom workflow involves two parts: the configuration file and the Python implementation.

=== ":material-file-document-outline: Configuration Schema"

    The configuration file tells the framework where to find your Python code.

    | Field         | Type     | Required | Description                                                                                             |
    |---------------|----------|----------|---------------------------------------------------------------------------------------------------------|
    | `name`        | `string` | Yes      | A unique identifier for the custom workflow.                                                            |
    | `description` | `string` | No       | A brief, human-readable description of what the workflow does.                                          |
    | `module_path` | `string` | Yes      | The path to the Python file containing your workflow class, relative to your project's root directory.  |
    | `class_name`  | `string` | Yes      | The name of the class within the module that implements the workflow.                                   |

=== ":material-code-braces: Python Implementation"

    Your Python class must inherit from `BaseCustomWorkflow` and implement the `run` method.

    ```python
    from typing import Any, Optional
    from aurite import AuriteEngine, BaseCustomWorkflow, AgentRunResult

    class MyWorkflow(BaseCustomWorkflow):
        async def run(
            self,
            initial_input: Any,
            executor: "AuriteEngine",
            session_id: Optional[str] = None
        ) -> Any:
            # Your custom logic goes here
            print(f"Workflow started with input: {initial_input}")

            # You can run agents using the executor instance passed to this method
            result: AgentRunResult = await executor.run_agent(
                agent_name="my-agent",
                user_message="What is the weather in SF?",
                session_id=session_id # Pass the session_id for history
            )

            return {"final_output": result.message_content}

        def get_input_type(self) -> Any:
            """(Optional) Returns the expected type of `initial_input`."""
            return str

        def get_output_type(self) -> Any:
            """(Optional) Returns the expected type of the workflow's final output."""
            return dict
    ```

    **Key Components:**

    - **`BaseCustomWorkflow`**: The required base class from `aurite`.
    - **`run(self, initial_input, executor, session_id)`**: The main entry point for your workflow's logic. This method must be implemented.
        - `initial_input`: The data passed to the workflow when it's executed.
        - `executor`: An instance of `AuriteEngine`, which allows you to run other components like agents (`executor.run_agent(...)`).
        - `session_id`: An optional session ID for maintaining conversation history.
    - **`get_input_type()` (Optional)**: A method that returns the expected Python type for `initial_input`. This can be used for documentation or validation.
    - **`get_output_type()` (Optional)**: A method that returns the expected Python type for the value your `run` method returns.

---

## :material-code-json: End-to-End Example

This example shows how to create a custom workflow that intelligently routes a task to one of two agents based on the input. The file structure illustrates how the `module_path` is relative to the directory containing the `.aurite` file.

=== "1. Project Structure"

    ```
    my_project/
    ├── .aurite
    ├── config/
    │   └── workflows/
    │       └── routing_workflow.json  <-- Configuration File
    └── custom_workflows/
        └── my_routing_logic.py      <-- Python Implementation
    ```

=== "2. Configuration File"

    `my_project/config/workflows/routing_workflow.json`

    ```json
    {
      "type": "custom_workflow",
      "name": "intelligent-routing-workflow",
      "description": "A workflow that dynamically routes tasks to different agents based on input content.",
      "module_path": "custom_workflows/my_routing_logic.py",
      "class_name": "MyRoutingWorkflow"
    }
    ```

=== "3. Python Implementation"

    `my_project/custom_workflows/my_routing_logic.py`

    ```python
    from typing import Any, Dict, Optional
    from aurite import AuriteEngine, BaseCustomWorkflow, AgentRunResult

    class MyRoutingWorkflow(BaseCustomWorkflow):
        """
        This workflow checks the input for keywords and routes the request
        to either a weather agent or a calculator agent.
        """
        async def run(
            self,
            initial_input: Dict[str, Any],
            executor: "AuriteEngine",
            session_id: Optional[str] = None
        ) -> AgentRunResult:
            user_message = initial_input.get("message", "")

            if "weather" in user_message.lower():
                agent_to_run = "weather-agent"
            elif "calculate" in user_message.lower():
                agent_to_run = "calculator-agent"
            else:
                agent_to_run = "general-qa-agent"

            print(f"Routing to agent: {agent_to_run}")

            # Run the selected agent using the provided executor
            result = await executor.run_agent(
                agent_name=agent_to_run,
                user_message=user_message,
                session_id=session_id
            )
            return result
    ```
