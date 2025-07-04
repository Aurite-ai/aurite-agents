import asyncio
import os
import typer
from pathlib import Path
import shutil
import importlib.resources
import json
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm, Prompt

# Relative imports from within the bin directory
from ..api.api import start as start_api_server
from ..tui.main import AuriteTUI
from ...host_manager import Aurite
from ...config.fast_loader import list_component_names

app = typer.Typer(
    name="aurite",
    help="A framework for building, testing, and running AI agents.",
    no_args_is_help=True,
)

list_app = typer.Typer(
    name="list", help="Inspect configurations for different component types."
)

app.add_typer(list_app)

console = Console()
logger = console.print


def copy_project_template(project_path: Path):
    """Copies the project template from the packaged data."""
    try:
        template_root = importlib.resources.files("aurite").joinpath("init_templates")

        for item in template_root.iterdir():
            source_path = template_root.joinpath(item.name)
            dest_path = project_path / item.name
            with importlib.resources.as_file(source_path) as sp:
                if sp.is_dir():
                    shutil.copytree(sp, dest_path)
                else:
                    shutil.copy2(sp, dest_path)

    except (ModuleNotFoundError, FileNotFoundError):
        logger(
            "[bold red]Error:[/bold red] Could not find 'aurite' package data. Creating minimal project."
        )
        (project_path / "config").mkdir(exist_ok=True)
        (project_path / "custom_workflows").mkdir(exist_ok=True)
        (project_path / "mcp_servers").mkdir(exist_ok=True)


@app.command()
def init(
    name: Optional[str] = typer.Argument(
        None, help="The name of the new project or workspace."
    ),
    project: bool = typer.Option(
        False, "--project", "-p", help="Initialize a new project."
    ),
    workspace: bool = typer.Option(
        False, "--workspace", "-w", help="Initialize a new workspace."
    ),
):
    """Initializes a new Aurite project or workspace."""

    if project and workspace:
        logger(
            "[bold red]Error:[/bold red] Cannot initialize a project and a workspace at the same time."
        )
        raise typer.Exit(code=1)

    if project:
        init_project(name)
    elif workspace:
        init_workspace(name)
    else:
        interactive_init()


def init_workspace(name: Optional[str] = None):
    """Initializes a new workspace to hold Aurite projects."""
    if not name:
        if Confirm.ask(
            "[bold yellow]No workspace name provided.[/bold yellow] Make the current directory a new workspace?"
        ):
            workspace_path = Path.cwd()
            name = workspace_path.name
        else:
            name = Prompt.ask(
                "[bold cyan]New workspace name[/bold cyan]", default="aurite-workspace"
            )
            workspace_path = Path(name)
            workspace_path.mkdir()
    else:
        workspace_path = Path(name)
        workspace_path.mkdir()

    if (workspace_path / ".aurite").exists():
        logger(
            f"[bold red]Error:[/bold red] An .aurite file already exists at '{workspace_path}'."
        )
        raise typer.Exit(code=1)

    (workspace_path / ".aurite").write_text(
        '[aurite]\ntype = "workspace"\nprojects = []'
    )
    logger(f"Initialized new workspace '{name}'.")


def init_project(name: Optional[str] = None):
    """Initializes a new Aurite project."""
    if not name:
        name = Prompt.ask(
            "[bold cyan]Project name[/bold cyan]", default="aurite-project"
        )

    project_path = Path(name)
    if project_path.exists():
        logger(f"[bold red]Error:[/bold red] Directory '{name}' already exists.")
        raise typer.Exit(code=1)

    project_path.mkdir()
    (project_path / ".aurite").touch()

    logger(f"Creating project '{name}'...")
    copy_project_template(project_path)

    # Add project to workspace if applicable
    workspace_path = None
    for parent in project_path.resolve().parents:
        if (parent / ".aurite").exists():
            workspace_path = parent
            break

    if workspace_path:
        try:
            with open(workspace_path / ".aurite", "r+") as f:
                content = f.read()
                if "projects = []" in content:
                    content = content.replace(
                        "projects = []", f'projects = ["./{name}"]'
                    )
                elif "projects = [" in content:
                    content = content.replace("]", f', "./{name}"]')

                f.seek(0)
                f.write(content)
                f.truncate()
            logger(f"Added project '{name}' to workspace '{workspace_path.name}'.")
        except Exception as e:
            logger(
                f"[bold yellow]Warning:[/bold yellow] Could not automatically add project to workspace file: {e}"
            )

    logger(f"\n[bold green]Project '{name}' initialized successfully![/bold green]")
    logger("\n[bold]Next steps:[/bold]")
    logger(f"1. Navigate into your project: [cyan]cd {name}[/cyan]")
    logger(
        "2. Create and populate your [yellow].env[/yellow] file from [yellow].env.example[/yellow]."
    )
    logger("3. Start building your agents and workflows!")


def interactive_init():
    """Interactive initialization of a new Aurite project."""
    # 1. Check for existing project
    if Path(".aurite").exists():
        logger(
            "[bold red]Error:[/bold red] An .aurite file already exists in this directory. Cannot create a project in a project."
        )
        raise typer.Exit(code=1)

    # 2. Check for workspace
    workspace_path = None
    for parent in Path.cwd().parents:
        if (parent / ".aurite").exists():
            workspace_path = parent
            break

    if not workspace_path:
        if Confirm.ask(
            "[bold yellow]No workspace found.[/bold yellow] Make the current directory a new workspace?"
        ):
            workspace_path = Path.cwd()
            (workspace_path / ".aurite").write_text(
                '[aurite]\ntype = "workspace"\nprojects = []'
            )
            logger("Initialized new workspace in current directory.")
        elif Confirm.ask("Create a new workspace directory instead?"):
            ws_name = Prompt.ask(
                "[bold cyan]New workspace name[/bold cyan]", default="aurite-workspace"
            )
            new_workspace_path = Path(ws_name)
            new_workspace_path.mkdir()
            (new_workspace_path / ".aurite").write_text(
                '[aurite]\ntype = "workspace"\nprojects = []'
            )
            logger(f"Workspace '{ws_name}' created. You are now inside of it.")
            os.chdir(new_workspace_path)
            # Update workspace_path to the new directory
            workspace_path = new_workspace_path

    # 3. Create the project
    proj_name = Prompt.ask(
        "[bold cyan]Project name[/bold cyan]", default="aurite-project"
    )
    init_project(proj_name)


@app.command()
def api():
    """
    Starts the Aurite FastAPI server.
    """
    logger("[bold green]Starting Aurite API server...[/bold green]")
    start_api_server()


@app.command()
def tui():
    """
    Starts the Aurite Textual TUI.
    """
    app = AuriteTUI()
    app.run()


# --- List Commands ---


def _get_aurite_instance() -> Aurite:
    """Helper to instantiate Aurite, automatically finding the project root."""
    return Aurite()


@list_app.command("all")
def list_all():
    """Lists all available component configurations, grouped by type."""
    aurite = _get_aurite_instance()
    all_configs = aurite.config_manager.get_all_configs()
    for comp_type, configs in all_configs.items():
        logger(f"\n[bold cyan]{comp_type.replace('_', ' ').title()}[/bold cyan]")
        if not configs:
            logger("  No configurations found.")
            continue
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name")
        table.add_column("Details")
        for name, config in configs.items():
            details = f"Provider: {config.get('provider', 'N/A')}, Model: {config.get('model', 'N/A')}"
            if comp_type == "agents":
                details = f"LLM: {config.get('llm_config_id', 'N/A')}, Servers: {len(config.get('mcp_servers', []))}"
            table.add_row(name, details)
        console.print(table)


@list_app.command("agents")
def list_agents():
    """Lists all available agent configurations."""
    aurite = _get_aurite_instance()
    configs = aurite.config_manager.list_configs("agents")
    # Similar table rendering as above
    table = Table(title="Agents")
    table.add_column("Name", style="cyan")
    table.add_column("LLM Config")
    table.add_column("MCP Servers")
    for config in configs:
        table.add_row(
            config.get("name"),
            config.get("llm_config_id"),
            str(config.get("mcp_servers", [])),
        )
    console.print(table)


# ... (Implement other list commands: llms, simple-workflows, etc. in a similar fashion)

# --- Completion Functions ---


def complete_component_type(incomplete: str):
    """Provides completion for component types."""
    types = ["agent", "simple-workflow", "custom-workflow"]
    for comp_type in types:
        if comp_type.startswith(incomplete):
            yield comp_type


def complete_component_name(ctx: typer.Context):
    """
    Provides completion for component names based on the component_type argument.
    """
    # The component_type is in the command's arguments list
    comp_type_arg = None
    if ctx.args:
        comp_type_arg = ctx.args[0]

    if comp_type_arg:
        # Typer might add quotes, remove them
        comp_type_clean = comp_type_arg.strip("'\"")
        # Use the fast loader to get names
        names = list_component_names(comp_type_clean)
        for name in names:
            yield name


# --- Run Commands ---


@app.command()
def run(
    component_type: str = typer.Argument(
        ...,
        help="The type of component to run (agent, simple-workflow, custom-workflow).",
        autocompletion=complete_component_type,
    ),
    name: str = typer.Argument(
        ...,
        help="The name of the component to run.",
        autocompletion=complete_component_name,
    ),
    user_message: Optional[str] = typer.Argument(
        None, help="The user message or initial input."
    ),
    system_prompt: Optional[str] = typer.Option(
        None, "--system-prompt", "-s", help="Override the default system prompt."
    ),
    session_id: Optional[str] = typer.Option(
        None, "--session-id", "-id", help="The session ID for history."
    ),
):
    """Executes a framework component."""

    async def main():
        async with Aurite() as aurite:
            if component_type == "agent":
                if not user_message:
                    logger(
                        "[bold red]Error:[/bold red] A user message is required to run an agent."
                    )
                    raise typer.Exit(code=1)
                result = await aurite.run_agent(
                    agent_name=name,
                    user_message=user_message,
                    system_prompt=system_prompt,
                    session_id=session_id,
                )
                logger("[bold]Agent Run Result:[/bold]")
                console.print(result)
            elif component_type == "simple-workflow":
                if not user_message:
                    logger(
                        "[bold red]Error:[/bold red] An initial input is required to run a simple workflow."
                    )
                    raise typer.Exit(code=1)
                result = await aurite.run_workflow(
                    workflow_name=name, initial_input=user_message
                )
                logger("[bold]Simple Workflow Result:[/bold]")
                console.print(result)
            elif component_type == "custom-workflow":
                if not user_message:
                    logger(
                        "[bold red]Error:[/bold red] An initial input is required to run a custom workflow."
                    )
                    raise typer.Exit(code=1)
                try:
                    parsed_input = json.loads(user_message)
                except json.JSONDecodeError:
                    parsed_input = user_message
                result = await aurite.run_custom_workflow(
                    workflow_name=name,
                    initial_input=parsed_input,
                    session_id=session_id,
                )
                logger("[bold]Custom Workflow Result:[/bold]")
                console.print(result)
            else:
                logger(
                    f"[bold red]Error:[/bold red] Unknown component type '{component_type}'."
                )
                raise typer.Exit(code=1)

    asyncio.run(main())


if __name__ == "__main__":
    app()
