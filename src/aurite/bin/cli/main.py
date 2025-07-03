import asyncio
import typer
from pathlib import Path
import shutil
import importlib.resources
from importlib.abc import Traversable
import json
from typing import Optional
from rich.console import Console
from rich.table import Table

# Relative imports from within the bin directory
from ..api.api import start as start_api_server
from ...host_manager import Aurite

app = typer.Typer(
    name="aurite",
    help="A framework for building, testing, and running AI agents.",
    no_args_is_help=True,
)

run_app = typer.Typer(
    name="run", help="Execute framework components like agents and workflows."
)
list_app = typer.Typer(
    name="list", help="Inspect configurations for different component types."
)

app.add_typer(run_app)
app.add_typer(list_app)

console = Console()
logger = console.print


def copy_project_template(template_path: Traversable, project_path: Path):
    """
    Copies the project template from the packaged data, excluding specified items.
    """
    excluded_items = {
        "__pycache__",
        "py.typed",
        ".pytest_cache",
        "__init__.py",
        "poetry.lock",
        "aurite.egg-info",
        ".git",
    }

    for item in template_path.iterdir():
        if item.name in excluded_items or item.name.endswith(".egg-info"):
            continue

        destination = project_path / item.name
        try:
            with importlib.resources.as_file(item) as item_path:
                if item_path.is_dir():
                    shutil.copytree(item_path, destination, dirs_exist_ok=True)
                elif item_path.is_file():
                    shutil.copy2(item_path, destination)
        except Exception as e:
            logger(f"[bold red]Warning:[/bold red] Could not copy {item.name}: {e}")


@app.command()
def init(
    project_directory_name: str = typer.Argument(
        ..., help="The name of the new project directory to create."
    ),
):
    """
    Initializes a new Aurite project with a default structure and configuration.
    """
    project_path = Path(project_directory_name)

    if project_path.exists():
        logger(
            f"[bold red]Error:[/bold red] Directory '{project_path.name}' already exists."
        )
        raise typer.Exit(code=1)

    try:
        logger(f"Initializing new Aurite project at: [cyan]./{project_path}[/cyan]")
        project_path.mkdir(parents=True)

        logger("Copying project template files...")
        template_root = importlib.resources.files("aurite")
        copy_project_template(template_root, project_path)

        # Create pyproject.toml
        pyproject_content = """
[tool.poetry]
name = "{project_name}"
version = "0.1.0"
description = ""
authors = ["Your Name <you@example.com>"]

[tool.poetry.dependencies]
python = "^3.9"
aurite = "*" # Replace with the correct version constraint

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.aurite]
# A list of directories, relative to this file, where component configs are located.
config_sources = [
    "config/"
]
# A list of directories, relative to this file, where custom Python modules are located.
custom_workflow_modules = [
    "custom_workflows/"
]
mcp_server_modules = [
    "mcp_servers/"
]
""".format(project_name=project_path.name)
        (project_path / "pyproject.toml").write_text(pyproject_content.strip())

        logger(
            f"\n[bold green]Project '{project_path.name}' initialized successfully![/bold green]"
        )
        logger("\n[bold]Next steps:[/bold]")
        logger(f"1. Navigate into your project: [cyan]cd {project_path.name}[/cyan]")
        logger(
            "2. Create and populate your [yellow].env[/yellow] file from [yellow].env.example[/yellow]."
        )
        logger("3. Install dependencies: [cyan]poetry install[/cyan]")
        logger("4. Run the example project: [cyan]python run_example_project.py[/cyan]")

    except Exception as e:
        logger(f"[bold red]Error during project initialization:[/bold red] {e}")
        if project_path.exists():
            shutil.rmtree(project_path)
        raise typer.Exit(code=1)


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
