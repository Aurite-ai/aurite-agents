"""
Tests for the Agent class implementation.
"""

import pytest
from unittest.mock import Mock, patch  # Use AsyncMock for async methods
import anthropic  # Add import
from anthropic.types import ToolUseBlock  # Add import

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

    # Removed obsolete test_agent_initialization_with_host_config

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
        # Patch the client constructor *before* initializing the agent
        with patch(
            "src.agents.agent.anthropic.Anthropic",
            # Configure the mock client if needed (default mock is usually fine for checking args)
            return_value=get_mock_anthropic_client(),
        ) as mock_constructor:
            # Instantiate Agent *inside* the patch context
            agent = Agent(config=agent_config_with_llm_params)
            # The agent.anthropic_client is now the mock instance
            mock_client = agent.anthropic_client

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
        # Patch the client constructor *before* initializing the agent
        with patch(
            "src.agents.agent.anthropic.Anthropic",
            # Configure the mock client if needed
            return_value=get_mock_anthropic_client(),
        ) as mock_constructor:
            # Instantiate Agent *inside* the patch context
            agent = Agent(config=minimal_agent_config)
            mock_client = agent.anthropic_client  # Get the mock from the agent instance

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

    @pytest.mark.parametrize(
        "agent_config_fixture, filter_ids_to_pass, expected_filter_in_host_call",
        [
            (
                "minimal_agent_config",
                None,
                None,
            ),  # Test case 1: No filter passed to execute_agent
            (
                "minimal_agent_config",
                ["client-x"],
                ["client-x"],
            ),  # Test case 2: Filter passed to execute_agent
            # ("agent_config_filtered", None, None), # Test case 3: Agent config filter is ignored if None passed to execute_agent
            (
                "agent_config_filtered",
                ["client-y"],
                ["client-y"],
            ),  # Test case 4: Filter passed to execute_agent overrides agent config filter
        ],
    )
    @pytest.mark.asyncio
    async def test_execute_tool_call_flow_with_filtering(
        self,
        request,
        agent_config_fixture,
        filter_ids_to_pass,
        expected_filter_in_host_call,
        mock_mcp_host,
    ):
        """
        Test the full flow when the LLM requests a tool call, verifying filter_client_ids pass-through.
        Uses parametrization to cover different filter scenarios.
        """
        # Get the actual agent_config fixture value using request.getfixturevalue
        agent_config = request.getfixturevalue(agent_config_fixture)

        # Define the tool call structure for the mock utility
        tool_use_id = f"tool_{agent_config_fixture}_{filter_ids_to_pass}"  # Make unique per test case
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
        # Get the response objects *from the mocks* to assert against later
        mock_llm_response_with_tool: anthropic.types.Message = (
            mock_client_tool_request.messages.create.return_value
        )
        # Extract the actual tool_use_id from the first mock response content
        actual_tool_use_id = None
        for block in mock_llm_response_with_tool.content:
            if isinstance(block, ToolUseBlock):
                actual_tool_use_id = block.id
                break
        assert actual_tool_use_id is not None, (
            "Mock response did not contain a ToolUseBlock"
        )

        mock_llm_final_response = (
            mock_client_final_response.messages.create.return_value
        )

        # Patch the constructor once to return a single mock client instance
        with patch("src.agents.agent.anthropic.Anthropic") as mock_constructor:
            # Instantiate Agent *inside* the patch context using the parametrized config
            agent = Agent(config=agent_config)
            mock_client = agent.anthropic_client  # Get the mock from the agent instance
            mock_constructor.return_value = (
                mock_client  # Ensure the patch uses this instance if needed by others
            )

            # Configure the side_effect on the *create method* of the instance
            mock_client.messages.create.side_effect = [
                mock_llm_response_with_tool,  # First call returns tool request
                mock_llm_final_response,  # Second call returns final text
            ]

            # Mock the tool result formatting, using the *actual* tool_use_id
            mock_tool_result_content = "Mock tool result content"  # Example content
            mock_tool_result_block = {
                "type": "tool_result",
                "tool_use_id": actual_tool_use_id,  # Use the extracted ID
                "content": [{"type": "text", "text": mock_tool_result_content}],
            }
            # Configure the mock host's create_tool_result_blocks to return this
            mock_mcp_host.tools.create_tool_result_blocks.return_value = (
                mock_tool_result_block
            )

            # Execute the agent, passing the filter_ids_to_pass from parametrization
            result = await agent.execute_agent(
                user_message="Use the mock tool",
                host_instance=mock_mcp_host,
                filter_client_ids=filter_ids_to_pass,  # Pass the filter
            )

            # Assertions
            # 1. Anthropic client's create method called twice
            assert mock_client.messages.create.call_count == 2

            # 2. Host's execute_tool was called with correct args, including the filter
            # Note: We assert on mock_mcp_host.execute_tool because that's the mock object
            # passed into agent.execute_agent as host_instance.
            mock_mcp_host.execute_tool.assert_awaited_once_with(
                tool_name=tool_name,
                arguments=tool_input,
                filter_client_ids=expected_filter_in_host_call,  # Assert filter pass-through
            )

            # 3. Host's create_tool_result_blocks was called (via host.tools)
            mock_mcp_host.tools.create_tool_result_blocks.assert_called_once()
            # We can add more specific checks on args if needed

            # 4. Second call to Anthropic included the tool result message
            #    Get args from the single mock client's create method history
            second_call_args, second_call_kwargs = (
                mock_client.messages.create.call_args_list[
                    1
                ]  # Index 1 for the second call
            )
            messages_for_second_call = second_call_kwargs.get("messages", [])
            assert len(messages_for_second_call) == 3, (
                "Second call should have 3 messages"
            )
            assert messages_for_second_call[0]["role"] == "user"
            assert (
                messages_for_second_call[1]["role"] == "assistant"
            )  # Tool request turn
            assert messages_for_second_call[2]["role"] == "user"  # Tool result turn
            assert messages_for_second_call[2]["content"] == [mock_tool_result_block], (
                "Tool result block in second call messages mismatch"
            )

            # 5. Final response is correct
            assert result["final_response"] == mock_llm_final_response
            assert result["tool_uses"] == [
                {"id": tool_use_id, "name": tool_name, "input": tool_input}
            ]  # Check returned tool uses

    # TODO: Add tests for error handling (e.g., tool execution fails, Anthropic API fails)
    # TODO: Add tests for history inclusion (`include_history=True`) when implemented
