"""
Unit tests for the PlanningAgent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json  # Add json import

# Use relative imports assuming tests run from aurite-mcp root
from src.agents.management.planning_agent import PlanningAgent
from src.host.models import AgentConfig, HostConfig
from src.host.host import MCPHost  # Needed for type hinting
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

        with pytest.raises(
            ValueError, match="Tool 'save_plan' not found on any registered client."
        ):
            # Call the agent method which should now fail internally when calling host.execute_tool
            await planning_agent.save_new_plan(
                host_instance=mock_mcp_host,
                plan_name="fail_plan",
                plan_content="wont work",
            )

    # TODO: Add tests for generate_plan if/when implemented
