"""
Tests for the evaluation workflow using the test_mcp_host fixture.

This module tests the EvaluationWorkflow implementation to verify:
1. Workflow initialization with the JSON-configured host
2. Workflow registration with the host system
3. Agent output evaluation using rubric-based assessment
4. Multi-run evaluation and statistical aggregation
5. End-to-end workflow execution through the host's workflow manager
"""

import pytest
import json
import logging
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import mcp.types as types

from src.host.host import MCPHost
from src.host.config import HostConfigModel, ClientConfig, RootConfig
from src.agents.evaluation.evaluation_workflow import (
    EvaluationWorkflow,
    EvaluateAgentStep,
    AggregateEvaluationsStep
)
from src.agents.evaluation.models import (
    create_standard_rubric,
    create_qa_rubric,
    create_planning_rubric,
)
from src.agents.base_models import AgentContext, StepStatus

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)


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


@pytest.mark.asyncio
async def test_evaluation_workflow_initialization(test_mcp_host):
    """Test that the evaluation workflow initializes correctly with the test host."""
    # Create workflow with the test host
    workflow = EvaluationWorkflow(host=test_mcp_host)
    
    # Check that workflow is set up correctly 
    assert isinstance(workflow.name, str) and workflow.name
    assert workflow.host == test_mcp_host
    
    # Check that the steps were created correctly
    assert len(workflow.steps) == 2  # EvaluateAgentStep and AggregateEvaluationsStep
    assert isinstance(workflow.steps[0], EvaluateAgentStep)
    assert isinstance(workflow.steps[1], AggregateEvaluationsStep)
    
    # Initialize workflow
    await workflow.initialize()
    
    # Verification - steps should be properly configured
    assert workflow.steps[0].name == "evaluate_agent"


@pytest.mark.asyncio
async def test_evaluation_workflow_registration(test_mcp_host):
    """Test registering the workflow with the host system."""
    # Register the workflow with the host
    workflow_name = await test_mcp_host.register_workflow(EvaluationWorkflow)
    
    # Verify registration
    # Could be either "EvaluationWorkflow" or "evaluation_workflow" depending on implementation
    assert workflow_name in ["EvaluationWorkflow", "evaluation_workflow"]
    assert test_mcp_host.workflows.has_workflow(workflow_name)
    
    # Get the registered workflow
    workflow = test_mcp_host.workflows.get_workflow(workflow_name)
    assert workflow is not None
    assert isinstance(workflow.name, str) and workflow.name
    assert workflow.host == test_mcp_host


@pytest.mark.asyncio
async def test_evaluate_agent_step_with_host(test_mcp_host, sample_agent_output):
    """Test the EvaluateAgentStep with the test host."""
    # Create the step
    step = EvaluateAgentStep()
    
    # Create a context with required inputs
    context = AgentContext()
    context.set("agent_output", sample_agent_output)
    context.set("rubric", create_standard_rubric().model_dump())
    context.set("expected_output", "")
    context.set("detailed_feedback", True)
    
    # Attach the host to the context
    context.host = test_mcp_host
    
    # Mock the host's tools.execute_tool to avoid actual LLM calls
    with patch.object(test_mcp_host.tools, "execute_tool") as mock_execute:
        # Create mock response
        mock_execute.return_value = [
            types.TextContent(
                type="text",
                text=json.dumps({
                    "score": 4.2,
                    "passed": True,
                    "criterion_scores": {
                        "accuracy": {
                            "score": 4.0,
                            "justification": "The agent provided mostly accurate information with only minor imprecisions."
                        },
                        "relevance": {
                            "score": 4.5,
                            "justification": "The output thoroughly addressed the query with comprehensive coverage."
                        },
                        "coherence": {
                            "score": 4.0,
                            "justification": "The response was well-structured and easy to follow."
                        },
                        "completeness": {
                            "score": 4.3,
                            "justification": "The output provided comprehensive coverage of the topic."
                        }
                    },
                    "summary_feedback": "Overall, the agent performed well, providing a comprehensive and accurate response that was well-structured.",
                    "strengths": [
                        "Thorough coverage of the topic",
                        "Well-organized presentation",
                        "Accurate information"
                    ],
                    "areas_for_improvement": [
                        "Could provide more specific examples",
                        "Minor inaccuracies in some details"
                    ]
                })
            )
        ]
        
        # Execute step
        result = await step.execute(context)
        
        # Verify tool execution was called
        mock_execute.assert_called_once_with("evaluate_agent", {
            "agent_output": sample_agent_output,
            "criteria": create_standard_rubric().model_dump(),
            "expected_output": "",
            "detailed_feedback": True,
        })
        
        # Verify result structure
        assert "evaluation_result" in result
        assert "raw_tool_result" in result
        
        # Check evaluation result content
        evaluation_result = result["evaluation_result"]
        assert "score" in evaluation_result
        assert "criterion_scores" in evaluation_result
        assert "strengths" in evaluation_result
        assert "areas_for_improvement" in evaluation_result


@pytest.mark.asyncio
async def test_aggregate_evaluations_step_with_host(test_mcp_host):
    """Test the AggregateEvaluationsStep with the test host."""
    # Create the step
    step = AggregateEvaluationsStep()
    
    # Create sample evaluation results
    evaluation_results = [
        {
            "score": 4.2,
            "passed": True,
            "criterion_scores": {
                "accuracy": {"score": 4.0, "justification": "Very accurate analysis"},
                "relevance": {"score": 4.5, "justification": "Highly relevant to the task"}
            },
            "strengths": ["Clear analysis", "Good insights"],
            "areas_for_improvement": ["Minor inaccuracies"]
        },
        {
            "score": 3.8,
            "passed": True,
            "criterion_scores": {
                "accuracy": {"score": 3.5, "justification": "Mostly accurate analysis"},
                "relevance": {"score": 4.0, "justification": "Generally relevant to the task"}
            },
            "strengths": ["Good structure", "Clear writing"],
            "areas_for_improvement": ["Some inaccuracies", "Missing details"]
        },
        {
            "score": 4.0,
            "passed": True,
            "criterion_scores": {
                "accuracy": {"score": 4.0, "justification": "Accurate analysis"},
                "relevance": {"score": 4.0, "justification": "Relevant to the task"}
            },
            "strengths": ["Clear analysis", "Good structure"],
            "areas_for_improvement": ["Could be more detailed"]
        }
    ]
    
    # Create a context with required inputs
    context = AgentContext()
    context.set("evaluation_results", evaluation_results)
    
    # Attach the host to the context
    context.host = test_mcp_host
    
    # Execute step (this will use in-memory aggregation)
    result = await step.execute(context)
    
    # Verify result structure
    assert "aggregated_result" in result
    assert "raw_tool_result" in result
    
    # Check aggregated result content
    aggregated_result = result["aggregated_result"]
    assert "mean_score" in aggregated_result
    assert "median_score" in aggregated_result
    assert "std_deviation" in aggregated_result
    assert "criterion_mean_scores" in aggregated_result
    assert "common_strengths" in aggregated_result
    assert "common_areas_for_improvement" in aggregated_result
    
    # Check aggregation accuracy
    assert abs(aggregated_result["mean_score"] - 4.0) < 0.1  # Should be close to 4.0
    assert "Clear analysis" in aggregated_result["common_strengths"]


@pytest.mark.asyncio
async def test_workflow_execution_with_host(test_mcp_host, sample_agent_output):
    """Test the full workflow execution with the test host."""
    # Register the workflow with the host
    workflow_name = await test_mcp_host.register_workflow(EvaluationWorkflow)
    
    # Create input data
    input_data = {
        "agent_output": sample_agent_output,
        "rubric": create_standard_rubric().model_dump(),  # Use the standard rubric
        "detailed_feedback": True
    }
    
    # Mock the host's tools.execute_tool to avoid actual LLM calls
    with patch.object(test_mcp_host.tools, "execute_tool") as mock_execute:
        # Create mock response for evaluation
        def mock_execute_tool(tool_name, arguments):
            if tool_name == "evaluate_agent":
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps({
                            "score": 4.2,
                            "passed": True,
                            "criterion_scores": {
                                "accuracy": {"score": 4.0, "justification": "Very accurate analysis"},
                                "relevance": {"score": 4.5, "justification": "Highly relevant to the task"},
                                "coherence": {"score": 4.0, "justification": "Well structured analysis"},
                                "completeness": {"score": 4.3, "justification": "Comprehensive coverage"}
                            },
                            "summary_feedback": "Overall excellent analysis with good insights.",
                            "strengths": ["Clear data presentation", "Insightful recommendations"],
                            "areas_for_improvement": ["Minor inaccuracies", "Could expand on recommendations"]
                        })
                    )
                ]
            return []
        
        mock_execute.side_effect = mock_execute_tool
        
        # Execute the workflow through the host's workflow manager
        result_context = await test_mcp_host.workflows.execute_workflow(
            workflow_name=workflow_name,
            input_data=input_data
        )
        
        # Verify the workflow executed successfully
        assert result_context is not None
        
        # Verify each step has a successful result
        assert "evaluate_agent" in result_context.step_results
        step_result = result_context.step_results["evaluate_agent"]
        assert step_result.status == StepStatus.COMPLETED
        
        # Verify outputs are present in context
        data_dict = result_context.get_data_dict()
        assert "evaluation_result" in data_dict
        
        # Verify the evaluation result structure
        evaluation_result = data_dict["evaluation_result"]
        assert "score" in evaluation_result
        assert "criterion_scores" in evaluation_result
        assert "strengths" in evaluation_result
        assert "areas_for_improvement" in evaluation_result


@pytest.mark.asyncio
async def test_workflow_multi_run_execution(test_mcp_host, sample_agent_output):
    """Test the multi-run evaluation execution with the test host."""
    # Create workflow with the test host
    workflow = EvaluationWorkflow(host=test_mcp_host)
    await workflow.initialize()
    
    # Mock the host's tools.execute_tool to avoid actual LLM calls
    with patch.object(test_mcp_host.tools, "execute_tool") as mock_execute:
        # Create mock response for evaluation
        def mock_execute_tool(tool_name, arguments):
            if tool_name == "evaluate_agent":
                # Vary the scores slightly to simulate multiple runs
                score_variance = 0.1 * (mock_execute.call_count % 3)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps({
                            "score": 4.0 + score_variance,
                            "passed": True,
                            "criterion_scores": {
                                "accuracy": {"score": 3.8 + score_variance, "justification": "Generally accurate"},
                                "relevance": {"score": 4.2 + score_variance, "justification": "Highly relevant"}
                            },
                            "summary_feedback": f"Run {mock_execute.call_count}: Good analysis.",
                            "strengths": ["Clear data", "Good insights"],
                            "areas_for_improvement": ["Some inaccuracies"]
                        })
                    )
                ]
            return []
        
        mock_execute.side_effect = mock_execute_tool
        
        # Use the evaluate_multi_run convenience method
        result = await workflow.evaluate_multi_run(
            agent_output=sample_agent_output,
            rubric=create_standard_rubric().model_dump(),
            num_runs=3
        )
        
        # Verify the multi-run result
        assert result is not None
        assert "success" in result
        assert result["success"] is True
        
        # Verify aggregated results are present
        assert "aggregated_result" in result["data"]
        
        # Check that the tool was called the expected number of times
        # First for each evaluation run, then maybe once for aggregation
        assert mock_execute.call_count >= 3


@pytest.mark.asyncio
async def test_workflow_convenience_methods(test_mcp_host, sample_agent_output):
    """Test the evaluate_agent convenience method of the workflow."""
    # Create workflow with the test host
    workflow = EvaluationWorkflow(host=test_mcp_host)
    await workflow.initialize()
    
    # Mock the host's tools.execute_tool to avoid actual LLM calls
    with patch.object(test_mcp_host.tools, "execute_tool") as mock_execute:
        # Create mock response for evaluation
        mock_execute.return_value = [
            types.TextContent(
                type="text",
                text=json.dumps({
                    "score": 4.2,
                    "passed": True,
                    "criterion_scores": {
                        "accuracy": {"score": 4.0, "justification": "Very accurate analysis"},
                        "relevance": {"score": 4.5, "justification": "Highly relevant to the task"}
                    },
                    "summary_feedback": "Overall excellent analysis.",
                    "strengths": ["Clear data", "Good insights"],
                    "areas_for_improvement": ["Minor inaccuracies"]
                })
            )
        ]
        
        # Use the evaluate_agent convenience method
        result = await workflow.evaluate_agent(
            agent_output=sample_agent_output,
            rubric="standard"  # Use a named standard rubric
        )
        
        # Verify the evaluation result
        assert result is not None
        assert "success" in result
        assert result["success"] is True
        
        # Verify evaluation data is present
        assert "data" in result
        assert "evaluation_result" in result["data"]
        
        # Verify the tool was called
        mock_execute.assert_called_once()
        
        # Reset mock for next test
        mock_execute.reset_mock()
        
        # Test with a different rubric type
        result = await workflow.evaluate_agent(
            agent_output=sample_agent_output,
            rubric="qa"  # Use the QA rubric
        )
        
        # Verify result
        assert result["success"] is True
        assert mock_execute.call_count == 1


@pytest.mark.asyncio
async def test_error_handling(test_mcp_host, sample_agent_output):
    """Test error handling in the workflow."""
    # Create workflow with the test host
    workflow = EvaluationWorkflow(host=test_mcp_host)
    await workflow.initialize()
    
    # Mock the host's tools.execute_tool to simulate an error
    with patch.object(test_mcp_host.tools, "execute_tool") as mock_execute:
        # Make the execute_tool raise an exception
        mock_execute.side_effect = ValueError("Test error in evaluation tool")
        
        # Create input data
        input_data = {
            "agent_output": sample_agent_output,
            "rubric": create_standard_rubric().model_dump()
        }
        
        # Execute workflow with error
        result_context = await workflow.execute(input_data)
        
        # Verify the step failed but didn't crash the workflow
        assert "evaluate_agent" in result_context.step_results
        step_result = result_context.step_results["evaluate_agent"]
        assert step_result.status == StepStatus.FAILED
        
        # Check error is recorded
        assert step_result.error is not None
        assert "Test error in evaluation tool" in str(step_result.error)
        
        # Summarize results - should show failure
        summary = result_context.summarize_results()
        assert summary["success"] is False