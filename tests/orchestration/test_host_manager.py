"""
Tests for the HostManager class.
"""

import pytest

# Mark all tests in this module as belonging to the Orchestration layer and use anyio
pytestmark = [pytest.mark.orchestration, pytest.mark.anyio]

import os  # Add import for environment variable check

# Assuming tests run from project root
from src.host_manager import HostManager
from src.host.host import MCPHost
from src.config.config_models import (
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
)

# Expected counts based on the mock_project_config_object fixture
EXPECTED_CLIENT_COUNT = 3
EXPECTED_AGENT_COUNT = 2
EXPECTED_LLM_CONFIG_COUNT = 1
EXPECTED_WORKFLOW_COUNT = 1
EXPECTED_CUSTOM_WORKFLOW_COUNT = 1


@pytest.mark.integration  # Still integration as it tests HostManager with (mocked) ProjectManager and real MCPHost
class TestHostManagerInitialization:
    """Tests related to HostManager initialization."""

    # @pytest.mark.asyncio # Removed - covered by module-level pytestmark
    # @pytest.mark.xfail( # Assuming the event loop issue might be resolved or less prevalent with mocks
    #     reason="Known 'Event loop is closed' error during host_manager fixture teardown"
    # ) # Keep xfail for now if it persists, but test with it removed first.
    async def test_host_manager_initialization_success(self, host_manager: HostManager):
        """
        Verify that the host_manager fixture successfully initializes the
        HostManager using the mocked ProjectManager, loads configurations,
        and initializes the MCPHost.
        """
        # Assertions using the host_manager fixture instance
        assert host_manager is not None
        assert host_manager.host is not None
        assert isinstance(host_manager.host, MCPHost)
        assert host_manager.current_project is not None
        assert host_manager.current_project.name == "MockedTestProject"

        # Check if configs are loaded from the mocked ProjectConfig
        assert len(host_manager.agent_configs) == EXPECTED_AGENT_COUNT
        assert all(
            isinstance(cfg, AgentConfig) for cfg in host_manager.agent_configs.values()
        )
        assert "Agent1" in host_manager.agent_configs
        assert "Weather Agent" in host_manager.agent_configs

        assert len(host_manager.llm_configs) == EXPECTED_LLM_CONFIG_COUNT
        assert "llm_default" in host_manager.llm_configs

        assert len(host_manager.workflow_configs) == EXPECTED_WORKFLOW_COUNT
        assert all(
            isinstance(cfg, WorkflowConfig)
            for cfg in host_manager.workflow_configs.values()
        )
        assert "main" in host_manager.workflow_configs

        assert (
            len(host_manager.custom_workflow_configs) == EXPECTED_CUSTOM_WORKFLOW_COUNT
        )
        assert all(
            isinstance(cfg, CustomWorkflowConfig)
            for cfg in host_manager.custom_workflow_configs.values()
        )
        assert "ExampleCustom" in host_manager.custom_workflow_configs

        # Check if the underlying host seems initialized (e.g., has clients from mock ProjectConfig)
        assert host_manager.host._clients is not None
        assert len(host_manager.host._clients) == EXPECTED_CLIENT_COUNT
        assert "client1" in host_manager.host._clients
        assert "weather_server" in host_manager.host._clients
        assert "planning_server" in host_manager.host._clients

        # Check if tool manager seems populated (via host property)
        # This depends on the dummy servers actually starting and registering tools.
        # The dummy_server1.py, weather_mcp_server.py, planning_server.py would need to be runnable.
        # For a more robust unit/integration test of HostManager with mocked ProjectManager,
        # we might not need to assert specific tools if client init is complex.
        # However, if the dummy client paths in mock_project_config_object are valid and runnable,
        # we can expect some tools.
        assert host_manager.host.tools is not None
        # If dummy servers are very basic and don't register tools, this might be 0.
        # For now, let's assume they might register something or MCPHost has default tools.
        # This assertion might need adjustment based on actual client behavior.
        # A more direct test of MCPHost client registration and tool loading would be separate.
        # Given the mock_project_config_object uses paths like "config/clients/weather_mcp_server.py",
        # these are real server files. If they are functional, tools should be loaded.
        if (
            len(host_manager.host._clients) > 0
        ):  # Only check tools if clients were loaded
            assert len(host_manager.host.tools._tools) > 0
            # Example: if weather_mcp_server.py registers 'weather_lookup'
            # This requires weather_mcp_server.py to be functional.
            # assert "weather_lookup" in host_manager.host.tools._tools


# Add more test classes/functions below for execution methods


@pytest.mark.integration
class TestHostManagerExecution:
    """Tests for HostManager execution methods."""

    @pytest.mark.skip(
        reason="HostManager execution methods removed, moved to ExecutionFacade"
    )
    async def test_execute_agent_success(self, host_manager: HostManager):
        """Test executing a known agent successfully."""
        agent_name = "Weather Agent"  # Agent defined in testing_config.json
        user_message = "What's the weather like?"

        # Requires ANTHROPIC_API_KEY to be set in environment
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("Requires ANTHROPIC_API_KEY environment variable")

        result = await host_manager.execute_agent(
            agent_name=agent_name, user_message=user_message
        )

        assert result is not None
        assert isinstance(result, dict)
        assert "final_response" in result
        assert "error" not in result or result["error"] is None

        # Check if the response content indicates success (might need refinement)
        # Example: Check if final_response has content and expected structure
        assert result["final_response"] is not None
        # Anthropic response structure check
        assert hasattr(result["final_response"], "content")
        assert len(result["final_response"].content) > 0
        assert hasattr(result["final_response"].content[0], "text")
        # We can't easily assert the *exact* text, but check it's non-empty
        assert isinstance(result["final_response"].content[0].text, str)
        assert len(result["final_response"].content[0].text) > 0

        # Optional: Check for tool usage if expected
        # assert "tool_uses" in result
        # assert len(result["tool_uses"]) > 0
        # assert result["tool_uses"][0]["name"] == "weather_lookup" # Example

    @pytest.mark.skip(
        reason="HostManager execution methods removed, moved to ExecutionFacade"
    )
    async def test_execute_workflow_success(self, host_manager: HostManager):
        """Test executing a known simple workflow successfully."""
        workflow_name = "Example workflow using weather and planning servers"  # From testing_config.json
        initial_message = "Get the weather and make a plan."

        # Requires ANTHROPIC_API_KEY for the agents within the workflow
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
        assert (
            len(result["final_message"]) > 0
        )  # Check that the final message is non-empty

        # We could potentially assert something about the content of the final message
        # if the workflow's output is predictable, e.g., confirming a plan was saved.
        # For now, just checking for successful completion and a non-empty message.
        print(f"\nWorkflow Final Message: {result['final_message']}")  # Log for info

    @pytest.mark.skip(
        reason="HostManager execution methods removed, moved to ExecutionFacade"
    )
    async def test_execute_custom_workflow_success(self, host_manager: HostManager):
        """Test executing a known custom workflow successfully."""
        workflow_name = "ExampleCustom"  # From testing_config.json
        initial_input = "Test Input String"

        # Requires ANTHROPIC_API_KEY for the agent called within the custom workflow
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("Requires ANTHROPIC_API_KEY environment variable")

        result = await host_manager.execute_custom_workflow(
            workflow_name=workflow_name, initial_input=initial_input
        )

        # Assertions based on the expected output of ExampleCustomWorkflow
        assert result is not None
        assert isinstance(result, dict)
        assert result.get("status") == "success"
        assert result.get("input_received") == initial_input
        assert "agent_result_text" in result
        assert isinstance(result["agent_result_text"], str)
        assert len(result["agent_result_text"]) > 0  # Check agent response is non-empty

        print(f"\nCustom Workflow Result: {result}")  # Log for info


from pathlib import Path  # Add Path import
