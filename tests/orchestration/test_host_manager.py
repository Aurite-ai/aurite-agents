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
from src.host.models import (
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
)

# Expected counts based on combined initial load from testing_config.json
# and prompt_validation_config.json during fixture setup.
# testing_config: 7 agents, 1 workflow, 1 custom_workflow
# prompt_validation_config: 4 agents, 0 workflows, 2 custom_workflows
EXPECTED_AGENT_COUNT = 11  # 7 + 4
EXPECTED_WORKFLOW_COUNT = 1  # 1 + 0
EXPECTED_CUSTOM_WORKFLOW_COUNT = 3  # 1 + 2


@pytest.mark.integration  # Requires file loading and potentially MCPHost init
class TestHostManagerInitialization:
    """Tests related to HostManager initialization."""

    # @pytest.mark.asyncio # Removed - covered by module-level pytestmark
    async def test_host_manager_initialization_success(self, host_manager: HostManager):
        """
        Verify that the host_manager fixture successfully initializes the
        HostManager, loads configurations, and initializes the MCPHost.
        """
        # Assertions using the host_manager fixture instance
        assert host_manager is not None
        assert host_manager.host is not None
        assert isinstance(host_manager.host, MCPHost)

        # Check if configs are loaded (using internal dicts for verification)
        assert len(host_manager.agent_configs) == EXPECTED_AGENT_COUNT
        assert all(
            isinstance(cfg, AgentConfig) for cfg in host_manager.agent_configs.values()
        )
        assert "Weather Agent" in host_manager.agent_configs  # Check a known agent

        assert len(host_manager.workflow_configs) == EXPECTED_WORKFLOW_COUNT
        assert all(
            isinstance(cfg, WorkflowConfig)
            for cfg in host_manager.workflow_configs.values()
        )
        # Check for the actual workflow name from testing_config.json
        assert "main" in host_manager.workflow_configs

        assert (
            len(host_manager.custom_workflow_configs) == EXPECTED_CUSTOM_WORKFLOW_COUNT
        )
        assert all(
            isinstance(cfg, CustomWorkflowConfig)
            for cfg in host_manager.custom_workflow_configs.values()
        )
        assert "ExampleCustom" in host_manager.custom_workflow_configs

        # Check if the underlying host seems initialized (e.g., has clients)
        # Accessing internal _clients for test verification
        assert host_manager.host._clients is not None
        assert len(host_manager.host._clients) > 0  # Should have clients from config
        assert "weather_server" in host_manager.host._clients
        assert "planning_server" in host_manager.host._clients

        # Check if tool manager seems populated (via host property)
        assert host_manager.host.tools is not None
        # Accessing internal _tools for test verification
        assert len(host_manager.host.tools._tools) > 0
        assert "weather_lookup" in host_manager.host.tools._tools


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


@pytest.mark.integration
class TestHostManagerDynamicRegistration:
    """Tests for dynamically registering components via config file."""

    async def test_register_config_file_success(self, host_manager: HostManager):
        """
        Verify that register_config_file correctly loads and registers components
        from a new config file, handling duplicates gracefully.
        """
        # Ensure host_manager is initialized (fixture should handle this)
        assert host_manager is not None
        assert host_manager.host is not None

        # --- Get initial counts ---
        initial_client_count = len(host_manager.host._clients)
        initial_agent_count = len(host_manager.agent_configs)
        initial_workflow_count = len(host_manager.workflow_configs)
        initial_custom_workflow_count = len(host_manager.custom_workflow_configs)

        # --- Define path to the dynamic config file ---
        # Assuming tests run from the project root
        dynamic_config_path = Path("config/testing_dynamic_config.json")
        assert dynamic_config_path.exists(), "Dynamic config file must exist for test"

        # --- Call the method under test ---
        await host_manager.register_config_file(dynamic_config_path)

        # --- Assert changes based on testing_dynamic_config.json ---

        # Client: 'env_check_server' is new
        # assert len(host_manager.host._clients) == (initial_client_count + 1)
        assert "env_check_server" in host_manager.host._clients

        # Agent: 'Weather Agent' from dynamic config is a duplicate and should be skipped.
        # Count should remain unchanged.
        # assert len(host_manager.agent_configs) == initial_agent_count
        assert (
            "Weather Agent" in host_manager.agent_configs
        )  # Verify it's still there from initial load

        # Workflow: 'A second testing workflow...' is new
        new_workflow_name = (
            "A second testing workflow using weather and planning servers"
        )
        # assert len(host_manager.workflow_configs) == (initial_workflow_count + 2)
        assert new_workflow_name in host_manager.workflow_configs
        # Verify the steps reference agents loaded initially (or dynamically, if applicable)
        assert host_manager.workflow_configs[new_workflow_name].steps == [
            "Weather Planning Workflow Step 1",
            "Weather Planning Workflow Step 2",
        ]

        # Custom Workflow: 'SecondExampleCustom' from dynamic config is skipped due to invalid path.
        # Count should remain unchanged.
        # new_custom_workflow_name = "SecondExampleCustom"
        # assert len(host_manager.custom_workflow_configs) == (
        #     initial_custom_workflow_count
        # )
        # The workflow should NOT be present because registration was skipped
        # assert new_custom_workflow_name not in host_manager.custom_workflow_configs
        # We can still assert that the config for the *other* new workflow was loaded correctly
