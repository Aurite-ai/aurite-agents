import importlib.resources
import os
import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt

from ...host_manager import Aurite

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
        logger("[bold red]Error:[/bold red] Could not find 'aurite' package data. Creating minimal project.")
        (project_path / "config").mkdir(exist_ok=True)
        (project_path / "custom_workflows").mkdir(exist_ok=True)
        (project_path / "mcp_servers").mkdir(exist_ok=True)


def init_workspace(name: Optional[str] = None):
    """Initializes a new workspace to hold Aurite projects."""
    if not name:
        if Confirm.ask(
            "[bold yellow]No workspace name provided.[/bold yellow] Make the current directory a new workspace?"
        ):
            workspace_path = Path.cwd()
            name = workspace_path.name
        else:
            name = Prompt.ask("[bold cyan]New workspace name[/bold cyan]", default="aurite-workspace")
            workspace_path = Path(name)
            workspace_path.mkdir()
    else:
        workspace_path = Path(name)
        workspace_path.mkdir()

    if (workspace_path / ".aurite").exists():
        logger(f"[bold red]Error:[/bold red] An .aurite file already exists at '{workspace_path}'.")
        raise typer.Exit(code=1)

    (workspace_path / ".aurite").write_text('[aurite]\ntype = "workspace"\nprojects = []')
    logger(f"Initialized new workspace '{name}'.")


def init_project(name: Optional[str] = None):
    """Initializes a new Aurite project."""
    if not name:
        name = Prompt.ask("[bold cyan]Project name[/bold cyan]", default="aurite-project")

    project_path = Path(name)
    if project_path.exists():
        logger(f"[bold red]Error:[/bold red] Directory '{name}' already exists.")
        raise typer.Exit(code=1)

    project_path.mkdir()

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
                import re

                # Find the projects list
                match = re.search(r"projects\s*=\s*(\[.*\])", content)
                if match:
                    projects_list_str = match.group(1)
                    # Remove brackets and whitespace
                    projects_str = projects_list_str.strip()[1:-1].strip()

                    if not projects_str:
                        # The list is empty
                        new_projects_list = f'["./{name}"]'
                    else:
                        # The list has existing projects
                        new_projects_list = f'[{projects_str}, "./{name}"]'

                    content = content.replace(
                        f"projects = {projects_list_str}",
                        f"projects = {new_projects_list}",
                    )

                f.seek(0)
                f.write(content)
                f.truncate()
            logger(f"Added project '{name}' to workspace '{workspace_path.name}'.")
        except Exception as e:
            logger(f"[bold yellow]Warning:[/bold yellow] Could not automatically add project to workspace file: {e}")

    logger(f"\n[bold green]Project '{name}' initialized successfully![/bold green]")
    logger("\n[bold]Next steps:[/bold]")
    logger(f"1. Navigate into your project: [cyan]cd {name}[/cyan]")
    logger("2. Create and populate your [yellow].env[/yellow] file from [yellow].env.example[/yellow].")
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
        if Confirm.ask("[bold yellow]No workspace found.[/bold yellow] Make the current directory a new workspace?"):
            workspace_path = Path.cwd()
            (workspace_path / ".aurite").write_text('[aurite]\ntype = "workspace"\nprojects = []')
            logger("Initialized new workspace in current directory.")
        elif Confirm.ask("Create a new workspace directory instead?"):
            ws_name = Prompt.ask("[bold cyan]New workspace name[/bold cyan]", default="aurite-workspace")
            new_workspace_path = Path(ws_name)
            new_workspace_path.mkdir()
            (new_workspace_path / ".aurite").write_text('[aurite]\ntype = "workspace"\nprojects = []')
            logger(f"Workspace '{ws_name}' created. You are now inside of it.")
            os.chdir(new_workspace_path)
            # Update workspace_path to the new directory
            workspace_path = new_workspace_path

    # 3. Create the project
    proj_name = Prompt.ask("[bold cyan]Project name[/bold cyan]", default="aurite-project")
    init_project(proj_name)


def _get_aurite_instance() -> Aurite:
    """Helper to instantiate Aurite, automatically finding the project root."""
    # This helper now correctly finds the root to initialize Aurite from.
    # It looks for an .aurite file in the current dir or any parent dir.
    return Aurite(start_dir=Path.cwd())
