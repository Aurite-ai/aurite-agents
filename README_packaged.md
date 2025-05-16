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
├── aurite_config.json        # Main project configuration file
├── config/                   # Directory for component configurations
│   ├── agents/
│   │   └── example_agent.json
│   ├── clients/
│   │   └── example_clients.json
│   ├── custom_workflows/
│   ├── llms/
│   │   └── default_llms.json
│   └── workflows/
├── custom_workflow_src/      # Python modules for your custom workflows
│   └── __init__.py
└── mcp_servers/              # Scripts for any custom MCP servers
```

### 2. Understanding Project Root and Path Resolution

Aurite determines the **root of your project (`current_project_root`)** as the directory containing the `aurite_config.json` file that you specify via the `PROJECT_CONFIG_PATH` environment variable.

Paths for component configurations (e.g., in `config/agents/`), custom workflow Python modules (`module_path`), and MCP server scripts (`server_path`) defined within your `aurite_config.json` or individual component JSON files are **resolved relative to this `current_project_root`**.

**Example:** If `PROJECT_CONFIG_PATH` is `/path/to/your_project_name/aurite_config.json`, then `current_project_root` is `/path/to/your_project_name/`. A `module_path` like `custom_workflow_src/my_flow.py` will resolve to `/path/to/your_project_name/custom_workflow_src/my_flow.py`.

**Integrating into Existing Projects (Nested `aurite_config.json`):**

If you are integrating Aurite into an existing project and choose to place your `aurite_config.json` file in a subdirectory (e.g., `my_existing_app/aurite_setup/aurite_config.json`), then `current_project_root` will be `my_existing_app/aurite_setup/`.

To reference files outside this specific `current_project_root` (e.g., an MCP server script located at `my_existing_app/scripts/my_server.py`), you will need to use `../` in your path strings within the configuration files. For instance, the `server_path` would be `../scripts/my_server.py`.

### 3. Understanding `aurite_config.json`

The `aurite_config.json` file at the root of your new project is the central configuration file. It defines the project's name, description, and lists the agents, LLMs, clients (MCP servers), simple workflows, and custom workflows that are part of this project.

Initially, it will look something like this:
```json
{
    "name": "your_project_name",
    "description": "A new Aurite Agents project: your_project_name",
    "clients": [],
    "llms": [],
    "agents": [],
    "simple_workflows": [],
    "custom_workflows": []
}
```
You will populate the arrays (e.g., `agents`, `custom_workflows`) with references to your component configuration files.

### 4. Locating Your Project Configuration

When you initialize the Aurite application (e.g., `app = Aurite()`), it determines the path to your main project configuration file (`aurite_config.json`) in the following order:

1.  **Directly Passed Argument:** If you provide a `config_path` when creating an `Aurite` instance (e.g., `Aurite(config_path=Path("my_specific_config.json"))`), that path will be used.
2.  **`PROJECT_CONFIG_PATH` Environment Variable:** If no `config_path` is passed to the constructor, Aurite checks for the `PROJECT_CONFIG_PATH` environment variable. If set, its value is used.
    ```bash
    export PROJECT_CONFIG_PATH=/path/to/your_project_name/aurite_config.json
    ```
    *(Adjust the path accordingly. You can use `$(pwd)/aurite_config.json` if you are inside `your_project_name` directory.)*
3.  **Default:** If neither of the above is provided, Aurite defaults to looking for a file named `aurite_config.json` in the current working directory from where your script is run.

For most cases after running `aurite init your_project_name` and navigating into `your_project_name/`, setting `PROJECT_CONFIG_PATH` or relying on the default (if your script is also in `your_project_name/`) is common.

```bash
export PROJECT_CONFIG_PATH=/path/to/your_project_name/aurite_config.json
```
*(Adjust the path accordingly. You can use `$(pwd)/aurite_config.json` if you are inside `your_project_name` directory.)*

Remember, all relative paths specified in your configurations will be based on the directory containing this `aurite_config.json` file.

## Example: Setting up a Custom Workflow with an Agent

Let's create a simple custom workflow that uses an agent.

### Step 1: Define your Agent

Create an agent configuration file, for example, `your_project_name/config/agents/my_query_agent.json`:

```json
{
  "name": "MyQueryAgent",
  "system_prompt": "You are a helpful assistant. Please answer the user's query.",
  "llm_config_id": "default_anthropic_haiku", // Assumes an LLM config with this ID exists
  "client_ids": [], // No external tools for this simple agent
  "auto": false,
  "include_history": true
}
```

### Step 2: Define your LLM Configuration (Optional)

If you're not using a pre-defined LLM configuration (like one from the examples copied by `aurite init`), define one in `your_project_name/config/llms/my_llms.json`:

```json
[ // Note: LLM config files usually contain a list
  {
    "llm_id": "default_anthropic_haiku",
    "provider": "anthropic",
    "model_name": "claude-3-haiku-20240307",
    "temperature": 0.7,
    "max_tokens": 1024,
    "default_system_prompt": "You are a helpful AI assistant."
  }
]
```
*(Ensure your Anthropic API key is set in your environment, e.g., `ANTHROPIC_API_KEY`)*

### Step 3: Create your Custom Workflow Python Module

Create a Python file for your custom workflow, e.g., `your_project_name/custom_workflow_src/my_processing_workflow.py`:

```python
# your_project_name/custom_workflow_src/my_processing_workflow.py
import logging

logger = logging.getLogger(__name__)

class MyWorkflow:
    async def execute_workflow(self, initial_input: dict, executor, session_id: str | None = None):
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
*Remember to make `custom_workflow_src` a package by ensuring it has an `__init__.py` file (which `aurite init` creates).*

**Note on Imports within your Custom Workflow:**
*   **Internal Imports (within `custom_workflow_src`):** For imports within your workflow file that refer to other Python files in the same `custom_workflow_src` directory (e.g., utility modules), use relative imports: `from . import my_utils` or `from .my_utils import some_function`. These work automatically because `custom_workflow_src` is a package.
*   **External Imports (from your broader project):** If your custom workflow needs to import modules from other parts of your project (e.g., from your application's main `src` folder located outside the `your_project_name` directory created by `aurite init`), you must ensure those modules are discoverable by Python. This typically involves:
    *   Adding your project's main source directory (e.g., `path/to/your_actual_project_root/src`) to the `PYTHONPATH` environment variable.
    *   Or, if your broader project is a package, installing it in editable mode (`pip install -e .` from that project's root).
    *   Or, ensuring you run your Aurite application from a directory that Python considers a root for your project's packages.

### Step 4: Define your Custom Workflow Configuration

Create a JSON configuration file for your custom workflow, e.g., `your_project_name/config/custom_workflows/main_processing.json`:

```json
{
  "name": "MainProcessingWorkflow",
  "module_path": "custom_workflow_src/my_processing_workflow.py", // Path relative to project root
  "class_name": "MyWorkflow",
  "description": "A workflow that uses MyQueryAgent to process a query."
}
```

### Step 5: Update `aurite_config.json`

Now, update your main `your_project_name/aurite_config.json` to include these new components:

```json
{
  "name": "your_project_name",
  "description": "A new Aurite Agents project: your_project_name",
  "clients": [], // Add any client (MCP server) configs here if needed
  "llms": [
    "config/llms/default_llms.json" // Copied by init
    // Add "config/llms/my_llms.json" if you created a custom one
  ],
  "agents": [
    "config/agents/example_agent.json", // Copied by init
    "config/agents/my_query_agent.json" // Your new agent
  ],
  "simple_workflows": [],
  "custom_workflows": [
    "config/custom_workflows/main_processing.json" // Your new custom workflow
  ]
}
```
*(Paths are relative to the location of `aurite_config.json`)*

### Step 6: Running your Custom Workflow

Create a Python script (e.g., `run_my_workflow.py` in `your_project_name`) to execute your workflow:

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

For more detailed documentation on component configuration, advanced features, and best practices, please refer to the main project repository and future documentation site (links to be added).
