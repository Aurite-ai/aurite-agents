import asyncio
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
from ...host_manager import Aurite

app = typer.Typer(
    name="aurite",
    help="A framework for building, testing, and running AI agents.",
    no_args_is_help=True,
)

init_app = typer.Typer(
    name="init", help="Initialize a new Aurite project or workspace."
)
run_app = typer.Typer(
    name="run", help="Execute framework components like agents and workflows."
)
list_app = typer.Typer(
    name="list", help="Inspect configurations for different component types."
)

app.add_typer(init_app)
app.add_typer(run_app)
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


@init_app.command("workspace")
def init_workspace(
    name: Optional[str] = typer.Argument(
        None, help="The name of the new workspace directory."
    ),
):
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


@init_app.command("project")
def init_project(
    name: Optional[str] = typer.Argument(
        None, help="The name of the new project directory."
    ),
):
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


@app.command()
def api():
    """
    Starts the Aurite FastAPI server.
    """
    logger("[bold green]Starting Aurite API server...[/bold green]")
    start_api_server()


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

# --- Run Commands ---


@run_app.command("agent")
def run_agent(
    agent_name: str = typer.Argument(..., help="The name of the agent to run."),
    user_message: str = typer.Argument(
        ..., help="The user message to send to the agent."
    ),
    system_prompt: Optional[str] = typer.Option(
        None, "--system-prompt", "-s", help="Override the default system prompt."
    ),
    session_id: Optional[str] = typer.Option(
        None, "--session-id", "-id", help="The session ID for history."
    ),
):
    """Runs a single turn of an agent's conversation."""

    async def main():
        async with Aurite() as aurite:
            result = await aurite.run_agent(
                agent_name=agent_name,
                user_message=user_message,
                system_prompt=system_prompt,
                session_id=session_id,
            )
            logger("[bold]Agent Run Result:[/bold]")
            console.print(result)

    asyncio.run(main())


@run_app.command("simple-workflow")
def run_simple_workflow(
    workflow_name: str = typer.Argument(
        ..., help="The name of the simple workflow to run."
    ),
    initial_input: str = typer.Argument(..., help="The initial input to the workflow."),
):
    """Executes a simple workflow."""

    async def main():
        async with Aurite() as aurite:
            result = await aurite.run_workflow(
                workflow_name=workflow_name, initial_input=initial_input
            )
            logger("[bold]Simple Workflow Result:[/bold]")
            console.print(result)

    asyncio.run(main())


@run_app.command("custom-workflow")
def run_custom_workflow(
    workflow_name: str = typer.Argument(
        ..., help="The name of the custom workflow to run."
    ),
    initial_input: str = typer.Argument(
        ..., help="The initial input to the workflow (as a JSON string)."
    ),
    session_id: Optional[str] = typer.Option(
        None, "--session-id", "-id", help="The session ID for history."
    ),
):
    """Executes a custom workflow."""

    async def main():
        async with Aurite() as aurite:
            try:
                # Assuming input is a simple string for now, can be expanded to JSON
                parsed_input = json.loads(initial_input)
            except json.JSONDecodeError:
                parsed_input = initial_input

            result = await aurite.run_custom_workflow(
                workflow_name=workflow_name,
                initial_input=parsed_input,
                session_id=session_id,
            )
            logger("[bold]Custom Workflow Result:[/bold]")
            console.print(result)

    asyncio.run(main())


if __name__ == "__main__":
    app()
