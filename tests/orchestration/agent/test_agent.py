"""
End-to-end tests for the Agent class, involving real MCPHost and client servers.
"""

import os
import pytest
# import asyncio # Removed

# Imports from the project
from src.host.models import AgentConfig
from src.agents.agent import Agent
from src.host_manager import HostManager  # Import HostManager

# Import fixtures explicitly for discovery


# --- Fixtures ---


# Removed module-scoped event_loop fixture - let pytest-anyio handle it


# real_mcp_host fixture moved to tests/fixtures/host_fixtures.py


@pytest.fixture
def e2e_agent_config(host_manager: HostManager) -> AgentConfig:
    """Provides an AgentConfig linked to the HostManager's HostConfig."""
    # Use the config *from* the initialized host_manager's host
    if not host_manager or not host_manager.host or not host_manager.host._config:
        pytest.fail("HostManager fixture did not provide a valid host config")
    return AgentConfig(
        name="E2E_Test_Agent",
        host=host_manager.host._config,  # Link to the host's config
        # Use default LLM params for this test
    )


# --- Test Class ---


# Mark all tests in this module as orchestration, e2e and use anyio backend
pytestmark = [
    pytest.mark.orchestration,  # Added orchestration marker
    pytest.mark.e2e,
    pytest.mark.anyio,
]


class TestAgentE2E:
    """End-to-end tests for the Agent class."""

    # Skip this test if the Anthropic API key is not available in the environment
    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="Requires ANTHROPIC_API_KEY environment variable",
    )
    # @pytest.mark.asyncio # Removed - covered by module-level pytestmark
    async def test_agent_e2e_basic_execution_real_llm(
        self, e2e_agent_config: AgentConfig, host_manager: HostManager
    ):
        """
        Test basic agent execution with a real host/client and real LLM call.
        Verifies agent setup, host interaction, LLM call success, and basic response structure.
        NOTE: This test makes a real API call to Anthropic.
        """
        agent = Agent(config=e2e_agent_config)

        # Execute the agent - NO MOCKING of Anthropic client
        user_message = "Briefly say hello."  # Keep it simple to minimize tokens
        try:
            result = await agent.execute_agent(
                user_message=user_message,
                host_instance=host_manager.host,  # Pass the host from host_manager
            )
        except Exception as e:
            pytest.fail(f"Agent execution failed with real LLM call: {e}")

        # Assertions
        assert "conversation" in result
        assert "final_response" in result
        assert result["final_response"] is not None  # Should have a response object
        # Check the structure of the real response (adapt as needed based on Anthropic SDK)
        assert hasattr(result["final_response"], "content")
        assert isinstance(result["final_response"].content, list)
        assert len(result["final_response"].content) > 0
        assert hasattr(result["final_response"].content[0], "type")
        assert result["final_response"].content[0].type == "text"
        assert hasattr(result["final_response"].content[0], "text")
        assert isinstance(result["final_response"].content[0].text, str)
        print(
            f"Real LLM Response Text: {result['final_response'].content[0].text}"
        )  # Print for info

        # Cannot easily assert on call_args for real LLM call, but we can check the result structure
        # TODO: Add assertion here if we can intercept/log the args passed to agent.execute's LLM call

        assert result.get("error") is None # Check that the error value is None on success
        assert (
            len(result["tool_uses"]) == 0
        )  # No tool use expected for "Briefly say hello."

        # We can't easily assert the *input* to the real LLM call without more complex interception,
        # but the previous mocked tests verified parameter handling.

    # TODO: Add e2e test that triggers a real tool call (e.g., echo) via the LLM (mocked response requesting tool)
    # TODO: Add e2e test with a real LLM call (requires API key and careful setup/cost consideration)
