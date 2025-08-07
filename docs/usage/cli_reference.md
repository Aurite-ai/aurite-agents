# Aurite CLI Reference

The Aurite Command Line Interface (CLI) is the primary tool for interacting with the Aurite framework. It allows you to initialize projects, manage configurations, run agents and workflows, and start various services and tools.

This document provides a comprehensive reference for all available CLI commands.

## Global Options

These options can be used with the base `aurite` command.

-   `--install-completion`: Installs shell completion for the `aurite` command.
-   `--show-completion`: Displays the shell completion script to be sourced or saved manually.
-   `--help`: Shows the main help message listing all commands.

## Command Reference

The following sections detail each of the main `aurite` commands.

---

### `aurite init`

Initializes a new Aurite project or workspace. Workspaces are used to manage multiple projects, while projects contain the actual component configurations.

**Usage:**

```bash
aurite init [OPTIONS] [NAME]
```

**Arguments:**

-   `[NAME]`: An optional name for the new project or workspace.

**Options:**

-   `-p`, `--project`: Initialize a new project.
-   `-w`, `--workspace`: Initialize a new workspace.

**Behavior:**

-   Running `aurite init` without options starts an interactive wizard to guide you through creating a project or workspace (RECOMMENDED).
-   `aurite init --project my_new_project`: Creates a new project directory named `my_new_project` with the standard Aurite project structure.
-   `aurite init --workspace my_workspace`: Creates a new workspace directory named `my_workspace`, ready to contain multiple projects.

---

### `aurite api`

Starts the Aurite FastAPI server, which exposes the framework's functionality via a REST API.

**Usage:**

```bash
aurite api
```

This command is used to power web frontends, programmatic integrations, and other services that need to interact with Aurite over HTTP.

---

### `aurite list`

Inspects and lists configurations for different component types.

**Usage:**

```bash
aurite list [COMMAND]
```

If run without a subcommand, `aurite list` displays a complete index of all available components.

**Subcommands:**

-   `aurite list all`: Lists all available component configurations, grouped by type.
-   `aurite list agents`: Lists all available agent configurations.
-   `aurite list llms`: Lists all available LLM configurations.
-   `aurite list mcp_servers`: Lists all available MCP server configurations.
-   `aurite list simple_workflows`: Lists all available simple workflow configurations.
-   `aurite list custom_workflows`: Lists all available custom workflow configurations.
-   `aurite list workflows`: Lists all workflow configurations (both simple and custom).
-   `aurite list index`: Prints the entire component index as a formatted table, including name, type, and source file path.

---

### `aurite show`

Displays the detailed configuration for a specific component or all components of a certain type.

**Usage:**

```bash
aurite show [OPTIONS] <NAME_OR_TYPE>
```

**Arguments:**

-   `<NAME_OR_TYPE>`: The name of a specific component (e.g., `my_agent`) or a component type (e.g., `agents`).

**Options:**

-   `-f`, `--full`: Display the complete, unabridged configuration.
-   `-s`, `--short`: Display a compact, summary view.

**Behavior:**

-   `aurite show my_agent`: Displays the default, detailed view for the component named `my_agent`.
-   `aurite show agents`: Displays a summary view for all components of type `agent`.
-   `aurite show my_llm --full`: Shows every configuration key and value for the `my_llm` component.

---

### `aurite run`

Executes a runnable framework component, such as an agent or a workflow.

**Usage:**

```bash
aurite run [OPTIONS] [NAME] [USER_MESSAGE]
```

**Arguments:**

-   `[NAME]`: The name of the component to run.
-   `[USER_MESSAGE]`: The initial user message or input to provide to the component.

**Behavior:**

-   **Interactive Chat (Agents):** If you run an agent by `NAME` without providing a `USER_MESSAGE`, Aurite will launch a full-featured interactive chat TUI.
    ```bash
    aurite run my_chat_agent
    ```
-   **Single-Shot Execution:** If you provide a `USER_MESSAGE`, the component will run once, and the output will be streamed to your terminal.
    ```bash
    aurite run my_task_agent "Summarize this text for me."
    ```
-   **Workflow Execution:** Workflows require an initial input to start.
    ```bash
    aurite run my_data_workflow '{"input_file": "/path/to/data.csv"}'
    ```

**Options:**

-   `--system-prompt TEXT`: Override the agent's default system prompt for this run.
-   `-id`, `--session-id TEXT`: Specify a session ID to maintain conversation history across runs. If not provided, a new one is generated for chats.
-   `-s`, `--short`: Display a compact, one-line summary of the run output.
-   `-d`, `--debug`: Display the full, raw event stream for debugging purposes.

---

### `aurite edit`

Starts the Aurite configuration editor TUI, a powerful terminal-based interface for creating and modifying component configurations.

**Usage:**

```bash
aurite edit [COMPONENT_NAME]
```

**Arguments:**

-   `[COMPONENT_NAME]`: (Optional) The name of a component to open directly for editing.

**Interface:**

-   The TUI features a three-pane layout:
    1.  **Navigation Tree (Left):** Browse components by type.
    2.  **Component List (Middle):** View all components of the selected type.
    3.  **Editor (Right):** Edit the configuration of the selected component using interactive widgets.
-   The editor provides fields for names, descriptions, system prompts, and allows you to select LLM configurations and MCP servers from dropdowns.
-   Changes can be saved directly to the appropriate configuration files.
