import json
from typing import Any, AsyncGenerator, Dict, Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.text import Text

console = Console()


class RunPresenter:
    """
    Handles the rich display of an agent or workflow run stream.
    """

    def __init__(self, mode: str = "default"):
        self.mode = mode
        self._live: Optional[Live] = None
        self._full_response = ""

    async def render_stream(self, stream: AsyncGenerator[Dict[str, Any], None], component_info: Dict[str, Any]):
        """
        Renders the event stream from a component run.
        """
        self._render_header(component_info)

        try:
            async for event in stream:
                event_type = event.get("type")
                handler = getattr(self, f"_handle_{event_type}", self._handle_unknown)
                await handler(event.get("data", {}))
        finally:
            if self._live and self._live.is_started:
                self._live.stop()

    def _render_header(self, component_info: Dict[str, Any]):
        """Renders the initial header for the component run."""
        name = component_info.get("name", "Unknown")
        comp_type = component_info.get("component_type", "Unknown")
        description = component_info.get("config", {}).get("description", "No description.")
        source_file = component_info.get("source_file", "N/A")

        header_text = Text()
        header_text.append("Name: ", style="bold")
        header_text.append(f"{name}\n")
        header_text.append("Type: ", style="bold")
        header_text.append(f"{comp_type}\n")
        header_text.append("Description: ", style="bold")
        header_text.append(f"{description}\n")
        header_text.append("Source: ", style="bold")
        header_text.append(f"{source_file}", style="dim")

        panel = Panel(
            header_text,
            title="[bold magenta]Component Run[/bold magenta]",
            border_style="magenta",
            expand=False,
        )
        console.print(panel)

    async def _handle_llm_response_start(self, data: Dict[str, Any]):
        if not self._live or not self._live.is_started:
            self._live = Live(console=console, auto_refresh=False)
            self._live.start()

    async def _handle_llm_response(self, data: Dict[str, Any]):
        if self._live:
            content = data.get("content", "")
            self._full_response += content
            self._live.update(Text(self._full_response, "bright_white"), refresh=True)

    async def _handle_llm_response_stop(self, data: Dict[str, Any]):
        if self._live:
            self._live.stop()
        console.print(
            Panel(
                Text(self._full_response, "bright_white"),
                title="[bold cyan]Agent Response[/bold cyan]",
                border_style="cyan",
            )
        )
        self._full_response = ""  # Reset for next turn

    async def _handle_tool_call(self, data: Dict[str, Any]):
        tool_name = data.get("name", "Unknown Tool")
        tool_input = data.get("input", {})

        input_json = json.dumps(tool_input, indent=2)
        syntax = Syntax(input_json, "json", theme="monokai", line_numbers=True)

        panel = Panel(
            syntax,
            title=f"[bold yellow]:hammer_and_wrench: Tool Call: {tool_name}[/bold yellow]",
            subtitle="[yellow]Input[/yellow]",
            border_style="yellow",
        )
        console.print(panel)
        console.print(Spinner("dots", text=f" Executing {tool_name}..."))

    async def _handle_tool_output(self, data: Dict[str, Any]):
        tool_name = data.get("name", "Unknown Tool")
        tool_output = data.get("output", "")

        try:
            output_data = json.loads(tool_output)
            output_json = json.dumps(output_data, indent=2)
            syntax = Syntax(output_json, "json", theme="monokai", line_numbers=True)
        except (json.JSONDecodeError, TypeError):
            syntax = Text(str(tool_output))

        panel = Panel(
            syntax,
            title=f"[bold green]:white_check_mark: Tool Output: {tool_name}[/bold green]",
            subtitle="[green]Output[/green]",
            border_style="green",
        )
        console.print(panel)

    async def _handle_error(self, data: Dict[str, Any]):
        error_message = data.get("message", "An unknown error occurred.")
        panel = Panel(
            Text(error_message, "bold red"),
            title="[bold red]:x: Error[/bold red]",
            border_style="red",
        )
        console.print(panel)

    async def _handle_workflow_step_start(self, data: Dict[str, Any]):
        console.print(f"[grey50]Running workflow step: [bold]{data.get('name', 'Unnamed')}[/bold]...[/grey50]")

    async def _handle_workflow_step_end(self, data: Dict[str, Any]):
        console.print(f"[grey50]... finished step: [bold]{data.get('name', 'Unnamed')}[/bold].[/grey50]")

    async def _handle_unknown(self, data: Dict[str, Any]):
        console.print(f"[dim]Unknown event type received: {data}[/dim]")
