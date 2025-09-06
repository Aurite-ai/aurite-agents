"""
Test for Agent max_iterations handling.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from aurite.execution.mcp_host.mcp_host import MCPHost
from aurite.lib.components.agent.agent import Agent
from aurite.lib.models.config.components import AgentConfig, LLMConfig


@pytest.mark.anyio
async def test_agent_handles_none_max_iterations():
    """Test that Agent handles None max_iterations gracefully."""

    # Create a mock AgentConfig with max_iterations set to None
    agent_config = AgentConfig(
        name="test_agent",
        type="agent",
        max_iterations=None,  # Explicitly set to None to trigger the bug
    )

    # Create a mock LLMConfig
    llm_config = LLMConfig(
        name="test_llm",
        type="llm",
        provider="openai",
        model="gpt-4",
        api_key_env_var="OPENAI_API_KEY",  # Add required parameter
    )

    # Create a mock MCPHost
    mock_host = Mock(spec=MCPHost)
    mock_host.get_formatted_tools = Mock(return_value=[])

    # Create initial messages
    initial_messages = [{"role": "user", "content": "Hello"}]

    # Create the Agent - this should not raise an error
    agent = Agent(
        agent_config=agent_config,
        base_llm_config=llm_config,
        host_instance=mock_host,
        initial_messages=initial_messages,
    )

    # Mock the turn processor to return a final response immediately
    with patch.object(agent, "_create_turn_processor") as mock_create_processor:
        mock_processor = Mock()
        mock_processor.process_turn = AsyncMock(
            return_value=(
                Mock(model_dump=lambda exclude_none=True: {"role": "assistant", "content": "Hi"}),
                [],
                True,  # is_final_turn
            )
        )
        mock_processor.get_last_llm_response = Mock(
            return_value=Mock(model_dump=lambda exclude_none=True: {"role": "assistant", "content": "Hi"})
        )
        mock_create_processor.return_value = mock_processor

        # This should not raise a TypeError about None not being a valid argument for range()
        result = await agent.run_conversation()

        assert result.status == "success"
        assert result.final_response is not None


@pytest.mark.anyio
async def test_agent_uses_default_max_iterations():
    """Test that Agent uses the default max_iterations when not specified."""

    # Create a mock AgentConfig without specifying max_iterations
    agent_config = AgentConfig(
        name="test_agent",
        type="agent",
        # max_iterations not specified, should use default of 50
    )

    # Create a mock LLMConfig
    llm_config = LLMConfig(
        name="test_llm",
        type="llm",
        provider="openai",
        model="gpt-4",
        api_key_env_var="OPENAI_API_KEY",  # Add required parameter
    )

    # Create a mock MCPHost
    mock_host = Mock(spec=MCPHost)
    mock_host.get_formatted_tools = Mock(return_value=[])

    # Create initial messages
    initial_messages = [{"role": "user", "content": "Hello"}]

    # Create the Agent
    agent = Agent(
        agent_config=agent_config,
        base_llm_config=llm_config,
        host_instance=mock_host,
        initial_messages=initial_messages,
    )

    # The agent should have max_iterations set to 50 (the default)
    assert agent.config.max_iterations == 50

    # Mock the turn processor to never return a final response
    with patch.object(agent, "_create_turn_processor") as mock_create_processor:
        mock_processor = Mock()
        mock_processor.process_turn = AsyncMock(
            return_value=(
                None,
                [],
                False,  # never final turn
            )
        )
        mock_processor.get_last_llm_response = Mock(
            return_value=Mock(model_dump=lambda exclude_none=True: {"role": "assistant", "content": "Continuing..."})
        )
        mock_create_processor.return_value = mock_processor

        # Run the conversation - it should hit max iterations
        result = await agent.run_conversation()

        assert result.status == "max_iterations_reached"
        assert result.error_message is not None
        assert "50 iterations" in result.error_message
        # Should have been called 50 times
        assert mock_create_processor.call_count == 50
