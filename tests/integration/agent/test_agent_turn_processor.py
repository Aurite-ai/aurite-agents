"""
Integration tests for the AgentTurnProcessor.
"""

from unittest.mock import AsyncMock

import pytest
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)

from aurite.components.agents.agent_turn_processor import AgentTurnProcessor
from aurite.components.llm.providers.litellm_client import LiteLLMClient
from aurite.config.config_models import AgentConfig
from aurite.host.host import MCPHost

# --- Fixtures ---


@pytest.fixture
def mock_llm_client() -> AsyncMock:
    """Mocks the LiteLLMClient with an AsyncMock."""
    return AsyncMock(spec=LiteLLMClient)


@pytest.fixture
def mock_host() -> AsyncMock:
    """Mocks the MCPHost with an AsyncMock."""
    return AsyncMock(spec=MCPHost)


@pytest.fixture
def basic_agent_config() -> AgentConfig:
    """Provides a basic AgentConfig."""
    return AgentConfig(name="test_agent", llm_config_id="test_llm")


# --- Test Cases ---


@pytest.mark.anyio
async def test_process_turn_text_response(
    mock_llm_client: LiteLLMClient,
    mock_host: MCPHost,
    basic_agent_config: AgentConfig,
):
    """
    Tests a simple turn where the LLM returns a final text response.
    """
    # Arrange
    llm_response = ChatCompletionMessage(role="assistant", content="This is the final answer.", tool_calls=None)
    mock_llm_client.create_message.return_value = llm_response  # type: ignore

    processor = AgentTurnProcessor(
        config=basic_agent_config,
        llm_client=mock_llm_client,
        host_instance=mock_host,
        current_messages=[{"role": "user", "content": "Hi"}],
        tools_data=None,
        effective_system_prompt="You are a test agent.",
    )

    # Act
    final_response, tool_results, is_final = await processor.process_turn()

    # Assert
    assert is_final is True
    assert final_response is not None
    assert final_response.content == "This is the final answer."
    assert tool_results is None
    mock_llm_client.create_message.assert_awaited_once()  # type: ignore
    mock_host.call_tool.assert_not_awaited()  # type: ignore


@pytest.mark.anyio
async def test_process_turn_successful_tool_call(
    mock_llm_client: LiteLLMClient,
    mock_host: MCPHost,
    basic_agent_config: AgentConfig,
):
    """
    Tests a turn where the LLM requests a tool and the host executes it successfully.
    """
    # Arrange
    tool_call = ChatCompletionMessageToolCall(
        id="tool_123",
        function=Function(name="get_weather", arguments='{"location": "Boston"}'),
        type="function",
    )
    llm_response = ChatCompletionMessage(role="assistant", content=None, tool_calls=[tool_call])
    mock_llm_client.create_message.return_value = llm_response  # type: ignore
    mock_host.call_tool.return_value = {"temperature": "75F"}  # type: ignore

    processor = AgentTurnProcessor(
        config=basic_agent_config,
        llm_client=mock_llm_client,
        host_instance=mock_host,
        current_messages=[{"role": "user", "content": "Weather in Boston?"}],
        tools_data=[{"name": "get_weather", "input_schema": {}}],
        effective_system_prompt="You are a test agent.",
    )

    # Act
    final_response, tool_results, is_final = await processor.process_turn()

    # Assert
    assert is_final is False
    assert final_response is None
    assert tool_results is not None
    assert len(tool_results) == 1
    assert tool_results[0]["role"] == "tool"
    assert tool_results[0]["tool_call_id"] == "tool_123"
    assert '"temperature": "75F"' in tool_results[0]["content"]

    mock_llm_client.create_message.assert_awaited_once()  # type: ignore
    mock_host.call_tool.assert_awaited_once_with(  # type: ignore
        name="get_weather", args={"location": "Boston"}
    )


@pytest.mark.anyio
async def test_process_turn_failed_tool_call(
    mock_llm_client: LiteLLMClient,
    mock_host: MCPHost,
    basic_agent_config: AgentConfig,
):
    """
    Tests a turn where the host fails to execute a requested tool.
    """
    # Arrange
    tool_call = ChatCompletionMessageToolCall(
        id="tool_456",
        function=Function(name="get_stock_price", arguments='{"ticker": "XYZ"}'),
        type="function",
    )
    llm_response = ChatCompletionMessage(role="assistant", content=None, tool_calls=[tool_call])
    mock_llm_client.create_message.return_value = llm_response  # type: ignore
    mock_host.call_tool.side_effect = Exception("API unavailable")  # type: ignore

    processor = AgentTurnProcessor(
        config=basic_agent_config,
        llm_client=mock_llm_client,
        host_instance=mock_host,
        current_messages=[{"role": "user", "content": "Stock price for XYZ?"}],
        tools_data=[{"name": "get_stock_price", "input_schema": {}}],
        effective_system_prompt="You are a test agent.",
    )

    # Act
    final_response, tool_results, is_final = await processor.process_turn()

    # Assert
    assert is_final is False
    assert final_response is None
    assert tool_results is not None
    assert len(tool_results) == 1
    assert tool_results[0]["role"] == "tool"
    assert tool_results[0]["tool_call_id"] == "tool_456"
    assert "Error executing tool 'get_stock_price': API unavailable" in tool_results[0]["content"]

    mock_llm_client.create_message.assert_awaited_once()  # type: ignore
    mock_host.call_tool.assert_awaited_once_with(  # type: ignore
        name="get_stock_price", args={"ticker": "XYZ"}
    )
