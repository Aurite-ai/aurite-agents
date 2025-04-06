"""
End-to-end tests for the Agent class, involving real MCPHost and client servers.
"""

import os
import pytest
import asyncio
from pathlib import Path

# Imports from the project
from src.host.models import AgentConfig, HostConfig, ClientConfig
from src.agents.agent import Agent
from src.host.host import MCPHost

# Assume the basic echo server is available for testing
# Adjust path relative to aurite-mcp directory
EXAMPLE_SERVER_PATH = Path("examples/basic/test_mcp_server.py")

# --- Fixtures ---


@pytest.fixture(scope="module")
def event_loop():
    """Ensure the event loop is available for async fixtures."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def real_mcp_host() -> MCPHost:
    """
    Sets up and tears down a real MCPHost instance connected to the example echo server.
    """
    if not EXAMPLE_SERVER_PATH.exists():
        pytest.skip(f"Example server not found at {EXAMPLE_SERVER_PATH}")

    # Define configuration for the host and the echo client
    client_config = ClientConfig(
        client_id="echo_server_e2e",
        server_path=EXAMPLE_SERVER_PATH.resolve(),  # Use absolute path
        roots=[],  # No roots needed for basic echo server
        capabilities=["tools"],  # Echo server provides tools
        timeout=15.0,  # Increase timeout for real server startup
    )
    host_config = HostConfig(name="E2E_Test_Host", clients=[client_config])

    # Initialize the host
    host = MCPHost(config=host_config)
    await host.initialize()  # This starts the client process

    yield host  # Provide the initialized host to the test

    # Teardown: Shutdown the host and its clients
    await host.shutdown()


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

        assert "error" not in result  # Should not have an error key if successful
        assert (
            len(result["tool_uses"]) == 0
        )  # No tool use expected for "Briefly say hello."

        # We can't easily assert the *input* to the real LLM call without more complex interception,
        # but the previous mocked tests verified parameter handling.

    # TODO: Add e2e test that triggers a real tool call (e.g., echo) via the LLM (mocked response requesting tool)
    # TODO: Add e2e test with a real LLM call (requires API key and careful setup/cost consideration)
