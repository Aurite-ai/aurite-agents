"""
Tests for the workflow manager component of the host system.

This module tests the WorkflowManager implementation to verify:
1. Workflow registration and management
2. Workflow execution through the manager
3. Integration with the host system
4. Proper management of workflow lifecycle
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

import mcp.types as types

from src.host.agent import WorkflowManager
from src.host.resources.tools import ToolManager
from src.agents.examples.data_analysis_workflow import DataAnalysisWorkflow
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
            return [
                types.TextContent(
                    type="text",
                    text="""
                    {
                        "dataset_id": "test_dataset",
                        "num_rows": 1000,
                        "columns": ["column1", "column2", "column3"],
                        "data_types": {"column1": "numeric", "column2": "categorical", "column3": "date"},
                        "last_updated": "2025-03-15"
                    }
                    """,
                )
            ]
        elif tool_name == "analyze_data_quality":
            return [
                types.TextContent(
                    type="text",
                    text="""
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
                    """,
                )
            ]
        elif tool_name == "calculate_statistics":
            return [
                types.TextContent(
                    type="text",
                    text="""
                    {
                        "descriptive_stats": {
                            "column1": {
                                "mean": 42.5,
                                "median": 41.2,
                                "std_dev": 5.3
                            }
                        }
                    }
                    """,
                )
            ]

        # Default response for unknown tools
        return [types.TextContent(type="text", text="Tool executed successfully")]

    # Set up the mocked methods
    tool_manager.execute_tool = AsyncMock(side_effect=mock_execute_tool)
    tool_manager.has_tool = MagicMock(return_value=True)
    tool_manager.format_tool_result = MagicMock(return_value="Formatted tool result")

    return tool_manager


@pytest.fixture
def workflow_manager(mock_tool_manager):
    """Create a workflow manager for testing"""
    manager = WorkflowManager(tool_manager=mock_tool_manager)
    return manager


# Tests


@pytest.mark.asyncio
async def test_workflow_registration(workflow_manager):
    """Test workflow registration and initialization"""
    # Register a workflow
    workflow_name = await workflow_manager.register_workflow(DataAnalysisWorkflow)

    # Verify the workflow was registered
    assert workflow_manager.has_workflow(workflow_name)
    assert workflow_name == "data_analysis_workflow"

    # List workflows and check metadata
    workflows = workflow_manager.list_workflows()
    assert len(workflows) == 1
    assert workflows[0]["name"] == workflow_name
    assert "Comprehensive data analysis" in workflows[0]["description"]

    # Get the workflow directly
    workflow = workflow_manager.get_workflow(workflow_name)
    assert workflow is not None
    assert workflow.name == workflow_name


@pytest.mark.asyncio
async def test_workflow_execution(workflow_manager):
    """Test workflow execution through the manager"""
    # Register a workflow
    workflow_name = await workflow_manager.register_workflow(DataAnalysisWorkflow)

    # Create input data
    input_data = {
        "dataset_id": "test_dataset",
        "analysis_type": "basic",
        "include_visualization": False,
        "max_rows": 500,
    }

    # Execute the workflow
    result_context = await workflow_manager.execute_workflow(
        workflow_name, input_data, metadata={"test_run": True}
    )

    # Verify results
    assert result_context is not None
    assert len(result_context.step_results) > 0

    # Check that important outputs were generated
    data_dict = result_context.get_data_dict()
    assert "dataset_info" in data_dict
    assert "statistical_metrics" in data_dict

    # Check visualizations were skipped due to input parameter
    viz_step_result = result_context.get_step_result("generate_visualizations")
    assert viz_step_result.status == StepStatus.SKIPPED

    # Summarize results
    summary = result_context.summarize_results()
    assert summary["success"] is True
    assert "execution_time" in summary


@pytest.mark.asyncio
async def test_multiple_workflow_registration(workflow_manager):
    """Test registration of multiple workflows with custom names"""
    # Register two workflows with the same class but different names
    name1 = await workflow_manager.register_workflow(
        DataAnalysisWorkflow, name="analysis_workflow_1"
    )
    name2 = await workflow_manager.register_workflow(
        DataAnalysisWorkflow, name="analysis_workflow_2"
    )

    # Verify both were registered with different names
    assert name1 == "analysis_workflow_1"
    assert name2 == "analysis_workflow_2"
    assert workflow_manager.has_workflow(name1)
    assert workflow_manager.has_workflow(name2)

    # List workflows and check count
    workflows = workflow_manager.list_workflows()
    assert len(workflows) == 2


@pytest.mark.asyncio
async def test_workflow_execution_with_invalid_name(workflow_manager):
    """Test error handling for invalid workflow name"""
    # Try to execute a non-existent workflow
    with pytest.raises(ValueError, match="Workflow not found"):
        await workflow_manager.execute_workflow(
            "non_existent_workflow", {"dataset_id": "test"}
        )


@pytest.mark.asyncio
async def test_workflow_shutdown(workflow_manager):
    """Test workflow shutdown"""
    # Register a workflow
    await workflow_manager.register_workflow(DataAnalysisWorkflow)

    # Shutdown should work without errors
    await workflow_manager.shutdown()

    # After shutdown, workflows should be cleared
    assert len(workflow_manager.list_workflows()) == 0
