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
from unittest.mock import MagicMock, AsyncMock

import mcp.types as types

# Use absolute imports instead of relative imports
from src.host.resources.tools import ToolManager
from src.agents.examples.data_analysis_workflow import (
    DataAnalysisWorkflow,
    DataLoadStep,
    StatisticalAnalysisStep,
    DataAnalysisContext,
    PromptBasedReportStep,
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
        elif tool_name == "create_visualization":
            return [
                types.TextContent(type="text", text="https://example.com/viz/test.png")
            ]
        elif tool_name == "generate_insights":
            return [
                types.TextContent(
                    type="text",
                    text="""
            {
                "key_findings": [
                    "The data shows a strong correlation between X and Y",
                    "There is a significant outlier group in column Z"
                ],
                "recommendations": [
                    "Further investigate the outlier group"
                ]
            }
            """,
                )
            ]
        elif tool_name == "generate_report":
            return [
                types.TextContent(
                    type="text", text="# Test Report\n\nThis is a test report."
                )
            ]

        # Default response for unknown tools
        return [types.TextContent(type="text", text="Tool executed successfully")]

    # Set up the mocked methods
    tool_manager.execute_tool = AsyncMock(side_effect=mock_execute_tool)
    tool_manager.has_tool = MagicMock(return_value=True)

    return tool_manager


@pytest.fixture
def mock_host():
    """Create a mock host for testing prompt-based execution"""
    mock_host = MagicMock()

    # Mock the execute_prompt_with_tools method
    async def mock_execute_prompt_with_tools(
        prompt_name, prompt_arguments, client_id, user_message, **kwargs
    ):
        """Mock prompt execution with predefined responses"""

        # For testing, we return a structured response mimicking the real response format
        # Create an object with a content attribute simulating the Anthropic response
        class MockResponse:
            def __init__(self, content):
                self.content = content

        final_response = MockResponse(
            [
                {"type": "text", "text": "# AI-Generated Data Analysis Report\n\n"},
                {"type": "text", "text": "## Dataset Overview\n\n"},
                {
                    "type": "text",
                    "text": "Dataset analysis complete with key metrics and insights.",
                },
            ]
        )

        return {
            "conversation": [
                {"role": "user", "content": user_message},
                {
                    "role": "assistant",
                    "content": "Generated report based on data analysis",
                },
            ],
            "final_response": final_response,
            "tool_uses": [],
        }

    # Set up the mocked method
    mock_host.execute_prompt_with_tools = AsyncMock(
        side_effect=mock_execute_prompt_with_tools
    )

    return mock_host


# Tests


@pytest.mark.asyncio
async def test_workflow_initialization(mock_tool_manager, mock_host):
    """Test that the workflow initializes correctly"""
    # Create workflow with tool_manager and host
    workflow = DataAnalysisWorkflow(tool_manager=mock_tool_manager, host=mock_host)

    # Check that workflow is set up correctly
    assert workflow.name == "data_analysis_workflow"
    assert (
        len(workflow.steps) == 4
    )  # 2 individual steps + 2 composite steps (commented out PromptBasedReportStep)
    assert workflow.tool_manager == mock_tool_manager
    assert workflow.host == mock_host

    # Initialize workflow
    await workflow.initialize()

    # Verify tool validation was called
    mock_tool_manager.has_tool.assert_called()

    # Uncomment the PromptBasedReportStep to use in tests
    workflow.add_step(PromptBasedReportStep())
    assert (
        len(workflow.steps) == 5
    )  # Now we have 5 steps including PromptBasedReportStep


@pytest.mark.asyncio
async def test_data_load_step(mock_tool_manager, mock_host):
    """Test the data load step"""
    # Create step
    step = DataLoadStep()

    # Create a context with AgentContext which has get method
    from src.agents.base_models import AgentContext

    context = AgentContext(
        data=DataAnalysisContext(
            dataset_id="test_dataset",
            analysis_type="basic",
            include_visualization=True,
            max_rows=1000,
        )
    )
    context.tool_manager = mock_tool_manager
    context.host = mock_host  # Add host to context

    # Execute step
    result = await step.execute(context)

    # Verify tool was called correctly
    mock_tool_manager.execute_tool.assert_called_with(
        "load_dataset",
        {"dataset_id": "test_dataset", "max_rows": 1000, "include_metadata": True},
    )

    # Verify result structure
    assert "dataset_info" in result
    assert result["dataset_info"]["id"] == "test_dataset"


@pytest.mark.asyncio
async def test_statistical_analysis_step(mock_tool_manager, mock_host):
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
        max_rows=1000,
    )
    # Set dataset_info after creation since it's an optional field
    data_model.dataset_info = {
        "id": "test_dataset",
        "columns": ["column1", "column2", "column3"],
        "data_types": {
            "column1": "numeric",
            "column2": "categorical",
            "column3": "date",
        },
    }

    # Create the context with get method
    context = AgentContext(data=data_model)
    context.tool_manager = mock_tool_manager
    context.host = mock_host  # Add host to context

    # Execute step
    result = await step.execute(context)

    # Verify tool was called correctly
    mock_tool_manager.execute_tool.assert_called()

    # Verify result structure
    assert "statistical_metrics" in result
    assert "descriptive_stats" in result["statistical_metrics"]


@pytest.mark.asyncio
async def test_full_workflow_execution(mock_tool_manager, mock_host):
    """Test the full workflow execution"""
    # Create workflow
    workflow = DataAnalysisWorkflow(mock_tool_manager, host=mock_host)
    await workflow.initialize()

    # Add the prompt-based step for testing
    workflow.add_step(PromptBasedReportStep())

    # Create input data
    input_data = {
        "dataset_id": "test_dataset",
        "analysis_type": "comprehensive",
        "include_visualization": True,
        "max_rows": 1000,
    }

    # Execute workflow
    result_context = await workflow.execute(input_data)

    # Verify all steps were executed
    assert len(result_context.step_results) >= 5  # Including PromptBasedReportStep

    # Check that no steps failed
    assert all(
        result.status != StepStatus.FAILED
        for result in result_context.step_results.values()
    )

    # Verify final outputs are present
    data_dict = result_context.get_data_dict()
    assert "dataset_info" in data_dict
    assert "data_quality_report" in data_dict
    assert "statistical_metrics" in data_dict
    assert "final_report" in data_dict
    assert (
        "prompt_execution_details" in data_dict
    )  # New field from PromptBasedReportStep

    # Verify the prompt-based step was executed
    assert "prompt_based_report" in result_context.step_results
    assert (
        result_context.step_results["prompt_based_report"].status
        == StepStatus.COMPLETED
    )

    # Verify host method was called
    mock_host.execute_prompt_with_tools.assert_called()

    # Summarize results
    summary = result_context.summarize_results()
    assert summary["success"] is True
    assert "execution_time" in summary
    assert summary["steps_completed"] >= 5


@pytest.mark.asyncio
async def test_convenience_method(mock_tool_manager, mock_host):
    """Test the convenience method for workflow execution"""
    # Create workflow
    workflow = DataAnalysisWorkflow(mock_tool_manager, host=mock_host)
    await workflow.initialize()

    # Add the prompt-based step
    workflow.add_step(PromptBasedReportStep())

    # Call convenience method
    results = await workflow.analyze_dataset(
        dataset_id="test_dataset",
        analysis_type="basic",
        include_visualization=False,
        max_rows=500,
    )

    # Verify results
    assert results["success"] is True
    assert "execution_time" in results
    assert "data" in results
    assert "final_report" in results["data"]
    assert "prompt_execution_details" in results["data"]

    # Verify host method was called
    mock_host.execute_prompt_with_tools.assert_called()


@pytest.mark.asyncio
async def test_error_handling(mock_tool_manager, mock_host):
    """Test error handling in the workflow"""
    # Create workflow
    workflow = DataAnalysisWorkflow(mock_tool_manager, host=mock_host)

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
        "max_rows": 1000,
    }

    # Execute workflow
    result_context = await workflow.execute(input_data)

    # Verify error handling by checking step status directly
    assert "load_dataset" in result_context.step_results
    assert result_context.step_results["load_dataset"].status == StepStatus.FAILED

    # Check error is recorded in the step result
    assert result_context.step_results["load_dataset"].error is not None
    assert "Test error in data loading" in str(
        result_context.step_results["load_dataset"].error
    )


@pytest.mark.asyncio
async def test_hooks(mock_tool_manager, mock_host):
    """Test that hooks are called correctly"""
    # Create workflow with mock hooks
    workflow = DataAnalysisWorkflow(mock_tool_manager, host=mock_host)

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
        "max_rows": 500,
    }

    # Execute workflow
    await workflow.execute(input_data)

    # Verify hooks were called
    workflow.before_workflow_hooks[0].assert_called_once()
    workflow.after_workflow_hooks[0].assert_called_once()
    assert workflow.before_step_hooks[0].call_count > 0
    assert workflow.after_step_hooks[0].call_count > 0


@pytest.mark.asyncio
async def test_conditional_step_execution(mock_tool_manager, mock_host):
    """Test that steps with conditions are executed conditionally"""
    # Create workflow
    workflow = DataAnalysisWorkflow(mock_tool_manager, host=mock_host)
    await workflow.initialize()

    # Test with visualizations disabled
    input_data_without_viz = {
        "dataset_id": "test_dataset",
        "analysis_type": "basic",
        "include_visualization": False,
        "max_rows": 500,
    }

    result_without_viz = await workflow.execute(input_data_without_viz)

    # Verify visualization step was skipped
    assert (
        result_without_viz.get_step_result("generate_visualizations").status
        == StepStatus.SKIPPED
    )

    # Test with visualizations enabled
    input_data_with_viz = {
        "dataset_id": "test_dataset",
        "analysis_type": "basic",
        "include_visualization": True,
        "max_rows": 500,
    }

    result_with_viz = await workflow.execute(input_data_with_viz)

    # Verify visualization step was executed
    assert (
        result_with_viz.get_step_result("generate_visualizations").status
        == StepStatus.COMPLETED
    )


@pytest.mark.asyncio
async def test_prompt_based_step(mock_tool_manager, mock_host):
    """Test the prompt-based step execution"""
    # Create the step
    step = PromptBasedReportStep()

    # Create context with required data
    from src.agents.base_models import AgentContext

    # Create the data model
    data_model = DataAnalysisContext(
        dataset_id="test_dataset",
        analysis_type="comprehensive",
        include_visualization=True,
        max_rows=1000,
    )
    # Set required data fields
    data_model.dataset_info = {
        "id": "test_dataset",
        "columns": ["column1", "column2", "column3"],
    }
    data_model.data_quality_report = {"overall_quality_score": 0.95}
    data_model.statistical_metrics = {"descriptive_stats": {"column1": {"mean": 42.5}}}
    data_model.analysis_results = {
        "key_findings": ["Finding 1", "Finding 2"],
        "recommendations": ["Recommendation 1"],
    }

    # Create context
    context = AgentContext(data=data_model)
    context.tool_manager = mock_tool_manager
    context.host = mock_host

    # Execute the step
    result = await step.execute(context)

    # Verify host.execute_prompt_with_tools was called
    mock_host.execute_prompt_with_tools.assert_called_once()

    # Verify results
    assert "final_report" in result
    assert "prompt_execution_details" in result
    assert isinstance(result["final_report"], str)
    assert "AI-Generated Data Analysis Report" in result["final_report"]
