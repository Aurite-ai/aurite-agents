"""
Tests for the Agent class implementation.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock  # Use AsyncMock for async methods

# Use relative imports from the project root (aurite-mcp)
from src.host.models import AgentConfig, HostConfig, ClientConfig, RootConfig
from src.agents.agent import Agent
from src.host.host import MCPHost
from src.host.resources import ToolManager, PromptManager


# --- Fixtures (Step 5.4) ---


@pytest.fixture
def minimal_agent_config() -> AgentConfig:
    """Provides a minimal AgentConfig."""
    return AgentConfig(name="TestAgentMinimal")


@pytest.fixture
def agent_config_with_llm_params() -> AgentConfig:
    """Provides an AgentConfig with specific LLM parameters."""
    return AgentConfig(
        name="TestAgentLLM",
        model="test-model-override",
        temperature=0.5,
        max_tokens=100,
        system_prompt="Test system prompt override.",
    )


@pytest.fixture
def mock_host_config() -> HostConfig:
    """Provides a mock HostConfig."""
    # Define a simple mock host config if needed for AgentConfig initialization
    return HostConfig(
        name="MockHost", clients=[]
    )  # Keep clients empty for simplicity here


@pytest.fixture
def agent_config_with_mock_host(mock_host_config) -> AgentConfig:
    """Provides an AgentConfig linked to a mock HostConfig."""
    return AgentConfig(name="TestAgentWithHostCfg", host=mock_host_config)


@pytest.fixture
def mock_mcp_host() -> Mock:
    """Provides a mock MCPHost instance with mocked managers."""
    host = Mock(spec=MCPHost)
    host.tools = Mock(spec=ToolManager)
    host.prompts = Mock(spec=PromptManager)
    # Mock the methods that will be called by Agent.execute
    host.tools.format_tools_for_llm = Mock(
        return_value=[
            {"name": "mock_tool", "description": "A mock tool", "input_schema": {}}
        ]
    )
    host.tools.execute_tool = AsyncMock(
        return_value={"result": "Mock tool executed successfully"}
    )  # Must be AsyncMock
    host.tools.create_tool_result_blocks = Mock(
        return_value={
            "type": "tool_result",
            "tool_use_id": "mock_id",
            "content": [{"type": "text", "text": "Mock tool result"}],
        }
    )
    return host


# Mock for Anthropic client
@pytest.fixture
def mock_anthropic_client():
    """Provides a mock Anthropic client."""
    with patch("anthropic.Anthropic") as mock_client_constructor:
        mock_client_instance = Mock()
        # Mock the messages.create method
        mock_response = Mock()
        # Simulate the structure of response content blocks (e.g., TextBlock)
        mock_text_block = Mock()
        mock_text_block.type = "text"
        mock_text_block.text = "Mock LLM response"
        mock_response.content = [
            mock_text_block
        ]  # List containing the mock block object
        mock_response.stop_reason = "end_turn"
        mock_client_instance.messages.create.return_value = mock_response
        mock_client_constructor.return_value = mock_client_instance
        yield mock_client_instance  # Yield the instance for potential assertions


# --- Test Class (Step 5.2) ---


class TestAgent:
    """Test suite for the Agent class."""

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
            await agent.execute(user_message="Test message", host_instance=None)

    @pytest.mark.asyncio
    async def test_execute_requires_mcp_host_instance(self, minimal_agent_config):
        """Test execute raises TypeError if host_instance is not MCPHost."""
        agent = Agent(config=minimal_agent_config)
        with pytest.raises(
            TypeError, match="host_instance must be an instance of MCPHost"
        ):
            await agent.execute(
                user_message="Test message", host_instance=Mock()
            )  # Pass a generic Mock

    @pytest.mark.asyncio
    async def test_execute_parameter_prioritization(
        self, agent_config_with_llm_params, mock_mcp_host, mock_anthropic_client
    ):
        """Verify agent LLM params override defaults when calling Anthropic."""
        agent = Agent(config=agent_config_with_llm_params)
        await agent.execute(user_message="Test message", host_instance=mock_mcp_host)

        # Assert that anthropic.messages.create was called with agent's config values
        mock_anthropic_client.messages.create.assert_called_once()
        call_args, call_kwargs = mock_anthropic_client.messages.create.call_args
        assert call_kwargs.get("model") == agent_config_with_llm_params.model
        assert (
            call_kwargs.get("temperature") == agent_config_with_llm_params.temperature
        )
        assert call_kwargs.get("max_tokens") == agent_config_with_llm_params.max_tokens
        assert call_kwargs.get("system") == agent_config_with_llm_params.system_prompt

    @pytest.mark.asyncio
    async def test_execute_parameter_defaults(
        self, minimal_agent_config, mock_mcp_host, mock_anthropic_client
    ):
        """Verify default LLM params are used when not in AgentConfig."""
        agent = Agent(config=minimal_agent_config)
        await agent.execute(user_message="Test message", host_instance=mock_mcp_host)

        # Assert that anthropic.messages.create was called with default values
        mock_anthropic_client.messages.create.assert_called_once()
        call_args, call_kwargs = mock_anthropic_client.messages.create.call_args
        assert call_kwargs.get("model") == "claude-3-opus-20240229"  # Default
        assert call_kwargs.get("temperature") == 0.7  # Default
        assert call_kwargs.get("max_tokens") == 4096  # Default
        assert call_kwargs.get("system") == "You are a helpful assistant."  # Default

    @pytest.mark.asyncio
    async def test_execute_tool_call_flow(
        self, minimal_agent_config, mock_mcp_host, mock_anthropic_client
    ):
        """Test the full flow when the LLM requests a tool call."""
        agent = Agent(config=minimal_agent_config)

        # Configure the mock Anthropic response to request a tool call
        tool_use_id = "tool_abc123"
        tool_name = "mock_tool"
        tool_input = {"arg1": "value1"}
        mock_llm_response_with_tool = Mock()
        # Simulate ToolUseBlock structure
        mock_tool_use_block = Mock()
        mock_tool_use_block.type = "tool_use"
        mock_tool_use_block.id = tool_use_id
        mock_tool_use_block.name = tool_name
        mock_tool_use_block.input = tool_input
        mock_llm_response_with_tool.content = [
            mock_tool_use_block
        ]  # Use the mock block object
        mock_llm_response_with_tool.stop_reason = "tool_use"

        # Second response after tool result is sent
        mock_llm_final_response = Mock()
        # Simulate TextBlock structure
        mock_final_text_block = Mock()
        mock_final_text_block.type = "text"
        mock_final_text_block.text = "Final response after tool use."
        mock_llm_final_response.content = [
            mock_final_text_block
        ]  # Use the mock block object
        mock_llm_final_response.stop_reason = "end_turn"

        # Set the side_effect for multiple calls
        mock_anthropic_client.messages.create.side_effect = [
            mock_llm_response_with_tool,
            mock_llm_final_response,
        ]

        # Mock the tool result formatting
        mock_tool_result_block = {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": [{"type": "text", "text": "Mock tool result content"}],
        }
        mock_mcp_host.tools.create_tool_result_blocks.return_value = (
            mock_tool_result_block
        )

        # Execute the agent
        result = await agent.execute(
            user_message="Use the mock tool", host_instance=mock_mcp_host
        )

        # Assertions
        # 1. Anthropic client called twice
        assert mock_anthropic_client.messages.create.call_count == 2

        # 2. Host's execute_tool was called with correct args
        mock_mcp_host.tools.execute_tool.assert_awaited_once_with(
            tool_name=tool_name, arguments=tool_input
        )

        # 3. Host's create_tool_result_blocks was called
        mock_mcp_host.tools.create_tool_result_blocks.assert_called_once()
        # We can add more specific checks on args if needed

        # 4. Second call to Anthropic included the tool result message
        second_call_args, second_call_kwargs = (
            mock_anthropic_client.messages.create.call_args_list[1]
        )
        messages = second_call_kwargs.get("messages", [])
        assert len(messages) == 3  # user -> assistant (tool_use) -> user (tool_result)
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
