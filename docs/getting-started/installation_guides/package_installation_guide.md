# Package Installation Guide

<!-- prettier-ignore -->
!!! tip "Quick Start"
    If you want a quick start we recommend starting with the [Quick Start Guide](../quick_start.md) to set up your first project quickly.

This guide walks you through installing the `aurite` Python package and setting up your first Aurite project. This is the recommended path for users who want to build applications using the Aurite framework.

<!-- prettier-ignore -->
!!! info "Need to install from the repository?"
    For instructions on setting up the framework from the main repository (e.g., if you plan to contribute to Aurite's framework), please see the [Repository Installation Guide](./repository_installation_guide.md). If this question confuses you, you probably do not need it.

## Setup Steps

=== "Environment Setup"

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
    5.  **Verify the installation:**
        ```bash
        aurite --version
        ```
        This should display the installed version of Aurite (e.g., `aurite 0.3.28`).

=== "Initialize Your Project"

    The `aurite init` command is the easiest way to get started. It runs an interactive wizard to create your workspace and first project.

    1.  **Run the Interactive Wizard:**
        From your workspace directory (`my-aurite-workspace`), run:
        ```bash
        aurite init
        ```
    2.  **Follow the Prompts:** The wizard will guide you through:

        - Creating a `.aurite` file to define your workspace.
        - Creating your first project directory (e.g., `my-first-project`).
        - Generating a default `config` directory inside your project with example component configurations.
        - Creating a `.env` file in your workspace root for your API keys.

    3.  **Add Your API Key:**
        Open the newly created `.env` file in your workspace root and add your LLM API key(s), for example:

        ```env
        OPENAI_API_KEY="your-key-here"
        ANTHROPIC_API_KEY="your-key-here"
        ```

        If you want to use the built-in Aurite API, you need to add an `API_KEY` to your .env file. You can set the value for this key to be anything you want, for example:

        ```env
        API_KEY=my_api_key
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

=== "Start Building"

    With your project initialized, you're ready to start building and running components.

    #### Use the CLI
    The Aurite CLI provides commands to manage your project, run agents, and workflows. For example, to run an agent, you can use:

    ```bash
    aurite run "Weather Agent" "What is the weather in London?"
    ```

    For a list of all available commands, you can run:
    ```bash
    aurite --help
    ```
    For more details on using the CLI, see the [CLI Reference](../../usage/cli_reference.md).

    #### Start the API Server

    To interact with your project programmatically or via a UI, start the FastAPI server. From anywhere inside your workspace, run:

    ```bash
    aurite api
    ```

    The API will be available at `http://localhost:8000`.

    For more details on the API endpoints, see the [API Reference](../../usage/api_reference.md).

    #### Launch Aurite Studio (Web UI)

    For the best development experience, use Aurite Studio - an integrated development environment that provides a web-based UI for managing your agents, workflows, and configurations. From anywhere inside your workspace, run:

    ```bash
    aurite studio
    ```

    This command will:
    - Automatically start the API server (if not already running)
    - Launch the React-based web interface at `http://localhost:8000/studio` (or the port you configured in your `.env` file)
    - Handle all frontend dependencies and build processes automatically
    - Open your default browser to the Studio interface

    Aurite Studio provides:
    - Visual agent configuration and testing
    - Workflow management and execution
    - LLM provider setup and testing
    - MCP server integration
    - Real-time execution monitoring

    <!-- prettier-ignore -->
    !!! info "System Requirements"
        Aurite Studio requires Node.js >= 18.0.0 and npm >= 8.0.0. The command will automatically check and try to install if these are missing.

    For advanced options like fresh rebuilds, see the [CLI Reference](../../usage/cli_reference.md#aurite-studio).

    #### Edit Configurations
    You can edit your component configurations using the `aurite edit` command, which opens a text editor for the specified component type. For example, to edit agents:
    ```bash
    aurite edit agents
    ```

    You can also edit these configurations directly in the `config/` directory using your preferred text editor. See the [Component Configurations guide](../../config/projects_and_workspaces.md) for more details on the configuration structure.

---
