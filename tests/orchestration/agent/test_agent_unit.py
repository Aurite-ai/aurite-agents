"""
Unit tests for the Agent class.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch # Import patch

# Mark all tests in this module
pytestmark = [pytest.mark.orchestration, pytest.mark.unit, pytest.mark.anyio]


# Imports from the project
from unittest.mock import call # Import call for checking multiple args
from src.agents.agent import Agent, _serialize_content_blocks # Import helper too
from src.host.models import AgentConfig
from src.storage.db_manager import StorageManager # Import for type hint/mocking
from anthropic.types import Message, TextBlock # For mocking LLM response
import anthropic # Import the library for exception types

# Import shared fixtures

# --- Fixtures ---

# Removed local mock_mcp_host fixture - using shared one
# Removed local minimal_agent_config fixture - using shared one
# Removed local mock_anthropic_client fixture - using shared one


@pytest.fixture
def agent(minimal_agent_config: AgentConfig) -> Agent:  # Now uses shared fixture
    """Provides an Agent instance initialized with minimal config."""
    return Agent(config=minimal_agent_config)


# --- Test Class ---


class TestAgentUnit:
    """Unit tests for the Agent class."""

    @pytest.mark.asyncio
    async def test_execute_agent_success_no_tool_use(
        self,
        agent: Agent,
        mock_mcp_host: AsyncMock,
        mock_anthropic_client: MagicMock,  # Add mock client fixture
    ):
        """
        Test successful agent execution when the LLM response does not request tool use.
        """
        print("\n--- Running Test: test_execute_agent_success_no_tool_use ---")
        user_message = "Hello, world!"
        # Mock the LLM response (no tool use requested)
        mock_llm_response = MagicMock(spec=Message)
        mock_llm_response.content = [MagicMock(type="text", text="Hello back!")]
        mock_llm_response.stop_reason = "end_turn"
        # Mock the internal _make_llm_call method directly
        agent._make_llm_call = AsyncMock(return_value=mock_llm_response)

        # Execute the agent
        result = await agent.execute_agent(
            user_message=user_message,
            host_instance=mock_mcp_host,
        )

        print(f"Execution Result: {result}")

        # Assertions
        # Check the call on the mocked internal method
        agent._make_llm_call.assert_awaited_once()
        mock_mcp_host.get_formatted_tools.assert_called_once()  # Use synchronous assertion
        mock_mcp_host.execute_tool.assert_not_awaited()  # Ensure no tool execution was attempted

        assert "conversation" in result
        assert len(result["conversation"]) == 2  # User message + Assistant response
        assert result["conversation"][0]["role"] == "user"
        assert result["conversation"][0]["content"] == user_message
        assert result["conversation"][1]["role"] == "assistant"
        # Check the structure of the assistant's content in history
        assistant_content = result["conversation"][1]["content"]
        assert isinstance(assistant_content, list)
        assert len(assistant_content) == 1
        assert assistant_content[0].type == "text"
        assert assistant_content[0].text == "Hello back!"

        assert "final_response" in result
        assert (
            result["final_response"] == mock_llm_response
        )  # Should return the raw response object

        assert "tool_uses" in result
        assert len(result["tool_uses"]) == 0  # No tool use expected

        print("Assertions passed.")
        print("--- Test Finished: test_execute_agent_success_no_tool_use ---")

    @pytest.mark.asyncio
    async def test_execute_agent_success_with_tool_use(
        self,
        agent: Agent,
        mock_mcp_host: AsyncMock,
        minimal_agent_config: AgentConfig,
        mock_anthropic_client: MagicMock,  # Add mock client fixture
    ):
        """
        Test successful agent execution with a single tool use request.
        """
        print("\n--- Running Test: test_execute_agent_success_with_tool_use ---")
        user_message = "Use the echo tool to say 'testing'."
        tool_name = "echo_tool"
        tool_input = {"text": "testing"}
        tool_id = "tool_abc123"
        tool_result_content = "Tool Result: testing"

        # --- Mock LLM Response 1 (Requesting Tool Use) ---
        mock_tool_use_block = MagicMock()
        mock_tool_use_block.type = "tool_use"
        mock_tool_use_block.id = tool_id
        mock_tool_use_block.name = tool_name
        mock_tool_use_block.input = tool_input

        mock_llm_response_1 = MagicMock(spec=Message)
        # Content includes the tool use block
        mock_llm_response_1.content = [mock_tool_use_block]
        mock_llm_response_1.stop_reason = "tool_use"

        # --- Mock LLM Response 2 (Final Text Response after Tool Result) ---
        mock_llm_response_2 = MagicMock(spec=Message)
        mock_llm_response_2.content = [
            MagicMock(type="text", text="Okay, I echoed it.")
        ]
        mock_llm_response_2.stop_reason = "end_turn"

        # Mock the internal _make_llm_call method to return responses sequentially
        agent._make_llm_call = AsyncMock(
            side_effect=[mock_llm_response_1, mock_llm_response_2]
        )

        # --- Mock Host Tool Execution ---
        # Mock the execute_tool method on the host instance
        mock_mcp_host.execute_tool = AsyncMock(return_value=tool_result_content)
        # Mock the create_tool_result_blocks method (needs to be on host.tools)
        # We need a mock 'tools' attribute on the host mock first
        mock_mcp_host.tools = Mock()
        # Define the content of the block
        mock_tool_result_block_content = {
            "type": "tool_result",
            "tool_use_id": tool_id,
            "content": tool_result_content,
        }
        # Mock create_tool_result_blocks to return a list containing the block content
        mock_mcp_host.tools.create_tool_result_blocks = Mock(
            return_value=[mock_tool_result_block_content]
        )

        # --- Execute the agent ---
        result = await agent.execute_agent(
            user_message=user_message,
            host_instance=mock_mcp_host,
        )

        print(f"Execution Result: {result}")

        # --- Assertions ---
        # Check the call count on the mocked internal method
        assert agent._make_llm_call.await_count == 2
        # Tools fetched once (at the start)
        mock_mcp_host.get_formatted_tools.assert_called_once()  # Use synchronous assertion
        # Tool executed once
        mock_mcp_host.execute_tool.assert_awaited_once_with(
            tool_name=tool_name,
            arguments=tool_input,
            agent_config=minimal_agent_config,  # Ensure config is passed for filtering
        )
        # Tool result block created once
        mock_mcp_host.tools.create_tool_result_blocks.assert_called_once_with(
            tool_id, tool_result_content
        )

        # Conversation history check
        assert "conversation" in result
        assert (
            len(result["conversation"]) == 4
        )  # user -> assistant (tool) -> user (result) -> assistant (final)
        # 1. Initial User Message
        assert result["conversation"][0]["role"] == "user"
        assert result["conversation"][0]["content"] == user_message
        # 2. Assistant Tool Request
        assert result["conversation"][1]["role"] == "assistant"
        assert result["conversation"][1]["content"] == mock_llm_response_1.content
        # 3. User Tool Result (Content is a list containing the list returned by create_tool_result_blocks)
        assert result["conversation"][2]["role"] == "user"
        assert result["conversation"][2]["content"] == [
            [mock_tool_result_block_content]
        ]  # Expect list of lists
        # 4. Final Assistant Response
        assert result["conversation"][3]["role"] == "assistant"
        assert result["conversation"][3]["content"] == mock_llm_response_2.content

        # Final response check
        assert "final_response" in result
        assert result["final_response"] == mock_llm_response_2

        # Tool uses check (should reflect the *last* turn that had tool use)
        assert "tool_uses" in result
        assert len(result["tool_uses"]) == 1
        assert result["tool_uses"][0]["id"] == tool_id
        assert result["tool_uses"][0]["name"] == tool_name
        assert result["tool_uses"][0]["input"] == tool_input

        print("Assertions passed.")
        print("--- Test Finished: test_execute_agent_success_with_tool_use ---")

    @pytest.mark.asyncio
    async def test_execute_agent_success_with_multiple_tool_uses(
        self,
        agent: Agent,
        mock_mcp_host: AsyncMock,
        minimal_agent_config: AgentConfig,
        mock_anthropic_client: MagicMock,  # Add mock client fixture
    ):
        """
        Test successful agent execution with multiple tool use requests in one turn.
        """
        print(
            "\n--- Running Test: test_execute_agent_success_with_multiple_tool_uses ---"
        )
        user_message = "Use tool1 with 'A' and tool2 with 'B'."
        tool1_name = "tool1"
        tool1_input = {"param": "A"}
        tool1_id = "tool_111"
        tool1_result_content = "Result A"
        tool2_name = "tool2"
        tool2_input = {"param": "B"}
        tool2_id = "tool_222"
        tool2_result_content = "Result B"

        # --- Mock LLM Response 1 (Requesting Multiple Tools) ---
        # Configure mocks to return the string name when .name is accessed
        mock_tool_use_block_1 = MagicMock()
        mock_tool_use_block_1.type = "tool_use"
        mock_tool_use_block_1.id = tool1_id
        mock_tool_use_block_1.name = tool1_name  # Set the return value for .name
        mock_tool_use_block_1.input = tool1_input

        mock_tool_use_block_2 = MagicMock()
        mock_tool_use_block_2.type = "tool_use"
        mock_tool_use_block_2.id = tool2_id
        mock_tool_use_block_2.name = tool2_name  # Set the return value for .name
        mock_tool_use_block_2.input = tool2_input

        mock_llm_response_1 = MagicMock(spec=Message)
        mock_llm_response_1.content = [
            mock_tool_use_block_1,
            mock_tool_use_block_2,
        ]  # Two tool uses
        mock_llm_response_1.stop_reason = "tool_use"

        # --- Mock LLM Response 2 (Final Text Response after Tool Results) ---
        mock_llm_response_2 = MagicMock(spec=Message)
        mock_llm_response_2.content = [
            MagicMock(type="text", text="Okay, used both tools.")
        ]
        mock_llm_response_2.stop_reason = "end_turn"

        # Mock the internal _make_llm_call method to return responses sequentially
        agent._make_llm_call = AsyncMock(
            side_effect=[mock_llm_response_1, mock_llm_response_2]
        )

        # --- Mock Host Tool Execution ---
        # Mock execute_tool to return different results based on tool name
        async def mock_execute_tool_multi(*args, **kwargs):
            if kwargs.get("tool_name") == tool1_name:
                return tool1_result_content
            elif kwargs.get("tool_name") == tool2_name:
                return tool2_result_content
            else:
                raise ValueError("Unexpected tool name in mock")

        mock_mcp_host.execute_tool = AsyncMock(side_effect=mock_execute_tool_multi)

        # Mock create_tool_result_blocks
        mock_mcp_host.tools = Mock()
        mock_tool1_result_block_content = {
            "type": "tool_result",
            "tool_use_id": tool1_id,
            "content": tool1_result_content,
        }
        mock_tool2_result_block_content = {
            "type": "tool_result",
            "tool_use_id": tool2_id,
            "content": tool2_result_content,
        }

        # Mock create_tool_result_blocks to return the correct block based on tool_id
        def mock_create_results(*args, **kwargs):
            tool_use_id = args[0]  # First positional arg is tool_use_id
            if tool_use_id == tool1_id:
                return [mock_tool1_result_block_content]
            elif tool_use_id == tool2_id:
                return [mock_tool2_result_block_content]
            else:
                raise ValueError("Unexpected tool_id in mock")

        mock_mcp_host.tools.create_tool_result_blocks = Mock(
            side_effect=mock_create_results
        )

        # --- Execute the agent ---
        result = await agent.execute_agent(
            user_message=user_message,
            host_instance=mock_mcp_host,
        )

        print(f"Execution Result: {result}")

        # --- Assertions ---
        # Check the call count on the mocked internal method
        assert agent._make_llm_call.await_count == 2
        mock_mcp_host.get_formatted_tools.assert_called_once()  # Use synchronous assertion
        # Tool executed twice
        assert mock_mcp_host.execute_tool.await_count == 2
        mock_mcp_host.execute_tool.assert_any_await(
            tool_name=tool1_name,
            arguments=tool1_input,
            agent_config=minimal_agent_config,
        )
        mock_mcp_host.execute_tool.assert_any_await(
            tool_name=tool2_name,
            arguments=tool2_input,
            agent_config=minimal_agent_config,
        )
        # Tool result block created twice
        assert mock_mcp_host.tools.create_tool_result_blocks.call_count == 2
        mock_mcp_host.tools.create_tool_result_blocks.assert_any_call(
            tool1_id, tool1_result_content
        )
        mock_mcp_host.tools.create_tool_result_blocks.assert_any_call(
            tool2_id, tool2_result_content
        )

        # Conversation history check
        assert "conversation" in result
        assert (
            len(result["conversation"]) == 4
        )  # user -> assistant (tools) -> user (results) -> assistant (final)
        assert result["conversation"][0]["role"] == "user"
        assert result["conversation"][1]["role"] == "assistant"
        assert result["conversation"][1]["content"] == mock_llm_response_1.content
        # Check the user message containing tool results (order might vary, check content)
        assert result["conversation"][2]["role"] == "user"
        user_tool_results_content = result["conversation"][2]["content"]
        assert isinstance(user_tool_results_content, list)
        assert (
            len(user_tool_results_content) == 2
        )  # Should contain results for both tools
        # Check if both expected result blocks are present (order doesn't matter)
        assert [mock_tool1_result_block_content] in user_tool_results_content
        assert [mock_tool2_result_block_content] in user_tool_results_content
        assert result["conversation"][3]["role"] == "assistant"
        assert result["conversation"][3]["content"] == mock_llm_response_2.content

        # Final response check
        assert "final_response" in result
        assert result["final_response"] == mock_llm_response_2

        # Tool uses check (should contain both tools from the first assistant turn)
        assert "tool_uses" in result
        assert len(result["tool_uses"]) == 2
        # Check presence of both tool uses (order might vary)
        assert any(
            tu["id"] == tool1_id and tu["name"] == tool1_name
            for tu in result["tool_uses"]
        )
        assert any(
            tu["id"] == tool2_id and tu["name"] == tool2_name
            for tu in result["tool_uses"]
        )

        print("Assertions passed.")
        print(
            "--- Test Finished: test_execute_agent_success_with_multiple_tool_uses ---"
        )

    @pytest.mark.asyncio
    async def test_execute_agent_tool_execution_error(
        self,
        agent: Agent,
        mock_mcp_host: AsyncMock,
        minimal_agent_config: AgentConfig,
        mock_anthropic_client: MagicMock,  # Add mock client fixture
    ):
        """
        Test agent execution when a requested tool fails during execution.
        The agent should send an error message back to the LLM.
        """
        print("\n--- Running Test: test_execute_agent_tool_execution_error ---")
        user_message = "Use the failing tool."
        tool_name = "failing_tool"
        tool_input = {"data": "irrelevant"}
        tool_id = "tool_fail123"
        tool_execution_error = ValueError("Tool exploded!")
        error_content_string = (
            f"Error executing tool '{tool_name}': {str(tool_execution_error)}"
        )

        # --- Mock LLM Response 1 (Requesting Tool Use) ---
        mock_tool_use_block = MagicMock()
        mock_tool_use_block.type = "tool_use"
        mock_tool_use_block.id = tool_id
        mock_tool_use_block.name = tool_name
        mock_tool_use_block.input = tool_input

        mock_llm_response_1 = MagicMock(spec=Message)
        mock_llm_response_1.content = [mock_tool_use_block]
        mock_llm_response_1.stop_reason = "tool_use"

        # --- Mock LLM Response 2 (Final Text Response after Error Result) ---
        mock_llm_response_2 = MagicMock(spec=Message)
        mock_llm_response_2.content = [
            MagicMock(type="text", text="Okay, the tool failed.")
        ]
        mock_llm_response_2.stop_reason = "end_turn"

        # Mock the internal _make_llm_call method to return responses sequentially
        agent._make_llm_call = AsyncMock(
            side_effect=[mock_llm_response_1, mock_llm_response_2]
        )

        # --- Mock Host Tool Execution (to raise error) ---
        mock_mcp_host.execute_tool = AsyncMock(side_effect=tool_execution_error)

        # Mock create_tool_result_blocks to return the error block
        mock_mcp_host.tools = Mock()
        mock_error_result_block_content = {
            "type": "tool_result",
            "tool_use_id": tool_id,
            "content": error_content_string,
        }
        # We expect create_tool_result_blocks to be called with the error string
        mock_mcp_host.tools.create_tool_result_blocks = Mock(
            return_value=[mock_error_result_block_content]
        )

        # --- Execute the agent ---
        result = await agent.execute_agent(
            user_message=user_message,
            host_instance=mock_mcp_host,
        )

        print(f"Execution Result: {result}")

        # --- Assertions ---
        # Check the call count on the mocked internal method
        assert agent._make_llm_call.await_count == 2
        mock_mcp_host.get_formatted_tools.assert_called_once()  # Use synchronous assertion
        # Tool execution attempted once
        mock_mcp_host.execute_tool.assert_awaited_once_with(
            tool_name=tool_name, arguments=tool_input, agent_config=minimal_agent_config
        )
        # Tool result block created once (with the error message)
        mock_mcp_host.tools.create_tool_result_blocks.assert_called_once_with(
            tool_id,
            error_content_string,  # Verify it was called with the error string
        )

        # Conversation history check
        assert "conversation" in result
        assert (
            len(result["conversation"]) == 4
        )  # user -> assistant (tool) -> user (error result) -> assistant (final)
        assert result["conversation"][0]["role"] == "user"
        assert result["conversation"][1]["role"] == "assistant"
        assert result["conversation"][1]["content"] == mock_llm_response_1.content
        # Check the user message containing the error tool result
        assert result["conversation"][2]["role"] == "user"
        assert result["conversation"][2]["content"] == [
            [mock_error_result_block_content]
        ]  # List of lists
        assert result["conversation"][3]["role"] == "assistant"
        assert result["conversation"][3]["content"] == mock_llm_response_2.content

        # Final response check
        assert "final_response" in result
        assert result["final_response"] == mock_llm_response_2

        # Tool uses check (should contain the failed tool use)
        assert "tool_uses" in result
        assert len(result["tool_uses"]) == 1
        assert result["tool_uses"][0]["id"] == tool_id
        assert result["tool_uses"][0]["name"] == tool_name

        print("Assertions passed.")
        print("--- Test Finished: test_execute_agent_tool_execution_error ---")

    @pytest.mark.asyncio
    async def test_execute_agent_filtering_passed_to_host(
        self,
        mock_mcp_host: AsyncMock,
        mock_anthropic_client: MagicMock,  # Add mock client fixture
    ):
        """
        Test that agent filtering parameters are correctly passed to
        host_instance.get_formatted_tools.
        """
        print("\n--- Running Test: test_execute_agent_filtering_passed_to_host ---")
        user_message = "Does filtering work?"
        # Create a specific agent config with filtering
        filtering_agent_config = AgentConfig(
            name="FilteringAgent",
            model="claude-3-haiku-20240307",
            client_ids=["client1", "client2"],
            exclude_components=["excluded_tool", "excluded_prompt"],
        )
        agent_with_filtering = Agent(config=filtering_agent_config)

        # Mock the LLM response (no tool use needed for this test)
        mock_llm_response = MagicMock(spec=Message)
        mock_llm_response.content = [
            MagicMock(type="text", text="Checking filtering...")
        ]
        mock_llm_response.stop_reason = "end_turn"
        # Mock the internal _make_llm_call method directly
        agent_with_filtering._make_llm_call = AsyncMock(return_value=mock_llm_response)

        # Mock get_formatted_tools on the host instance (return value doesn't matter)
        # Note: get_formatted_tools is now mocked via the mock_mcp_host fixture itself
        # mock_mcp_host.get_formatted_tools = AsyncMock(return_value=[]) # No longer needed here

        # Execute the agent
        await agent_with_filtering.execute_agent(
            user_message=user_message,
            host_instance=mock_mcp_host,
        )

        # --- Assertions ---
        # Verify get_formatted_tools was called exactly once with the correct agent_config
        mock_mcp_host.get_formatted_tools.assert_called_once_with(  # Use synchronous assertion
            agent_config=filtering_agent_config
        )

        print("Assertions passed.")
        print("--- Test Finished: test_execute_agent_filtering_passed_to_host ---")

    @pytest.mark.asyncio
    async def test_execute_agent_llm_call_failure(
        self,
        agent: Agent,
        mock_mcp_host: AsyncMock,
        mock_anthropic_client: MagicMock,  # Add mock client fixture
    ):
        """
        Test agent execution when the _make_llm_call method raises an exception.
        """
        print("\n--- Running Test: test_execute_agent_llm_call_failure ---")
        user_message = "This will fail."
        # Instantiate the error, providing a mock for the required 'request' argument
        llm_error = anthropic.APIConnectionError(request=Mock())

        # Mock the internal _make_llm_call method to raise an error
        agent._make_llm_call = AsyncMock(side_effect=llm_error)

        # Execute the agent
        result = await agent.execute_agent(
            user_message=user_message,
            host_instance=mock_mcp_host,
        )

        print(f"Execution Result: {result}")

        # Assertions
        # Check the call on the mocked internal method
        agent._make_llm_call.assert_awaited_once()  # LLM call was attempted
        mock_mcp_host.get_formatted_tools.assert_called_once()  # Use synchronous assertion
        mock_mcp_host.execute_tool.assert_not_awaited()  # Tool execution should not happen

        # Check the returned error structure
        assert "error" in result
        assert result["error"] == f"Anthropic API call failed: {str(llm_error)}"
        assert result["final_response"] is None
        assert "conversation" in result
        # History should contain only the initial user message before the error
        assert len(result["conversation"]) == 1
        assert result["conversation"][0]["role"] == "user"
        assert result["conversation"][0]["content"] == user_message
        assert "tool_uses" in result
        assert len(result["tool_uses"]) == 0

        print("Assertions passed.")
        print("--- Test Finished: test_execute_agent_llm_call_failure ---")


    # --- History Tests ---

    @pytest.mark.asyncio
    @patch('src.agents.agent.Agent._make_llm_call', new_callable=AsyncMock) # Patch the method
    async def test_execute_agent_history_enabled_loads_and_saves(
        self,
        mock_llm_call: AsyncMock, # Mock is passed as first arg
        mock_mcp_host: AsyncMock,
        # mock_anthropic_client is no longer needed directly as we patch _make_llm_call
    ):
        """
        Test that history is loaded and saved when include_history=True
        and a storage_manager is provided.
        """
        print("\n--- Running Test: test_execute_agent_history_enabled_loads_and_saves ---")
        user_message = "Third message"
        session_id = "test_session_123" # Define a session ID for the test
        # Create agent config with history enabled
        history_agent_config = AgentConfig(
            name="HistoryAgent",
            model="claude-3-haiku-20240307",
            include_history=True,
        )
        agent_with_history = Agent(config=history_agent_config)

        # Mock StorageManager
        mock_storage = MagicMock(spec=StorageManager)
        # Define mock history to be loaded (already serialized format)
        mock_loaded_history = [
            {"role": "user", "content": [{"type": "text", "text": "First message"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "Second message"}]},
        ]
        mock_storage.load_history.return_value = mock_loaded_history
        # save_full_history doesn't need a return value for the mock

        # Mock LLM response
        mock_llm_response = MagicMock(spec=Message)
        mock_llm_response.content = [MagicMock(type="text", text="Fourth message")]
        mock_llm_response.stop_reason = "end_turn"
        # Configure the patched mock's return value
        mock_llm_call.return_value = mock_llm_response

        # Execute the agent, passing the mock storage manager
        result = await agent_with_history.execute_agent(
            user_message=user_message,
            host_instance=mock_mcp_host,
            storage_manager=mock_storage, # Pass the mock
            session_id=session_id, # Pass the session ID
        )

        # --- Assertions ---
        # 1. History Loading
        mock_storage.load_history.assert_called_once_with(
            agent_name=history_agent_config.name,
            session_id=session_id # Verify session_id was passed
        )

        # 2. LLM Call includes history
        mock_llm_call.assert_awaited_once() # Assert the call happened
        # Get the arguments captured by the mock (which might reflect post-call state)
        actual_call_kwargs = mock_llm_call.await_args.kwargs
        actual_messages_arg = actual_call_kwargs.get('messages', [])
        # Assert based on what *should have been* passed at call time
        assert len(actual_messages_arg) >= 3 # Should have at least history + user msg
        # Check the messages that *should* have been sent
        assert actual_messages_arg[0] == mock_loaded_history[0] # Check first history item
        assert actual_messages_arg[1] == mock_loaded_history[1] # Check second history item
        # The user message should be the third item *at the time of the call*
        assert actual_messages_arg[2]["role"] == "user"
        assert actual_messages_arg[2]["content"] == user_message
        # Also check other key args were passed correctly
        assert actual_call_kwargs.get('model') == history_agent_config.model
        assert actual_call_kwargs.get('system_prompt') == (history_agent_config.system_prompt or "You are a helpful assistant.")

        # 3. History Saving
        mock_storage.save_full_history.assert_called_once()
        # Check keyword arguments passed to the mock
        save_call_kwargs = mock_storage.save_full_history.call_args.kwargs
        assert save_call_kwargs.get("agent_name") == history_agent_config.name
        assert save_call_kwargs.get("session_id") == session_id # Verify session_id was passed
        saved_conversation = save_call_kwargs.get("conversation")

        # Assertions on saved conversation content remain the same
        assert len(saved_conversation) == 4 # History (2) + Current User (1) + Final Assistant (1)
        # Verify the content was serialized correctly (using the helper implicitly)
        assert saved_conversation[0] == mock_loaded_history[0]
        assert saved_conversation[1] == mock_loaded_history[1]
        assert saved_conversation[2]["role"] == "user"
        # User message content should be serialized (wrapped in list/dict)
        assert saved_conversation[2]["content"] == [{"type": "text", "text": user_message}]
        # Check only the role of the final assistant message in the saved history
        assert saved_conversation[3]["role"] == "assistant"
        # Avoid asserting the exact content structure of the serialized mock, as it's fragile

        # 4. Final Result Structure (optional, but good practice)
        assert result["error"] is None
        assert result["final_response"] == mock_llm_response

        print("Assertions passed.")
        print("--- Test Finished: test_execute_agent_history_enabled_loads_and_saves ---")


    @pytest.mark.asyncio
    @patch('src.agents.agent.Agent._make_llm_call', new_callable=AsyncMock) # Patch the method
    async def test_execute_agent_history_disabled(
        self,
        mock_llm_call: AsyncMock, # Mock is passed as first arg
        agent: Agent, # Uses minimal_agent_config (history defaults to None/False)
        mock_mcp_host: AsyncMock,
        # mock_anthropic_client no longer needed
    ):
        """
        Test that history is NOT loaded or saved when include_history=False.
        """
        print("\n--- Running Test: test_execute_agent_history_disabled ---")
        user_message = "No history please"
        session_id = "test_session_disabled" # Define session ID even though it shouldn't be used
        # Agent fixture uses minimal_agent_config where include_history is default (False)

        # Mock StorageManager (methods should NOT be called)
        mock_storage = MagicMock(spec=StorageManager)

        # Mock LLM response
        mock_llm_response = MagicMock(spec=Message)
        mock_llm_response.content = [MagicMock(type="text", text="Okay, no history.")]
        mock_llm_response.stop_reason = "end_turn"
        # Configure the patched mock
        mock_llm_call.return_value = mock_llm_response

        # Execute the agent, passing the mock storage manager
        result = await agent.execute_agent(
            user_message=user_message,
            host_instance=mock_mcp_host,
            storage_manager=mock_storage, # Pass the mock
            session_id=session_id, # Pass session ID (agent should ignore it)
        )

        # --- Assertions ---
        # 1. History Loading NOT called
        mock_storage.load_history.assert_not_called()

        # 2. LLM Call does NOT include history
        mock_llm_call.assert_awaited_once() # Assert the call happened
        # Get the arguments captured by the mock
        actual_call_kwargs = mock_llm_call.await_args.kwargs
        actual_messages_arg = actual_call_kwargs.get('messages', [])
        # Assert based on what *should have been* passed at call time
        assert len(actual_messages_arg) >= 1 # Should have at least user msg
        # The user message should be the first item *at the time of the call*
        assert actual_messages_arg[0]["role"] == "user"
        assert actual_messages_arg[0]["content"] == user_message
        # Check other key args, accounting for fallbacks in execute_agent
        expected_model = agent.config.model or "claude-3-opus-20240229"
        expected_system_prompt = agent.config.system_prompt or "You are a helpful assistant."
        assert actual_call_kwargs.get('model') == expected_model
        assert actual_call_kwargs.get('system_prompt') == expected_system_prompt


        # 3. History Saving NOT called
        mock_storage.save_full_history.assert_not_called()

        # 4. Final Result Structure
        assert result["error"] is None
        assert result["final_response"] == mock_llm_response

        print("Assertions passed.")
        print("--- Test Finished: test_execute_agent_history_disabled ---")


    @pytest.mark.asyncio
    @patch('src.agents.agent.Agent._make_llm_call', new_callable=AsyncMock) # Patch the method
    async def test_execute_agent_history_enabled_no_storage_manager(
        self,
        mock_llm_call: AsyncMock, # Mock is passed as first arg
        mock_mcp_host: AsyncMock,
        # mock_anthropic_client no longer needed
    ):
        """
        Test that execution proceeds without error when include_history=True
        but no storage_manager is provided.
        """
        print("\n--- Running Test: test_execute_agent_history_enabled_no_storage_manager ---")
        user_message = "History enabled, but no storage"
        session_id = "test_session_no_storage" # Define session ID
        # Create agent config with history enabled
        history_agent_config = AgentConfig(
            name="HistoryAgentNoStorage",
            model="claude-3-haiku-20240307",
            include_history=True, # History is enabled
        )
        agent_with_history = Agent(config=history_agent_config)

        # Mock LLM response
        mock_llm_response = MagicMock(spec=Message)
        mock_llm_response.content = [MagicMock(type="text", text="Okay")]
        mock_llm_response.stop_reason = "end_turn"
        # Configure the patched mock
        mock_llm_call.return_value = mock_llm_response

        # Execute the agent, passing storage_manager=None
        result = await agent_with_history.execute_agent(
            user_message=user_message,
            host_instance=mock_mcp_host,
            storage_manager=None, # Explicitly pass None
            session_id=session_id, # Pass session ID (agent should log warning but proceed)
        )

        # --- Assertions ---
        # 1. LLM Call does NOT include history (as it couldn't be loaded)
        mock_llm_call.assert_awaited_once() # Assert the call happened
        # Get the arguments captured by the mock
        actual_call_kwargs = mock_llm_call.await_args.kwargs
        actual_messages_arg = actual_call_kwargs.get('messages', [])
        # Assert based on what *should have been* passed at call time
        assert len(actual_messages_arg) >= 1 # Should have at least user msg
        # The user message should be the first item *at the time of the call*
        assert actual_messages_arg[0]["role"] == "user"
        assert actual_messages_arg[0]["content"] == user_message
        # Check other key args
        assert actual_call_kwargs.get('model') == history_agent_config.model
        assert actual_call_kwargs.get('system_prompt') == (agent_with_history.config.system_prompt or "You are a helpful assistant.")

        # 2. Final Result Structure
        assert result["error"] is None
        assert result["final_response"] == mock_llm_response

        print("Assertions passed.")
        print("--- Test Finished: test_execute_agent_history_enabled_no_storage_manager ---")
