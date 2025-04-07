"""
Unit tests for the PlanningAgent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import json  # Add json import
import anthropic  # Add anthropic import

# Use relative imports assuming tests run from aurite-mcp root
from src.agents.management.planning_agent import PlanningAgent
from src.host.models import AgentConfig
import mcp.types as types


@pytest.mark.unit
class TestPlanningAgentUnit:
    """Unit tests for PlanningAgent methods."""

    @pytest.fixture
    def mock_agent_config(self) -> AgentConfig:
        """Provides a mock AgentConfig."""
        # Minimal config needed for agent initialization
        return AgentConfig(name="TestPlanningAgent")

    @pytest.fixture
    def planning_agent(self, mock_agent_config: AgentConfig) -> PlanningAgent:
        """Provides an instance of PlanningAgent."""
        return PlanningAgent(config=mock_agent_config)

    @pytest.mark.asyncio
    async def test_save_new_plan(
        self, planning_agent: PlanningAgent, mock_mcp_host: MagicMock
    ):
        """Verify save_new_plan calls execute_tool with correct arguments."""
        plan_name = "test_plan_1"
        plan_content = "Step 1: Do thing.\nStep 2: Do other thing."
        tags = ["testing", "example"]

        # Configure the mock host's tool manager
        # Assume execute_tool returns a list with one TextContent containing JSON
        mock_response_dict = {
            "success": True,
            "message": "Plan saved",
            "path": "/path/to/plan.txt",
        }
        mock_response_text = json.dumps(mock_response_dict)  # Use json.dumps
        # Mock the new host-level method
        mock_mcp_host.execute_tool = AsyncMock(
            return_value=[types.TextContent(type="text", text=mock_response_text)]
        )
        # No longer need to mock get_clients_for_tool for this test path

        result = await planning_agent.save_new_plan(
            host_instance=mock_mcp_host,
            plan_name=plan_name,
            plan_content=plan_content,
            tags=tags,
        )

        # Assert the host-level execute_tool was called correctly
        mock_mcp_host.execute_tool.assert_called_once_with(
            # client_name="planning_client_1", # client_name is now optional
            tool_name="save_plan",
            arguments={
                "plan_name": plan_name,
                "plan_content": plan_content,
                "tags": tags,
            },
        )

        # Assert the parsed result
        assert result == mock_response_dict  # Assert against the original dict

    @pytest.mark.asyncio
    async def test_save_new_plan_no_tags(
        self, planning_agent: PlanningAgent, mock_mcp_host: MagicMock
    ):
        """Verify save_new_plan works correctly without tags."""
        plan_name = "test_plan_no_tags"
        plan_content = "Simple plan."

        mock_response_dict = {
            "success": True,
            "message": "Plan saved",
            "path": "/path/to/plan2.txt",
        }
        mock_response_text = json.dumps(mock_response_dict)  # Use json.dumps
        # Mock the new host-level method
        mock_mcp_host.execute_tool = AsyncMock(
            return_value=[types.TextContent(type="text", text=mock_response_text)]
        )
        # No longer need to mock get_clients_for_tool

        result = await planning_agent.save_new_plan(
            host_instance=mock_mcp_host,
            plan_name=plan_name,
            plan_content=plan_content,
            # tags=None (default)
        )

        # Assert the host-level execute_tool was called correctly
        mock_mcp_host.execute_tool.assert_called_once_with(
            # client_name="planning_client_1", # client_name is now optional
            tool_name="save_plan",
            arguments={
                "plan_name": plan_name,
                "plan_content": plan_content,
                # 'tags' key should not be present
            },
        )
        assert result == mock_response_dict  # Assert against the original dict

    @pytest.mark.asyncio
    async def test_list_existing_plans(
        self, planning_agent: PlanningAgent, mock_mcp_host: MagicMock
    ):
        """Verify list_existing_plans calls execute_tool with correct arguments."""
        tag_filter = "urgent"

        mock_plan_list = [{"name": "plan_a", "tags": ["urgent"]}, {"name": "plan_b"}]
        # Use json.dumps for the whole structure
        mock_response_dict = {"success": True, "plans": mock_plan_list, "count": 2}
        mock_response_text = json.dumps(mock_response_dict)
        # Mock the new host-level method
        mock_mcp_host.execute_tool = AsyncMock(
            return_value=[types.TextContent(type="text", text=mock_response_text)]
        )
        # No longer need to mock get_clients_for_tool

        result = await planning_agent.list_existing_plans(
            host_instance=mock_mcp_host, tag=tag_filter
        )

        # Assert the host-level execute_tool was called correctly
        mock_mcp_host.execute_tool.assert_called_once_with(
            # client_name="planning_client_1", # client_name is now optional
            tool_name="list_plans",
            arguments={"tag": tag_filter},
        )
        assert result == mock_response_dict  # Assert against the original dict

    @pytest.mark.asyncio
    async def test_list_existing_plans_no_tag(
        self, planning_agent: PlanningAgent, mock_mcp_host: MagicMock
    ):
        """Verify list_existing_plans works correctly without a tag filter."""
        mock_plan_list = [{"name": "plan_c"}, {"name": "plan_d"}]
        # Use json.dumps for the whole structure
        mock_response_dict = {"success": True, "plans": mock_plan_list, "count": 2}
        mock_response_text = json.dumps(mock_response_dict)
        # Mock the new host-level method
        mock_mcp_host.execute_tool = AsyncMock(
            return_value=[types.TextContent(type="text", text=mock_response_text)]
        )
        # No longer need to mock get_clients_for_tool

        result = await planning_agent.list_existing_plans(
            host_instance=mock_mcp_host  # tag=None (default)
        )

        # Assert the host-level execute_tool was called correctly
        mock_mcp_host.execute_tool.assert_called_once_with(
            # client_name="planning_client_1", # client_name is now optional
            tool_name="list_plans",
            arguments={},  # No tag argument
        )
        assert result == mock_response_dict  # Assert against the original dict

    @pytest.mark.asyncio
    async def test_find_planning_client_id_error(
        self, planning_agent: PlanningAgent, mock_mcp_host: MagicMock
    ):
        """Verify _find_planning_client_id raises error if tool not found."""
        # Configure the host-level method to raise the expected error
        mock_mcp_host.execute_tool = AsyncMock(
            side_effect=ValueError(
                "Tool 'save_plan' not found on any registered client."
            )
        )

        # The save_new_plan method now catches the exception and returns a dict
        result = await planning_agent.save_new_plan(
            host_instance=mock_mcp_host,
            plan_name="fail_plan",
            plan_content="wont work",
        )
        assert result.get("success") is False
        assert "Tool 'save_plan' not found" in result.get("message", "")

    # --- Tests for execute_workflow ---

    @pytest.mark.asyncio
    async def test_execute_workflow_success(
        self, planning_agent: PlanningAgent, mock_mcp_host: MagicMock
    ):
        """Verify successful execution of the planning workflow."""
        user_message = "Create a plan for testing."
        plan_name = "workflow_test_plan"
        tags = ["workflow", "unit_test"]
        generated_plan_content = "Step 1: Write test. Step 2: Run test."
        save_tool_result = {"success": True, "message": "Plan saved successfully."}

        # Mock the internal _make_llm_call on the agent instance
        mock_llm_response = MagicMock(spec=anthropic.types.Message)
        mock_llm_response.content = [
            anthropic.types.TextBlock(  # Use anthropic.types
                type="text", text=generated_plan_content
            )  # Use anthropic.types
        ]
        # Patch the method on the *instance* for this test
        planning_agent._make_llm_call = AsyncMock(return_value=mock_llm_response)

        # Mock the save_new_plan method (which internally calls the tool)
        # Note: We still mock save_new_plan here because execute_workflow calls it.
        # This isolates the test to the workflow logic itself, not the tool interaction details.
        planning_agent.save_new_plan = AsyncMock(return_value=save_tool_result)

        result = await planning_agent.execute_workflow(
            user_message=user_message,
            host_instance=mock_mcp_host,
            plan_name=plan_name,
            tags=tags,
            # anthropic_api_key no longer needed
        )

        # Assertions
        assert result["error"] is None
        assert result["final_output"] == save_tool_result
        assert (
            len(result["workflow_steps"]) == 4
        )  # Setup(implicit ok) + LLM Call + LLM Success + Tool Call + Tool Success

        # Check LLM call mock (now directly on the agent instance)
        planning_agent._make_llm_call.assert_awaited_once()
        # call_args is now empty tuple, call_kwargs contains the arguments
        _, call_kwargs = planning_agent._make_llm_call.call_args
        assert call_kwargs["system_prompt"].startswith(
            "You are an AI planning assistant"
        )
        assert call_kwargs["tools"] == []  # Ensure no tools were passed for generation
        assert call_kwargs["messages"] == [{"role": "user", "content": user_message}]

        # Check save_new_plan mock
        planning_agent.save_new_plan.assert_awaited_once_with(
            host_instance=mock_mcp_host,
            plan_name=plan_name,
            plan_content=generated_plan_content,
            tags=tags,
        )

        # Check workflow steps structure (basic check)
        assert result["workflow_steps"][0]["step"] == 1
        assert result["workflow_steps"][0]["action"] == "LLM Call (Generate Plan)"
        assert result["workflow_steps"][1]["step"] == 1
        assert result["workflow_steps"][1]["status"] == "Success"
        assert result["workflow_steps"][2]["step"] == 2
        assert result["workflow_steps"][2]["action"] == "Tool Call (save_plan)"
        assert result["workflow_steps"][3]["step"] == 2
        assert result["workflow_steps"][3]["status"] == "Success"

    @pytest.mark.asyncio
    async def test_execute_workflow_llm_failure(
        self, planning_agent: PlanningAgent, mock_mcp_host: MagicMock
    ):
        """Verify workflow handles failure during the LLM call (Step 1)."""
        user_message = "Create a plan for failure."
        plan_name = "fail_llm_plan"

        # Mock _make_llm_call on the agent instance to raise an exception
        llm_error = anthropic.APIConnectionError(
            message="Network error",
            request=MagicMock(),  # Provide a mock request object
        )
        planning_agent._make_llm_call = AsyncMock(side_effect=llm_error)
        planning_agent.save_new_plan = (
            AsyncMock()
        )  # Mock save to ensure it's NOT called

        result = await planning_agent.execute_workflow(
            user_message=user_message,
            host_instance=mock_mcp_host,
            plan_name=plan_name,
            # anthropic_api_key no longer needed
        )

        # Assertions
        assert "Plan generation failed" in result["error"]
        assert str(llm_error) in result["error"]
        assert result["final_output"] is None
        assert len(result["workflow_steps"]) == 2  # LLM Call + LLM Failure

        # Check LLM call mock was called
        planning_agent._make_llm_call.assert_awaited_once()
        # Check save_new_plan was NOT called
        planning_agent.save_new_plan.assert_not_awaited()

        # Check workflow steps
        assert result["workflow_steps"][0]["step"] == 1
        assert result["workflow_steps"][0]["action"] == "LLM Call (Generate Plan)"
        assert result["workflow_steps"][1]["step"] == 1
        assert result["workflow_steps"][1]["status"] == "Failed"
        assert str(llm_error) in result["workflow_steps"][1]["error"]

    @pytest.mark.asyncio
    async def test_execute_workflow_tool_failure(
        self, planning_agent: PlanningAgent, mock_mcp_host: MagicMock
    ):
        """Verify workflow handles failure during the tool call (Step 2)."""
        user_message = "Create a plan for tool failure."
        plan_name = "fail_tool_plan"
        generated_plan_content = "Step 1: Generate. Step 2: Fail save."

        # Mock LLM call success on the agent instance
        mock_llm_response = MagicMock(spec=anthropic.types.Message)
        mock_llm_response.content = [
            anthropic.types.TextBlock(
                type="text", text=generated_plan_content
            )  # Use anthropic.types
        ]
        planning_agent._make_llm_call = AsyncMock(return_value=mock_llm_response)

        # Mock save_new_plan on the agent instance to raise an exception
        tool_error = ValueError("Disk full")
        planning_agent.save_new_plan = AsyncMock(side_effect=tool_error)

        result = await planning_agent.execute_workflow(
            user_message=user_message,
            host_instance=mock_mcp_host,
            plan_name=plan_name,
            # anthropic_api_key no longer needed
        )

        # Assertions
        assert "Plan saving failed" in result["error"]
        assert str(tool_error) in result["error"]
        assert result["final_output"] is None
        assert (
            len(result["workflow_steps"]) == 4
        )  # LLM Call + LLM Success + Tool Call + Tool Failure

        # Check mocks were called
        planning_agent._make_llm_call.assert_awaited_once()
        planning_agent.save_new_plan.assert_awaited_once()

        # Check workflow steps
        assert result["workflow_steps"][0]["step"] == 1
        assert result["workflow_steps"][0]["action"] == "LLM Call (Generate Plan)"
        assert result["workflow_steps"][1]["step"] == 1
        assert result["workflow_steps"][1]["status"] == "Success"
        assert result["workflow_steps"][2]["step"] == 2
        assert result["workflow_steps"][2]["action"] == "Tool Call (save_plan)"
        assert result["workflow_steps"][3]["step"] == 2
        assert result["workflow_steps"][3]["status"] == "Failed"
        assert str(tool_error) in result["workflow_steps"][3]["error"]

    # TODO: Add tests for generate_plan if/when implemented
