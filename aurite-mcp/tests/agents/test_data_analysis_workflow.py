"""
Tests for the data analysis workflow.

This module tests the DataAnalysisWorkflow implementation to verify:
1. Workflow initialization and setup
2. Step execution sequence
3. Proper use of ToolManager
4. Error handling and hooks
5. End-to-end workflow execution
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any, List

import mcp.types as types

# Use absolute imports instead of relative imports
from src.host.host import MCPHost
from src.host.resources.tools import ToolManager
from src.agents.examples.data_analysis_workflow import (
    DataAnalysisWorkflow,
    DataLoadStep,
    StatisticalAnalysisStep,
    DataAnalysisContext
)
from src.agents.base_models import StepStatus


# Test fixtures

@pytest.fixture
def mock_tool_manager():
    """Create a mock tool manager for testing"""
    tool_manager = MagicMock(spec=ToolManager)
    
    # Mock the execute_tool method
    async def mock_execute_tool(tool_name, arguments):
        """Mock tool execution with predefined responses"""
        if tool_name == "load_dataset":
            return [types.TextContent(type="text", text="""
            {
                "dataset_id": "test_dataset",
                "num_rows": 1000,
                "columns": ["column1", "column2", "column3"],
                "data_types": {"column1": "numeric", "column2": "categorical", "column3": "date"},
                "last_updated": "2025-03-15"
            }
            """)]
        elif tool_name == "analyze_data_quality":
            return [types.TextContent(type="text", text="""
            {
                "missing_values": {
                    "column1": 0.05,
                    "column2": 0.02,
                    "column3": 0.00
                },
                "outliers": {
                    "column1": 0.03
                },
                "overall_quality_score": 0.95
            }
            """)]
        elif tool_name == "calculate_statistics":
            return [types.TextContent(type="text", text="""
            {
                "descriptive_stats": {
                    "column1": {
                        "mean": 42.5,
                        "median": 41.2,
                        "std_dev": 5.3
                    }
                }
            }
            """)]
        elif tool_name == "create_visualization":
            return [types.TextContent(type="text", text="https://example.com/viz/test.png")]
        elif tool_name == "generate_insights":
            return [types.TextContent(type="text", text="""
            {
                "key_findings": [
                    "The data shows a strong correlation between X and Y",
                    "There is a significant outlier group in column Z"
                ],
                "recommendations": [
                    "Further investigate the outlier group"
                ]
            }
            """)]
        elif tool_name == "generate_report":
            return [types.TextContent(type="text", text="# Test Report\n\nThis is a test report.")]
        
        # Default response for unknown tools
        return [types.TextContent(type="text", text="Tool executed successfully")]
    
    # Set up the mocked methods
    tool_manager.execute_tool = AsyncMock(side_effect=mock_execute_tool)
    tool_manager.has_tool = MagicMock(return_value=True)
    
    return tool_manager


@pytest.fixture
def mock_host(mock_tool_manager):
    """Create a mock host for testing"""
    host = MagicMock(spec=MCPHost)
    host._tool_manager = mock_tool_manager
    
    # Mock required host methods
    host.call_tool = AsyncMock(side_effect=lambda tool_name, args: 
        mock_tool_manager.execute_tool(tool_name, args))
    
    return host


# Tests

@pytest.mark.asyncio
async def test_workflow_initialization(mock_host):
    """Test that the workflow initializes correctly"""
    # Create workflow
    workflow = DataAnalysisWorkflow(mock_host)
    
    # Check that workflow is set up correctly
    assert workflow.name == "data_analysis_workflow"
    assert len(workflow.steps) == 4  # 2 individual steps + 2 composite steps
    assert workflow.tool_manager == mock_host._tool_manager
    
    # Initialize workflow
    await workflow.initialize()
    
    # Verify tool validation was called
    mock_host._tool_manager.has_tool.assert_called()


@pytest.mark.asyncio
async def test_data_load_step(mock_host, mock_tool_manager):
    """Test the data load step"""
    # Create step
    step = DataLoadStep()
    
    # Create a context with AgentContext which has get method
    from src.agents.base_models import AgentContext
    context = AgentContext(data=DataAnalysisContext(
        dataset_id="test_dataset",
        analysis_type="basic",
        include_visualization=True,
        max_rows=1000
    ))
    context.tool_manager = mock_tool_manager
    
    # Execute step
    result = await step.execute(context, mock_host)
    
    # Verify tool was called correctly
    mock_tool_manager.execute_tool.assert_called_with(
        "load_dataset", 
        {"dataset_id": "test_dataset", "max_rows": 1000, "include_metadata": True}
    )
    
    # Verify result structure
    assert "dataset_info" in result
    assert result["dataset_info"]["id"] == "test_dataset"


@pytest.mark.asyncio
async def test_statistical_analysis_step(mock_host, mock_tool_manager):
    """Test the statistical analysis step"""
    # Create step
    step = StatisticalAnalysisStep()
    
    # Create a context with required inputs
    from src.agents.base_models import AgentContext
    
    # First create the data model
    data_model = DataAnalysisContext(
        dataset_id="test_dataset",
        analysis_type="comprehensive",
        include_visualization=True,
        max_rows=1000
    )
    # Set dataset_info after creation since it's an optional field
    data_model.dataset_info = {
        "id": "test_dataset",
        "columns": ["column1", "column2", "column3"],
        "data_types": {"column1": "numeric", "column2": "categorical", "column3": "date"}
    }
    
    # Create the context with get method
    context = AgentContext(data=data_model)
    context.tool_manager = mock_tool_manager
    
    # Execute step
    result = await step.execute(context, mock_host)
    
    # Verify tool was called correctly
    mock_tool_manager.execute_tool.assert_called()
    
    # Verify result structure
    assert "statistical_metrics" in result
    assert "descriptive_stats" in result["statistical_metrics"]


@pytest.mark.asyncio
async def test_full_workflow_execution(mock_host):
    """Test the full workflow execution"""
    # Create workflow
    workflow = DataAnalysisWorkflow(mock_host)
    await workflow.initialize()
    
    # Create input data
    input_data = {
        "dataset_id": "test_dataset",
        "analysis_type": "comprehensive",
        "include_visualization": True,
        "max_rows": 1000
    }
    
    # Execute workflow
    result_context = await workflow.execute(input_data)
    
    # Verify all steps were executed
    assert len(result_context.step_results) >= 4
    
    # Check that no steps failed
    assert all(
        result.status != StepStatus.FAILED 
        for result in result_context.step_results.values()
    )
    
    # Verify final outputs are present
    data_dict = result_context.data.model_dump()
    assert "dataset_info" in data_dict
    assert "data_quality_report" in data_dict
    assert "statistical_metrics" in data_dict
    assert "final_report" in data_dict
    
    # Summarize results
    summary = result_context.summarize_results()
    assert summary["success"] is True
    assert "execution_time" in summary
    assert summary["steps_completed"] >= 4


@pytest.mark.asyncio
async def test_convenience_method(mock_host):
    """Test the convenience method for workflow execution"""
    # Create workflow
    workflow = DataAnalysisWorkflow(mock_host)
    await workflow.initialize()
    
    # Call convenience method
    results = await workflow.analyze_dataset(
        dataset_id="test_dataset",
        analysis_type="basic",
        include_visualization=False,
        max_rows=500
    )
    
    # Verify results
    assert results["success"] is True
    assert "execution_time" in results
    assert "data" in results
    assert "final_report" in results["data"]


@pytest.mark.asyncio
async def test_error_handling(mock_host, mock_tool_manager):
    """Test error handling in the workflow"""
    # Create workflow
    workflow = DataAnalysisWorkflow(mock_host)
    
    # Mock error in tool execution
    async def mock_error_execute(*args, **kwargs):
        if args[0] == "load_dataset":
            raise ValueError("Test error in data loading")
        return await mock_tool_manager.execute_tool(*args, **kwargs)
    
    mock_tool_manager.execute_tool = AsyncMock(side_effect=mock_error_execute)
    
    await workflow.initialize()
    
    # Create input data
    input_data = {
        "dataset_id": "error_dataset",
        "analysis_type": "basic",
        "include_visualization": True,
        "max_rows": 1000
    }
    
    # Execute workflow
    result_context = await workflow.execute(input_data)
    
    # Verify error handling by checking step status directly
    assert "load_dataset" in result_context.step_results
    assert result_context.step_results["load_dataset"].status == StepStatus.FAILED
    
    # Check error is recorded in the step result
    assert result_context.step_results["load_dataset"].error is not None
    assert "Test error in data loading" in str(result_context.step_results["load_dataset"].error)


@pytest.mark.asyncio
async def test_hooks(mock_host):
    """Test that hooks are called correctly"""
    # Create workflow with mock hooks
    workflow = DataAnalysisWorkflow(mock_host)
    
    # Replace hooks with mocks by replacing the hooks in before_workflow_hooks, etc.
    workflow.before_workflow_hooks = [AsyncMock()]
    workflow.after_workflow_hooks = [AsyncMock()]
    workflow.before_step_hooks = [AsyncMock()]
    workflow.after_step_hooks = [AsyncMock()]
    
    await workflow.initialize()
    
    # Create input data
    input_data = {
        "dataset_id": "test_dataset",
        "analysis_type": "basic",
        "include_visualization": False,
        "max_rows": 500
    }
    
    # Execute workflow
    await workflow.execute(input_data)
    
    # Verify hooks were called
    workflow.before_workflow_hooks[0].assert_called_once()
    workflow.after_workflow_hooks[0].assert_called_once()
    assert workflow.before_step_hooks[0].call_count > 0
    assert workflow.after_step_hooks[0].call_count > 0


@pytest.mark.asyncio
async def test_conditional_step_execution(mock_host):
    """Test that steps with conditions are executed conditionally"""
    # Create workflow
    workflow = DataAnalysisWorkflow(mock_host)
    await workflow.initialize()
    
    # Test with visualizations disabled
    input_data_without_viz = {
        "dataset_id": "test_dataset",
        "analysis_type": "basic",
        "include_visualization": False,
        "max_rows": 500
    }
    
    result_without_viz = await workflow.execute(input_data_without_viz)
    
    # Verify visualization step was skipped
    assert result_without_viz.get_step_result("generate_visualizations").status == StepStatus.SKIPPED
    
    # Test with visualizations enabled
    input_data_with_viz = {
        "dataset_id": "test_dataset",
        "analysis_type": "basic",
        "include_visualization": True,
        "max_rows": 500
    }
    
    result_with_viz = await workflow.execute(input_data_with_viz)
    
    # Verify visualization step was executed
    assert result_with_viz.get_step_result("generate_visualizations").status == StepStatus.COMPLETED