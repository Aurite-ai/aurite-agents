"""
Tests for the Agent class implementation.
"""

import pytest
from unittest.mock import Mock, patch  # Use AsyncMock for async methods

# Use relative imports from the project root (aurite-mcp)
from src.agents.agent import Agent

# Import the new mock utility
from tests.mocks.mock_anthropic import get_mock_anthropic_client

# Import fixtures explicitly (pytest doesn't auto-discover from non-conftest files)


# --- Test Class ---


@pytest.mark.unit
class TestAgent:
    """Test suite for the Agent class (Unit/Integration with mocks)."""

    # --- Test Cases (Step 5.3) ---

    def test_agent_initialization_minimal(self, minimal_agent_config):
        """Test Agent initialization with minimal config."""
        agent = Agent(config=minimal_agent_config)
        assert agent.config == minimal_agent_config
        assert agent.config.name == "TestAgentMinimal"

    def test_agent_initialization_with_llm_params(self, agent_config_with_llm_params):
        """Test Agent initialization with LLM parameters."""
        agent = Agent(config=agent_config_with_llm_params)
        assert agent.config == agent_config_with_llm_params
        assert agent.config.model == "test-model-override"

    def test_agent_initialization_with_host_config(self, agent_config_with_mock_host):
        """Test Agent initialization with linked HostConfig."""
        agent = Agent(config=agent_config_with_mock_host)
        assert agent.config == agent_config_with_mock_host
        assert agent.config.host is not None
        assert agent.config.host.name == "MockHost"

    def test_agent_initialization_invalid_config(self):
        """Test Agent initialization raises TypeError with invalid config type."""
        with pytest.raises(
            TypeError, match="config must be an instance of AgentConfig"
        ):
            Agent(config={"name": "Invalid"})  # Pass a dict instead of AgentConfig

    @pytest.mark.asyncio
    async def test_execute_requires_host(self, minimal_agent_config):
        """Test execute raises ValueError if host_instance is missing."""
        agent = Agent(config=minimal_agent_config)
        with pytest.raises(
            ValueError, match="MCPHost instance is required for execution"
        ):
            await agent.execute_agent(user_message="Test message", host_instance=None)

    @pytest.mark.asyncio
    async def test_execute_requires_mcp_host_instance(self, minimal_agent_config):
        """Test execute raises TypeError if host_instance is not MCPHost."""
        agent = Agent(config=minimal_agent_config)
        with pytest.raises(
            TypeError, match="host_instance must be an instance of MCPHost"
        ):
            await agent.execute_agent(
                user_message="Test message", host_instance=Mock()
            )  # Pass a generic Mock

    @pytest.mark.asyncio
    # Remove mock_anthropic_client fixture, use patch instead
    async def test_execute_parameter_prioritization(
        self, agent_config_with_llm_params, mock_mcp_host
    ):
        """Verify agent LLM params override defaults when calling Anthropic."""
        agent = Agent(config=agent_config_with_llm_params)
        # Patch the client within the agent's execution scope
        with patch(
            "src.agents.agent.anthropic.Anthropic",
            return_value=get_mock_anthropic_client(),
        ) as mock_constructor:
            mock_client = mock_constructor.return_value  # Get the mock client instance
            await agent.execute_agent(
                user_message="Test message", host_instance=mock_mcp_host
            )

            # Assert that anthropic.messages.create was called with agent's config values
            mock_client.messages.create.assert_called_once()
            call_args, call_kwargs = mock_client.messages.create.call_args
            assert call_kwargs.get("model") == agent_config_with_llm_params.model
            assert (
                call_kwargs.get("temperature")
                == agent_config_with_llm_params.temperature
            )
        assert call_kwargs.get("max_tokens") == agent_config_with_llm_params.max_tokens
        assert call_kwargs.get("system") == agent_config_with_llm_params.system_prompt

    @pytest.mark.asyncio
    # Remove mock_anthropic_client fixture, use patch instead
    async def test_execute_parameter_defaults(
        self, minimal_agent_config, mock_mcp_host
    ):
        """Verify default LLM params are used when not in AgentConfig."""
        agent = Agent(config=minimal_agent_config)
        with patch(
            "src.agents.agent.anthropic.Anthropic",
            return_value=get_mock_anthropic_client(),
        ) as mock_constructor:
            mock_client = mock_constructor.return_value
            await agent.execute_agent(
                user_message="Test message", host_instance=mock_mcp_host
            )

            # Assert that anthropic.messages.create was called with default values
            mock_client.messages.create.assert_called_once()
            call_args, call_kwargs = mock_client.messages.create.call_args
            assert call_kwargs.get("model") == "claude-3-opus-20240229"  # Default
            assert call_kwargs.get("temperature") == 0.7  # Default
        assert call_kwargs.get("max_tokens") == 4096  # Default
        assert call_kwargs.get("system") == "You are a helpful assistant."  # Default

    @pytest.mark.asyncio
    # Remove mock_anthropic_client fixture, use patch instead
    async def test_execute_tool_call_flow(self, minimal_agent_config, mock_mcp_host):
        """Test the full flow when the LLM requests a tool call."""
        agent = Agent(config=minimal_agent_config)

        # Define the tool call structure for the mock utility
        tool_use_id = "tool_abc123"
        tool_name = "mock_tool"
        tool_input = {"arg1": "value1"}
        tool_calls_spec = [{"id": tool_use_id, "name": tool_name, "input": tool_input}]

        # Create mocks using the utility
        mock_client_tool_request = get_mock_anthropic_client(tool_calls=tool_calls_spec)
        mock_client_final_response = get_mock_anthropic_client(
            response_text="Final response after tool use."
        )

        # Get the response objects *from the mocks* to assert against later
        # Note: The mock utility already configures the return_value for messages.create
        mock_llm_response_with_tool = (
            mock_client_tool_request.messages.create.return_value
        )
        mock_llm_final_response = (
            mock_client_final_response.messages.create.return_value
        )

        # Patch the constructor once to return a single mock client instance
        with patch("src.agents.agent.anthropic.Anthropic") as mock_constructor:
            # Get the single mock client instance
            mock_client = (
                get_mock_anthropic_client()
            )  # Use default simple response initially
            mock_constructor.return_value = mock_client

            # Configure the side_effect on the *create method* of the instance
            mock_client.messages.create.side_effect = [
                mock_llm_response_with_tool,  # First call returns tool request
                mock_llm_final_response,  # Second call returns final text
            ]

            # Mock the tool result formatting (remains the same)
            mock_tool_result_block = {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": [{"type": "text", "text": "Mock tool result content"}],
            }
            mock_mcp_host.tools.create_tool_result_blocks.return_value = (
                mock_tool_result_block
            )

            # Execute the agent
            result = await agent.execute_agent(
                user_message="Use the mock tool", host_instance=mock_mcp_host
            )

            # Assertions
            # 1. Anthropic client's create method called twice
            assert mock_client.messages.create.call_count == 2

            # 2. Host's execute_tool was called with correct args (remains the same)
            mock_mcp_host.tools.execute_tool.assert_awaited_once_with(
                tool_name=tool_name, arguments=tool_input
            )

            # 3. Host's create_tool_result_blocks was called
            mock_mcp_host.tools.create_tool_result_blocks.assert_called_once()
            # We can add more specific checks on args if needed

            # 4. Second call to Anthropic included the tool result message
            #    Get args from the single mock client's create method history
            second_call_args, second_call_kwargs = (
                mock_client.messages.create.call_args_list[1]
            )
            messages = second_call_kwargs.get("messages", [])
            assert (
                len(messages) == 3
            )  # user -> assistant (tool_use) -> user (tool_result)
            assert messages[2]["role"] == "user"
            assert messages[2]["content"] == [
                mock_tool_result_block
            ]  # Check content matches formatted block

            # 5. Final response is correct
            assert result["final_response"] == mock_llm_final_response
            assert result["tool_uses"] == [
                {"id": tool_use_id, "name": tool_name, "input": tool_input}
            ]  # Check returned tool uses

    # TODO: Add tests for error handling (e.g., tool execution fails, Anthropic API fails)
    # TODO: Add tests for history inclusion (`include_history=True`) when implemented
