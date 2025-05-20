# Aurite Agent Framework

Aurite is a Python framework designed for developing and running sophisticated AI agents. It provides tools for managing configurations, orchestrating agent workflows, and interacting with various Language Models (LLMs) and external services via the Model Context Protocol (MCP).

## Installation

You can install Aurite using pip.

**From PyPI (once published):**
```bash
pip install aurite
```

**From a local wheel file (for current testing):**
```bash
pip install /path/to/your/aurite-agents/dist/aurite-0.2.0-py3-none-any.whl
```
*(Replace with the actual path and filename of your generated wheel.)*

## Getting Started

### 1. Initialize a New Project

After installing the `aurite` package, you can create a new project structure using the CLI:

```bash
aurite init (optional project name)
```
This command will scaffold a new directory with the following structure:

```
your_project_name/
├── aurite_config.json              # Main project configuration file (references components)
├── config/                         # Directory for component configurations
│   ├── agents/
│   │   └── agents.json             # Example agent configurations
│   ├── clients/
│   │   └── clients.json            # Example client configurations
│   ├── custom_workflows/
│   │   └── custom_workflows.json   # Example custom workflow configurations
│   ├── llms/
│   │   └── llms.json               # Example LLM configurations
│   ├── workflows/
│   │   └── simple_workflows.json   # Example simple workflow configurations
│   └── testing/
│       └── planning_agent_test.json # Example test configuration
├── custom_workflows/               # Python modules for your custom workflows
│   ├── __init__.py
│   └── example_workflow.py         # Example custom workflow Python code
├── mcp_servers/                    # Scripts for any custom MCP servers
│   ├── weather_mcp_server.py
│   └── planning_server.py
└── run_example_project.py          # Script to run an example
```

### 2. Understanding Project Root and Path Resolution

Aurite determines the **root of your project (`current_project_root`)** as the directory containing the main project configuration file (by default, `aurite_config.json` created by `aurite init`).

Paths for component configurations (e.g., in `config/agents/agents.json`), custom workflow Python modules (`module_path` like `custom_workflows.example_workflow`), and MCP server scripts (`server_path` like `mcp_servers/weather_mcp_server.py`) defined within your `aurite_config.json` or individual component JSON files are **resolved relative to this `current_project_root`**.

**Example:** If your project is `your_project_name/` and it contains `your_project_name/aurite_config.json`, then `current_project_root` is `your_project_name/`. A `module_path` like `custom_workflows.example_workflow` (referencing `your_project_name/custom_workflows/example_workflow.py`) or a `server_path` like `mcp_servers/weather_mcp_server.py` (referencing `your_project_name/mcp_servers/weather_mcp_server.py`) will be correctly resolved.

**Integrating into Existing Projects (Nested `aurite_config.json`):**

If you are integrating Aurite into an existing project and choose to place your main project configuration file (e.g., `aurite_config.json`) in a subdirectory (e.g., `my_existing_app/aurite_setup/aurite_config.json`), then `current_project_root` will be `my_existing_app/aurite_setup/` (assuming you point Aurite to this specific config file, see "Locating Your Project Configuration" below).

To reference files outside this specific `current_project_root` (e.g., an MCP server script located at `my_existing_app/scripts/my_server.py`), you will need to use `../` in your path strings within the configuration files. For instance, the `server_path` would be `../scripts/my_server.py`.

For more details on project structure and configuration, see [`docs/components/project_configs.md`](https://publish.obsidian.md/aurite/components/project_configs).

### 3. Understanding `aurite_config.json`

The `aurite_config.json` file at the root of your new project (created by `aurite init`) is the central configuration file. It defines the project's name, description, and lists the agents, LLMs, clients (MCP servers), simple workflows, and custom workflows that are part of this project by referencing other JSON configuration files.

Initially, it will look something like this. Note that component lists (like `llms`, `clients`, `agents`, etc.) can contain:
1.  Directly embedded JSON objects defining the component.
2.  Strings that are paths to other JSON files (which themselves contain lists of component definitions).
3.  Strings that are component IDs/names (if those components are defined elsewhere, e.g., in one of the referenced files, or are globally available).

```json
// Example: your_project_name/aurite_config.json
{
  "name": "your_project_name",
  "description": "A new Aurite Agents project: your_project_name",
  "llms": [
    // LLM configurations can be defined directly
    {
      "llm_id": "default_llm_config",
      "provider": "anthropic", // or "openai", "google", etc.
      "model_name": "claude-3-haiku-20240307", // replace with your model
      "temperature": 0.7,
      "max_tokens": 1024
    }
    // You can also list paths to files containing more LLM configs, e.g.,
    // "config/llms/additional_llms.json"
  ],
  "clients": [
    // Reference a client by its ID (if defined elsewhere or built-in)
    "a_globally_known_client_id",
    // Or define a client configuration directly
    {
      "client_id": "my_local_script_client",
      "server_path": "mcp_servers/my_script_server.py", // Relative to project root
      "capabilities": ["tools"]
    }
    // You can also list paths to files containing more Client configs, e.g.,
    // "config/clients/more_clients.json"
  ],
  "agents": [
    // Define an agent configuration directly
    {
      "name": "MyFirstAgent",
      "system_prompt": "You are a helpful assistant.",
      "llm_config_id": "default_llm_config",
      "client_ids": ["my_local_script_client"]
    }
    // You can also list paths to files containing more Agent configs, e.g.,
    // "config/agents/other_agents.json"
  ],
  "simple_workflows": [
    // Define a simple workflow directly
    {
      "name": "MySimpleSequence",
      "steps": ["MyFirstAgent", "another_agent_name_if_defined"]
    }
    // You can also list paths to files containing more Simple Workflow configs, e.g.,
    // "config/workflows/more_simple_workflows.json"
  ],
  "custom_workflows": [
    // Define a custom workflow directly
    {
      "name": "MyComplexProcess",
      // Assumes 'aurite init' creates 'custom_workflows/' for Python modules,
      // and 'my_custom_logic.py' is inside it.
      "module_path": "custom_workflows.my_custom_logic",
      "class_name": "MyCustomWorkflowClass"
    }
    // You can also list paths to files containing more Custom Workflow configs, e.g.,
    // "config/custom_workflows/more_custom_workflows.json"
  ]
}
```
You will typically edit the referenced files (e.g., `config/agents/agents.json` if you use file paths) or the main `aurite_config.json` to define your specific components.
For detailed information on `ProjectConfig` and how it references other component files, see [`docs/components/project_configs.md`](https://publish.obsidian.md/aurite/components/project_configs).

### 4. Locating Your Project Configuration

When you initialize the Aurite application (e.g., `app = Aurite()`), it determines the path to your main project configuration file in the following order:

1.  **Directly Passed Argument:** If you provide a `config_path` when creating an `Aurite` instance (e.g., `Aurite(config_path=Path("my_specific_config.json"))`), that path will be used.
2.  **`PROJECT_CONFIG_PATH` Environment Variable:** If no `config_path` is passed to the constructor, Aurite checks for the `PROJECT_CONFIG_PATH` environment variable. If set, its value is used. This is useful if you run your application from a directory different from your project root or use a non-standard config file name.
    ```bash
    export PROJECT_CONFIG_PATH=/path/to/your_project_name/aurite_config.json
    ```
3.  **Default:** If neither of the above is provided, Aurite defaults to looking for a file named `aurite_config.json` in the current working directory from where your script is run.

After running `aurite init your_project_name` and navigating into `your_project_name/`, running your Python scripts (like the example `run_example_project.py`) from within this directory will allow Aurite to find `aurite_config.json` by default.

Remember, all relative paths specified in your configurations (e.g., paths to other component JSON files, `server_path` for stdio clients, `module_path` for custom workflows) will be based on the directory containing the main project configuration file being used.

## Example: Setting up a Custom Workflow with an Agent

Let's create a simple custom workflow that uses an agent. This example assumes you've run `aurite init your_project_name` and are working within that directory.

### Step 1: Define your Agent

Create or modify an agent configuration file, for example, `your_project_name/config/agents/agents.json`. Add your new agent to the list in this file:

```json
// In your_project_name/config/agents/agents.json
[
  // ... any existing agents copied by `aurite init` ...
  {
    "name": "MyQueryAgent",
    "system_prompt": "You are a helpful assistant. Please answer the user's query.",
    "llm_config_id": "default_anthropic_haiku", // Assumes an LLM config with this ID exists in llms.json
    "client_ids": [], // No external tools for this simple agent
    "auto": false, // 'auto' mode for dynamic tool selection, false by default
    "include_history": true
  }
]
```
For more details on `AgentConfig`, see [`docs/components/agents.md`](https://publish.obsidian.md/aurite/components/agents).

### Step 2: Define your LLM Configuration (Ensure it Exists)

The `aurite init` command copies a `llms.json` file (e.g., `your_project_name/config/llms/llms.json`) with example LLM configurations. Ensure the `llm_config_id` used by your agent (e.g., "default_anthropic_haiku") exists in this file.
If you need a custom one:

```json
// In your_project_name/config/llms/llms.json
[
  // ... any existing LLM configs ...
  {
    "llm_id": "default_anthropic_haiku", // Ensure this matches agent's llm_config_id
    "provider": "anthropic",
    "model_name": "claude-3-haiku-20240307",
    "temperature": 0.7,
    "max_tokens": 1024,
    "default_system_prompt": "You are a helpful AI assistant."
  }
]
```
*(Ensure your Anthropic API key is set in your environment, e.g., `ANTHROPIC_API_KEY`)*.
For more details on `LLMConfig`, see [`docs/components/llms.md`](https://publish.obsidian.md/aurite/components/llms).

### Step 3: Create your Custom Workflow Python Module

Create a Python file for your custom workflow, e.g., `your_project_name/custom_workflows/my_processing_workflow.py` (note: `aurite init` creates the `custom_workflows` directory):

```python
# your_project_name/custom_workflows/my_processing_workflow.py
import logging
from aurite.execution.facade import ExecutionFacade # Import the facade

logger = logging.getLogger(__name__)

class MyWorkflow:
    async def execute_workflow(self, initial_input: dict, executor: ExecutionFacade, session_id: str | None = None):
        user_query = initial_input.get("query")
        if not user_query:
            return {"error": "No query provided in initial_input"}

        logger.info(f"Workflow received query: {user_query}")

        # Run the agent
        agent_result = await executor.run_agent(
            agent_name="MyQueryAgent",
            user_message=user_query,
            session_id=session_id
        )

        if agent_result.get("error"):
            logger.error(f"Agent run failed: {agent_result.get('error')}")
            return {"error": f"Agent error: {agent_result.get('error')}"}

        final_response_message = agent_result.get("final_response", {}).get("content", [{}])[0].get("text", "No response from agent.")

        processed_result = f"Workflow processed: Agent said - '{final_response_message}'"
        logger.info(f"Workflow returning: {processed_result}")
        return {"result": processed_result}

```
*The `aurite init` command creates `custom_workflows/__init__.py`, making it a package.*

**Note on Imports within your Custom Workflow:**
*   **Internal Imports (within `custom_workflows`):** For imports within your workflow file that refer to other Python files in the same `custom_workflows` directory, use relative imports: `from . import my_utils`.
*   **External Imports:** If your custom workflow needs to import modules from other parts of your broader project (outside the `your_project_name` directory), ensure those modules are discoverable by Python (e.g., via `PYTHONPATH` or by installing your main project in editable mode).

### Step 4: Define your Custom Workflow Configuration

Create or modify `your_project_name/config/custom_workflows/custom_workflows.json`. Add your new custom workflow to the list:

```json
// In your_project_name/config/custom_workflows/custom_workflows.json
[
  // ... any existing custom workflow configs ...
  {
    "name": "MainProcessingWorkflow",
    "module_path": "custom_workflows.my_processing_workflow", // Path relative to project root, using dot notation
    "class_name": "MyWorkflow",
    "description": "A workflow that uses MyQueryAgent to process a query."
  }
]
```
For more details on `CustomWorkflowConfig`, see [`docs/components/custom_workflows.md`](https://publish.obsidian.md/aurite/components/custom_workflows).

### Step 5: Ensure `aurite_config.json` References Component Files

The `aurite_config.json` file created by `aurite init` should already reference `config/agents/agents.json`, `config/llms/llms.json`, and `config/custom_workflows/custom_workflows.json`. Verify these paths are correct.

```json
// your_project_name/aurite_config.json (ensure these files are listed)
{
  "name": "your_project_name",
  "description": "A new Aurite Agents project: your_project_name",
  "clients": [
    "config/clients/clients.json" // Add client configs if needed. For details see https://publish.obsidian.md/aurite/components/clients
  ],
  "llms": [
    "config/llms/llms.json"
  ],
  "agents": [
    "config/agents/agents.json"
  ],
  "simple_workflows": [
    // "config/workflows/simple_workflows.json" // For simple workflows, see https://publish.obsidian.md/aurite/components/simple_workflows
  ],
  "custom_workflows": [
    "config/custom_workflows/custom_workflows.json"
  ]
}
```

### Step 6: Running your Custom Workflow

The `aurite init` command creates an example script `your_project_name/run_example_project.py`. You can modify this script or create a new one (e.g., `run_my_workflow.py` in `your_project_name`) to execute your workflow:

```python
# your_project_name/run_my_workflow.py
import asyncio
import os
from pathlib import Path
from aurite import Aurite # Changed from HostManager

async def main():
    # Aurite() will automatically use PROJECT_CONFIG_PATH or default to "aurite_config.json"
    # if no argument is passed. For this example, we'll rely on that.
    # If you need to specify a different path, you can do:
    # aurite_app = Aurite(config_path=Path("/custom/path/to/config.json"))

    # Ensure PROJECT_CONFIG_PATH is set if not passing config_path directly
    # or if not relying on the default "aurite_config.json" in CWD.
    if not os.getenv("PROJECT_CONFIG_PATH") and not Path("aurite_config.json").exists():
        print("Error: PROJECT_CONFIG_PATH not set and aurite_config.json not found in current directory.")
        print("Please set PROJECT_CONFIG_PATH or run this script from your project directory containing aurite_config.json.")
        return

    aurite_app = Aurite()

    try:
        await aurite_app.initialize()

        workflow_input = {"query": "What is the weather like in London today?"}
        session_id = "test_session_123" # Optional: for history tracking

        print(f"Running workflow 'MainProcessingWorkflow' with input: {workflow_input}")

        # Ensure the execution attribute is available after initialization
        if not aurite_app.execution:
            print("Error: Execution facade not initialized.")
            return

        result = await aurite_app.execution.run_custom_workflow(
            workflow_name="MainProcessingWorkflow",
            initial_input=workflow_input,
            session_id=session_id
        )

        print("\nWorkflow Result:")
        print(result)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if aurite_app.host: # Check if host was initialized
            await aurite_app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

To run this:
1.  Ensure `PROJECT_CONFIG_PATH` is set (or you are in the directory with `aurite_config.json` if relying on the default).
2.  Ensure any necessary API keys (e.g., `ANTHROPIC_API_KEY`) are set in your environment.
3.  Execute: `python your_project_name/run_my_workflow.py`

## Running the API Server (Optional)

If you want to interact with your Aurite project via a REST API, you can use the `aurite-api` command (this assumes `PROJECT_CONFIG_PATH` is set or `aurite_config.json` is in your CWD):

```bash
start-api
```
This will launch a Uvicorn server, typically on `http://0.0.0.0:8000`.

## Further Information

For more detailed documentation on component configuration, advanced features, and best practices, please refer to:
*   The official documentation site: [https://publish.obsidian.md/aurite/HOME](https://publish.obsidian.md/aurite/HOME)
*   The main project repository: [https://github.com/Aurite-ai/aurite-agents](https://github.com/Aurite-ai/aurite-agents)
