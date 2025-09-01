import asyncio
import os
from typing import Optional

import typer
from rich.console import Console

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
