import json
import os
import shutil
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from ...host_manager import Aurite

console = Console()
logger = console.print


def _format_agent_details(component: dict, level: str) -> str:
    """Formats the details of an agent component for display."""
    config = component["config"]
    content = ""
    if level == "short":
        content += (
            f"[bold blue]LLM Config:[/bold blue] {config.get('llm_config_id', 'N/A')}\n"
        )
        content += (
            f"[bold blue]MCP Servers:[/bold blue] {config.get('mcp_servers', [])}"
        )
    elif level == "full":
        content += f"[bold blue]Description:[/bold blue] {config.get('description', 'No description.')}\n"
        content += (
            f"[bold blue]LLM Config:[/bold blue] {config.get('llm_config_id', 'N/A')}\n"
        )
        content += (
            f"[bold blue]MCP Servers:[/bold blue] {config.get('mcp_servers', [])}\n"
        )
        content += f"[bold blue]System Prompt:[/bold blue] {config.get('system_prompt', 'N/A')}\n"
        other_vars = {
            k: v
            for k, v in config.items()
            if k
            not in [
                "name",
                "description",
                "llm_config_id",
                "mcp_servers",
                "system_prompt",
                "type",
            ]
        }
        if other_vars:
            content += "[bold blue]Other Configs:[/bold blue]\n"
            content += json.dumps(other_vars, indent=2)
    else:  # default
        terminal_width = shutil.get_terminal_size().columns
        max_len = terminal_width - 25  # Adjust for label and padding

        description = config.get("description", "No description.")
        truncated_description = (
            (description[: max_len - 4] + "...")
            if len(description) > max_len
            else description
        )
        content += f"[bold blue]Description:[/bold blue] {truncated_description}\n"

        content += (
            f"[bold blue]LLM Config:[/bold blue] {config.get('llm_config_id', 'N/A')}\n"
        )
        content += (
            f"[bold blue]MCP Servers:[/bold blue] {config.get('mcp_servers', [])}\n"
        )

        system_prompt = config.get("system_prompt", "")
        if system_prompt:
            truncated_prompt = (
                (system_prompt[: max_len - 4] + "...")
                if len(system_prompt) > max_len
                else system_prompt
            )
            content += f"[bold blue]System Prompt:[/bold blue] {truncated_prompt}"
    return content


def _format_llm_details(component: dict, level: str) -> str:
    """Formats the details of an LLM component for display."""
    config = component["config"]
    content = ""
    if level == "short":
        content += f"[bold blue]Provider:[/bold blue] {config.get('provider', 'N/A')}\n"
        content += f"[bold blue]Model:[/bold blue] {config.get('model', 'N/A')}"
    elif level == "full":
        content += f"[bold blue]Provider:[/bold blue] {config.get('provider', 'N/A')}\n"
        content += f"[bold blue]Model:[/bold blue] {config.get('model', 'N/A')}\n"
        content += (
            f"[bold blue]Temperature:[/bold blue] {config.get('temperature', 'N/A')}\n"
        )
        content += (
            f"[bold blue]Max Tokens:[/bold blue] {config.get('max_tokens', 'N/A')}\n"
        )
        content += f"[bold blue]API Base:[/bold blue] {config.get('api_base', 'N/A')}\n"
        content += (
            f"[bold blue]API Version:[/bold blue] {config.get('api_version', 'N/A')}"
        )
    else:  # default
        content += f"[bold blue]Provider:[/bold blue] {config.get('provider', 'N/A')}\n"
        content += f"[bold blue]Model:[/bold blue] {config.get('model', 'N/A')}"
    return content


def _format_mcp_server_details(component: dict, level: str) -> str:
    """Formats the details of an MCP server component for display."""
    config = component["config"]
    content = ""
    transport_type = config.get("transport_type")
    content += f"[bold blue]Transport:[/bold blue] {transport_type}\n"

    if transport_type == "stdio":
        content += (
            f"[bold blue]Server Path:[/bold blue] {config.get('server_path', 'N/A')}"
        )
    elif transport_type == "http_stream":
        content += (
            f"[bold blue]Endpoint:[/bold blue] {config.get('http_endpoint', 'N/A')}"
        )
    elif transport_type == "local":
        content += f"[bold blue]Command:[/bold blue] {config.get('command', 'N/A')}\n"
        content += f"[bold blue]Arguments:[/bold blue] {config.get('args', [])}"

    if level == "full":
        content += f"\n[bold blue]Timeout:[/bold blue] {config.get('timeout', 10.0)}\n"
        content += (
            f"[bold blue]Capabilities:[/bold blue] {config.get('capabilities', [])}"
        )
    return content


def _format_simple_workflow_details(component: dict, level: str) -> str:
    """Formats the details of a simple workflow component for display."""
    config = component["config"]
    content = ""
    description = config.get("description", "No description.")

    if level == "default":
        terminal_width = shutil.get_terminal_size().columns
        max_len = terminal_width - 25
        truncated_description = (
            (description[: max_len - 4] + "...")
            if len(description) > max_len
            else description
        )
        content += f"[bold blue]Description:[/bold blue] {truncated_description}\n"
    else:
        content += f"[bold blue]Description:[/bold blue] {description}\n"

    steps = config.get("steps", [])
    if level == "short":
        content += f"[bold blue]Steps:[/bold blue] {len(steps)} step(s)"
    else:
        content += "[bold blue]Steps:[/bold blue]\n"
        for i, step in enumerate(steps):
            if isinstance(step, dict):
                content += f"  {i+1}. {step.get('name')} ({step.get('type')})\n"
            else:
                content += f"  {i+1}. {step}\n"
    return content.strip()


def _format_custom_workflow_details(component: dict, level: str) -> str:
    """Formats the details of a custom workflow component for display."""
    config = component["config"]
    content = ""
    description = config.get("description", "No description.")

    if level == "default":
        terminal_width = shutil.get_terminal_size().columns
        max_len = terminal_width - 25
        truncated_description = (
            (description[: max_len - 4] + "...")
            if len(description) > max_len
            else description
        )
        content += f"[bold blue]Description:[/bold blue] {truncated_description}\n"
    else:
        content += f"[bold blue]Description:[/bold blue] {description}\n"

    content += (
        f"[bold blue]Module Path:[/bold blue] {config.get('module_path', 'N/A')}\n"
    )
    content += f"[bold blue]Class Name:[/bold blue] {config.get('class_name', 'N/A')}"
    return content


def format_component_details(component: dict, level: str) -> str:
    """Formats the details of a component for display by dispatching to the correct formatter."""
    comp_type = component["component_type"]
    formatters = {
        "agent": _format_agent_details,
        "llm": _format_llm_details,
        "mcp_server": _format_mcp_server_details,
        "simple_workflow": _format_simple_workflow_details,
        "custom_workflow": _format_custom_workflow_details,
    }
    formatter = formatters.get(
        comp_type, lambda c, loc: json.dumps(loc["config"], indent=2)
    )

    # Base details for default and full levels
    base_content = ""
    source_file = component.get("source_file", "N/A")
    if source_file != "N/A":
        try:
            # Make path relative for easier clicking
            source_file = os.path.relpath(source_file, Path.cwd())
        except ValueError:
            # This can happen on Windows if the path is on a different drive
            pass

    if level in ["default", "full"]:
        base_content += f"[bold blue]File Path:[/bold blue] {source_file}\n"

    specific_content = formatter(component, level)
    return base_content + specific_content


def display_component(component: dict, level: str = "default"):
    """Displays a single component with varying levels of detail."""
    content = format_component_details(component, level)
    panel = Panel(
        content,
        title=f"[bold cyan]{component['name']} ({component['component_type']})[/bold cyan]",
        border_style="magenta",
    )
    console.print(panel)


def _get_aurite_instance() -> Aurite:
    """Helper to instantiate Aurite, automatically finding the project root."""
    return Aurite(start_dir=Path.cwd())


def show_components(name: str, full: bool = False, short: bool = False):
    """Displays the configuration for a component or all components of a type."""
    aurite = _get_aurite_instance()
    component_index = aurite.get_config_manager().get_component_index()

    # Check if the name is a component type
    component_types = {item["component_type"] for item in component_index}
    type_to_show = None
    if name in component_types:
        type_to_show = name
    elif f"{name}s" in component_types:  # e.g., "agent" -> "agents"
        type_to_show = f"{name}s"
    elif name.rstrip("s") in component_types:  # e.g., "agents" -> "agent"
        type_to_show = name.rstrip("s")

    if type_to_show:
        components_to_show = [
            item for item in component_index if item["component_type"] == type_to_show
        ]
        for component in components_to_show:
            display_component(component, level="short" if short else "default")
        return

    # Find all components with the given name
    found_components = [item for item in component_index if item["name"] == name]

    if not found_components:
        logger(f"Component or type '{name}' not found.")
        return

    if len(found_components) > 1:
        first_type = found_components[0]["component_type"]
        if not all(c["component_type"] == first_type for c in found_components):
            logger(
                f"Multiple components found with name '{name}'. Please specify a type:"
            )
            for comp in found_components:
                logger(f"  - {comp['component_type']}")
            return

    level = "default"
    if full:
        level = "full"
    elif short:
        level = "short"

    for component in found_components:
        display_component(component, level=level)
