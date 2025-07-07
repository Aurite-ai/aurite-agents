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
        if self.mode == "default":
            self._render_header(component_info)

        final_output = ""
        try:
            async for event in stream:
                event_type = event.get("type")
                event_data = event.get("data", {})

                # Handle different display modes
                if self.mode == "debug":
                    console.print(event)
                elif self.mode == "default":
                    handler = getattr(self, f"_handle_{event_type}", self._handle_unknown)
                    await handler(event_data)
                elif self.mode == "short":
                    # Only accumulate for short mode
                    if event_type == "llm_response":
                        final_output += event_data.get("content", "")
                    elif event_type == "tool_output":
                        final_output = event_data.get("output", "")

        finally:
            if self._live and self._live.is_started:
                self._live.stop()
            if self.mode == "short":
                console.print(
                    f"[bold green]✔[/bold green] {component_info.get('name', 'Component')} finished: {str(final_output).strip()}"
                )

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
        # No longer using Live, so this is a no-op
        pass

    async def _handle_llm_response(self, data: Dict[str, Any]):
        content = data.get("content", "")
        self._full_response += content

    async def _handle_llm_response_stop(self, data: Dict[str, Any]):
        response_text = Text(self._full_response, "bright_white")
        response_text.no_wrap = False
        
        console.print(
            Panel(
                response_text,
                title="[bold cyan]Agent Response[/bold cyan]",
                border_style="cyan",
                expand=True,
            )
        )
        self._full_response = ""  # Reset for next turn

    async def _handle_tool_call(self, data: Dict[str, Any]):
        tool_name = data.get("name", "Unknown Tool")
        tool_input = data.get("input", {})

        input_json = json.dumps(tool_input, indent=2)
        syntax = Syntax(input_json, "json", theme="monokai", line_numbers=True, word_wrap=True)

        panel = Panel(
            syntax,
            title=f"[bold yellow]:hammer_and_wrench: Tool Call: {tool_name}[/bold yellow]",
            subtitle="[yellow]Input[/yellow]",
            border_style="yellow",
            expand=True,
        )
        console.print(panel)
        console.print(Spinner("dots", text=f" Executing {tool_name}..."))

    async def _handle_tool_output(self, data: Dict[str, Any]):
        tool_name = data.get("name", "Unknown Tool")
        tool_output = data.get("output", "")

        try:
            output_data = json.loads(tool_output)
            output_json = json.dumps(output_data, indent=2)
            syntax = Syntax(output_json, "json", theme="monokai", line_numbers=True, word_wrap=True)
        except (json.JSONDecodeError, TypeError):
            # For non-JSON output, create a Text object with proper wrapping
            syntax = Text(str(tool_output))
            syntax.no_wrap = False

        panel = Panel(
            syntax,
            title=f"[bold green]:white_check_mark: Tool Output: {tool_name}[/bold green]",
            subtitle="[green]Output[/green]",
            border_style="green",
            expand=True,
        )
        console.print(panel)

    async def _handle_error(self, data: Dict[str, Any]):
        error_message = data.get("message", "An unknown error occurred.")
        error_text = Text(error_message, "bold red")
        error_text.no_wrap = False
        
        panel = Panel(
            error_text,
            title="[bold red]:x: Error[/bold red]",
            border_style="red",
            expand=True,
        )
        console.print(panel)

    async def _handle_workflow_step_start(self, data: Dict[str, Any]):
        console.print(f"[grey50]Running workflow step: [bold]{data.get('name', 'Unnamed')}[/bold]...[/grey50]")

    async def _handle_workflow_step_end(self, data: Dict[str, Any]):
        console.print(f"[grey50]... finished step: [bold]{data.get('name', 'Unnamed')}[/bold].[/grey50]")

    async def _handle_unknown(self, data: Dict[str, Any]):
        console.print(f"[dim]Unknown event type received: {data}[/dim]")
