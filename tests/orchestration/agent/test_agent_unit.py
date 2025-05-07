"""
Unit tests for the Agent class, focusing on orchestration logic.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import List

# Mark all tests in this module
pytestmark = [pytest.mark.orchestration, pytest.mark.unit, pytest.mark.anyio]

# Imports from the project
from src.agents.agent import Agent
from src.agents.conversation_manager import ConversationManager  # Added
from src.agents.agent_models import (
    AgentExecutionResult,
    AgentOutputMessage,
    AgentOutputContentBlock,
)
from src.host.models import AgentConfig
from src.llm.base_client import BaseLLM
from src.host.host import MCPHost
from anthropic.types import MessageParam

# --- Fixtures ---


@pytest.fixture
def mock_agent_config() -> AgentConfig:
    """Provides a basic mock AgentConfig."""
    return AgentConfig(
        name="UnitTestAgent",
        llm_config_id="test_llm",
        max_iterations=5,  # Set a default max iterations for tests
    )


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Provides a mock BaseLLM client."""
    return MagicMock(spec=BaseLLM)


@pytest.fixture
def mock_mcp_host() -> MagicMock:
    """Provides a mock MCPHost instance."""
    mock_host = MagicMock(spec=MCPHost)
    # Configure get_formatted_tools to return an empty list by default
    mock_host.get_formatted_tools.return_value = []
    return mock_host


@pytest.fixture
def agent_instance(mock_agent_config: AgentConfig, mock_llm_client: MagicMock) -> Agent:
    """Provides an Agent instance initialized with mock config and LLM client."""
    return Agent(config=mock_agent_config, llm_client=mock_llm_client)


@pytest.fixture
def initial_messages() -> List[MessageParam]:
    """Provides a basic list of initial messages (user message)."""
    return [{"role": "user", "content": [{"type": "text", "text": "Hello Agent"}]}]


# --- Test Class ---


class TestConversationManagerUnit:  # Renamed class
    """Unit tests for the ConversationManager class orchestration logic."""

    @pytest.mark.anyio
    # Patched AgentTurnProcessor where ConversationManager uses it
    @patch("src.agents.conversation_manager.AgentTurnProcessor", autospec=True)
    async def test_run_conversation_single_turn_no_tool(  # Renamed test method
        self,
        MockAgentTurnProcessor: MagicMock,  # The patched class
        agent_instance: Agent,  # Still need agent for ConversationManager
        mock_mcp_host: MagicMock,
        initial_messages: List[MessageParam],
        mock_agent_config: AgentConfig,
        mock_llm_client: MagicMock,
    ):
        """
        Tests run_conversation for a single turn with a final response (no tools).
        Verifies AgentTurnProcessor is called correctly and the loop terminates.
        """
        # --- Arrange ---
        # Mock the final response the TurnProcessor should return
        mock_final_assistant_response = AgentOutputMessage(
            id="llm_msg_final",
            role="assistant",
            model="test_model",
            content=[AgentOutputContentBlock(type="text", text="Final answer.")],
            stop_reason="end_turn",
            usage={"input_tokens": 10, "output_tokens": 5},
        )

        # Configure the mock TurnProcessor instance that will be created
        mock_turn_processor_instance = MockAgentTurnProcessor.return_value
        # process_turn should be an async mock
        mock_turn_processor_instance.process_turn = AsyncMock(
            return_value=(
                mock_final_assistant_response,  # turn_final_response
                None,  # turn_tool_results_params
                True,  # is_final_turn
            )
        )
        # Configure other methods if needed (e.g., if Agent calls them directly)
        mock_turn_processor_instance.get_last_llm_response.return_value = (
            mock_final_assistant_response
        )
        mock_turn_processor_instance.get_tool_uses_this_turn.return_value = []

        # --- Act ---
        # Instantiate ConversationManager
        conversation_manager = ConversationManager(
            agent=agent_instance,
            host_instance=mock_mcp_host,
            initial_messages=initial_messages,
            system_prompt_override=None,  # Corresponds to old system_prompt
        )
        result: AgentExecutionResult = await conversation_manager.run_conversation()

        # --- Assert ---
        # 1. MCPHost setup called
        mock_mcp_host.get_formatted_tools.assert_called_once_with(
            agent_config=mock_agent_config
        )

        # 2. AgentTurnProcessor instantiated correctly in the loop (once)
        MockAgentTurnProcessor.assert_called_once_with(
            config=mock_agent_config,
            llm_client=mock_llm_client,
            host_instance=mock_mcp_host,
            current_messages=initial_messages,  # Initial call uses initial_messages
            tools_data=[],  # Based on mock_mcp_host.get_formatted_tools
            effective_system_prompt="You are a helpful assistant.",  # Default from config/agent logic
        )

        # 3. process_turn called on the instance
        mock_turn_processor_instance.process_turn.assert_awaited_once()

        # 4. Result object checks
        assert isinstance(result, AgentExecutionResult)
        assert result.error is None
        assert result.final_response == mock_final_assistant_response
        assert result.tool_uses_in_final_turn == []

        # 5. Conversation history check
        # Conversation history in AgentExecutionResult is List[AgentOutputMessage]
        # The initial messages are also added to the internal conversation_history as dicts
        # and then validated into AgentOutputMessage for the result.
        assert len(result.conversation) == 2
        # Initial user message (validated and dumped)
        # For simplicity, we'll check key parts. Full validation is complex here.
        # The _prepare_agent_result method in ConversationManager handles this serialization.
        # We trust that if the final_response is correct, and the length is correct,
        # the history processing is likely working as intended for this unit test.
        # A more direct test of _prepare_agent_result might be useful separately.
        assert result.conversation[0].role == "user"
        assert result.conversation[0].content[0].text == "Hello Agent"
        # Final assistant message
        assert result.conversation[1].model_dump(
            mode="json"
        ) == mock_final_assistant_response.model_dump(mode="json")

    @pytest.mark.anyio
    @patch("src.agents.conversation_manager.AgentTurnProcessor", autospec=True)
    async def test_run_conversation_multi_turn_with_tool(
        self,
        MockAgentTurnProcessor: MagicMock,
        agent_instance: Agent,
        mock_mcp_host: MagicMock,
        initial_messages: List[MessageParam],
        mock_agent_config: AgentConfig,
        mock_llm_client: MagicMock,
    ):
        """
        Tests run_conversation for a two-turn execution involving a tool call.
        Turn 1: LLM requests tool use.
        Turn 2: LLM gives final response after getting tool result.
        """
        # --- Arrange ---
        tool_name = "test_tool"
        tool_use_id = "tool_123"
        tool_input = {"query": "test"}
        tool_result_content_str = "{'result': 'tool success'}"  # Example result

        # --- Mock Turn 1: Tool Use Request ---
        mock_assistant_response_turn1 = AgentOutputMessage(
            id="llm_msg_tool_req",
            role="assistant",
            model="test_model",
            content=[
                AgentOutputContentBlock(
                    type="tool_use", id=tool_use_id, name=tool_name, input=tool_input
                )
            ],
            stop_reason="tool_use",
            usage={"input_tokens": 10, "output_tokens": 10},
        )
        # Tool results prepared by AgentTurnProcessor (mocked return value)
        mock_tool_results_params_turn1: List[MessageParam] = [
            {
                "type": "tool_result",  # This is a ToolResultBlockParam
                "tool_use_id": tool_use_id,
                "content": [
                    {"type": "text", "text": tool_result_content_str}
                ],  # Content should be a list of blocks
            }
        ]

        # --- Mock Turn 2: Final Response ---
        mock_final_assistant_response_turn2 = AgentOutputMessage(
            id="llm_msg_final_tool",
            role="assistant",
            model="test_model",
            content=[
                AgentOutputContentBlock(type="text", text="Tool used successfully.")
            ],
            stop_reason="end_turn",
            usage={"input_tokens": 20, "output_tokens": 5},
        )

        # Configure the mock TurnProcessor instance return values for sequential calls
        mock_turn_processor_instance = MockAgentTurnProcessor.return_value
        mock_turn_processor_instance.process_turn.side_effect = [
            # Turn 1 result: (final_response, tool_results, is_final)
            (None, mock_tool_results_params_turn1, False),
            # Turn 2 result:
            (mock_final_assistant_response_turn2, None, True),
        ]
        # Configure get_last_llm_response for each turn
        mock_turn_processor_instance.get_last_llm_response.side_effect = [
            mock_assistant_response_turn1,
            mock_final_assistant_response_turn2,
        ]
        # Configure get_tool_uses_this_turn for each turn
        mock_turn_processor_instance.get_tool_uses_this_turn.side_effect = [
            [
                {"id": tool_use_id, "name": tool_name, "input": tool_input}
            ],  # Tool use in turn 1
            [],  # No tool use in turn 2
        ]

        # --- Act ---
        conversation_manager = ConversationManager(
            agent=agent_instance,
            host_instance=mock_mcp_host,
            initial_messages=initial_messages,
            system_prompt_override=None,
        )
        result: AgentExecutionResult = await conversation_manager.run_conversation()

        # --- Assert ---
        # 1. MCPHost setup called once
        mock_mcp_host.get_formatted_tools.assert_called_once_with(
            agent_config=mock_agent_config
        )

        # 2. AgentTurnProcessor instantiated twice
        assert MockAgentTurnProcessor.call_count == 2

        # 3. Check arguments for each instantiation
        call_args_list = MockAgentTurnProcessor.call_args_list
        # Call 1 Args
        call1_kwargs = call_args_list[0].kwargs
        assert call1_kwargs["config"] == mock_agent_config
        assert call1_kwargs["llm_client"] == mock_llm_client
        assert call1_kwargs["host_instance"] == mock_mcp_host
        assert (
            call1_kwargs["current_messages"] == initial_messages
        )  # First call uses initial
        assert call1_kwargs["tools_data"] == []
        assert call1_kwargs["effective_system_prompt"] == "You are a helpful assistant."

        # Call 2 Args - Construct expected messages list after turn 1 for AgentTurnProcessor
        # ConversationManager internally manages `self.messages` which are MessageParam
        # It passes a *copy* of `self.messages` to AgentTurnProcessor
        # After turn 1, self.messages would be:
        # 1. Initial user message (MessageParam)
        # 2. Assistant's tool use request (MessageParam format)
        # 3. User message with tool results (MessageParam format)

        expected_messages_for_turn_processor_call2 = [
            initial_messages[0],  # Original user MessageParam
            {  # Assistant's tool use request, converted to MessageParam for next LLM call
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": tool_use_id,
                        "name": tool_name,
                        "input": tool_input,
                    }
                ],
            },
            {  # User message with tool results (already List[MessageParam], so this is one item)
                # Actually, mock_tool_results_params_turn1 is List[MessageParam],
                # and ConversationManager appends:
                # self.messages.append({"role": "user", "content": turn_tool_results_params})
                # So the content of this user message is a list of tool result blocks.
                "role": "user",
                "content": mock_tool_results_params_turn1,  # This is List[MessageParam]
            },
        ]

        call2_kwargs = call_args_list[1].kwargs
        assert call2_kwargs["config"] == mock_agent_config
        assert call2_kwargs["llm_client"] == mock_llm_client
        assert call2_kwargs["host_instance"] == mock_mcp_host

        actual_messages_for_processor_turn2 = call2_kwargs["current_messages"]
        assert len(actual_messages_for_processor_turn2) == 3
        assert (
            actual_messages_for_processor_turn2[0]
            == expected_messages_for_turn_processor_call2[0]
        )
        assert (
            actual_messages_for_processor_turn2[1]
            == expected_messages_for_turn_processor_call2[1]
        )
        assert (
            actual_messages_for_processor_turn2[2]
            == expected_messages_for_turn_processor_call2[2]
        )

        assert (
            call2_kwargs["tools_data"] == []
        )  # Assuming mock_mcp_host.get_formatted_tools still returns []
        assert call2_kwargs["effective_system_prompt"] == "You are a helpful assistant."

        # 4. process_turn called twice on the instance(s)
        assert mock_turn_processor_instance.process_turn.await_count == 2

        # 5. Result object checks
        assert isinstance(result, AgentExecutionResult)
        assert result.error is None
        assert result.final_response == mock_final_assistant_response_turn2
        # Tool uses should reflect the *last* turn where tools were used (turn 1)
        assert result.tool_uses_in_final_turn == [
            {"id": tool_use_id, "name": tool_name, "input": tool_input}
        ]

        # 6. Conversation history check
        # user_initial -> assistant_tool_req -> user_tool_result -> assistant_final
        assert len(result.conversation) == 4
        assert result.conversation[0].role == "user"  # Initial User
        assert result.conversation[0].content[0].text == "Hello Agent"

        # Assistant Tool Request
        assert result.conversation[1].model_dump(
            mode="json"
        ) == mock_assistant_response_turn1.model_dump(mode="json")

        # User Tool Result
        # ConversationManager._prepare_agent_result serializes MessageParam for history.
        # The 'user' message with tool results has content that is a list of ToolResultBlockParam.
        # AgentOutputMessage expects content to be List[AgentOutputContentBlock].
        # The _serialize_content_blocks and validation in _prepare_agent_result handle this.
        # For this test, we'll check the key parts.
        assert result.conversation[2].role == "user"
        assert (
            len(result.conversation[2].content) == 1
        )  # The list of tool results becomes one content block
        user_tool_result_content_block = result.conversation[2].content[0]
        # Check how the ToolResultBlockParam's content (which was a list containing a TextBlockParam)
        # gets serialized into the AgentOutputMessage history. It appears to become a single TextBlock.
        assert user_tool_result_content_block.type == "text"
        assert user_tool_result_content_block.text == tool_result_content_str
        # The tool_use_id association might be lost in this simplified history representation.

        # Final Assistant Response
        assert result.conversation[3].model_dump(
            mode="json"
        ) == mock_final_assistant_response_turn2.model_dump(mode="json")

    @pytest.mark.anyio
    @patch(
        "src.agents.conversation_manager.AgentTurnProcessor", autospec=True
    )  # Patched
    async def test_run_conversation_max_iterations_reached(  # Renamed
        self,
        MockAgentTurnProcessor: MagicMock,
        agent_instance: Agent,
        mock_mcp_host: MagicMock,
        initial_messages: List[MessageParam],
        mock_agent_config: AgentConfig,
        mock_llm_client: MagicMock,
    ):
        """
        Tests that the conversation loop terminates after reaching max_iterations.
        """
        # --- Arrange ---
        max_iters = 3  # Set a low number for testing
        mock_agent_config.max_iterations = max_iters

        # Mock the TurnProcessor to always return a non-final state (e.g., tool use)
        # to force the loop to continue until max_iterations
        mock_assistant_response_loop = AgentOutputMessage(
            id="llm_msg_loop",
            role="assistant",
            model="test_model",
            content=[AgentOutputContentBlock(type="text", text="Looping...")],
            stop_reason="end_turn",  # Even if stop is end_turn, mock is_final=False
            usage={"input_tokens": 5, "output_tokens": 5},
        )

        # Configure the mock TurnProcessor instance
        mock_turn_processor_instance = MockAgentTurnProcessor.return_value
        # Always return is_final=False to prevent loop breaking early
        # Define a dummy tool result to ensure the loop continues
        dummy_tool_result: List[MessageParam] = [
            {"role": "user", "content": [{"type": "text", "text": "dummy"}]}
        ]
        mock_turn_processor_instance.process_turn = AsyncMock(
            return_value=(
                mock_assistant_response_loop,  # Return a response object
                dummy_tool_result,  # Return non-empty list for tool_results to bypass schema check path
                False,  # IMPORTANT: Never signal final turn
            )
        )
        # Configure other methods
        mock_turn_processor_instance.get_last_llm_response.return_value = (
            mock_assistant_response_loop
        )
        mock_turn_processor_instance.get_tool_uses_this_turn.return_value = []

        # --- Act ---
        conversation_manager = ConversationManager(
            agent=agent_instance,
            host_instance=mock_mcp_host,
            initial_messages=initial_messages,
            system_prompt_override=None,
        )
        result: AgentExecutionResult = await conversation_manager.run_conversation()

        # --- Assert ---
        # 1. AgentTurnProcessor instantiated max_iterations times
        assert MockAgentTurnProcessor.call_count == max_iters

        # 2. process_turn called max_iterations times
        assert mock_turn_processor_instance.process_turn.await_count == max_iters

        # 3. Result object checks
        assert isinstance(result, AgentExecutionResult)
        assert result.error is None  # Should not error, just stop
        # The final_response should be the last assistant message generated
        assert result.final_response == mock_assistant_response_loop
        assert result.tool_uses_in_final_turn == []

        # 4. Conversation history check (user + (assistant + dummy_user_tool_result) * max_iters)
        assert len(result.conversation) == 1 + (
            max_iters * 2
        )  # Initial user + (max_iters * (assistant + dummy user tool result))
        assert result.conversation[0].role == "user"
        assert result.conversation[0].content[0].text == "Hello Agent"
        # Check the pattern: assistant, user, assistant, user...
        for i in range(max_iters):
            assistant_index = 1 + (i * 2)
            user_index = 2 + (i * 2)
            # Check assistant message
            assert result.conversation[assistant_index].model_dump(
                mode="json"
            ) == mock_assistant_response_loop.model_dump(mode="json")
            # Check dummy user message
            assert result.conversation[user_index].role == "user"
            assert result.conversation[user_index].content[0].type == "text"
            assert result.conversation[user_index].content[0].text == "dummy"

    @pytest.mark.anyio
    @patch(
        "src.agents.conversation_manager.AgentTurnProcessor", autospec=True
    )  # Patched
    async def test_run_conversation_schema_correction_loop(  # Renamed
        self,
        MockAgentTurnProcessor: MagicMock,
        agent_instance: Agent,
        mock_mcp_host: MagicMock,
        initial_messages: List[MessageParam],
        mock_agent_config: AgentConfig,
        mock_llm_client: MagicMock,
    ):
        """
        Tests run_conversation handles the schema correction loop.
        Turn 1: LLM returns invalid JSON, TurnProcessor signals failure.
        Turn 2: Agent sends correction message, LLM returns valid JSON.
        """
        # --- Arrange ---
        # Add a schema to the agent config for this test
        test_schema = {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
        }
        mock_agent_config.config_validation_schema = test_schema
        invalid_json_text = '{"wrong_key": "needs correction"}'
        valid_json_text = '{"key": "corrected value"}'

        # --- Mock Turn 1: Invalid Schema Response ---
        mock_assistant_response_turn1 = AgentOutputMessage(
            id="llm_msg_invalid_schema",
            role="assistant",
            model="test_model",
            content=[AgentOutputContentBlock(type="text", text=invalid_json_text)],
            stop_reason="end_turn",  # LLM thought it was done, but schema failed
            usage={"input_tokens": 10, "output_tokens": 10},
        )

        # --- Mock Turn 2: Valid Schema Response ---
        mock_final_assistant_response_turn2 = AgentOutputMessage(
            id="llm_msg_valid_schema",
            role="assistant",
            model="test_model",
            content=[AgentOutputContentBlock(type="text", text=valid_json_text)],
            stop_reason="end_turn",
            usage={
                "input_tokens": 50,
                "output_tokens": 8,
            },  # More tokens due to correction msg
        )

        # Configure the mock TurnProcessor instance return values for sequential calls
        mock_turn_processor_instance = MockAgentTurnProcessor.return_value
        mock_turn_processor_instance.process_turn.side_effect = [
            # Turn 1 result: Schema validation fails (final_response=None, is_final=False)
            (None, None, False),
            # Turn 2 result: Schema validation succeeds
            (mock_final_assistant_response_turn2, None, True),
        ]
        # Configure get_last_llm_response for each turn
        mock_turn_processor_instance.get_last_llm_response.side_effect = [
            mock_assistant_response_turn1,  # Return the invalid one first
            mock_final_assistant_response_turn2,
        ]
        # Configure get_tool_uses_this_turn (no tools used)
        mock_turn_processor_instance.get_tool_uses_this_turn.return_value = []

        # --- Act ---
        conversation_manager = ConversationManager(
            agent=agent_instance,
            host_instance=mock_mcp_host,
            initial_messages=initial_messages,
            system_prompt_override=None,
        )
        result: AgentExecutionResult = await conversation_manager.run_conversation()

        # --- Assert ---
        # 1. MCPHost setup called once
        mock_mcp_host.get_formatted_tools.assert_called_once_with(
            agent_config=mock_agent_config
        )

        # 2. AgentTurnProcessor instantiated twice
        assert MockAgentTurnProcessor.call_count == 2

        # 3. Check arguments for each instantiation
        call_args_list = MockAgentTurnProcessor.call_args_list
        # Call 1 Args (Initial messages)
        call1_kwargs = call_args_list[0].kwargs
        assert call1_kwargs["current_messages"] == initial_messages

        # Call 2 Args (Should include initial user, invalid assistant (MessageParam), and correction user message (MessageParam))
        # for AgentTurnProcessor
        call2_kwargs = call_args_list[1].kwargs
        actual_messages_for_processor_turn2 = call2_kwargs["current_messages"]
        assert len(actual_messages_for_processor_turn2) == 3

        # 1. Initial User Message
        assert actual_messages_for_processor_turn2[0]["role"] == "user"
        assert (
            actual_messages_for_processor_turn2[0]["content"][0]["text"]
            == initial_messages[0]["content"][0]["text"]
        )  # type: ignore

        # 2. Assistant's Invalid Response (as MessageParam for next LLM call)
        assert actual_messages_for_processor_turn2[1]["role"] == "assistant"
        assert actual_messages_for_processor_turn2[1]["content"][0]["type"] == "text"  # type: ignore
        assert (
            actual_messages_for_processor_turn2[1]["content"][0]["text"]
            == invalid_json_text
        )  # type: ignore

        # 3. User's Correction Message (as MessageParam)
        assert actual_messages_for_processor_turn2[2]["role"] == "user"
        assert len(actual_messages_for_processor_turn2[2]["content"]) == 1  # type: ignore
        assert actual_messages_for_processor_turn2[2]["content"][0]["type"] == "text"  # type: ignore
        assert (
            "must be a valid JSON object matching this schema"
            in actual_messages_for_processor_turn2[2]["content"][0]["text"]
        )  # type: ignore

        # 4. process_turn called twice on the instance(s)
        assert mock_turn_processor_instance.process_turn.await_count == 2

        # 5. Result object checks
        assert isinstance(result, AgentExecutionResult)
        assert result.error is None
        assert (
            result.final_response == mock_final_assistant_response_turn2
        )  # Should be the corrected one
        assert result.tool_uses_in_final_turn == []

        # 6. Conversation history check (user -> assistant(invalid) -> user(correction) -> assistant(valid))
        assert len(result.conversation) == 4
        assert result.conversation[0].role == "user"
        assert result.conversation[0].content[0].text == "Hello Agent"

        # Invalid assistant response logged
        assert result.conversation[1].model_dump(
            mode="json"
        ) == mock_assistant_response_turn1.model_dump(mode="json")

        # Correction message logged
        assert result.conversation[2].role == "user"
        assert (
            "must be a valid JSON object matching this schema"
            in result.conversation[2].content[0].text
        )

        # Valid final response logged
        assert result.conversation[3].model_dump(
            mode="json"
        ) == mock_final_assistant_response_turn2.model_dump(mode="json")
