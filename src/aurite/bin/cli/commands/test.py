"""
Test command for running QA evaluations on components.

This module provides the 'aurite test' CLI command for running
evaluation configurations against components.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

from ....aurite import Aurite
from ....testing.qa.qa_engine import QAEngine
from ....utils.errors import AuriteError

console = Console()
logger = console.print


# --- Helper Functions ---

_aurite_instance = None


async def get_aurite_instance():
    """Get or create the singleton Aurite instance."""
    global _aurite_instance
    if _aurite_instance is None:
        _aurite_instance = Aurite(start_dir=Path.cwd())
        await _aurite_instance._ensure_initialized()
    return _aurite_instance


def format_test_case_panel(
    case_index: int,
    test_name: str,
    case_id: str,
    case_result: Any,
    expectations: list,
    original_tc: dict,
) -> Panel:
    """
    Create a formatted panel for a single test case result.

    Args:
        case_index: The index of the test case (0-based)
        test_name: The name of the test case
        case_id: The UUID of the test case result
        case_result: The test case result object
        expectations: List of expectations for this test
        original_tc: Original test case configuration

    Returns:
        A Rich Panel containing the formatted test case result
    """
    # Determine pass/fail status
    status_emoji = "✅" if case_result.grade == "PASS" else "❌"
    status_text = "PASSED" if case_result.grade == "PASS" else "FAILED"
    status_color = "green" if case_result.grade == "PASS" else "red"

    # Format input
    input_str = json.dumps(case_result.input) if hasattr(case_result, "input") else "N/A"
    if len(input_str) > 100:
        input_str = input_str[:97] + "..."

    # Format expectations
    expectations_lines = []
    if expectations:
        for exp in expectations:
            expectations_lines.append(f"  • {exp}")
    else:
        expectations_lines.append("  No expectations defined")

    # Format analysis
    analysis = case_result.analysis if case_result.analysis else "No analysis available"
    # Word wrap analysis at ~70 chars for readability
    analysis_lines = []
    words = analysis.split()
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 > 70:
            if current_line:
                analysis_lines.append(current_line)
            current_line = word
        else:
            current_line = f"{current_line} {word}" if current_line else word
    if current_line:
        analysis_lines.append(current_line)

    # Build the panel content
    content_lines = [
        f"[bold {status_color}]{status_emoji} {status_text}[/bold {status_color}] (Score: {'100%' if case_result.grade == 'PASS' else '0%'})",
        "",
        "[bold cyan]Input:[/bold cyan]",
        f"  {input_str}",
        "",
        "[bold cyan]Expectations:[/bold cyan]",
    ]
    content_lines.extend(expectations_lines)
    content_lines.extend(
        [
            "",
            "[bold cyan]Analysis:[/bold cyan]",
        ]
    )
    for line in analysis_lines:
        content_lines.append(f"  {line}")

    # Add UUID at the bottom in smaller text
    content_lines.extend(
        [
            "",
            f"[dim]UUID: {case_id}[/dim]",
        ]
    )

    # Create the panel
    panel = Panel(
        "\n".join(content_lines),
        title=f"[bold]Test #{case_index + 1}: {test_name}[/bold]",
        border_style="blue" if case_result.grade == "PASS" else "red",
        expand=False,
    )

    return panel


# --- Main Test Command ---


async def test_evaluation(
    name: str,
    test_cases: Optional[str] = None,
    short: bool = False,
    debug: bool = False,
    verbose: bool = False,
):
    """
    Run an evaluation configuration against components.

    Args:
        name: Name of the evaluation configuration to run
        test_cases: Optional filter for specific test cases
        short: Display compact output
        debug: Enable debug logging
        verbose: Show additional details
    """
    # Configure logging
    if not debug:
        logging.getLogger("aurite").setLevel(logging.WARNING)
        logging.getLogger("ComponentQATester").setLevel(logging.WARNING)

    aurite = None
    try:
        aurite = await get_aurite_instance()

        # Initialize QA Engine
        qa_engine = QAEngine(config_manager=aurite.kernel.config_manager)

        # Get evaluation config to check test cases before filtering
        eval_config = aurite.kernel.config_manager.get_config("evaluation", name)
        if not eval_config:
            logger(f"[bold red]Error:[/bold red] Evaluation configuration '{name}' not found.")
            return

        total_test_cases = len(eval_config.get("test_cases", []))
        filter_info = ""

        if test_cases:
            filter_info = f" with filter: {test_cases}"

        # Show progress while running evaluation
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(f"[cyan]Running evaluation: {name}{filter_info}[/cyan]", total=None)

            try:
                # Run the evaluation with optional test case filter
                results = await qa_engine.evaluate_by_config_id(
                    evaluation_config_id=name, executor=aurite.kernel.execution, test_cases_filter=test_cases
                )
                progress.update(task, completed=True)
            except Exception as e:
                progress.stop()
                logger(f"\n[bold red]Evaluation failed:[/bold red] {str(e)}")
                return

        # Display results for each component
        for _component_name, result in results.items():
            # Create summary panel
            status_color = "green" if result.status == "success" else "red"
            status_text = "✅ SUCCESS" if result.status == "success" else "❌ FAILED"

            panel_content = []
            panel_content.append(f"[bold]Component:[/bold] {result.component_name}")
            panel_content.append(f"[bold]Type:[/bold] {result.component_type}")
            panel_content.append(f"[bold]Status:[/bold] {status_text}")
            panel_content.append(f"[bold]Overall Score:[/bold] {result.overall_score:.1f}%")

            # Add Review LLM info
            review_llm = eval_config.get("review_llm", "default")
            panel_content.append(f"[bold]Review LLM:[/bold] {review_llm if review_llm else 'default'}")

            # Show filtering info if applicable
            if test_cases:
                panel_content.append(
                    f"[bold]Tests:[/bold] {result.passed_cases} passed, "
                    f"{result.failed_cases} failed "
                    f"(filtered: {result.total_cases}/{total_test_cases})"
                )
            else:
                panel_content.append(
                    f"[bold]Tests:[/bold] {result.passed_cases} passed, "
                    f"{result.failed_cases} failed (total: {result.total_cases})"
                )

            # Display the summary panel
            console.print(
                Panel(
                    "\n".join(panel_content),
                    title=f"[bold {status_color}]Evaluation Results: {name}[/bold {status_color}]",
                    border_style=status_color,
                )
            )

            # Display detailed test results if not in short mode
            if not short and result.case_results:
                # Get original test cases from config
                original_test_cases = eval_config.get("test_cases", []) if eval_config else []

                # Create a mapping of test cases by index
                test_case_map = {}
                for i, tc in enumerate(original_test_cases):
                    test_case_map[i] = tc

                console.print("\n[bold cyan]Test Case Details:[/bold cyan]\n")

                # Process each test case result
                case_index = 0
                for case_id, case_result in result.case_results.items():
                    # Get the original test case data
                    original_tc = test_case_map.get(case_index, {})
                    test_name = original_tc.get("name", f"Test {case_index + 1}")
                    expectations = original_tc.get("expectations", [])

                    # Create and display the panel for this test case
                    test_panel = format_test_case_panel(
                        case_index=case_index,
                        test_name=test_name,
                        case_id=case_id,
                        case_result=case_result,
                        expectations=expectations,
                        original_tc=original_tc,
                    )

                    console.print(test_panel)

                    case_index += 1
                    if case_index < len(result.case_results):
                        console.print()  # Add space between test cases

            # Show recommendations if any
            if result.recommendations and not short:
                console.print("\n[bold yellow]Recommendations:[/bold yellow]")
                for rec in result.recommendations:
                    console.print(f"  • {rec}")

            # Show execution time if verbose
            if verbose and result.duration_seconds:
                console.print(f"\n[dim]Execution time: {result.duration_seconds:.2f} seconds[/dim]")

    except AuriteError as e:
        console.print(
            Panel(
                Text(str(e), style="bold red"),
                title="[bold red]❌ Error[/bold red]",
                border_style="red",
            )
        )
    except Exception as e:
        logger(f"[bold red]Unexpected error:[/bold red] {str(e)}")
        if debug:
            import traceback

            console.print(traceback.format_exc())
    finally:
        if aurite:
            await aurite.kernel.shutdown()
