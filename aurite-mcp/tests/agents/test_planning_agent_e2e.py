"""
E2E tests for the PlanningAgent using a real host and planning server.
"""

import pytest
import logging
import uuid
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock  # Add mock imports
import anthropic  # Add anthropic import

# Use relative imports assuming tests run from aurite-mcp root
from src.agents.management.planning_agent import PlanningAgent
from src.host.models import AgentConfig
from src.host.host import MCPHost  # Needed for type hinting

logger = logging.getLogger(__name__)

# Define the client ID used in testing_config.json for the planning server
PLANNING_CLIENT_ID = "planning_server_test"

# Define the directory where the planning server saves plans
# (relative to the planning_server.py file location)
PLAN_SAVE_DIR = Path("src/servers/management/plans")


@pytest.mark.e2e
# Apply xfail due to the known host shutdown issue with the fixture
@pytest.mark.xfail(
    reason="Known issue with real_mcp_host teardown async complexity", strict=False
)
class TestPlanningAgentE2E:
    """E2E tests for PlanningAgent interactions with a live planning server."""

    @pytest.fixture
    def planning_agent_config(self) -> AgentConfig:
        """Provides a basic AgentConfig for the PlanningAgent."""
        # HostConfig isn't strictly needed here as the agent gets the
        # host instance passed into its methods during the test.
        return AgentConfig(name="E2EPlanningAgent")

    @pytest.fixture
    def planning_agent_instance(
        self, planning_agent_config: AgentConfig
    ) -> PlanningAgent:
        """Provides an instance of PlanningAgent."""
        return PlanningAgent(config=planning_agent_config)

    @pytest.fixture(autouse=True)
    def check_client_exists(self, real_mcp_host: MCPHost):
        """Fixture to ensure the planning client is loaded before tests run."""
        if PLANNING_CLIENT_ID not in real_mcp_host.clients:
            pytest.skip(
                f"Planning server client '{PLANNING_CLIENT_ID}' not found in host config. "
                "Ensure it's defined in config/agents/testing_config.json"
            )
        logger.info(f"Host fixture confirmed client '{PLANNING_CLIENT_ID}' is loaded.")
        # Ensure the plan save directory exists for cleanup later
        PLAN_SAVE_DIR.mkdir(parents=True, exist_ok=True)

    @pytest.mark.asyncio
    async def test_save_and_list_plan_e2e(
        self, planning_agent_instance: PlanningAgent, real_mcp_host: MCPHost
    ):
        """Verify saving a plan via the agent and then listing it."""
        host = real_mcp_host
        agent = planning_agent_instance
        plan_name = f"e2e_test_plan_{uuid.uuid4()}"  # Unique name for test isolation
        plan_content = "Step 1: Run E2E test.\nStep 2: Verify results."
        tags = ["e2e", "testing"]
        plan_file_path = PLAN_SAVE_DIR / f"{plan_name}.txt"
        meta_file_path = PLAN_SAVE_DIR / f"{plan_name}.meta.json"

        # --- Save Plan ---
        logger.info(f"Attempting to save plan '{plan_name}' via agent...")
        save_result = await agent.save_new_plan(
            host_instance=host,
            plan_name=plan_name,
            plan_content=plan_content,
            tags=tags,
        )
        logger.info(f"Save plan result: {save_result}")
        assert save_result.get("success") is True
        assert plan_name in save_result.get("message", "")
        # Check if file was actually created (basic verification)
        assert plan_file_path.exists(), f"Plan file {plan_file_path} was not created"
        assert meta_file_path.exists(), f"Meta file {meta_file_path} was not created"

        # --- List Plan (No Tag) ---
        logger.info("Attempting to list all plans via agent...")
        list_all_result = await agent.list_existing_plans(host_instance=host)
        logger.info(f"List all plans result: {list_all_result}")
        assert list_all_result.get("success") is True
        assert isinstance(list_all_result.get("plans"), list)
        # Check if our saved plan is in the list
        found_plan = any(
            p.get("name") == plan_name for p in list_all_result.get("plans", [])
        )
        assert found_plan, f"Saved plan '{plan_name}' not found in list_all_result"

        # --- List Plan (With Tag) ---
        logger.info("Attempting to list plans with tag 'e2e' via agent...")
        list_tagged_result = await agent.list_existing_plans(
            host_instance=host, tag="e2e"
        )
        logger.info(f"List tagged plans result: {list_tagged_result}")
        assert list_tagged_result.get("success") is True
        assert isinstance(list_tagged_result.get("plans"), list)
        found_tagged_plan = False
        for plan in list_tagged_result.get("plans", []):
            if plan.get("name") == plan_name:
                found_tagged_plan = True
                assert "e2e" in plan.get("tags", [])
                assert "testing" in plan.get("tags", [])
                break
        assert found_tagged_plan, (
            f"Saved plan '{plan_name}' not found in list_tagged_result with tag 'e2e'"
        )

        # --- Cleanup ---
        logger.info(f"Cleaning up created plan files for '{plan_name}'...")
        if plan_file_path.exists():
            plan_file_path.unlink()
        if meta_file_path.exists():
            meta_file_path.unlink()

    @pytest.mark.asyncio
    async def test_execute_workflow_e2e(
        self, planning_agent_instance: PlanningAgent, real_mcp_host: MCPHost
    ):
        """Verify the full planning workflow E2E: LLM call (mocked) -> save_plan tool call."""
        host = real_mcp_host
        agent = planning_agent_instance
        user_message = "Generate an E2E test plan."
        plan_name = f"e2e_workflow_plan_{uuid.uuid4()}"
        tags = ["e2e", "workflow_test"]
        generated_plan_content = "Step 1: Setup E2E env.\nStep 2: Run workflow.\nStep 3: Assert file creation."
        plan_file_path = PLAN_SAVE_DIR / f"{plan_name}.txt"
        meta_file_path = PLAN_SAVE_DIR / f"{plan_name}.meta.json"

        # --- Mock the LLM Call within the workflow ---
        # We mock _make_llm_call because we don't want to hit the actual LLM API,
        # but we DO want to hit the actual save_plan tool via the host.
        mock_llm_response = MagicMock(spec=anthropic.types.Message)
        mock_llm_response.content = [
            anthropic.types.TextBlock(type="text", text=generated_plan_content)
        ]
        # Patch the method on the *instance* for this test
        agent._make_llm_call = AsyncMock(return_value=mock_llm_response)

        # --- Execute Workflow ---
        logger.info(f"Attempting to execute workflow for plan '{plan_name}'...")
        result = await agent.execute_workflow(
            user_message=user_message,
            host_instance=host,
            plan_name=plan_name,
            tags=tags,
            # anthropic_api_key is not needed here as _make_llm_call is mocked
        )
        logger.info(f"Execute workflow result: {result}")

        # --- Assertions ---
        assert result.get("error") is None, (
            f"Workflow returned error: {result.get('error')}"
        )
        assert result.get("final_output") is not None, "Workflow final_output is None"
        final_output = result.get("final_output", {})
        assert final_output.get("success") is True, (
            "Final output (save_plan result) indicates failure"
        )
        assert plan_name in final_output.get("message", "")

        # Verify workflow steps log (basic check)
        assert (
            len(result.get("workflow_steps", [])) >= 4
        )  # LLM Call, LLM Success, Tool Call, Tool Success
        assert result["workflow_steps"][0]["action"] == "LLM Call (Generate Plan)"
        assert result["workflow_steps"][1]["status"] == "Success"
        assert result["workflow_steps"][2]["action"] == "Tool Call (save_plan)"
        assert result["workflow_steps"][3]["status"] == "Success"

        # Check mocks
        agent._make_llm_call.assert_awaited_once()  # Ensure mocked LLM part was called

        # Check file system for actual file creation by the real planning server
        assert plan_file_path.exists(), (
            f"Plan file {plan_file_path} was not created by the server"
        )
        assert meta_file_path.exists(), (
            f"Meta file {meta_file_path} was not created by the server"
        )

        # --- Cleanup ---
        logger.info(f"Cleaning up created plan files for '{plan_name}'...")
        if plan_file_path.exists():
            plan_file_path.unlink()
        if meta_file_path.exists():
            meta_file_path.unlink()
