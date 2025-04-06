"""
End-to-end tests for the Agent class, involving real MCPHost and client servers.
"""

import os
import pytest
import asyncio

# Imports from the project
from src.host.models import AgentConfig
from src.agents.agent import Agent
from src.host.host import MCPHost

# Import fixtures explicitly for discovery


# --- Fixtures ---


@pytest.fixture(scope="module")
def event_loop():
    """Ensure the event loop is available for async fixtures."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# real_mcp_host fixture moved to tests/fixtures/host_fixtures.py


@pytest.fixture
def e2e_agent_config(real_mcp_host) -> AgentConfig:
    """Provides an AgentConfig linked to the real HostConfig."""
    # We use the config *from* the initialized host fixture
    return AgentConfig(
        name="E2E_Test_Agent",
        host=real_mcp_host._config,  # Link to the actual config used by the host
        # Use default LLM params for this test
    )


# --- Test Class ---


@pytest.mark.e2e  # Mark as an end-to-end test
class TestAgentE2E:
    """End-to-end tests for the Agent class."""

    # Skip this test if the Anthropic API key is not available in the environment
    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="Requires ANTHROPIC_API_KEY environment variable",
    )
    @pytest.mark.xfail(reason="Known async teardown issue in real_mcp_host fixture")
    @pytest.mark.asyncio
    async def test_agent_e2e_basic_execution_real_llm(
        self, e2e_agent_config: AgentConfig, real_mcp_host: MCPHost
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
            result = await agent.execute(
                user_message=user_message,
                host_instance=real_mcp_host,  # Pass the real host instance
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

        assert "error" not in result  # Should not have an error key if successful
        assert (
            len(result["tool_uses"]) == 0
        )  # No tool use expected for "Briefly say hello."

        # We can't easily assert the *input* to the real LLM call without more complex interception,
        # but the previous mocked tests verified parameter handling.

    # TODO: Add e2e test that triggers a real tool call (e.g., echo) via the LLM (mocked response requesting tool)
    # TODO: Add e2e test with a real LLM call (requires API key and careful setup/cost consideration)
