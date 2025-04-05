"""
Tests for the evaluation workflow.

This module tests the EvaluationWorkflow implementation to verify:
1. Workflow initialization and setup
2. Agent output evaluation
3. Multi-run evaluation
4. Result aggregation
5. Rubric handling
"""

import pytest
import json
from unittest.mock import AsyncMock

import mcp.types as types

# Use absolute imports for better clarity
from src.agents.evaluation.evaluation_workflow import (
    EvaluationWorkflow,
    EvaluateAgentStep,
    AggregateEvaluationsStep,
)
from src.agents.evaluation.models import (
    create_standard_rubric,
)


# --- Test Fixtures ---


@pytest.fixture
def mock_evaluation_tool_manager(mock_tool_manager):
    """Create a mock tool manager for evaluation testing."""

    # Add specific mock responses for evaluation tools
    async def mock_execute_tool(tool_name, arguments):
        """Mock tool execution with predefined responses for evaluation tools."""
        if tool_name == "evaluate_agent":
            agent_output = arguments.get("agent_output", "")
            criteria = arguments.get("criteria", {})
            expected_output = arguments.get("expected_output", "")

            # Return a mock evaluation result
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "score": 4.2,
                            "passed": True,
                            "criterion_scores": {
                                "accuracy": {
                                    "score": 4.0,
                                    "justification": "The agent provided mostly accurate information with only minor imprecisions.",
                                },
                                "relevance": {
                                    "score": 4.5,
                                    "justification": "The output thoroughly addressed the query with comprehensive coverage.",
                                },
                                "coherence": {
                                    "score": 4.0,
                                    "justification": "The response was well-structured and easy to follow.",
                                },
                                "completeness": {
                                    "score": 4.3,
                                    "justification": "The output provided comprehensive coverage of the topic.",
                                },
                            },
                            "summary_feedback": "Overall, the agent performed well, providing a comprehensive and accurate response that was well-structured.",
                            "strengths": [
                                "Thorough coverage of the topic",
                                "Well-organized presentation",
                                "Accurate information",
                            ],
                            "areas_for_improvement": [
                                "Could provide more specific examples",
                                "Minor inaccuracies in some details",
                            ],
                        }
                    ),
                )
            ]
        elif tool_name == "aggregate_evaluations":
            # Return a mock aggregation result
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "mean_score": 4.15,
                            "median_score": 4.2,
                            "min_score": 3.8,
                            "max_score": 4.5,
                            "std_deviation": 0.25,
                            "pass_rate": 1.0,
                            "criterion_mean_scores": {
                                "accuracy": 4.1,
                                "relevance": 4.3,
                                "coherence": 4.0,
                                "completeness": 4.2,
                            },
                            "criterion_std_deviations": {
                                "accuracy": 0.3,
                                "relevance": 0.2,
                                "coherence": 0.3,
                                "completeness": 0.25,
                            },
                            "common_strengths": [
                                "Thorough coverage of the topic",
                                "Well-organized presentation",
                            ],
                            "common_areas_for_improvement": [
                                "Could provide more specific examples",
                                "Minor inaccuracies in some details",
                            ],
                            "summary": "Across 3 evaluations, the agent demonstrates very good performance that is somewhat variable (σ=0.25). Key strengths include Thorough coverage of the topic, Well-organized presentation. Areas for improvement include Could provide more specific examples, Minor inaccuracies in some details.",
                            "num_runs": 3,
                        }
                    ),
                )
            ]

        # Default response for unknown tools
        return [
            types.TextContent(
                type="text", text=f"Executed {tool_name} with {arguments}"
            )
        ]

    # Replace the mock_execute_tool with our evaluation-specific version
    mock_tool_manager.execute_tool = AsyncMock(side_effect=mock_execute_tool)

    return mock_tool_manager


@pytest.fixture
def sample_agent_output():
    """Sample agent output for testing."""
    return """I've analyzed the data and here are my findings:

1. Revenue increased by 15% year-over-year, reaching $2.4 million
2. Customer acquisition cost decreased from $52 to $48
3. Retention rate improved from 68% to 72%

The main growth drivers were:
- New product line expansion (+22% revenue impact)
- Improved marketing efficiency (+8% conversion rate)
- Price optimization strategy (+5% margin improvement)

Recommendations:
1. Continue investing in product expansion
2. Allocate more resources to high-converting marketing channels
3. Consider further price optimization in underperforming segments
4. Improve onboarding to boost retention further

Let me know if you need more specific analysis on any of these areas."""


# --- Tests ---


@pytest.mark.asyncio
async def test_workflow_initialization(mock_evaluation_tool_manager, mock_mcp_host):
    """Test that the evaluation workflow initializes correctly."""
    # Create workflow with tool_manager and host
    workflow = EvaluationWorkflow(
        tool_manager=mock_evaluation_tool_manager, host=mock_mcp_host
    )

    # Check that workflow is set up correctly
    assert workflow.name == "evaluation_workflow"
    assert len(workflow.steps) == 2  # Evaluate and Aggregate steps
    assert workflow.tool_manager == mock_evaluation_tool_manager
    assert workflow.host == mock_mcp_host

    # Initialize workflow
    await workflow.initialize()

    # Verify tool validation was called
    mock_evaluation_tool_manager.has_tool.assert_called()


@pytest.mark.asyncio
async def test_evaluate_agent_step(mock_evaluation_tool_manager, sample_agent_output):
    """Test the evaluate agent step."""
    # Create step
    step = EvaluateAgentStep()

    # Create a context with required inputs
    from src.agents.base_models import AgentContext, AgentData

    context = AgentContext(
        data=AgentData(
            agent_output=sample_agent_output,
            rubric=create_standard_rubric().model_dump(),
            expected_output="",
            detailed_feedback=True,
        )
    )
    context.tool_manager = mock_evaluation_tool_manager

    # Execute step
    result = await step.execute(context)

    # Verify tool was called correctly
    mock_evaluation_tool_manager.execute_tool.assert_called_once()
    args = mock_evaluation_tool_manager.execute_tool.call_args[0]
    assert args[0] == "evaluate_agent"

    # Verify result structure
    assert "evaluation_result" in result
    assert "raw_tool_result" in result
    assert "score" in result["evaluation_result"]
    assert "criterion_scores" in result["evaluation_result"]
    assert "summary_feedback" in result["evaluation_result"]


@pytest.mark.asyncio
async def test_aggregate_evaluations_step(mock_evaluation_tool_manager):
    """Test the aggregate evaluations step."""
    # Create step
    step = AggregateEvaluationsStep()

    # Create a context with required inputs - three evaluation results
    from src.agents.base_models import AgentContext, AgentData

    evaluation_results = [
        {
            "score": 4.2,
            "criterion_scores": {
                "accuracy": {"score": 4.0, "justification": "Good accuracy"},
                "relevance": {"score": 4.5, "justification": "Very relevant"},
                "coherence": {"score": 4.0, "justification": "Well structured"},
                "completeness": {"score": 4.3, "justification": "Comprehensive"},
            },
            "strengths": ["Thorough coverage", "Well organized"],
            "areas_for_improvement": ["More examples", "Minor inaccuracies"],
        },
        {
            "score": 4.0,
            "criterion_scores": {
                "accuracy": {"score": 3.8, "justification": "Some inaccuracies"},
                "relevance": {"score": 4.2, "justification": "Mostly relevant"},
                "coherence": {"score": 4.0, "justification": "Well structured"},
                "completeness": {"score": 4.0, "justification": "Good coverage"},
            },
            "strengths": ["Well organized", "Good structure"],
            "areas_for_improvement": ["More examples", "Improve accuracy"],
        },
        {
            "score": 4.3,
            "criterion_scores": {
                "accuracy": {"score": 4.2, "justification": "Very accurate"},
                "relevance": {"score": 4.5, "justification": "Highly relevant"},
                "coherence": {"score": 4.0, "justification": "Well structured"},
                "completeness": {"score": 4.5, "justification": "Very comprehensive"},
            },
            "strengths": ["Thorough coverage", "Accurate information"],
            "areas_for_improvement": ["More examples", "Could be more concise"],
        },
    ]

    context = AgentContext(data=AgentData(evaluation_results=evaluation_results))
    context.tool_manager = mock_evaluation_tool_manager

    # Execute step
    result = await step.execute(context)

    # Verify result structure for in-memory aggregation
    assert "aggregated_result" in result
    assert "raw_tool_result" in result
    assert "mean_score" in result["aggregated_result"]
    assert "criterion_mean_scores" in result["aggregated_result"]

    # Test using evaluation IDs
    context = AgentContext(
        data=AgentData(
            evaluation_ids=["eval_001", "eval_002", "eval_003"], agent_id="test_agent"
        )
    )
    context.tool_manager = mock_evaluation_tool_manager

    # Execute step
    result = await step.execute(context)

    # Verify tool was called correctly
    tool_called = False
    for call in mock_evaluation_tool_manager.execute_tool.call_args_list:
        args = call[0]
        if args[0] == "aggregate_evaluations":
            tool_called = True
            assert "evaluation_ids" in args[1]
            assert "agent_id" in args[1]

    assert tool_called

    # Verify result structure
    assert "aggregated_result" in result
    assert "mean_score" in result["aggregated_result"]


@pytest.mark.asyncio
async def test_evaluation_workflow_single_run(
    mock_evaluation_tool_manager, mock_mcp_host, sample_agent_output
):
    """Test the complete evaluation workflow with a single run."""
    # Create workflow
    workflow = EvaluationWorkflow(
        tool_manager=mock_evaluation_tool_manager, host=mock_mcp_host
    )

    # Initialize
    await workflow.initialize()

    # Execute using the high-level method
    result = await workflow.evaluate_agent(
        agent_output=sample_agent_output,
        rubric="standard",
        expected_output="",
        detailed_feedback=True,
    )

    # Verify result
    assert result["success"] is True
    assert "data" in result
    assert "evaluation_result" in result["data"]
    assert "score" in result["data"]["evaluation_result"]

    # Test different rubric types
    for rubric_name in ["qa", "planning", "analysis", "creative"]:
        result = await workflow.evaluate_agent(
            agent_output=sample_agent_output, rubric=rubric_name
        )
        assert result["success"] is True


@pytest.mark.asyncio
@pytest.mark.multirun
async def test_evaluation_workflow_multi_run(
    mock_evaluation_tool_manager, mock_mcp_host, sample_agent_output
):
    """Test the multi-run evaluation workflow."""
    # Create workflow
    workflow = EvaluationWorkflow(
        tool_manager=mock_evaluation_tool_manager, host=mock_mcp_host
    )

    # Initialize
    await workflow.initialize()

    # Execute multi-run evaluation
    result = await workflow.evaluate_multi_run(
        agent_output=sample_agent_output, rubric="standard", num_runs=3
    )

    # Verify result
    assert result["success"] is True
    assert "data" in result
    assert "aggregated_result" in result["data"]
    assert "mean_score" in result["data"]["aggregated_result"]
    assert "criterion_mean_scores" in result["data"]["aggregated_result"]
    assert "summary" in result["data"]["aggregated_result"]


@pytest.mark.asyncio
async def test_rubric_loading(mock_evaluation_tool_manager, mock_mcp_host):
    """Test that rubrics are loaded correctly."""
    # Create workflow
    workflow = EvaluationWorkflow(
        tool_manager=mock_evaluation_tool_manager, host=mock_mcp_host
    )

    # Initialize
    await workflow.initialize()

    # Get input data with string rubric
    from src.agents.evaluation.models import (
        get_standard_rubric,
        get_qa_rubric,
        get_planning_rubric,
    )

    # Verify standard rubric
    standard_rubric = get_standard_rubric()
    assert "criteria" in standard_rubric
    assert "accuracy" in standard_rubric["criteria"]
    assert "scale" in standard_rubric

    # Verify QA rubric
    qa_rubric = get_qa_rubric()
    assert "criteria" in qa_rubric
    assert "accuracy" in qa_rubric["criteria"]
    assert qa_rubric["criteria"]["accuracy"]["weight"] == 0.4  # QA-specific weight

    # Verify planning rubric
    planning_rubric = get_planning_rubric()
    assert "criteria" in planning_rubric
    assert "feasibility" in planning_rubric["criteria"]  # Planning-specific criterion

    # Test passing a dictionary instead of a string
    custom_rubric = {
        "criteria": {
            "custom_criterion": {
                "description": "A custom criterion",
                "weight": 1.0,
                "scoring": {"1": "Poor", "5": "Excellent"},
            }
        },
        "scale": {"min": 1, "max": 5, "increment": 1},
    }

    # Create input data
    input_data = {
        "agent_output": "Test output",
        "rubric": custom_rubric,
        "expected_output": "",
        "detailed_feedback": True,
    }

    # Execute the workflow
    result_context = await workflow.execute(input_data)

    # Verify custom rubric was passed to the tool
    tool_called = False
    for call in mock_evaluation_tool_manager.execute_tool.call_args_list:
        args = call[0]
        if args[0] == "evaluate_agent":
            tool_called = True
            assert "criteria" in args[1]["criteria"]
            assert "custom_criterion" in args[1]["criteria"]

    assert tool_called


@pytest.mark.asyncio
async def test_error_handling(mock_evaluation_tool_manager, mock_mcp_host):
    """Test error handling in the evaluation workflow."""
    # Create workflow
    workflow = EvaluationWorkflow(
        tool_manager=mock_evaluation_tool_manager, host=mock_mcp_host
    )

    # Initialize
    await workflow.initialize()

    # Force an error by using a non-standard tool response
    async def mock_error_execute(tool_name, arguments):
        """Mock tool execution that returns an invalid response."""
        if tool_name == "evaluate_agent":
            return "This is not a valid response format"
        return [types.TextContent(type="text", text="Default response")]

    # Replace the mock with our error function
    mock_evaluation_tool_manager.execute_tool = AsyncMock(
        side_effect=mock_error_execute
    )

    # Create input data with minimal requirements
    input_data = {
        "agent_output": "Test output",
        "rubric": create_standard_rubric().model_dump(),
    }

    # Execute the workflow (should handle the error gracefully)
    result_context = await workflow.execute(input_data)

    # Verify step result indicates error but doesn't crash
    step_result = result_context.step_results.get("evaluate_agent")
    assert step_result is not None

    # The step should complete, but the result should contain error info
    evaluation_result = result_context.get("evaluation_result", {})
    assert "error" in evaluation_result
