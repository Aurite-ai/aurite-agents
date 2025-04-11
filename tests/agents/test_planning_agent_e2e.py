"""
E2E tests for interacting with planning tools via a generic Agent.
"""

import pytest
import logging
import uuid
from pathlib import Path

# Use relative imports assuming tests run from aurite-mcp root
from src.host.models import AgentConfig
from src.host_manager import HostManager  # Import HostManager
from src.agents.agent import Agent  # Import the generic Agent

logger = logging.getLogger(__name__)

# Define the client ID used in testing_config.json for the planning server
# Ensure this matches the client_id in your config/testing_config.json
PLANNING_CLIENT_ID = "planning_server"

# Define the directory where the planning server saves plans
# This should match the directory used by your planning_server.py implementation
# Assuming it's relative to project root for consistency
PLAN_SAVE_DIR = Path("src/packaged_servers/plans")


# Mark all tests in this module as e2e and use anyio backend
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.anyio,
]


class TestPlanningAgentE2E:
    """E2E tests for Planning tools via Agent interactions."""

    @pytest.fixture
    def planning_agent_config(self, host_manager: HostManager) -> AgentConfig:
        """
        Provides an AgentConfig suitable for interacting with the planning server.
        Uses the host config from the host_manager fixture.
        """
        if not host_manager or not host_manager.host or not host_manager.host._config:
            pytest.fail("HostManager fixture did not provide a valid host config")

        # Create a config that targets the planning server
        # You might want to load a specific agent config from the main config file
        # if one is defined there for planning tasks. For now, create a basic one.
        return AgentConfig(
            name="E2EPlanningToolTesterAgent",
            host=host_manager.host._config,  # Link to the host's config
            client_ids=[PLANNING_CLIENT_ID],  # Explicitly target planning server
            system_prompt="You are an agent designed to test planning tools.",
            # Add other relevant params like model if needed, or rely on defaults
        )

    @pytest.fixture(autouse=True)
    def check_client_exists(self, host_manager: HostManager):
        """Fixture to ensure the planning client is loaded before tests run."""
        if PLANNING_CLIENT_ID not in host_manager.host.clients:
            pytest.skip(
                f"Planning server client '{PLANNING_CLIENT_ID}' not found in host config. "
                "Ensure it's defined in config/testing_config.json"
            )
        logger.info(f"Host fixture confirmed client '{PLANNING_CLIENT_ID}' is loaded.")
        # Ensure the plan save directory exists for cleanup later
        PLAN_SAVE_DIR.mkdir(parents=True, exist_ok=True)

    @pytest.mark.skip(
        reason="Test logic needs to be implemented for generic Agent and tools"
    )
    async def test_planning_tools_via_agent(
        self, planning_agent_config: AgentConfig, host_manager: HostManager
    ):
        """
        TODO: Implement E2E test for save_plan and list_plans tools.
        1. Instantiate the generic Agent with planning_agent_config.
        2. Craft a user_message that instructs the agent to save a specific plan.
        3. Execute the agent using agent.execute_agent().
        4. Verify the agent correctly called the 'save_plan' tool via host_manager.host.
        5. Verify the plan file and meta file were created in PLAN_SAVE_DIR.
        6. Craft a user_message to list plans (all and tagged).
        7. Execute the agent again.
        8. Verify the agent called the 'list_plans' tool.
        9. Verify the response contains the previously saved plan.
        10. Clean up created files.
        """
        # Example setup (needs implementation)
        agent = Agent(config=planning_agent_config)
        host = host_manager.host
        plan_name = f"rebuilt_e2e_plan_{uuid.uuid4()}"
        plan_content = "Step 1: Rebuild test.\nStep 2: Implement logic."
        tags = ["rebuilt", "testing"]
        plan_file_path = PLAN_SAVE_DIR / f"{plan_name}.txt"
        meta_file_path = PLAN_SAVE_DIR / f"{plan_name}.meta.json"

        logger.info(f"Placeholder test for plan: {plan_name}")

        # --- Test Logic Placeholder ---
        # Example: Save Plan via Agent
        # save_message = f"Save a plan named '{plan_name}' with content: {plan_content}"
        # save_result = await agent.execute_agent(save_message, host, filter_client_ids=[PLANNING_CLIENT_ID])
        # assert 'save_plan' in [use['name'] for use in save_result.get('tool_uses', [])]
        # assert plan_file_path.exists()
        # assert meta_file_path.exists()

        # Example: List Plan via Agent
        # list_message = f"List plans tagged 'rebuilt'"
        # list_result = await agent.execute_agent(list_message, host, filter_client_ids=[PLANNING_CLIENT_ID])
        # assert 'list_plans' in [use['name'] for use in list_result.get('tool_uses', [])]
        # Check final_response content for the plan details

        # --- Cleanup ---
        # if plan_file_path.exists(): plan_file_path.unlink()
        # if meta_file_path.exists(): meta_file_path.unlink()

        pass  # Remove once implemented
