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
    """Format a tool call message with user-friendly parameter display."""
    if not tool_input:
        return f"[bold yellow]🔧 Calling tool:[/bold yellow] [bold]{tool_name}[/bold]\n[dim]No parameters[/dim]"

    # Format parameters in a user-friendly way
    param_lines = []
    for key, value in tool_input.items():
        if isinstance(value, str):
            param_lines.append(f"  {key}: {value}")
        else:
            param_lines.append(f"  {key}: {json.dumps(value)}")

    params_str = "\n".join(param_lines)
    return (
        f"[bold yellow]🔧 Calling tool:[/bold yellow] [bold]{tool_name}[/bold]\n"
        f"[dim]Parameters:[/dim]\n[dim]{params_str}[/dim]"
    )


def format_tool_output_message(tool_name: str, tool_output: str) -> str:
    """Format a tool output message with clean, user-friendly display."""
    try:
        # Parse the MCP tool result format
        output_data = json.loads(tool_output)

        # Extract the actual content from MCP format
        if isinstance(output_data, dict):
            # Check for MCP format with content array
            if "content" in output_data and isinstance(output_data["content"], list):
                content_texts = []
                for item in output_data["content"]:
                    if isinstance(item, dict) and "text" in item:
                        content_texts.append(item["text"])
                    else:
                        content_texts.append(str(item))

                if content_texts:
                    result_text = "\n".join(content_texts)
                else:
                    result_text = "No content returned"

            # Check for error status
            elif "isError" in output_data and output_data["isError"]:
                error_msg = output_data.get("content", [{}])[0].get("text", "Unknown error")
                return f"[bold red]❌ Tool error:[/bold red] [bold]{tool_name}[/bold]\n[dim]{error_msg}[/dim]"

            # Fallback for other dict formats
            else:
                result_text = json.dumps(output_data, indent=2)
        else:
            result_text = str(output_data)

    except (json.JSONDecodeError, TypeError, KeyError):
        # If it's not JSON or doesn't match expected format, use as-is
        result_text = str(tool_output)

    # Truncate very long outputs for display
    if len(result_text) > 500:
        result_text = result_text[:500] + "..."

    return f"[bold green]✅ Tool result:[/bold green] [bold]{tool_name}[/bold]\n[dim]{result_text}[/dim]"


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
