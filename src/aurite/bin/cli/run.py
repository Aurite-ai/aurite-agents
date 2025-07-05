import json
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ...errors import AuriteError
from ...host_manager import Aurite
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

    try:
        async with Aurite(start_dir=Path.cwd()) as aurite:
            component_index = aurite.kernel.config_manager.get_component_index()
            found_components = [item for item in component_index if item["name"] == name]

            if not found_components:
                logger(f"Component '{name}' not found.")
                return

            component_to_run = next(
                (
                    comp
                    for comp in found_components
                    if comp["component_type"] in ["agent", "simple_workflow", "custom_workflow"]
                ),
                found_components[0],
            )

            component_type = component_to_run["component_type"]
            presenter = RunPresenter(mode=output_mode)

            if component_type == "agent":
                if not user_message:
                    logger("[bold red]Error:[/bold red] A user message is required to run an agent.")
                    return
                stream = aurite.stream_agent(
                    agent_name=name,
                    user_message=user_message,
                    system_prompt=system_prompt,
                    session_id=session_id,
                )
                await presenter.render_stream(stream, component_to_run)

            elif component_type in ["simple_workflow", "custom_workflow"]:
                if not user_message:
                    logger(f"[bold red]Error:[/bold red] An initial input is required to run a {component_type}.")
                    return

                async def workflow_streamer():
                    yield {"type": "workflow_step_start", "data": {"name": name}}
                    try:
                        if component_type == "simple_workflow":
                            result = await aurite.run_simple_workflow(workflow_name=name, initial_input=user_message)
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
