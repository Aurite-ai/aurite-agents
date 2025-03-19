"""
Integration test for the evaluation workflow with planning workflow.

This focused test verifies:
1. The evaluation workflow can evaluate outputs from planning workflow
2. Different rubrics can be applied to evaluate planning content
3. Integration between the two workflows is seamless
"""

import logging
import pytest
import time
import json
from unittest.mock import patch, MagicMock
from typing import Dict, Any, Optional

import mcp.types as types

from src.agents.planning.planning_workflow import PlanningWorkflow
from src.agents.evaluation.evaluation_workflow import EvaluationWorkflow
from src.agents.evaluation.models import (
    create_standard_rubric,
    create_planning_rubric,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)


async def setup_workflow_for_testing(host, workflow_class, name: str):
    """Helper function to set up and initialize a workflow for testing."""
    workflow = workflow_class(host=host, name=name)
    with patch.object(workflow, "_validate_tools", return_value=None):
        await workflow.initialize()
    host.workflows._workflows[name] = workflow
    return workflow


def create_mock_evaluation_result(
    score: float = 4.5,
    rubric_type: str = "planning",
    strengths: Optional[list] = None,
    areas_for_improvement: Optional[list] = None,
    criterion_scores: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Helper function to create a mock evaluation result."""
    return {
        "score": score,
        "feedback": f"Good output with a {rubric_type} rubric evaluation",
        "strengths": strengths
        or [
            "Clear structure",
            "Good progression",
            "Realistic timeframes",
        ],
        "areas_for_improvement": areas_for_improvement
        or [
            "Could add more resources",
            "More specific milestones",
        ],
        "criterion_scores": criterion_scores
        or {
            "structure": 4.5,
            "content": 4.3,
            "feasibility": 4.7,
            "clarity": 4.4,
        },
        "passed": True,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


async def mock_tool_execution(tool_name: str, arguments: Dict[str, Any]) -> list:
    """Helper function to mock tool execution responses."""
    if tool_name == "evaluate_agent":
        rubric_type = (
            "planning"
            if "planning" in str(arguments.get("criteria", {}))
            else "standard"
        )
        score = 4.5 if rubric_type == "planning" else 4.2
        result = create_mock_evaluation_result(score=score, rubric_type=rubric_type)
        return [types.TextContent(type="text", text=json.dumps(result))]
    elif tool_name == "save_plan":
        timestamp = int(time.time())
        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": True,
                        "message": "Plan saved successfully",
                        "path": f"plans/test_plan_{timestamp}.txt",
                    }
                ),
            )
        ]
    return [types.TextContent(type="text", text=f"Executed {tool_name}")]


@pytest.mark.asyncio
async def test_evaluation_workflow_initialization(test_mcp_host):
    """Test that the evaluation workflow initializes correctly with the test host."""
    workflow = await setup_workflow_for_testing(
        test_mcp_host, EvaluationWorkflow, "test_evaluation_workflow"
    )
    assert isinstance(workflow.name, str) and workflow.name
    assert workflow.host == test_mcp_host
    assert len(workflow.steps) >= 1


@pytest.mark.asyncio
async def test_workflow_evaluation(test_mcp_host):
    """
    Test evaluating a workflow's output using the evaluation workflow.
    This test demonstrates how to evaluate any workflow output with different rubrics.
    """
    logger.info("Starting workflow evaluation test...")

    try:
        # Set up both workflows
        planning_workflow = await setup_workflow_for_testing(
            test_mcp_host, PlanningWorkflow, "test_planning_workflow"
        )
        eval_workflow = await setup_workflow_for_testing(
            test_mcp_host, EvaluationWorkflow, "test_evaluation_workflow"
        )

        # Create sample workflow output (can be replaced with actual workflow execution)
        workflow_output = """
        # Python Learning Plan

        ## Month 1: Basics
        - Learn Python syntax
        - Practice with exercises

        ## Month 2: Intermediate
        - Data structures
        - Functions and modules

        ## Month 3: Projects
        - Build small applications
        - Code review practice
        """

        # Get rubrics for testing
        planning_rubric = create_planning_rubric().model_dump()
        standard_rubric = create_standard_rubric().model_dump()

        # Mock tool execution
        with patch.object(
            test_mcp_host.tools, "execute_tool", side_effect=mock_tool_execution
        ):
            # Test with planning rubric
            logger.info("Testing evaluation with planning rubric...")
            plan_eval = await eval_workflow.evaluate_agent(
                agent_output=workflow_output,
                rubric=planning_rubric,
                detailed_feedback=True,
            )

            # Verify planning rubric evaluation
            assert plan_eval["success"] is True
            assert "data" in plan_eval
            assert "evaluation_result" in plan_eval["data"]

            eval_data = plan_eval["data"]["evaluation_result"]
            logger.info(f"Planning rubric score: {eval_data.get('score', 'unknown')}")
            assert (
                eval_data["score"] >= 4.0
            ), "Planning evaluation score should be >= 4.0"

            # Test with standard rubric
            logger.info("Testing evaluation with standard rubric...")
            std_eval = await eval_workflow.evaluate_agent(
                agent_output=workflow_output,
                rubric=standard_rubric,
                detailed_feedback=True,
            )

            # Verify standard rubric evaluation
            assert std_eval["success"] is True
            std_data = std_eval["data"]["evaluation_result"]
            logger.info(f"Standard rubric score: {std_data.get('score', 'unknown')}")
            assert (
                std_data["score"] >= 4.0
            ), "Standard evaluation score should be >= 4.0"

    except Exception as e:
        logger.error(f"Error during workflow evaluation test: {e}")
        raise

    logger.info("Workflow evaluation test completed successfully")


@pytest.mark.asyncio
async def test_multi_run_workflow_evaluation(test_mcp_host):
    """
    Test evaluating a workflow's output multiple times for statistical significance.
    """
    logger.info("Starting multi-run workflow evaluation test...")

    try:
        # Set up workflows
        eval_workflow = await setup_workflow_for_testing(
            test_mcp_host, EvaluationWorkflow, "test_evaluation_workflow"
        )

        # Sample workflow output
        workflow_output = """
        # Data Analysis Plan

        ## Phase 1: Data Collection
        - Define data sources
        - Set up collection pipeline

        ## Phase 2: Processing
        - Clean and validate data
        - Transform for analysis

        ## Phase 3: Analysis
        - Apply statistical methods
        - Generate insights
        """

        # Use planning rubric for multi-run evaluation
        planning_rubric = create_planning_rubric().model_dump()

        # Mock tool execution
        with patch.object(
            test_mcp_host.tools, "execute_tool", side_effect=mock_tool_execution
        ):
            # Perform multi-run evaluation
            logger.info("Performing multi-run evaluation...")
            multi_eval = await eval_workflow.evaluate_multi_run(
                agent_output=workflow_output,
                rubric=planning_rubric,
                num_runs=3,
                detailed_feedback=True,
            )

            # Verify multi-run results
            assert multi_eval["success"] is True
            assert "data" in multi_eval
            assert "aggregated_result" in multi_eval["data"]

            agg_data = multi_eval["data"]["aggregated_result"]
            logger.info(
                f"Multi-run mean score: {agg_data.get('mean_score', 'unknown')}"
            )
            assert (
                agg_data["mean_score"] >= 4.0
            ), "Mean evaluation score should be >= 4.0"
            assert agg_data["std_deviation"] < 0.5, "Score variation should be < 0.5"

    except Exception as e:
        logger.error(f"Error during multi-run workflow evaluation test: {e}")
        raise

    logger.info("Multi-run workflow evaluation test completed successfully")
