import json
import os
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ....aurite import Aurite
from ....utils.cli.ui_presenter import RunPresenter
from ....utils.errors import AuriteError

console = Console()
logger = console.print


# --- Main Execution Logic ---

_aurite_instance = None


async def get_aurite_instance():
    global _aurite_instance
    if _aurite_instance is None:
        _aurite_instance = Aurite(start_dir=Path.cwd())
        await _aurite_instance._ensure_initialized()
    return _aurite_instance


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
    import logging

    os.environ["AURITE_CONFIG_FORCE_REFRESH"] = "false"
    output_mode = "default"
    if short:
        output_mode = "short"
    if debug:
        output_mode = "debug"
    else:
        # Suppress all Aurite logs unless in debug mode
        logging.getLogger("aurite").setLevel(logging.WARNING)
        logging.getLogger("ComponentQATester").setLevel(logging.WARNING)

    aurite = None
    try:
        aurite = await get_aurite_instance()

        component_index = aurite.kernel.config_manager.get_component_index()
        found_components = [item for item in component_index if item["name"] == name]

        if not found_components:
            logger(f"Component '{name}' not found.")
            return

        component_to_run = next(
            (
                comp
                for comp in found_components
                if comp["component_type"]
                in ["agent", "linear_workflow", "custom_workflow", "graph_workflow", "evaluation"]
            ),
            found_components[0],
        )

        component_type = component_to_run["component_type"]

        if component_type == "agent":
            if not user_message:
                # Interactive mode - use Textual TUI
                from ...tui.apps.chat import TextualChatApp

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

        elif component_type in ["linear_workflow", "custom_workflow", "graph_workflow"]:
            presenter = RunPresenter(mode=output_mode)
            if not user_message:
                logger(f"[bold red]Error:[/bold red] An initial input is required to run a {component_type}.")
                return

            async def workflow_streamer():
                yield {"type": "workflow_step_start", "data": {"name": name}}
                try:
                    if component_type == "linear_workflow":
                        result = await aurite.run_linear_workflow(workflow_name=name, initial_input=user_message)
                    elif component_type == "graph_workflow":
                        result = await aurite.run_graph_workflow(workflow_name=name, initial_input=user_message)
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

        elif component_type == "evaluation":
            import logging

            from rich.progress import Progress, SpinnerColumn, TextColumn
            from rich.table import Table

            from ....testing.qa.qa_engine import QAEngine

            # Control logging based on debug flag
            if not debug:
                # Suppress INFO logs unless in debug mode
                logging.getLogger("aurite").setLevel(logging.WARNING)
                logging.getLogger("ComponentQATester").setLevel(logging.WARNING)

            # Initialize QA Engine with config manager
            qa_engine = QAEngine(config_manager=aurite.kernel.config_manager)

            # Show progress while running evaluation
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,  # Clear progress after completion
            ) as progress:
                task = progress.add_task(f"[cyan]Running evaluation: {name}[/cyan]", total=None)

                try:
                    # Run the evaluation
                    # aurite.kernel.execution is the AuriteEngine instance
                    results = await qa_engine.evaluate_by_config_id(
                        evaluation_config_id=name, executor=aurite.kernel.execution
                    )
                    progress.update(task, completed=True)
                except Exception as e:
                    progress.stop()
                    logger(f"\n[bold red]Evaluation failed:[/bold red] {str(e)}")
                    return

            # Ensure we're on a new line after progress completes
            logger("")  # Empty line for spacing

            # Display results for each component
            for _component_name, result in results.items():
                # Create a summary panel
                panel_content = []
                panel_content.append(f"[bold]Component:[/bold] {result.component_name}")
                panel_content.append(f"[bold]Type:[/bold] {result.component_type}")
                panel_content.append(
                    f"[bold]Status:[/bold] {'✅ SUCCESS' if result.status == 'success' else '❌ FAILED'}"
                )
                panel_content.append(f"[bold]Overall Score:[/bold] {result.overall_score:.1f}%")
                panel_content.append(
                    f"[bold]Tests:[/bold] {result.passed_cases} passed, {result.failed_cases} failed (total: {result.total_cases})"
                )

                console.print(
                    Panel(
                        "\n".join(panel_content),
                        title=f"[bold green]Evaluation Results: {name}[/bold green]",
                        border_style="green" if result.status == "success" else "red",
                    )
                )

                # Create detailed test results table if not in short mode
                if not short and result.case_results:
                    table = Table(title="Test Case Details", show_header=True, header_style="bold magenta")
                    table.add_column("Test Case", style="cyan", no_wrap=True)
                    table.add_column("Score", justify="right")
                    table.add_column("Status", justify="center")
                    table.add_column("Analysis")  # No width constraint for full text

                    for case_name, case_result in result.case_results.items():
                        # case_result is a CaseEvaluationResult object
                        # Use grade field to determine pass/fail
                        status_str = "✅" if case_result.grade == "PASS" else "❌"
                        # Calculate score based on grade (100% for PASS, 0% for FAIL)
                        score_str = "100%" if case_result.grade == "PASS" else "0%"
                        analysis = case_result.analysis if case_result.analysis else "No analysis available"
                        # Show full analysis text (no truncation)
                        table.add_row(case_name, score_str, status_str, analysis)

                    console.print(table)

                # Show recommendations if any
                if result.recommendations:
                    console.print("\n[bold yellow]Recommendations:[/bold yellow]")
                    for rec in result.recommendations:
                        console.print(f"  • {rec}")

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
