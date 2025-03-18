"""
Tests for the planning workflow.

This module tests the PlanningWorkflow implementation to verify:
1. Workflow initialization and setup
2. Prompt-based plan creation
3. Plan saving functionality
4. Plan analysis capabilities
5. Plan listing functionality
6. End-to-end workflow execution
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

import mcp.types as types

# Use absolute imports for better clarity
from src.host.resources.tools import ToolManager
from src.agents.planning.planning_workflow import (
    PlanningWorkflow,
    PlanCreationStep,
    PlanSaveStep,
    PlanAnalysisStep,
    PlanListStep,
    PlanningContext,
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
        if tool_name == "save_plan":
            return [
                types.TextContent(
                    type="text",
                    text="""
                    {
                        "success": true,
                        "message": "Plan 'test_plan' saved successfully",
                        "path": "plans/test_plan.txt"
                    }
                    """,
                )
            ]
        elif tool_name == "list_plans":
            tag = arguments.get("tag")
            if tag:
                return [
                    types.TextContent(
                        type="text",
                        text="""
                        {
                            "success": true,
                            "plans": [
                                {
                                    "name": "test_plan",
                                    "created_at": "2025-03-15 10:00:00",
                                    "tags": ["test", "filtered"],
                                    "path": "plans/test_plan.txt"
                                }
                            ],
                            "count": 1
                        }
                        """,
                    )
                ]
            else:
                return [
                    types.TextContent(
                        type="text",
                        text="""
                        {
                            "success": true,
                            "plans": [
                                {
                                    "name": "test_plan",
                                    "created_at": "2025-03-15 10:00:00",
                                    "tags": ["test", "filtered"],
                                    "path": "plans/test_plan.txt"
                                },
                                {
                                    "name": "another_plan",
                                    "created_at": "2025-03-16 11:30:00",
                                    "tags": ["another"],
                                    "path": "plans/another_plan.txt"
                                }
                            ],
                            "count": 2
                        }
                        """,
                    )
                ]
        
        # Default response for unknown tools
        return [types.TextContent(type="text", text="Tool executed successfully")]
    
    # Set up the mocked methods
    tool_manager.execute_tool = AsyncMock(side_effect=mock_execute_tool)
    tool_manager.has_tool = MagicMock(return_value=True)
    tool_manager.format_tool_result = MagicMock(side_effect=lambda r: r[0].text if r and isinstance(r, list) else str(r))
    
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
        class MockResponse:
            def __init__(self, content):
                self.content = content
                
        if prompt_name == "planning_prompt":
            final_response = MockResponse(
                [
                    {"type": "text", "text": "# Project Plan: Note-Taking Application\n\n"},
                    {"type": "text", "text": "## Objective\nCreate a user-friendly note-taking application that allows users to create, edit, organize, and share notes.\n\n"},
                    {"type": "text", "text": "## Key Steps\n1. Requirements gathering\n2. Design and architecture\n3. Frontend development\n4. Backend development\n5. Testing and QA\n6. Deployment\n\n"}
                ]
            )
        elif prompt_name == "plan_analysis_prompt":
            final_response = MockResponse(
                [
                    {"type": "text", "text": "# Analysis of Plan: test_plan\n\n"},
                    {"type": "text", "text": "## Strengths\n- Clear objectives defined\n- Comprehensive timeline\n\n"},
                    {"type": "text", "text": "## Areas for Improvement\n- Consider adding more details about testing strategy\n- Add contingency plans for potential delays\n\n"}
                ]
            )
        else:
            final_response = MockResponse(
                [{"type": "text", "text": "Default prompt response"}]
            )
        
        return {
            "conversation": [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": "Generated response based on prompt"},
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
    workflow = PlanningWorkflow(tool_manager=mock_tool_manager, host=mock_host)
    
    # Check that workflow is set up correctly
    assert workflow.name == "planning_workflow"
    assert len(workflow.steps) == 2  # PlanCreationStep and PlanSaveStep
    assert workflow.tool_manager == mock_tool_manager
    assert workflow.host == mock_host
    
    # Initialize workflow
    await workflow.initialize()
    
    # Verify tool validation was called
    mock_tool_manager.has_tool.assert_called()


@pytest.mark.asyncio
async def test_plan_creation_step(mock_tool_manager, mock_host):
    """Test the plan creation step"""
    # Create step
    step = PlanCreationStep()
    
    # Create a context with required inputs
    from src.agents.base_models import AgentContext
    
    context = AgentContext(
        data=PlanningContext(
            task="Create a website for a small business",
            plan_name="test_plan",
            timeframe="2 weeks",
            resources=["Web developer", "Designer"]
        )
    )
    context.tool_manager = mock_tool_manager
    context.host = mock_host
    
    # Execute step
    result = await step.execute(context)
    
    # Verify host method was called with correct parameters
    mock_host.execute_prompt_with_tools.assert_called_once()
    call_args = mock_host.execute_prompt_with_tools.call_args[1]
    assert call_args["prompt_name"] == "planning_prompt"
    assert call_args["prompt_arguments"]["task"] == "Create a website for a small business"
    assert call_args["prompt_arguments"]["timeframe"] == "2 weeks"
    assert "resources" in call_args["prompt_arguments"]
    
    # Verify result structure
    assert "plan_content" in result
    assert result["plan_content"].startswith("# Project Plan")


@pytest.mark.asyncio
async def test_plan_save_step(mock_tool_manager, mock_host):
    """Test the plan save step"""
    # Create step
    step = PlanSaveStep()
    
    # Create a context with required inputs
    from src.agents.base_models import AgentContext
    
    context = AgentContext(
        data=PlanningContext(
            task="Create a website for a small business",
            plan_name="test_plan",
            plan_content="# Test Plan\n\nThis is a test plan content."
        )
    )
    context.tool_manager = mock_tool_manager
    context.host = mock_host
    
    # Execute step
    result = await step.execute(context)
    
    # Verify tool was called correctly
    mock_tool_manager.execute_tool.assert_called_with(
        "save_plan",
        {
            "plan_name": "test_plan",
            "plan_content": "# Test Plan\n\nThis is a test plan content.",
            "tags": None
        }
    )
    
    # Verify result structure
    assert "save_result" in result
    assert "plan_path" in result
    assert result["save_result"]["success"] is True


@pytest.mark.asyncio
async def test_plan_analysis_step(mock_tool_manager, mock_host):
    """Test the plan analysis step"""
    # Create step
    step = PlanAnalysisStep()
    
    # Create a context with required inputs
    from src.agents.base_models import AgentContext
    
    context = AgentContext(
        data=PlanningContext(
            task="Required field that we don't use in this test",
            plan_name="test_plan"
        )
    )
    context.tool_manager = mock_tool_manager
    context.host = mock_host
    
    # Execute step
    result = await step.execute(context)
    
    # Verify host method was called with correct parameters
    mock_host.execute_prompt_with_tools.assert_called_once()
    call_args = mock_host.execute_prompt_with_tools.call_args[1]
    assert call_args["prompt_name"] == "plan_analysis_prompt"
    assert call_args["prompt_arguments"]["plan_name"] == "test_plan"
    
    # Verify result structure
    assert "analysis_report" in result
    assert "prompt_execution_details" in result
    assert result["analysis_report"].startswith("# Analysis of Plan")


@pytest.mark.asyncio
async def test_plan_list_step(mock_tool_manager, mock_host):
    """Test the plan list step"""
    # Create step
    step = PlanListStep()
    
    # Create a context
    from src.agents.base_models import AgentContext
    
    context = AgentContext(
        data=PlanningContext(
            task="Required field that we don't use in this test",
            plan_name="dummy"
        )
    )
    context.tool_manager = mock_tool_manager
    context.host = mock_host
    
    # Execute step
    result = await step.execute(context)
    
    # Verify tool was called correctly
    mock_tool_manager.execute_tool.assert_called_with("list_plans", {})
    
    # Verify result structure
    assert "plans_list" in result
    
    # Test with filter tag
    context = AgentContext(
        data=PlanningContext(
            task="Required field that we don't use in this test",
            plan_name="dummy",
            filter_tag="test"
        )
    )
    context.tool_manager = mock_tool_manager
    context.host = mock_host
    
    # Execute step again
    await step.execute(context)
    
    # Verify tool was called with filter
    mock_tool_manager.execute_tool.assert_called_with("list_plans", {"tag": "test"})


@pytest.mark.asyncio
async def test_full_workflow_execution(mock_tool_manager, mock_host):
    """Test the full workflow execution"""
    # Create workflow
    workflow = PlanningWorkflow(tool_manager=mock_tool_manager, host=mock_host)
    await workflow.initialize()
    
    # Create input data
    input_data = {
        "task": "Create a marketing campaign for a new product",
        "plan_name": "marketing_plan",
        "timeframe": "3 weeks",
        "resources": ["Marketing specialist", "Graphic designer", "Social media expert"]
    }
    
    # Execute workflow
    result_context = await workflow.execute(input_data)
    
    # Verify all steps were executed
    assert len(result_context.step_results) == 2  # Create and Save
    
    # Check that no steps failed
    assert all(
        result.status != StepStatus.FAILED
        for result in result_context.step_results.values()
    )
    
    # Verify final outputs are present in context
    data_dict = result_context.get_data_dict()
    assert "plan_content" in data_dict
    assert "plan_path" in data_dict
    assert "save_result" in data_dict
    
    # Verify both steps were completed
    assert result_context.step_results["create_plan"].status == StepStatus.COMPLETED
    assert result_context.step_results["save_plan"].status == StepStatus.COMPLETED
    
    # Summarize results
    summary = result_context.summarize_results()
    assert summary["success"] is True
    assert summary["steps_completed"] == 2


@pytest.mark.asyncio
async def test_convenience_methods(mock_tool_manager, mock_host):
    """Test the convenience methods"""
    # Create workflow
    workflow = PlanningWorkflow(tool_manager=mock_tool_manager, host=mock_host)
    await workflow.initialize()
    
    # Test create_plan convenience method
    create_result = await workflow.create_plan(
        task="Build a mobile app",
        plan_name="mobile_app_plan",
        timeframe="2 months",
        resources=["iOS developer", "Android developer", "UI designer"]
    )
    
    # Verify results
    assert create_result["success"] is True
    assert "data" in create_result
    assert "plan_content" in create_result["data"]
    
    # Test analyze_plan convenience method
    analyze_result = await workflow.analyze_plan("test_plan")
    
    # Verify results
    assert analyze_result["success"] is True
    assert "data" in analyze_result
    assert "analysis_report" in analyze_result["data"]
    
    # Test list_plans convenience method
    list_result = await workflow.list_plans()
    
    # Verify results
    assert list_result["success"] is True
    assert "data" in list_result
    assert "plans_list" in list_result["data"]
    
    # Test list_plans with filter
    filtered_result = await workflow.list_plans(filter_tag="test")
    
    # Verify results
    assert filtered_result["success"] is True
    assert "data" in filtered_result
    assert "plans_list" in filtered_result["data"]


@pytest.mark.asyncio
async def test_error_handling(mock_tool_manager, mock_host):
    """Test error handling in the workflow"""
    # Create workflow
    workflow = PlanningWorkflow(mock_tool_manager, host=mock_host)
    
    # Mock error in tool execution
    async def mock_error_execute(*args, **kwargs):
        if args[0] == "save_plan":
            raise ValueError("Test error in plan saving")
        return await mock_tool_manager.execute_tool(*args, **kwargs)
    
    mock_tool_manager.execute_tool = AsyncMock(side_effect=mock_error_execute)
    
    await workflow.initialize()
    
    # Create input data that will cause an error in the save step
    input_data = {
        "task": "Create a plan that will fail to save",
        "plan_name": "failing_plan"
    }
    
    # Execute workflow
    result_context = await workflow.execute(input_data)
    
    # Verify first step is completed
    assert result_context.step_results["create_plan"].status == StepStatus.COMPLETED
    
    # Verify error handling in save step
    assert result_context.step_results["save_plan"].status == StepStatus.FAILED
    
    # Check error is recorded
    assert result_context.step_results["save_plan"].error is not None
    assert "Test error in plan saving" in str(result_context.step_results["save_plan"].error)
    
    # Summarize results - should show failure
    summary = result_context.summarize_results()
    assert summary["success"] is False