import json
from pathlib import Path
from typing import Optional
from rich.console import Console
from ...host_manager import Aurite
from ...errors import AuriteError

console = Console()
logger = console.print


async def run_component(
    name: str,
    user_message: Optional[str],
    system_prompt: Optional[str],
    session_id: Optional[str],
):
    """
    Finds a component by name, infers its type, and executes it.
    """
    try:
        async with Aurite(start_dir=Path.cwd()) as aurite:
            component_index = aurite.get_config_manager().get_component_index()
            found_components = [
                item for item in component_index if item["name"] == name
            ]

            if not found_components:
                logger(f"Component '{name}' not found.")
                return

            component_to_run = None
            if len(found_components) > 1:
                # Disambiguate if multiple components have the same name
                # For now, we'll just pick the first runnable one.
                # A better implementation might prompt the user.
                runnable_types = ["agent", "simple_workflow", "custom_workflow"]
                for comp in found_components:
                    if comp["component_type"] in runnable_types:
                        component_to_run = comp
                        break
                if not component_to_run:
                    logger(
                        f"Found multiple components named '{name}', but none are runnable."
                    )
                    return
            else:
                component_to_run = found_components[0]

            component_type = component_to_run["component_type"]

            if component_type == "agent":
                if not user_message:
                    logger(
                        "[bold red]Error:[/bold red] A user message is required to run an agent."
                    )
                    return

                logger("[bold]Agent Run Result:[/bold]")
                async for event in aurite.stream_agent(
                    agent_name=name,
                    user_message=user_message,
                    system_prompt=system_prompt,
                    session_id=session_id,
                ):
                    if event.get("type") == "llm_response":
                        print(
                            event.get("data", {}).get("content", ""), end="", flush=True
                        )
                print()  # for newline at the end

            elif component_type == "simple_workflow":
                if not user_message:
                    logger(
                        "[bold red]Error:[/bold red] An initial input is required to run a simple workflow."
                    )
                    return
                result = await aurite.run_simple_workflow(
                    workflow_name=name, initial_input=user_message
                )
                logger("\n[bold]Simple Workflow Result:[/bold]")
                console.print(result)

            elif component_type == "custom_workflow":
                if not user_message:
                    logger(
                        "[bold red]Error:[/bold red] An initial input is required to run a custom workflow."
                    )
                    return
                try:
                    parsed_input = json.loads(user_message)
                except json.JSONDecodeError:
                    parsed_input = user_message
                result = await aurite.run_custom_workflow(
                    workflow_name=name,
                    initial_input=parsed_input,
                    session_id=session_id,
                )
                logger("\n[bold]Custom Workflow Result:[/bold]")
                console.print(result)
            else:
                logger(
                    f"Component '{name}' is of type '{component_type}', which is not runnable."
                )

    except AuriteError as e:
        logger(f"\n[bold red]Framework Error:[/bold red] {e}")
