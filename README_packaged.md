# Aurite Agent Framework

Aurite is a Python framework designed for developing and running sophisticated AI agents. It provides tools for managing configurations, orchestrating agent workflows, and interacting with various Language Models (LLMs) and external services via the Model Context Protocol (MCP).

## Installation and Setup

For detailed instructions on how to install the `aurite` package and set up your first project, please see the [Package Installation Guide](docs/package_installation_guide.md).

## Getting Started

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

From this point, the framework operates the same as it does in the aurite-agents repository README. See this document for more information: **[README](https://github.com/Aurite-ai/aurite-agents)**
## Path Resolution

Aurite determines the **root of your project (`current_project_root`)** as the directory containing the main project configuration file (by default, `aurite_config.json` created by `aurite init`).

Paths for component configurations (e.g., in `config/agents/agents.json`), custom workflow Python modules (`module_path` like `custom_workflows.example_workflow`), and MCP server scripts (`server_path` like `mcp_servers/weather_mcp_server.py`) defined within your `aurite_config.json` or individual component JSON files are **resolved relative to this `current_project_root`**.

**Example:** If your project is `your_project_name/` and it contains `your_project_name/aurite_config.json`, then `current_project_root` is `your_project_name/`. A `module_path` like `custom_workflows.example_workflow` (referencing `your_project_name/custom_workflows/example_workflow.py`) or a `server_path` like `mcp_servers/weather_mcp_server.py` (referencing `your_project_name/mcp_servers/weather_mcp_server.py`) will be correctly resolved.

**Integrating into Existing Projects (Nested `aurite_config.json`):**

If you are integrating Aurite into an existing project and choose to place your main project configuration file (e.g., `aurite_config.json`) in a subdirectory (e.g., `my_existing_app/aurite_setup/aurite_config.json`), then `current_project_root` will be `my_existing_app/aurite_setup/` (assuming you point Aurite to this specific config file, see "Locating Your Project Configuration" below).

To reference files outside this specific `current_project_root` (e.g., an MCP server script located at `my_existing_app/scripts/my_server.py`), you will need to use `../` in your path strings within the configuration files. For instance, the `server_path` would be `../scripts/my_server.py`.

For more details on project structure and configuration, see [`docs/components/project_configs.md`](https://publish.obsidian.md/aurite/components/PROJECT).

## Further Information

For more detailed documentation on component configuration, advanced features, and best practices, please refer to:
*   The official documentation site: [https://publish.obsidian.md/aurite/HOME](https://publish.obsidian.md/aurite/HOME)
*   The main project repository: [https://github.com/Aurite-ai/aurite-agents](https://github.com/Aurite-ai/aurite-agents)
