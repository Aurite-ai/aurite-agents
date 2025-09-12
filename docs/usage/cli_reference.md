# :material-console: CLI Reference

The Aurite Command Line Interface (CLI) is the primary tool for interacting with the Aurite framework. It allows you to initialize projects, manage configurations, run agents and workflows, and start services.

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

    **Examples**

    ```bash
    # List all available agents
    aurite list agents

    # List all workflows (linear and custom)
    aurite list workflows
    ```

=== ":material-eye: `aurite show`"

    Displays the detailed configuration for a specific component or all components of a certain type.

    | Argument / Option | Type | Description |
    | --- | --- | --- |
    | `<NAME_OR_TYPE>` | `string` | The name of a specific component (e.g., `my_agent`) or a component type (e.g., `agents`). |
    | `-f`, `--full` | `flag` | Display the complete, unabridged configuration. |
    | `-s`, `--short` | `flag` | Display a compact, summary view. |

    **Examples**

    ```bash
    # Show the full configuration for the "Weather Agent"
    aurite show "Weather Agent" --full

    # Show a summary of all linear workflow configurations
    aurite show linear_workflows -s
    ```

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

    **Examples**

    ```bash
    # Run the "Weather Agent" in interactive chat mode
    aurite run "Weather Agent"

    # Run the "Weather Agent" once with a specific question
    aurite run "Weather Agent" "What is the weather in London?"

    # Run the "Weather Planning Workflow"
    aurite run "Weather Planning Workflow" "Plan a trip to Paris next week"

    # Run the "Example Custom Workflow" with JSON input
    aurite run "Example Custom Workflow" '{"city": "Tokyo"}'
    ```

=== ":material-api: `aurite api`"

    Starts the Aurite FastAPI server, which exposes the framework's functionality via a REST API. This is used to power web frontends and programmatic integrations.

    ```bash
    aurite api
    ```

=== ":material-desktop-mac: `aurite studio`"

    Starts the Aurite Studio integrated development environment, which launches both the API server and React frontend concurrently. This provides a unified development experience with automatic dependency management and graceful shutdown handling.

    | Option | Description |
    | --- | --- |
    | `--rebuild-fresh` | Clean all build artifacts and rebuild frontend packages from scratch |

    !!! info "Integrated Development Environment"
        The studio command automatically:

        - Validates Node.js and npm dependencies
        - Installs frontend workspace dependencies if needed
        - Builds frontend packages when artifacts are missing
        - Starts the API server (if not already running)
        - Launches the React development server on port 3000
        - Provides unified logging with `[API]` and `[STUDIO]` prefixes
        - Handles graceful shutdown with Ctrl+C

    **System Requirements**

    - Node.js >= 18.0.0
    - npm >= 8.0.0

    **Examples**

    ```bash
    # Start the integrated development environment
    aurite studio

    # Start with a fresh rebuild of frontend packages
    aurite studio --rebuild-fresh
    ```

    **Fresh Rebuild Process**

    When using `--rebuild-fresh`, the command performs:

    1. **Clean Build Artifacts**: Runs `npm run clean` to remove all build outputs
    2. **Clear npm Cache**: Removes `node_modules/.cache` directory
    3. **Rebuild Packages**: Runs `npm run build` to rebuild all workspace packages
    4. **Start Servers**: Proceeds with normal server startup

    **Ports Used**

    - API Server: Configured port (default 8000)
    - Studio UI: http://localhost:3000

=== ":material-pencil: `aurite edit`"

    Starts the Aurite configuration editor TUI, a powerful terminal-based interface for creating and modifying component configurations.

    | Argument | Type | Description |
    | --- | --- | --- |
    | `[COMPONENT_NAME]` | `string` | (Optional) The name of a component to open directly for editing. |

    !!! info "TUI Interface"
        The editor features a three-pane layout for navigation, component listing, and editing, with interactive widgets and dropdowns for easy configuration.

    **Examples**

    ```bash
    # Open the TUI editor
    aurite edit

    # Open the "Weather Agent" configuration directly in the editor
    aurite edit "Weather Agent"
    ```

=== ":material-database-arrow-right: `aurite migrate`"

    Migrates data between SQLite and PostgreSQL databases. This is useful when transitioning between development and production environments or creating backups.

    | Option | Type | Description |
    | --- | --- | --- |
    | `--source-type` | `string` | Source database type (`sqlite` or `postgresql`) |
    | `--target-type` | `string` | Target database type (`sqlite` or `postgresql`) |
    | `--source-path` | `string` | Path to source SQLite database (if source is SQLite) |
    | `--target-path` | `string` | Path to target SQLite database (if target is SQLite) |
    | `--from-env` | `flag` | Use current environment configuration as source |
    | `--verify/--no-verify` | `flag` | Verify migration after completion (default: verify) |

    !!! info "Interactive Mode"
        Running `aurite migrate` without options starts an interactive wizard that guides you through the migration process, using environment variables as defaults where available.

    **Examples**

    ```bash
    # Interactive migration wizard
    aurite migrate

    # Migrate from current database to opposite type
    aurite migrate --from-env

    # Migrate from SQLite to PostgreSQL (uses env vars for PostgreSQL)
    aurite migrate --source-type sqlite --target-type postgresql

    # Create a backup of production PostgreSQL to local SQLite
    aurite migrate \
      --source-type postgresql \
      --target-type sqlite \
      --target-path backups/aurite_backup.db
    ```

    !!! tip "Environment Variables"
        The migration command automatically uses your configured environment variables for database connections, making it easy to migrate between your configured databases.

=== ":material-database-export: `aurite export`"

    Exports all configurations from the file system to the database. This command reads from local config files and uploads them to your configured database (SQLite or PostgreSQL).

    **Examples**

    ```bash
    # Export all local configurations to the database
    aurite export
    ```

    !!! warning "Database Mode Required"
        This command requires `AURITE_ENABLE_DB=true` in your environment configuration. The database type and connection details are determined by your environment variables.

    **What Gets Exported**

    - All agent configurations
    - All LLM configurations
    - All MCP server configurations
    - All workflow configurations (linear and custom)
    - Any other component configurations in your workspace

=== ":material-docker: `aurite docker`"

    Manages Aurite Docker containers for containerized deployment and development. This command provides a complete Docker workflow from initialization to deployment.

    | Argument / Option | Type | Description |
    | --- | --- | --- |
    | `[ACTION]` | `string` | Docker action to perform (default: `run`) |
    | `-p`, `--project` | `string` | Path to Aurite project directory (default: current directory) |
    | `-n`, `--name` | `string` | Container name (default: `aurite-server`) |
    | `--port` | `integer` | Port to expose (default: `8000`) |
    | `-e`, `--env-file` | `string` | Path to environment file |
    | `-v`, `--version` | `string` | Docker image version tag (default: `latest`) |
    | `-d/-D`, `--detach/--no-detach` | `flag` | Run in background (default: detached) |
    | `--pull` | `flag` | Pull latest image before running |
    | `-f`, `--force` | `flag` | Force action (e.g., remove existing container) |
    | `-t`, `--build-tag` | `string` | Tag for built image (e.g., `my-project:latest`) |
    | `--push` | `flag` | Push built image to registry after building |
    | `--regenerate` | `flag` | Regenerate Docker files with fresh templates |
    | `--dockerfile` | `string` | Path to custom Dockerfile (build action only) |

    **Actions**

    | Action | Description |
    | --- | --- |
    | `run` | Start a new container (mounts project as volume) |
    | `stop` | Stop running container |
    | `logs` | View container logs |
    | `shell` | Open shell in container |
    | `status` | Check container status |
    | `pull` | Pull latest image |
    | `build` | Build custom image with project embedded |
    | `init` | Create Docker files without building |

    !!! info "Container vs Build Modes"
        - **Run Mode**: Mounts your project directory as a volume for development
        - **Build Mode**: Embeds your project into a custom image for deployment

    **Examples**

    ```bash
    # Start Aurite container with project mounted as volume
    aurite docker run

    # Start container with custom settings
    aurite docker run --port 9000 --name my-aurite --env-file .env.prod

    # Initialize Docker files for customization
    aurite docker init

    # Build custom image with project embedded
    aurite docker build --build-tag my-project:v1.0

    # Build and push to registry
    aurite docker build --build-tag my-project:v1.0 --push

    # Check container status
    aurite docker status --name my-aurite

    # View container logs
    aurite docker logs --name my-aurite

    # Open shell in running container
    aurite docker shell --name my-aurite

    # Stop container
    aurite docker stop --name my-aurite

    # Pull latest base image
    aurite docker pull --version latest
    ```

    **Docker File Management**

    The `init` and `build` actions create two files in your project directory:

    - **`Dockerfile.aurite`**: Customizable Dockerfile with a USER CUSTOMIZATION SECTION
    - **`.dockerignore`**: Optimized ignore patterns for Aurite projects

    !!! tip "Customization Workflow"
        1. Run `aurite docker init` to create Docker files
        2. Edit the USER CUSTOMIZATION SECTION in `Dockerfile.aurite` to add dependencies
        3. Run `aurite docker build` to create your custom image
        4. Use `--regenerate` flag to overwrite existing Docker files with fresh templates

    **Pre-flight Checks**

    The `run` action performs automatic validation:

    - ✓ Docker installation and daemon status
    - ✓ Aurite project directory validation (`.aurite` file)
    - ✓ Environment file detection and confirmation
    - ✓ Port availability checking
    - ✓ Container name conflict resolution

    **System Requirements**

    - Docker installed and running
    - Valid Aurite project directory (contains `.aurite` file)
    - Available port for API server (default: 8000)

    **Container Features**

    When running containers, you get:

    - API Server: `http://localhost:{port}`
    - Health Check: `http://localhost:{port}/health`
    - API Documentation: `http://localhost:{port}/api-docs`
    - Project volume mount: `/app/project` (run mode)
    - Environment file support
    - Automatic cleanup on container removal

    **Environment Variables**

    The Docker container supports several environment variables for configuration:

    | Variable | Default | Description |
    | --- | --- | --- |
    | `API_KEY` | *required* | Authentication key for API server access |
    | `AURITE_ENABLE_DB` | `false` | Enable database mode (SQLite or PostgreSQL) |
    | `AURITE_AUTO_EXPORT` | `true` | Automatically export configurations to database on startup |
    | `LOG_LEVEL` | `INFO` | Set to `DEBUG` for verbose container logging |

    **Database Configuration** (when `AURITE_ENABLE_DB=true`):

    | Variable | Description |
    | --- | --- |
    | `AURITE_DB_TYPE` | Database type (`sqlite` or `postgres`) |
    | `AURITE_DB_HOST` | PostgreSQL host (if using PostgreSQL) |
    | `AURITE_DB_PORT` | PostgreSQL port (default: 5432) |
    | `AURITE_DB_USER` | PostgreSQL username |
    | `AURITE_DB_PASSWORD` | PostgreSQL password |
    | `AURITE_DB_NAME` | Database name |

    !!! info "Auto-Export Behavior"
        When `AURITE_ENABLE_DB=true`, the container automatically exports all file-based configurations to the database on startup unless `AURITE_AUTO_EXPORT=false` is set. This ensures your database stays synchronized with your project files.

    **Examples with Environment Variables**

    ```bash
    # Run with database mode and auto-export enabled
    aurite docker run \
      --env-file .env \
      -e AURITE_ENABLE_DB=true \
      -e AURITE_AUTO_EXPORT=true \
      -e API_KEY=$(openssl rand -hex 32)

    # Run with auto-export disabled
    aurite docker run \
      --env-file .env \
      -e AURITE_ENABLE_DB=true \
      -e AURITE_AUTO_EXPORT=false \
      -e API_KEY=your-secure-api-key

    # Run with debug logging
    aurite docker run \
      --env-file .env \
      -e LOG_LEVEL=DEBUG \
      -e API_KEY=your-secure-api-key
    ```

---

## Global Options

These options can be used with the base `aurite` command.

| Option                 | Description                                                           |
| ---------------------- | --------------------------------------------------------------------- |
| `--install-completion` | Installs shell completion for the `aurite` command.                   |
| `--show-completion`    | Displays the shell completion script to be sourced or saved manually. |
| `--help`               | Shows the main help message listing all commands.                     |

---
