"""
Integration tests for the Agent class, covering the full conversation loop.
"""

from unittest.mock import AsyncMock

import pytest
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageFunctionToolCall,
    Function,
)

from aurite.execution.mcp_host import MCPHost
from aurite.lib.components.agent.agent import Agent
from aurite.lib.components.llm.litellm_client import LiteLLMClient
from aurite.lib.models.config.components import AgentConfig, LLMConfig

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
def multi_turn_agent_config() -> AgentConfig:
    """Provides an AgentConfig for multi-turn tests."""
    return AgentConfig(name="multi_turn_agent", llm_config_id="test_llm")


@pytest.fixture
def base_llm_config() -> LLMConfig:
    """Provides a base LLMConfig."""
    return LLMConfig(name="test_llm", provider="anthropic", model="claude-3-haiku-20240307")


# --- Test Cases ---


@pytest.mark.anyio
async def test_agent_run_conversation_with_tool_use(
    mocker: AsyncMock,
    mock_host: AsyncMock,
    multi_turn_agent_config: AgentConfig,
    base_llm_config: LLMConfig,
):
    """
    Tests a full, multi-turn conversation where the agent uses a tool
    and then provides a final answer.
    """
    # --- Arrange ---

    # Turn 1: LLM asks to use a tool
    tool_call = ChatCompletionMessageFunctionToolCall(
        id="tool_abc",
        function=Function(name="get_user_info", arguments='{"user_id": "123"}'),
        type="function",
    )
    llm_response_turn_1 = ChatCompletionMessage(role="assistant", content=None, tool_calls=[tool_call])

    # Turn 2: LLM provides the final answer based on the tool result
    final_text_response = "The user's name is Alice."
    llm_response_turn_2 = ChatCompletionMessage(role="assistant", content=final_text_response, tool_calls=None)

    # Patch the LiteLLMClient to use our mock
    mock_llm_instance = AsyncMock(spec=LiteLLMClient)
    mock_llm_instance.create_message.side_effect = [
        llm_response_turn_1,
        llm_response_turn_2,
    ]
    mocker.patch("aurite.lib.components.agent.agent.LiteLLMClient", return_value=mock_llm_instance)

    # Configure the mock host to return a result for the tool call
    mock_host.get_formatted_tools.return_value = [{"name": "get_user_info", "input_schema": {}}]
    mock_host.call_tool.return_value = {"name": "Alice", "status": "active"}

    # --- Act ---

    # Initialize the agent
    agent = Agent(
        agent_config=multi_turn_agent_config,
        base_llm_config=base_llm_config,
        host_instance=mock_host,
        initial_messages=[{"role": "user", "content": "What is user 123's name?"}],
    )

    # Run the full conversation
    result = await agent.run_conversation()

    # --- Assert ---

    # Final Result Assertions
    assert result.status == "success"
    assert result.has_error is False
    assert result.error_message is None
    assert result.final_response is not None
    assert result.final_response.content == final_text_response

    # History Assertions
    history = result.conversation_history
    assert len(history) == 4  # user -> assistant(tool) -> tool -> assistant(final)

    # 1. User's initial message
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "What is user 123's name?"

    # 2. Assistant's tool call message
    assert history[1]["role"] == "assistant"
    assert history[1]["tool_calls"][0]["id"] == "tool_abc"
    assert history[1]["tool_calls"][0]["function"]["name"] == "get_user_info"

    # 3. The result from the tool
    assert history[2]["role"] == "tool"
    assert history[2]["tool_call_id"] == "tool_abc"
    assert '"name": "Alice"' in history[2]["content"]

    # 4. The final response from the assistant
    assert history[3]["role"] == "assistant"
    assert history[3]["content"] == final_text_response

    # Mock Call Assertions
    assert mock_llm_instance.create_message.call_count == 2
    mock_host.call_tool.assert_awaited_once_with(
        name="get_user_info", args={"user_id": "123"}, agent_config=multi_turn_agent_config
    )
