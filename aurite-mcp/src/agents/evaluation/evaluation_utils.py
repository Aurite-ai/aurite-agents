"""
Utility functions for performing evaluations with the EvaluationWorkflow.

This module provides reusable functions for evaluating outputs from
different workflows or agents using configurable rubrics.
"""

import logging
from typing import Dict, Any, Optional

from .models import (
    create_standard_rubric,
    create_planning_rubric,
    create_qa_rubric,
    create_analysis_rubric,
    create_creative_rubric,
)
from .evaluation_workflow import EvaluationWorkflow

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)


async def evaluate_workflow_output(
    evaluation_workflow: EvaluationWorkflow,
    workflow_name: str,
    workflow_output: str,
    rubric_type: str = "standard",
    custom_rubric: Optional[Dict[str, Any]] = None,
    run_count: int = 1,
    expected_output: str = "",
    detailed_feedback: bool = True,
) -> Dict[str, Any]:
    """
    Evaluate output from any workflow with configurable rubric.

    This utility function provides a standardized way to evaluate outputs
    from any workflow or agent using different rubric types. It supports
    both single-run and multi-run evaluations.

    Args:
        evaluation_workflow: Instance of EvaluationWorkflow to use
        workflow_name: Name of the workflow being evaluated (for logging)
        workflow_output: The output content to evaluate
        rubric_type: One of "standard", "planning", "qa", "analysis", "creative"
        custom_rubric: Optional custom rubric dict, overrides rubric_type
        run_count: Number of evaluation runs (1 for single, >1 for multi-run)
        expected_output: Optional reference output for comparison
        detailed_feedback: Whether to generate detailed feedback

    Returns:
        Dict containing evaluation results with metadata
    """
    # Get the appropriate rubric
    if custom_rubric:
        rubric = custom_rubric
        rubric_name = "custom"
    else:
        if rubric_type == "planning":
            rubric = create_planning_rubric().model_dump()
        elif rubric_type == "qa":
            rubric = create_qa_rubric().model_dump()
        elif rubric_type == "analysis":
            rubric = create_analysis_rubric().model_dump()
        elif rubric_type == "creative":
            rubric = create_creative_rubric().model_dump()
        else:
            rubric = create_standard_rubric().model_dump()
        rubric_name = rubric_type

    # Perform evaluation
    logger.info(f"Evaluating {workflow_name} output with {rubric_name} rubric...")

    if run_count <= 1:
        # Single evaluation
        result = await evaluation_workflow.evaluate_agent(
            agent_output=workflow_output,
            rubric=rubric,
            expected_output=expected_output,
            detailed_feedback=detailed_feedback,
        )
        return {
            "workflow_name": workflow_name,
            "rubric_type": rubric_name,
            "single_run": True,
            "result": result,
        }
    else:
        # Multi-run evaluation
        result = await evaluation_workflow.evaluate_multi_run(
            agent_output=workflow_output,
            rubric=rubric,
            expected_output=expected_output,
            num_runs=run_count,
            detailed_feedback=detailed_feedback,
        )
        return {
            "workflow_name": workflow_name,
            "rubric_type": rubric_name,
            "single_run": False,
            "num_runs": run_count,
            "result": result,
        }


def get_rubric_by_type(rubric_type: str) -> Dict[str, Any]:
    """
    Get a rubric configuration by type name.

    Args:
        rubric_type: One of "standard", "planning", "qa", "analysis", "creative"

    Returns:
        Rubric configuration as a dictionary
    """
    if rubric_type == "planning":
        return create_planning_rubric().model_dump()
    elif rubric_type == "qa":
        return create_qa_rubric().model_dump()
    elif rubric_type == "analysis":
        return create_analysis_rubric().model_dump()
    elif rubric_type == "creative":
        return create_creative_rubric().model_dump()
    else:
        return create_standard_rubric().model_dump()


def summarize_evaluation_result(evaluation_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a summarized version of an evaluation result.

    Args:
        evaluation_result: Full evaluation result from evaluate_workflow_output

    Returns:
        Simplified evaluation summary
    """
    workflow_name = evaluation_result["workflow_name"]
    rubric_type = evaluation_result["rubric_type"]

    if evaluation_result["single_run"]:
        # Extract single run data
        result_data = evaluation_result["result"]["data"]["evaluation_result"]
        score = result_data.get("score", 0)
        passed = result_data.get("passed", False)
        strengths = result_data.get("strengths", [])
        areas = result_data.get("areas_for_improvement", [])

        return {
            "workflow_name": workflow_name,
            "rubric_type": rubric_type,
            "single_run": True,
            "score": score,
            "passed": passed,
            "strengths": strengths[:3],  # Top 3 strengths
            "areas_for_improvement": areas[:3],  # Top 3 areas
        }
    else:
        # Extract multi-run data
        aggregated = evaluation_result["result"]["data"]["aggregated_result"]
        return {
            "workflow_name": workflow_name,
            "rubric_type": rubric_type,
            "single_run": False,
            "num_runs": evaluation_result["num_runs"],
            "mean_score": aggregated.get("mean_score", 0),
            "median_score": aggregated.get("median_score", 0),
            "pass_rate": aggregated.get("pass_rate", 0),
            "common_strengths": aggregated.get("common_strengths", [])[:3],
            "common_areas_for_improvement": aggregated.get(
                "common_areas_for_improvement", []
            )[:3],
            "summary": aggregated.get("summary", ""),
        }
