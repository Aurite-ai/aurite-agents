"""
Shared UI utilities for formatting messages across CLI and TUI interfaces.
"""

import json
from typing import Any, Dict


def format_user_message(message: str) -> str:
    """Format a user message with consistent styling."""
    return f"[bold green]You:[/bold green] {message}"


def format_agent_message(message: str) -> str:
    """Format an agent response message with consistent styling."""
    return f"[bold cyan]Agent:[/bold cyan] {message}"


def format_tool_call_message(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """Format a tool call message with consistent styling."""
    input_str = json.dumps(tool_input, indent=2) if tool_input else "{}"
    return (
        f"[bold yellow]🔧 Calling tool:[/bold yellow] [bold]{tool_name}[/bold]\n"
        f"[dim]Input:[/dim]\n[dim]{input_str}[/dim]"
    )


def format_tool_output_message(tool_name: str, tool_output: str) -> str:
    """Format a tool output message with consistent styling."""
    # Truncate very long outputs for display
    display_output = tool_output
    if len(display_output) > 500:
        display_output = display_output[:500] + "..."

    # Try to format as JSON if possible
    try:
        output_data = json.loads(tool_output)
        formatted_output = json.dumps(output_data, indent=2)
    except (json.JSONDecodeError, TypeError):
        formatted_output = str(tool_output)

    return f"[bold green]✅ Tool result:[/bold green] [bold]{tool_name}[/bold]\n" f"[dim]{formatted_output}[/dim]"


def format_status_message(message: str, style: str = "dim") -> str:
    """Format a status message with consistent styling."""
    return f"[{style}]{message}[/{style}]"


def format_error_message(error_message: str) -> str:
    """Format an error message with consistent styling."""
    return f"[bold red]❌ Error:[/bold red] {error_message}"


def format_thinking_message() -> str:
    """Format the 'thinking' status message."""
    return format_status_message("🤔 Agent is thinking...")


def format_workflow_step_start(step_name: str) -> str:
    """Format a workflow step start message."""
    return f"[grey50]Running workflow step: [bold]{step_name}[/bold]...[/grey50]"


def format_workflow_step_end(step_name: str) -> str:
    """Format a workflow step end message."""
    return f"[grey50]... finished step: [bold]{step_name}[/bold].[/grey50]"
