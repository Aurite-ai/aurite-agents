import asyncio
from typing import Optional

import typer
from rich.console import Console

from ...config.fast_loader import list_component_names
from ..api.api import start as start_api_server
from ..tui.edit import AuriteEditTUI

# Relative imports from within the bin directory
from .commands import (
    init_project,
    init_workspace,
    interactive_init,
)
from .list import (
    list_all,
    list_components_by_type,
    list_index,
    list_workflows,
)
from .run import run_component
from .show import show_components

app = typer.Typer(
    name="aurite",
    help="A framework for building, testing, and running AI agents.",
    no_args_is_help=True,
)

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


console = Console()
logger = console.print


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
    start_api_server()


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


@list_app.command("simple_workflows")
def list_simple_workflows_cmd():
    """Lists all available simple workflow configurations."""
    list_components_by_type("simple_workflow")


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
    types = ["agent", "simple_workflow", "custom_workflow"]
    for comp_type in types:
        if comp_type.startswith(incomplete):
            yield comp_type


def complete_runnable_component_name(incomplete: str):
    """Provides completion for runnable component names."""
    # This is a simplified example. A real implementation would use the
    # config manager to get a list of all runnable components.
    all_names = []
    for comp_type in ["agent", "simple_workflow", "custom_workflow"]:
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
