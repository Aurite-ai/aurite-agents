"""
Tests for the Aurite class.
"""

import pytest

# Mark all tests in this module as belonging to the Orchestration layer and use anyio
pytestmark = [pytest.mark.orchestration, pytest.mark.anyio]


# Assuming tests run from project root
from aurite.host_manager import Aurite
from aurite.host.host import MCPHost
from aurite.config.config_models import (
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
)

# Expected counts based on loading config/testing_config.json
EXPECTED_CLIENT_COUNT = 3
EXPECTED_AGENT_COUNT = 7
EXPECTED_LLM_CONFIG_COUNT = 0  # testing_config.json doesn't define any LLM configs
EXPECTED_WORKFLOW_COUNT = 1
EXPECTED_CUSTOM_WORKFLOW_COUNT = 1


@pytest.mark.integration  # Tests Aurite with real ProjectManager and real MCPHost/clients
class TestAuriteInitialization:
    """Tests related to Aurite initialization."""

    # @pytest.mark.asyncio # Removed - covered by module-level pytestmark
    # @pytest.mark.xfail( # Assuming the event loop issue might be resolved or less prevalent with mocks
    #     reason="Known 'Event loop is closed' error during host_manager fixture teardown"
    # ) # Keep xfail for now if it persists, but test with it removed first.
    async def test_host_manager_initialization_success(self, host_manager: Aurite):
        """
        Verify that the host_manager fixture successfully initializes the
        Aurite using the mocked ProjectManager, loads configurations,
        and initializes the MCPHost.
        """
        # Assertions using the host_manager fixture instance
        assert host_manager is not None
        assert host_manager.host is not None
        assert isinstance(host_manager.host, MCPHost)

        active_project = host_manager.project_manager.get_active_project_config()
        assert active_project is not None
        # Assert based on the name in config/testing_config.json
        assert active_project.name == "DefaultMCPHost"

        # Check if configs are loaded into the active_project managed by ProjectManager
        assert len(active_project.agents) == EXPECTED_AGENT_COUNT
        assert all(
            isinstance(cfg, AgentConfig)
            for cfg in active_project.agents.values()
        )
        assert "Weather Agent" in active_project.agents  # Check a known agent
        assert "Planning Agent" in active_project.agents  # Check another

        assert (
            len(active_project.llms) == EXPECTED_LLM_CONFIG_COUNT
        )  # Should be 0

        assert len(active_project.simple_workflows) == EXPECTED_WORKFLOW_COUNT
        assert all(
            isinstance(cfg, WorkflowConfig)
            for cfg in active_project.simple_workflows.values()
        )
        assert (
            "main" in active_project.simple_workflows
        )  # Check the workflow name

        assert (
            len(active_project.custom_workflows)
            == EXPECTED_CUSTOM_WORKFLOW_COUNT
        )
        assert all(
            isinstance(cfg, CustomWorkflowConfig)
            for cfg in active_project.custom_workflows.values()
        )
        assert (
            "ExampleCustomWorkflow" in active_project.custom_workflows
        )  # Check the custom workflow name

        # Check if the underlying host seems initialized (e.g., has clients from config)
        assert host_manager.host.client_manager.active_clients is not None
        assert (
            len(host_manager.host.client_manager.active_clients)
            == EXPECTED_CLIENT_COUNT
        )
        assert (
            "weather_server" in host_manager.host.client_manager.active_clients
        )  # Check client IDs from config
        assert "planning_server" in host_manager.host.client_manager.active_clients
        assert "address_server" in host_manager.host.client_manager.active_clients

        # Check if tool manager seems populated (via host property)
        # This depends on the servers actually starting and registering tools.
        # The dummy_server1.py, weather_mcp_server.py, planning_server.py would need to be runnable.
        # For a more robust unit/integration test of Aurite with mocked ProjectManager,
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
            len(host_manager.host.client_manager.active_clients) > 0
        ):  # Only check tools if clients were loaded
            assert len(host_manager.host.tools._tools) > 0
            # Example: if weather_mcp_server.py registers 'weather_lookup'
            # This requires weather_mcp_server.py to be functional.
            # assert "weather_lookup" in host_manager.host.tools._tools
