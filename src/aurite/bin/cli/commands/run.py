import json
import os
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel

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
    test_cases: Optional[str] = None,
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

            from ....testing.qa.qa_engine import QAEngine

            # Control logging based on debug flag
            if not debug:
                # Suppress INFO logs unless in debug mode
                logging.getLogger("aurite").setLevel(logging.WARNING)
                logging.getLogger("ComponentQATester").setLevel(logging.WARNING)

            # Initialize QA Engine with config manager
            qa_engine = QAEngine(config_manager=aurite.kernel.config_manager)

            # Get evaluation config to check test cases before filtering
            eval_config = aurite.kernel.config_manager.get_config("evaluation", name)
            total_test_cases = len(eval_config.get("test_cases", []))
            filter_info = ""

            if test_cases:
                filter_info = f" with filter: {test_cases}"

            # Show progress while running evaluation
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,  # Clear progress after completion
            ) as progress:
                task = progress.add_task(f"[cyan]Running evaluation: {name}{filter_info}[/cyan]", total=None)

                try:
                    # Run the evaluation with optional test case filter
                    # aurite.kernel.execution is the AuriteEngine instance
                    results = await qa_engine.evaluate_by_config_id(
                        evaluation_config_id=name, executor=aurite.kernel.execution, test_cases_filter=test_cases
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

                # Add Review LLM info
                review_llm = eval_config.get("review_llm", "default")
                panel_content.append(f"[bold]Review LLM:[/bold] {review_llm if review_llm else 'default'}")

                # Show filtering info if applicable
                if test_cases:
                    panel_content.append(
                        f"[bold]Tests:[/bold] {result.passed_cases} passed, {result.failed_cases} failed "
                        f"(filtered: {result.total_cases}/{total_test_cases})"
                    )
                else:
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
                    # Get original test cases from config to match with results
                    original_test_cases = eval_config.get("test_cases", []) if eval_config else []

                    # Create a mapping of test cases by index
                    test_case_map = {}
                    for i, tc in enumerate(original_test_cases):
                        # Results are keyed by UUID, but we can match by order
                        test_case_map[i] = tc

                    console.print("\n[bold cyan]Test Case Details:[/bold cyan]\n")

                    # Process each test case result
                    case_index = 0
                    for case_id, case_result in result.case_results.items():
                        # Get the original test case data if available
                        original_tc = test_case_map.get(case_index, {})
                        test_name = original_tc.get("name", f"Test {case_index + 1}")
                        expectations = original_tc.get("expectations", [])

                        # Merge status into score
                        status_emoji = "✅" if case_result.grade == "PASS" else "❌"
                        score_str = f"{status_emoji} 100%" if case_result.grade == "PASS" else f"{status_emoji} 0%"

                        expectations_str = (
                            "\n".join([f"• {exp}" for exp in expectations])
                            if expectations
                            else "No expectations defined"
                        )
                        input_str = json.dumps(case_result.input) if hasattr(case_result, "input") else "N/A"
                        if len(input_str) > 100:  # Truncate very long inputs
                            input_str = input_str[:100] + "..."
                        analysis = case_result.analysis if case_result.analysis else "No analysis available"

                        # Create the 3-row layout using a Panel with formatted text
                        from rich.columns import Columns
                        from rich.console import Group
                        from rich.text import Text

                        # Row 1: Test Name and Expectations
                        row1 = Columns(
                            [
                                Text(f"[bold cyan]Test Name:[/bold cyan] {test_name}", overflow="fold"),
                                Text(f"[bold cyan]Expectations:[/bold cyan]\n{expectations_str}", overflow="fold"),
                            ],
                            equal=True,
                            expand=True,
                        )

                        # Row 2: UUID and Input
                        row2 = Columns(
                            [
                                Text(f"[bold cyan]UUID:[/bold cyan] {case_id}", overflow="fold"),
                                Text(f"[bold cyan]Input:[/bold cyan] {input_str}", overflow="fold"),
                            ],
                            equal=True,
                            expand=True,
                        )

                        # Row 3: Score and Analysis
                        row3 = Columns(
                            [
                                Text(f"[bold cyan]Score:[/bold cyan] {score_str}", overflow="fold"),
                                Text(f"[bold cyan]Analysis:[/bold cyan] {analysis}", overflow="fold"),
                            ],
                            equal=True,
                            expand=True,
                        )

                        # Group the rows together
                        content = Group(row1, Text(""), row2, Text(""), row3)  # Empty Text for spacing

                        # Wrap in a panel for each test case
                        test_panel = Panel(content, title=f"[bold]Test #{case_index + 1}[/bold]", border_style="blue")

                        console.print(test_panel)

                        case_index += 1
                        if case_index < len(result.case_results):
                            console.print("")  # Add space between test cases

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
