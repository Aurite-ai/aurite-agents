import json
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ...aurite import Aurite
from ...errors import AuriteError
from .ui_presenter import RunPresenter

console = Console()
logger = console.print


# --- Main Execution Logic ---


async def run_component(
    name: str,
    user_message: Optional[str],
    system_prompt: Optional[str],
    session_id: Optional[str],
    short: bool,
    debug: bool,
):
    """
    Finds a component by name, infers its type, and executes it with rich UI rendering.
    """
    output_mode = "default"
    if short:
        output_mode = "short"
    if debug:
        output_mode = "debug"

    aurite = None
    try:
        aurite = Aurite(start_dir=Path.cwd())
        await aurite._ensure_initialized()

        component_index = aurite.kernel.config_manager.get_component_index()
        found_components = [item for item in component_index if item["name"] == name]

        if not found_components:
            logger(f"Component '{name}' not found.")
            return

        component_to_run = next(
            (
                comp
                for comp in found_components
                if comp["component_type"] in ["agent", "linear_workflow", "custom_workflow"]
            ),
            found_components[0],
        )

        component_type = component_to_run["component_type"]

        if component_type == "agent":
            if not user_message:
                # Interactive mode - use Textual TUI
                from ..tui.chat import TextualChatApp

                if not session_id:
                    logger(
                        "[bold yellow]Warning:[/bold yellow] No --session-id provided. History will not be saved across runs."
                    )

                logger(f"[bold cyan]Launching interactive chat with agent: {name}[/bold cyan]")

                # Create and run the textual chat app with logging disabled
                chat_app = TextualChatApp(
                    agent_name=name,
                    session_id=session_id,
                    system_prompt=system_prompt,
                    start_dir=Path.cwd(),
                )

                try:
                    await chat_app.run_async()
                except KeyboardInterrupt:
                    pass
                finally:
                    logger("[bold cyan]Exiting interactive chat.[/bold cyan]")
            else:
                # Single-shot mode
                presenter = RunPresenter(mode=output_mode)
                stream = aurite.stream_agent(
                    agent_name=name,
                    user_message=user_message,
                    system_prompt=system_prompt,
                    session_id=session_id,
                )
                await presenter.render_stream(stream, component_to_run)

        elif component_type in ["linear_workflow", "custom_workflow"]:
            presenter = RunPresenter(mode=output_mode)
            if not user_message:
                logger(f"[bold red]Error:[/bold red] An initial input is required to run a {component_type}.")
                return

            async def workflow_streamer():
                yield {"type": "workflow_step_start", "data": {"name": name}}
                try:
                    if component_type == "linear_workflow":
                        result = await aurite.run_linear_workflow(workflow_name=name, initial_input=user_message)
                    else:
                        try:
                            parsed_input = json.loads(user_message)
                        except json.JSONDecodeError:
                            parsed_input = user_message
                        result = await aurite.run_custom_workflow(
                            workflow_name=name,
                            initial_input=parsed_input,
                            session_id=session_id,
                        )
                    yield {"type": "tool_output", "data": {"name": "Workflow Result", "output": str(result)}}
                except Exception as e:
                    yield {"type": "error", "data": {"message": str(e)}}
                finally:
                    yield {"type": "workflow_step_end", "data": {"name": name}}

            await presenter.render_stream(workflow_streamer(), component_to_run)

        else:
            logger(f"Component '{name}' is of type '{component_type}', which is not runnable.")

    except AuriteError as e:
        # Use a simple panel for top-level errors
        console.print(
            Panel(
                Text(str(e), "bold red"),
                title="[bold red]:x: Error[/bold red]",
                border_style="red",
            )
        )
    finally:
        if aurite:
            await aurite.kernel.shutdown()
