# Package Installation Guide

This guide walks you through installing the `aurite` Python package and setting up your first Aurite project. This is the recommended path for users who want to build applications using the Aurite framework.

For instructions on setting up the framework from the main repository (e.g., for development or contribution), please see the [Repository Installation Guide](./repository_installation_guide.md).

## Step 1: Environment Setup

Before installing, ensure your environment is ready.

1.  **Python >= 3.12:** The Aurite framework requires Python 3.12 or higher. Check your version with `python --version`.
2.  **Create a Workspace Directory:** Choose a location on your computer for your Aurite projects.
    ```bash
    mkdir my-aurite-workspace
    cd my-aurite-workspace
    ```
3.  **Activate a Virtual Environment:** It is highly recommended to use a virtual environment.
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```
4.  **Install the `aurite` package:**
    ```bash
    pip install aurite
    ```

## Step 2: Initialize Your Project

The `aurite init` command is the easiest way to get started. It runs an interactive wizard to create your workspace and first project.

1.  **Run the Interactive Wizard:**
    From your workspace directory (`my-aurite-workspace`), run:
    ```bash
    aurite init
    ```
2.  **Follow the Prompts:** The wizard will guide you through:
    *   Creating a `.aurite` file to define your workspace.
    *   Creating your first project directory (e.g., `my-first-project`).
    *   Generating a default `config` directory inside your project with example component configurations.
    *   Creating a `.env` file in your workspace root for your API keys.

3.  **Add Your API Key:**
    Open the newly created `.env` file in your workspace root and add your LLM API key(s), for example:
    ```env
    OPENAI_API_KEY="your-key-here"
    ANTHROPIC_API_KEY="your-key-here"
    ```

Your directory structure should now look like this:
```
my-aurite-workspace/
├── .aurite                   # Defines the workspace
├── .env                      # Your secret API keys
├── .venv/
└── my-first-project/
    ├── .aurite               # Defines the project
    ├── config/               # Your project's component configs
    │   ├── agents/
    │   ├── llms/
    │   └── ...
    ├── custom_workflows/     # Python source for custom workflows
    │   └── example_workflow.py
    ├── mcp_servers/          # Python source for MCP servers
    │   └── weather_server.py
    └── run_example_project.py  # Script to run an example
```
The `init` command populates your project with a rich set of examples, including multiple agent, LLM, and workflow configurations located in the `config/` directory. It also provides runnable Python source code for custom workflows and MCP servers.

For a deeper understanding of how projects and workspaces function, see the [Projects and Workspaces guide](../../config/projects_and_workspaces.md).

## Step 3: Start Building

With your project initialized, you're ready to start building and running components.

### Start the API Server

To interact with your project programmatically or via a UI, start the FastAPI server. From anywhere inside your workspace, run:

```bash
aurite api
```

The API will be available at `http://localhost:8000`.

### Next Steps

You now have a fully functional Aurite environment. Here are some resources to guide you:

-   **Explore the CLI:** Use the command line to manage your project. See the [**CLI Reference**](../../usage/cli_reference.md) for a full list of commands like `aurite list`, `aurite show`, and `aurite run`.
-   **Edit Configurations:** Use the built-in TUI to easily edit your agent, LLM, and other component configurations.
    ```bash
    aurite edit
    ```
    Learn more in the [**TUI Guide**](../../usage/tui_guide.md).
-   **Use the API:** Interact with the framework programmatically. The [**API Reference**](../../usage/api_reference.md) provides a complete overview of all available endpoints.
