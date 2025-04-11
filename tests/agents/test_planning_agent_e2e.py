"""
E2E tests for interacting with planning tools via a generic Agent.
"""

import pytest
import logging
import uuid
import json  # <-- Add this import
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

        # Use a slightly more specific system prompt for the test agent
        return AgentConfig(
            name="E2EPlanningToolTesterAgent",
            # host=host_manager.host._config, # AgentConfig doesn't take host directly
            client_ids=[PLANNING_CLIENT_ID],  # Explicitly target planning server
            system_prompt=(
                "You are an agent designed to test planning tools. "
                "Use the 'save_plan' tool to save plans and 'list_plans' to list them. "
                "Follow the user's instructions precisely. "
                "When listing plans, make sure to include the names of the plans found in your final response."
            ),
            model="claude-3-haiku-20240307",  # Use a faster model for testing
            temperature=0.1,  # Low temperature for predictable results
        )

    @pytest.fixture(autouse=True)
    def check_client_exists(self, host_manager: HostManager):
        """Fixture to ensure the planning client is loaded before tests run."""
        # Access the private _clients attribute, which holds the client sessions
        if PLANNING_CLIENT_ID not in host_manager.host._clients:
            pytest.skip(
                f"Planning server client '{PLANNING_CLIENT_ID}' not found in host config. "
                "Ensure it's defined in config/testing_config.json"
            )
        logger.info(f"Host fixture confirmed client '{PLANNING_CLIENT_ID}' is loaded.")
        # Ensure the plan save directory exists
        PLAN_SAVE_DIR.mkdir(parents=True, exist_ok=True)

    # Remove the skip marker
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
        agent = Agent(config=planning_agent_config)
        # host_manager already provides the initialized host via its .host attribute
        host = host_manager.host
        plan_name = f"e2e_plan_{uuid.uuid4()}"
        plan_content = (
            "Step 1: Define test.\nStep 2: Run test.\nStep 3: Verify results."
        )
        tags = ["e2e", "testing"]
        plan_file_path = PLAN_SAVE_DIR / f"{plan_name}.txt"
        meta_file_path = PLAN_SAVE_DIR / f"{plan_name}.meta.json"

        logger.info(f"Starting E2E planning test for plan: {plan_name}")

        # Ensure files don't exist initially (e.g., from failed previous run)
        if plan_file_path.exists():
            plan_file_path.unlink()
        if meta_file_path.exists():
            meta_file_path.unlink()

        try:
            # 1. Save Plan via Agent
            save_message = (
                f"Save a plan named '{plan_name}' with the following content:\n"
                f"{plan_content}\n"
                f"Also, tag it with: {json.dumps(tags)}"
            )
            logger.info(f"Sending save message to agent: {save_message}")
            save_result = await agent.execute_agent(
                user_message=save_message,
                host_instance=host,
                filter_client_ids=[PLANNING_CLIENT_ID],
            )

            logger.debug(f"Save agent result: {save_result}")

            # Verify save_plan tool was used
            tool_uses = save_result.get("tool_uses", [])
            assert any(use["name"] == "save_plan" for use in tool_uses), (
                "Agent did not use 'save_plan' tool"
            )
            logger.info("Verified 'save_plan' tool was used.")

            # Verify files were created
            assert plan_file_path.exists(), (
                f"Plan file was not created: {plan_file_path}"
            )
            assert meta_file_path.exists(), (
                f"Metadata file was not created: {meta_file_path}"
            )
            logger.info("Verified plan and metadata files were created.")

            # Optional: Verify content
            with open(plan_file_path, "r") as f:
                # Strip whitespace from each line before comparing
                actual_content_lines = [line.strip() for line in f.readlines()]
                expected_content_lines = [
                    line.strip() for line in plan_content.splitlines()
                ]
                assert actual_content_lines == expected_content_lines, (
                    f"Plan content mismatch after stripping lines.\nExpected: {expected_content_lines}\nActual: {actual_content_lines}"
                )
            with open(meta_file_path, "r") as f:
                meta_data = json.load(f)
                assert meta_data.get("name") == plan_name
                assert set(meta_data.get("tags", [])) == set(tags)
            logger.info("Verified file content and metadata.")

            # 2. List Plans (Tagged) via Agent
            list_message = "List all plans tagged with 'e2e'"
            logger.info(f"Sending list message to agent: {list_message}")
            list_result = await agent.execute_agent(
                user_message=list_message,
                host_instance=host,
                filter_client_ids=[PLANNING_CLIENT_ID],
            )

            logger.debug(f"List agent result: {list_result}")

            # Verify list_plans tool was used
            list_tool_uses = list_result.get("tool_uses", [])
            assert any(use["name"] == "list_plans" for use in list_tool_uses), (
                "Agent did not use 'list_plans' tool"
            )
            logger.info("Verified 'list_plans' tool was used.")

            # Verify the final response contains the plan name
            final_response_content = ""
            if list_result.get("final_response"):
                # Extract text from potential list of content blocks
                content_list = getattr(list_result["final_response"], "content", [])
                text_blocks = [
                    block.text for block in content_list if block.type == "text"
                ]
                final_response_content = "\n".join(text_blocks)

            assert plan_name in final_response_content

        finally:
            # --- Cleanup ---
            logger.info("Cleaning up created test files...")
            if plan_file_path.exists():
                plan_file_path.unlink()
                logger.info(f"Deleted plan file: {plan_file_path}")
            else:
                logger.warning(f"Plan file not found for cleanup: {plan_file_path}")

            if meta_file_path.exists():
                meta_file_path.unlink()
                logger.info(f"Deleted metadata file: {meta_file_path}")
            else:
                logger.warning(f"Metadata file not found for cleanup: {meta_file_path}")
