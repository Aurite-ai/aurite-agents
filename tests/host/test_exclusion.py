# filepath: /home/wilcoxr/workspace/aurite/aurite-agents/tests/host/test_host_manager.py
"""
Tests for the HostManager class.
"""

import pytest
import os  # Add import for environment variable check

# Assuming tests run from project root
from src.host_manager import HostManager
from src.host.host import MCPHost
from src.host.models import (
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
)

# Expected counts based on testing_config.json
EXPECTED_AGENT_COUNT = 4
EXPECTED_WORKFLOW_COUNT = 1
EXPECTED_CUSTOM_WORKFLOW_COUNT = 1


@pytest.mark.integration
class TestHostManagerInitialization:
    """Tests related to HostManager initialization."""

    async def test_host_manager_initialization_success(self, host_manager: HostManager):
        """
        Verify that the host_manager fixture successfully initializes the
        HostManager, loads configurations, and initializes the MCPHost.
        """
        assert host_manager is not None
        assert host_manager.host is not None
        assert isinstance(host_manager.host, MCPHost)

        # Check if configs are loaded
        assert len(host_manager.agent_configs) == EXPECTED_AGENT_COUNT
        assert all(
            isinstance(cfg, AgentConfig) for cfg in host_manager.agent_configs.values()
        )
        assert "Weather Agent" in host_manager.agent_configs

        assert len(host_manager.workflow_configs) == EXPECTED_WORKFLOW_COUNT
        assert all(
            isinstance(cfg, WorkflowConfig)
            for cfg in host_manager.workflow_configs.values()
        )
        assert (
            "Example workflow using weather and planning servers"
            in host_manager.workflow_configs
        )

        assert (
            len(host_manager.custom_workflow_configs) == EXPECTED_CUSTOM_WORKFLOW_COUNT
        )
        assert all(
            isinstance(cfg, CustomWorkflowConfig)
            for cfg in host_manager.custom_workflow_configs.values()
        )
        assert "ExampleCustom" in host_manager.custom_workflow_configs

        # Check if the underlying host seems initialized
        assert host_manager.host._clients is not None
        assert len(host_manager.host._clients) > 0
        assert "weather_server" in host_manager.host._clients
        assert "planning_server" in host_manager.host._clients

        # Check if tool manager seems populated
        assert host_manager.host.tools is not None
        assert len(host_manager.host.tools._tools) > 0
        assert "weather_lookup" in host_manager.host.tools._tools


@pytest.mark.integration
class TestHostManagerExecution:
    """Tests for HostManager execution methods."""

    async def test_execute_agent_success(self, host_manager: HostManager):
        """Test executing a known agent successfully."""
        agent_name = "Weather Agent"
        user_message = "What's the weather like?"

        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("Requires ANTHROPIC_API_KEY environment variable")

        result = await host_manager.execute_agent(
            agent_name=agent_name, user_message=user_message
        )

        assert result is not None
        assert isinstance(result, dict)
        assert "final_response" in result
        assert "error" not in result or result["error"] is None
        assert result["final_response"] is not None
        # Check Anthropic response structure
        assert hasattr(result["final_response"], "content")
        assert len(result["final_response"].content) > 0
        assert hasattr(result["final_response"].content[0], "text")
        assert isinstance(result["final_response"].content[0].text, str)
        assert len(result["final_response"].content[0].text) > 0

    async def test_execute_workflow_success(self, host_manager: HostManager):
        """Test executing a known simple workflow successfully."""
        workflow_name = "Example workflow using weather and planning servers"
        initial_message = "Get the weather and make a plan."

        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("Requires ANTHROPIC_API_KEY environment variable")

        result = await host_manager.execute_workflow(
            workflow_name=workflow_name, initial_user_message=initial_message
        )

        assert result is not None
        assert isinstance(result, dict)
        assert result.get("workflow_name") == workflow_name
        assert result.get("status") == "completed"
        assert result.get("error") is None
        assert "final_message" in result
        assert isinstance(result["final_message"], str)
        assert len(result["final_message"]) > 0

    async def test_execute_custom_workflow_success(self, host_manager: HostManager):
        """Test executing a known custom workflow successfully."""
        workflow_name = "ExampleCustom"
        initial_input = "Test Input String"

        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("Requires ANTHROPIC_API_KEY environment variable")

        result = await host_manager.execute_custom_workflow(
            workflow_name=workflow_name, initial_input=initial_input
        )

        assert result is not None
        assert isinstance(result, dict)
        assert result.get("status") == "success"
        assert result.get("input_received") == initial_input
        assert "agent_result_text" in result
        assert isinstance(result["agent_result_text"], str)
        assert len(result["agent_result_text"]) > 0
