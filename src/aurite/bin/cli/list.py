import os
from pathlib import Path

from rich.console import Console
from rich.table import Table

from ...host_manager import Aurite

console = Console()
logger = console.print


def display_component_table(components: list, component_type: str):
    """Displays a list of components in a table."""
    if not components:
        logger(f"No {component_type}s found.")
        return

    logger(f"\n[bold cyan]{component_type.replace('_', ' ').title()}[/bold cyan]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name")
    table.add_column("File Path")

    for item in components:
        source_file = item.get("source_file", "N/A")
        if source_file != "N/A":
            try:
                # Make path relative for easier clicking
                source_file = os.path.relpath(source_file, Path.cwd())
            except ValueError:
                # This can happen on Windows if the path is on a different drive
                pass
        table.add_row(
            item["name"],
            source_file,
        )
    console.print(table)


def _get_aurite_instance() -> Aurite:
    """Helper to instantiate Aurite, automatically finding the project root."""
    return Aurite(start_dir=Path.cwd())


def list_all():
    """Lists all available component configurations, grouped by type."""
    aurite = _get_aurite_instance()
    component_index = aurite.kernel.config_manager.get_component_index()

    grouped_by_type = {}
    for item in component_index:
        comp_type = item["component_type"]
        if comp_type not in grouped_by_type:
            grouped_by_type[comp_type] = []
        grouped_by_type[comp_type].append(item)

    for comp_type, items in grouped_by_type.items():
        display_component_table(items, comp_type)


def list_components_by_type(component_type: str):
    """Lists all available components of a specific type."""
    aurite = _get_aurite_instance()
    component_index = aurite.kernel.config_manager.get_component_index()
    items = [item for item in component_index if item["component_type"] == component_type]
    display_component_table(items, component_type)


def list_workflows():
    """Lists all available workflow components."""
    aurite = _get_aurite_instance()
    component_index = aurite.kernel.config_manager.get_component_index()
    items = [item for item in component_index if item["component_type"].endswith("_workflow")]
    display_component_table(items, "Workflows")


def list_index():
    """Displays the entire component index as a table."""
    aurite = _get_aurite_instance()
    component_index = aurite.kernel.config_manager.get_component_index()

    if not component_index:
        logger("Component index is empty.")
        return

    logger("\n[bold cyan]Component Index[/bold cyan]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("File Path")

    for item in component_index:
        source_file = item.get("source_file", "N/A")
        if source_file != "N/A":
            try:
                # Make path relative for easier clicking
                source_file = os.path.relpath(source_file, Path.cwd())
            except ValueError:
                # This can happen on Windows if the path is on a different drive
                pass
        table.add_row(
            item["name"],
            item.get("component_type", "N/A"),
            source_file,
        )
    console.print(table)
