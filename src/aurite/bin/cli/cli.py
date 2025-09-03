import asyncio
import os
import socket
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

try:
    from importlib.metadata import version
except ImportError:
    # Python < 3.8
    from importlib_metadata import version

# Relative imports from within the bin directory
from ...lib.config import ConfigManager
from ...lib.storage import StorageManager
from ...utils.cli.fast_loader import list_component_names
from ..studio import start_studio
from ..tui.apps.edit import AuriteEditTUI
from .commands.init import init_project, init_workspace, interactive_init
from .commands.list import list_all, list_components_by_type, list_index, list_workflows
from .commands.migrate import migrate_database, migrate_from_env
from .commands.run import run_component
from .commands.show import show_components

console = Console()
logger = console.print


def version_callback(value: bool):
    """Callback function to display version information."""
    if value:
        try:
            aurite_version = version("aurite")
            console.print(f"aurite {aurite_version}")
        except Exception:
            console.print("aurite version unknown")
        raise typer.Exit()


app = typer.Typer(
    name="aurite",
    help="A framework for building, testing, and running AI agents.",
    no_args_is_help=True,
)


# Add global --version option
@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True, help="Show version and exit."
    ),
):
    """A framework for building, testing, and running AI agents."""
    pass


list_app = typer.Typer(
    name="list",
    help="Inspect configurations for different component types.",
    no_args_is_help=False,
    invoke_without_command=True,
)
app.add_typer(list_app)


@list_app.callback()
def list_main(ctx: typer.Context):
    """
    Display the component index if no subcommand is specified.
    """
    if ctx.invoked_subcommand is None:
        list_index()


# Docker helper functions
def _check_docker_installed() -> bool:
    """Check if Docker is installed and running."""
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            return False

        # Check if Docker daemon is running
        result = subprocess.run(["docker", "info"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _check_port_available(port: int) -> bool:
    """Check if port is available."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", port)) != 0
    except Exception:
        return False


def _validate_project_directory(path: str) -> bool:
    """Check if directory is a valid Aurite project."""
    aurite_file = Path(path) / ".aurite"
    return aurite_file.exists()


def _find_env_file(project_path: str, env_file: Optional[str] = None) -> Optional[str]:
    """Find environment file, checking common locations."""
    if env_file and Path(env_file).exists():
        return env_file

    # Check common locations
    common_locations = [
        Path(project_path) / ".env",
        Path(".env"),
        Path(project_path) / ".env.example",
        Path(".env.example"),
    ]

    for location in common_locations:
        if location.exists():
            return str(location)

    return None


def _get_container_status(container_name: str) -> str:
    """Get the status of a Docker container."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return "not found"
    except Exception:
        return "error"


def _container_exists(container_name: str) -> bool:
    """Check if a container with the given name exists."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0 and container_name in result.stdout
    except Exception:
        return False


def _pull_image(image_name: str) -> bool:
    """Pull the latest Docker image."""
    try:
        logger(f"[bold blue]Pulling Docker image: {image_name}[/bold blue]")
        result = subprocess.run(["docker", "pull", image_name], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


@app.command()
def init(
    name: Optional[str] = typer.Argument(None, help="The name of the new project or workspace."),
    project: bool = typer.Option(False, "--project", "-p", help="Initialize a new project."),
    workspace: bool = typer.Option(False, "--workspace", "-w", help="Initialize a new workspace."),
):
    """Initializes a new Aurite project or workspace."""

    if project and workspace:
        logger("[bold red]Error:[/bold red] Cannot initialize a project and a workspace at the same time.")
        raise typer.Exit(code=1)

    if project:
        init_project(name)
    elif workspace:
        init_workspace(name)
    else:
        interactive_init()


@app.command()
def api():
    """
    Starts the Aurite FastAPI server.
    """
    logger("[bold green]Starting Aurite API server...[/bold green]")
    # Lazy import - only load API module when actually starting the server
    from ..api.api import start as start_api_server

    start_api_server()


@app.command()
def studio(
    rebuild_fresh: bool = typer.Option(
        False, "--rebuild-fresh", help="Clean all build artifacts and rebuild frontend packages from scratch"
    ),
):
    """
    Starts the Aurite Studio integrated development environment.

    This command starts both the API server and React frontend concurrently,
    providing a unified development experience with automatic dependency
    management and graceful shutdown handling.
    """

    async def main_studio():
        success = await start_studio(rebuild_fresh=rebuild_fresh)
        if not success:
            raise typer.Exit(code=1)

    asyncio.run(main_studio())


@app.command()
def docker(
    action: str = typer.Argument("run", help="Docker action: run, stop, logs, shell, status, pull, build"),
    project_path: str = typer.Option(".", "--project", "-p", help="Path to Aurite project directory"),
    container_name: str = typer.Option("aurite-server", "--name", "-n", help="Container name"),
    port: int = typer.Option(8000, "--port", help="Port to expose (default: 8000)"),
    env_file: Optional[str] = typer.Option(None, "--env-file", "-e", help="Path to environment file"),
    version_tag: str = typer.Option("latest", "--version", "-v", help="Docker image version"),
    detach: bool = typer.Option(True, "--detach/--no-detach", "-d/-D", help="Run in background"),
    pull: bool = typer.Option(False, "--pull", help="Pull latest image before running"),
    force: bool = typer.Option(False, "--force", "-f", help="Force action (e.g., remove existing container)"),
    build_tag: Optional[str] = typer.Option(
        None, "--build-tag", "-t", help="Tag for built image (e.g., my-project:latest)"
    ),
    push_after_build: bool = typer.Option(False, "--push", help="Push built image to registry after building"),
):
    """
    Manage Aurite Docker containers.

    Actions:
      run     - Start a new container (mounts project as volume)
      stop    - Stop running container
      logs    - View container logs
      shell   - Open shell in container
      status  - Check container status
      pull    - Pull latest image
      build   - Build custom image with project embedded
    """

    # Validate Docker installation
    if not _check_docker_installed():
        logger("[bold red]✗ Docker is not installed or not running[/bold red]")
        logger("Please install Docker and ensure the Docker daemon is running.")
        raise typer.Exit(code=1)

    image_name = f"aurite/aurite-agents:{version_tag}"

    if action == "run":
        # Pre-flight checks
        logger("[bold green]🐳 Starting Aurite Docker container...[/bold green]")

        # Check if project directory is valid
        if not _validate_project_directory(project_path):
            logger(f"[bold yellow]⚠ Warning:[/bold yellow] No .aurite file found in {project_path}")
            if not typer.confirm("Continue anyway?"):
                raise typer.Exit()
        else:
            logger(f"[bold green]✓[/bold green] Found Aurite project at {project_path}")

        # Find environment file
        found_env_file = _find_env_file(project_path, env_file)
        if found_env_file:
            logger(f"[bold green]✓[/bold green] Using environment file: {found_env_file}")
        else:
            logger("[bold yellow]⚠ Warning:[/bold yellow] No .env file found")
            if not typer.confirm("Continue without environment file?"):
                raise typer.Exit()

        # Check port availability
        if not _check_port_available(port):
            logger(f"[bold red]✗ Port {port} is already in use[/bold red]")
            raise typer.Exit(code=1)
        else:
            logger(f"[bold green]✓[/bold green] Port {port} is available")

        # Check if container already exists
        if _container_exists(container_name):
            if force:
                logger(f"[bold yellow]Removing existing container: {container_name}[/bold yellow]")
                subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
            else:
                logger(f"[bold red]✗ Container '{container_name}' already exists[/bold red]")
                logger("Use --force to remove existing container or choose a different name with --name")
                raise typer.Exit(code=1)

        # Pull image if requested or if image doesn't exist locally
        should_pull = pull
        if not should_pull:
            # Check if image exists locally
            try:
                result = subprocess.run(["docker", "image", "inspect", image_name], capture_output=True, text=True)
                if result.returncode != 0:
                    logger(f"[bold blue]Image not found locally, pulling: {image_name}[/bold blue]")
                    should_pull = True
            except Exception:
                should_pull = True

        if should_pull:
            if not _pull_image(image_name):
                logger(f"[bold red]✗ Failed to pull image: {image_name}[/bold red]")
                raise typer.Exit(code=1)

        # Build Docker command
        cmd = [
            "docker",
            "run",
            "--name",
            container_name,
            "-v",
            f"{os.path.abspath(project_path)}:/app/project",
            "-p",
            f"{port}:8000",
        ]

        if detach:
            cmd.append("-d")
        else:
            cmd.extend(["-it"])

        cmd.append("--rm")

        if found_env_file:
            cmd.extend(["--env-file", found_env_file])

        cmd.append(image_name)

        # Run container
        logger(f"[bold blue]→ Starting container '{container_name}'...[/bold blue]")
        try:
            result = subprocess.run(cmd, capture_output=detach, text=True)
            if result.returncode == 0:
                if detach:
                    logger("[bold green]✓ Container started successfully![/bold green]")

                    # Create info panel
                    info_table = Table.grid(padding=(0, 2))
                    info_table.add_column(style="bold cyan")
                    info_table.add_column()

                    info_table.add_row("API Server:", f"http://localhost:{port}")
                    info_table.add_row("Health Check:", f"http://localhost:{port}/health")
                    info_table.add_row("API Docs:", f"http://localhost:{port}/api-docs")
                    info_table.add_row("Container:", container_name)

                    panel = Panel(info_table, title="🚀 Aurite Container Running", border_style="green")
                    console.print(panel)

                    logger("\n[bold cyan]Management commands:[/bold cyan]")
                    logger(f"  View logs: [bold]aurite docker logs --name {container_name}[/bold]")
                    logger(f"  Stop container: [bold]aurite docker stop --name {container_name}[/bold]")
                    logger(f"  Open shell: [bold]aurite docker shell --name {container_name}[/bold]")
            else:
                logger("[bold red]✗ Failed to start container[/bold red]")
                if result.stderr:
                    logger(f"Error: {result.stderr}")
                raise typer.Exit(code=1)
        except KeyboardInterrupt:
            logger("\n[bold yellow]Container startup interrupted[/bold yellow]")
            raise typer.Exit() from None

    elif action == "stop":
        logger(f"[bold yellow]Stopping container: {container_name}[/bold yellow]")
        result = subprocess.run(["docker", "stop", container_name], capture_output=True, text=True)
        if result.returncode == 0:
            logger("[bold green]✓ Container stopped successfully[/bold green]")
        else:
            logger(f"[bold red]✗ Failed to stop container: {result.stderr}[/bold red]")
            raise typer.Exit(code=1)

    elif action == "logs":
        logger(f"[bold blue]Showing logs for container: {container_name}[/bold blue]")
        try:
            subprocess.run(["docker", "logs", "-f", container_name])
        except KeyboardInterrupt:
            logger("\n[bold yellow]Log viewing interrupted[/bold yellow]")

    elif action == "shell":
        logger(f"[bold blue]Opening shell in container: {container_name}[/bold blue]")
        try:
            subprocess.run(["docker", "exec", "-it", container_name, "/bin/bash"])
        except subprocess.CalledProcessError:
            # Try with sh if bash is not available
            subprocess.run(["docker", "exec", "-it", container_name, "/bin/sh"])

    elif action == "status":
        status = _get_container_status(container_name)

        status_table = Table.grid(padding=(0, 2))
        status_table.add_column(style="bold cyan")
        status_table.add_column()

        status_table.add_row("Container:", container_name)
        status_table.add_row("Status:", status)

        if "Up" in status:
            status_table.add_row("Health:", f"http://localhost:{port}/health")
            panel_style = "green"
            title = "🟢 Container Status"
        elif status == "not found":
            panel_style = "red"
            title = "🔴 Container Status"
        else:
            panel_style = "yellow"
            title = "🟡 Container Status"

        panel = Panel(status_table, title=title, border_style=panel_style)
        console.print(panel)

    elif action == "pull":
        if not _pull_image(image_name):
            logger(f"[bold red]✗ Failed to pull image: {image_name}[/bold red]")
            raise typer.Exit(code=1)
        else:
            logger(f"[bold green]✓ Successfully pulled: {image_name}[/bold green]")

    elif action == "build":
        # Build custom image with project embedded
        logger("[bold green]🔨 Building custom Aurite image with project embedded...[/bold green]")

        # Validate project directory
        if not _validate_project_directory(project_path):
            logger(f"[bold red]✗ No .aurite file found in {project_path}[/bold red]")
            logger("Please run this command from an Aurite project directory.")
            raise typer.Exit(code=1)
        else:
            logger(f"[bold green]✓[/bold green] Found Aurite project at {project_path}")

        # Determine build tag
        if not build_tag:
            project_name = Path(project_path).resolve().name
            build_tag = f"{project_name.lower()}:latest"
            logger(f"[bold blue]Using auto-generated tag: {build_tag}[/bold blue]")

        # Create temporary Dockerfile
        dockerfile_content = f"""# Auto-generated Dockerfile for Aurite project
FROM aurite/aurite-agents:{version_tag}

# Copy project files into the container
COPY . /app/project/

# Set working directory
WORKDIR /app/project

# Ensure proper permissions
USER root
RUN chown -R appuser:appuser /app/project
USER appuser

# The base image already has the correct entrypoint and CMD
"""

        # Create .dockerignore to exclude unnecessary files
        dockerignore_content = """# Auto-generated .dockerignore for Aurite build
# Python cache files
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE files
.vscode/
.idea/
*.swp
*.swo
*~

# OS files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Git
.git/
.gitignore

# Docker files
Dockerfile*
.dockerignore
docker-compose*.yml

# Logs
*.log
logs/

# Node modules (if any)
node_modules/

# Temporary files
tmp/
temp/
*.tmp

# Large data files
*.db
*.sqlite
*.sqlite3

# Cache directories
.cache/
.pytest_cache/
.coverage
htmlcov/

# Build artifacts
*.tar.gz
*.zip
"""

        dockerfile_path = Path(project_path) / "Dockerfile.aurite"
        dockerignore_path = Path(project_path) / ".dockerignore"
        dockerignore_backup_path = Path(project_path) / ".dockerignore.backup"

        # Backup existing .dockerignore if it exists
        existing_dockerignore = dockerignore_path.exists()
        if existing_dockerignore:
            dockerignore_path.rename(dockerignore_backup_path)
            logger("[bold blue]Backed up existing .dockerignore[/bold blue]")

        try:
            # Write temporary Dockerfile
            with open(dockerfile_path, "w") as f:
                f.write(dockerfile_content)

            # Write temporary .dockerignore
            with open(dockerignore_path, "w") as f:
                f.write(dockerignore_content)

            logger(f"[bold blue]Created temporary Dockerfile: {dockerfile_path}[/bold blue]")
            logger(f"[bold blue]Created temporary .dockerignore: {dockerignore_path}[/bold blue]")

            # Pull base image first
            logger(f"[bold blue]Ensuring base image is available: {image_name}[/bold blue]")
            if not _pull_image(image_name):
                logger(f"[bold red]✗ Failed to pull base image: {image_name}[/bold red]")
                raise typer.Exit(code=1)

            # Build the image (Docker automatically uses .dockerignore)
            build_cmd = ["docker", "build", "-f", str(dockerfile_path), "-t", build_tag, project_path]

            logger(f"[bold blue]Building image: {build_tag}[/bold blue]")
            result = subprocess.run(build_cmd, capture_output=False, text=True)

            if result.returncode == 0:
                logger(f"[bold green]✓ Successfully built image: {build_tag}[/bold green]")

                # Show build summary
                build_table = Table.grid(padding=(0, 2))
                build_table.add_column(style="bold cyan")
                build_table.add_column()

                build_table.add_row("Built Image:", build_tag)
                build_table.add_row("Base Image:", image_name)
                build_table.add_row("Project Path:", project_path)

                panel = Panel(build_table, title="🔨 Build Complete", border_style="green")
                console.print(panel)

                # Push if requested
                if push_after_build:
                    logger(f"[bold blue]Pushing image to registry: {build_tag}[/bold blue]")
                    push_result = subprocess.run(["docker", "push", build_tag], capture_output=True, text=True)
                    if push_result.returncode == 0:
                        logger(f"[bold green]✓ Successfully pushed: {build_tag}[/bold green]")
                    else:
                        logger(f"[bold red]✗ Failed to push image: {push_result.stderr}[/bold red]")

                logger("\n[bold cyan]Usage examples:[/bold cyan]")
                logger(f"  Run your custom image: [bold]docker run -p 8000:8000 --env-file .env {build_tag}[/bold]")
                logger(f"  Push to registry: [bold]docker push {build_tag}[/bold]")

            else:
                logger("[bold red]✗ Failed to build image[/bold red]")
                raise typer.Exit(code=1)

        finally:
            # Clean up temporary files
            if dockerfile_path.exists():
                dockerfile_path.unlink()
                logger("[bold blue]Cleaned up temporary Dockerfile[/bold blue]")
            if dockerignore_path.exists():
                dockerignore_path.unlink()
                logger("[bold blue]Cleaned up temporary .dockerignore[/bold blue]")

            # Restore original .dockerignore if it existed
            if existing_dockerignore and dockerignore_backup_path.exists():
                dockerignore_backup_path.rename(dockerignore_path)
                logger("[bold blue]Restored original .dockerignore[/bold blue]")

    else:
        logger(f"[bold red]Unknown action: {action}[/bold red]")
        logger("Available actions: run, stop, logs, shell, status, pull, build")
        raise typer.Exit(code=1)


@app.command()
def edit(component_name: Optional[str] = typer.Argument(None, help="The name of the component to edit directly.")):
    """
    Starts the Aurite configuration editor TUI.
    """
    app = AuriteEditTUI(component_name=component_name)
    app.run()


@app.command()
def show(
    name: str = typer.Argument(..., help="The name or type of the component(s) to show."),
    full: bool = typer.Option(False, "--full", "-f", help="Display the full configuration."),
    short: bool = typer.Option(False, "--short", "-s", help="Display a short summary."),
):
    """Displays the configuration for a component or all components of a type."""
    show_components(name, full=full, short=short)


@app.command()
def migrate(
    source_type: Optional[str] = typer.Option(None, "--source-type", help="Source database type (sqlite/postgresql)"),
    target_type: Optional[str] = typer.Option(None, "--target-type", help="Target database type (sqlite/postgresql)"),
    source_path: Optional[str] = typer.Option(None, "--source-path", help="Source SQLite database path"),
    target_path: Optional[str] = typer.Option(None, "--target-path", help="Target SQLite database path"),
    verify: bool = typer.Option(True, "--verify/--no-verify", help="Verify migration after completion"),
    from_env: bool = typer.Option(False, "--from-env", help="Use current environment configuration as source"),
):
    """
    Migrate data between SQLite and PostgreSQL databases.

    Examples:
        aurite migrate                    # Interactive mode
        aurite migrate --from-env          # Migrate from current DB to opposite type
        aurite migrate --source-type sqlite --target-type postgresql
    """
    if from_env:
        migrate_from_env()
    else:
        migrate_database(
            source_type=source_type,
            target_type=target_type,
            source_path=source_path,
            target_path=target_path,
            verify=verify,
        )


@app.command()
def export():
    """
    Exports all configurations from the file system to the database.
    This command reads from the local config files and upserts them into the DB.
    """
    logger("[bold green]Starting configuration export to database...[/bold green]")
    try:
        # 1. First, ensure database tables exist
        logger("Initializing database...")
        storage_manager = StorageManager()
        storage_manager.init_db()  # Create tables if they don't exist

        # 2. Temporarily disable DB mode to load from files
        original_db_setting = os.getenv("AURITE_ENABLE_DB", "false")
        os.environ["AURITE_ENABLE_DB"] = "false"

        # 3. Load configs from files
        logger("Loading configurations from file system...")
        config_manager = ConfigManager()
        component_index = config_manager.get_all_configs()

        # 4. Restore original DB setting
        os.environ["AURITE_ENABLE_DB"] = original_db_setting

        if not component_index:
            logger("[bold yellow]No configurations found to export.[/bold yellow]")
            raise typer.Exit()

        # 5. Sync to database
        logger("Syncing configurations to database...")
        storage_manager.sync_index_to_db(component_index)

        # 6. Display summary
        total_count = sum(len(components) for components in component_index.values())
        logger("\n[bold green]✅ Configuration export completed successfully![/bold green]")
        logger(f"  Exported {total_count} components to database")

        for comp_type, components in component_index.items():
            if components:
                logger(f"  • {len(components)} {comp_type}(s)")

    except Exception as e:
        logger(f"\n[bold red]Error during export:[/bold red] {e}")
        raise typer.Exit(code=1) from e


# --- List Commands ---


@list_app.command("all")
def list_all_cmd():
    """Lists all available component configurations, grouped by type."""
    list_all()


@list_app.command("agents")
def list_agents_cmd():
    """Lists all available agent configurations."""
    list_components_by_type("agent")


@list_app.command("llms")
def list_llms_cmd():
    """Lists all available LLM configurations."""
    list_components_by_type("llm")


@list_app.command("mcp_servers")
def list_mcp_servers_cmd():
    """Lists all available MCP server configurations."""
    list_components_by_type("mcp_server")


@list_app.command("linear_workflows")
def list_linear_workflows_cmd():
    """Lists all available linear workflow configurations."""
    list_components_by_type("linear_workflow")


@list_app.command("custom_workflows")
def list_custom_workflows_cmd():
    """Lists all available custom workflow configurations."""
    list_components_by_type("custom_workflow")


@list_app.command("workflows")
def list_workflows_cmd():
    """Lists all available workflow configurations."""
    list_workflows()


@list_app.command("index")
def list_index_cmd():
    """Prints the entire component index as a formatted JSON."""
    list_index()


# --- Completion Functions ---


def complete_component_type(incomplete: str):
    """Provides completion for component types."""
    types = ["agent", "linear_workflow", "custom_workflow"]
    for comp_type in types:
        if comp_type.startswith(incomplete):
            yield comp_type


def complete_runnable_component_name(incomplete: str):
    """Provides completion for runnable component names."""
    # This is a simplified example. A real implementation would use the
    # config manager to get a list of all runnable components.
    all_names = []
    for comp_type in ["agent", "linear_workflow", "custom_workflow"]:
        all_names.extend(list_component_names(comp_type))

    for name in all_names:
        if name.startswith(incomplete):
            yield name


# --- Run Commands ---


@app.command()
def run(
    name: Optional[str] = typer.Argument(
        None,
        help="The name of the component to run.",
        autocompletion=complete_runnable_component_name,
    ),
    user_message: Optional[str] = typer.Argument(None, help="The user message or initial input."),
    system_prompt: Optional[str] = typer.Option(None, "--system-prompt", help="Override the default system prompt."),
    session_id: Optional[str] = typer.Option(None, "--session-id", "-id", help="The session ID for history."),
    short: bool = typer.Option(False, "--short", "-s", help="Display a compact, one-line summary of the run."),
    debug: bool = typer.Option(False, "--debug", "-d", help="Display the full, raw event stream for debugging."),
):
    """Executes a framework component."""

    async def main_run():
        if not name:
            # This is a placeholder for a future interactive agent selection TUI
            console.print("[bold yellow]Interactive agent selection is not yet implemented.[/bold yellow]")
            console.print("Please provide an agent name to run.")
            return
        await run_component(name, user_message, system_prompt, session_id, short, debug)

    asyncio.run(main_run())


if __name__ == "__main__":
    app()
