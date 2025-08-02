# :material-console: CLI Reference

The Aurite Command Line Interface (CLI) is the primary tool for interacting with the Aurite framework. It allows you to initialize projects, manage configurations, run agents and workflows, and start services.

---

## Global Options

These options can be used with the base `aurite` command.

| Option                 | Description                                                           |
| ---------------------- | --------------------------------------------------------------------- |
| `--install-completion` | Installs shell completion for the `aurite` command.                   |
| `--show-completion`    | Displays the shell completion script to be sourced or saved manually. |
| `--help`               | Shows the main help message listing all commands.                     |

---

## Commands

The CLI is organized into several main commands.

=== ":material-rocket-launch: `aurite init`"

    Initializes a new Aurite project or workspace.

    | Argument / Option | Type | Description |
    | --- | --- | --- |
    | `[NAME]` | `string` | An optional name for the new project or workspace. |
    | `-p`, `--project` | `flag` | Initialize a new project. |
    | `-w`, `--workspace` | `flag` | Initialize a new workspace. |

    !!! info "Interactive Wizard"
        Running `aurite init` without options starts an interactive wizard to guide you through creating a project or workspace (recommended).

=== ":material-format-list-bulleted: `aurite list`"

    Inspects and lists configurations for different component types. If run without a subcommand, it displays a complete index of all available components.

    | Subcommand | Description |
    | --- | --- |
    | `all` | Lists all available component configurations, grouped by type. |
    | `agents` | Lists all available agent configurations. |
    | `llms` | Lists all available LLM configurations. |
    | `mcp_servers` | Lists all available MCP server configurations. |
    | `linear_workflows` | Lists all available linear workflow configurations. |
    | `custom_workflows` | Lists all available custom workflow configurations. |
    | `workflows` | Lists all workflow configurations (both linear and custom). |
    | `index` | Prints the entire component index as a formatted table. |

=== ":material-eye: `aurite show`"

    Displays the detailed configuration for a specific component or all components of a certain type.

    | Argument / Option | Type | Description |
    | --- | --- | --- |
    | `<NAME_OR_TYPE>` | `string` | The name of a specific component (e.g., `my_agent`) or a component type (e.g., `agents`). |
    | `-f`, `--full` | `flag` | Display the complete, unabridged configuration. |
    | `-s`, `--short` | `flag` | Display a compact, summary view. |

=== ":material-play: `aurite run`"

    Executes a runnable framework component, such as an agent or a workflow.

    | Argument / Option | Type | Description |
    | --- | --- | --- |
    | `[NAME]` | `string` | The name of the component to run. |
    | `[USER_MESSAGE]` | `string` | The initial user message or input to provide to the component. |
    | `--system-prompt` | `string` | Override the agent's default system prompt for this run. |
    | `-id`, `--session-id` | `string` | Specify a session ID to maintain conversation history. |
    | `-s`, `--short` | `flag` | Display a compact, one-line summary of the run output. |
    | `-d`, `--debug` | `flag` | Display the full, raw event stream for debugging. |

    !!! abstract "Execution Behavior"
        - **Interactive Chat:** Running an agent by `NAME` without a `USER_MESSAGE` launches an interactive chat TUI.
        - **Single-Shot:** Providing a `USER_MESSAGE` runs the component once and streams the output to the terminal.

=== ":material-api: `aurite api`"

    Starts the Aurite FastAPI server, which exposes the framework's functionality via a REST API. This is used to power web frontends and programmatic integrations.

    ```bash
    aurite api
    ```

=== ":material-pencil: `aurite edit`"

    Starts the Aurite configuration editor TUI, a powerful terminal-based interface for creating and modifying component configurations.

    | Argument | Type | Description |
    | --- | --- | --- |
    | `[COMPONENT_NAME]` | `string` | (Optional) The name of a component to open directly for editing. |

    !!! info "TUI Interface"
        The editor features a three-pane layout for navigation, component listing, and editing, with interactive widgets and dropdowns for easy configuration.
