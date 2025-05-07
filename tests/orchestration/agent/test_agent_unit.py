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


class TestAgentUnit:
    """Unit tests for the Agent class orchestration logic."""

    @pytest.mark.anyio
    @patch("src.agents.agent.AgentTurnProcessor", autospec=True)  # Patch the class
    async def test_execute_agent_single_turn_no_tool(
        self,
        MockAgentTurnProcessor: MagicMock,  # The patched class
        agent_instance: Agent,
        mock_mcp_host: MagicMock,
        initial_messages: List[MessageParam],
        mock_agent_config: AgentConfig,  # Get config for assertions
        mock_llm_client: MagicMock,  # Get LLM client for assertions
    ):
        """
        Tests execute_agent for a single turn with a final response (no tools).
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
        result: AgentExecutionResult = await agent_instance.execute_agent(
            initial_messages=initial_messages,
            host_instance=mock_mcp_host,
            system_prompt=None,  # Use default from config
        )

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
        assert (
            len(result.conversation) == 2
        )  # Initial user message + final assistant message
        # Check initial user message (make sure it was serialized correctly)
        assert result.conversation[0].role == "user"
        assert result.conversation[0].content[0].type == "text"
        assert result.conversation[0].content[0].text == "Hello Agent"
        # Check final assistant message
        assert result.conversation[1] == mock_final_assistant_response

    @pytest.mark.anyio
    @patch("src.agents.agent.AgentTurnProcessor", autospec=True)  # Patch the class
    async def test_execute_agent_multi_turn_with_tool(
        self,
        MockAgentTurnProcessor: MagicMock,  # The patched class
        agent_instance: Agent,
        mock_mcp_host: MagicMock,
        initial_messages: List[MessageParam],  # User: "Hello Agent"
        mock_agent_config: AgentConfig,
        mock_llm_client: MagicMock,
    ):
        """
        Tests execute_agent for a two-turn execution involving a tool call.
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
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": tool_result_content_str,
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
        result: AgentExecutionResult = await agent_instance.execute_agent(
            initial_messages=initial_messages,
            host_instance=mock_mcp_host,
            system_prompt=None,
        )

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

        # Call 2 Args - Construct expected messages list after turn 1
        expected_messages_turn2 = [
            initial_messages[0],  # Original user message
            mock_assistant_response_turn1.model_dump(
                mode="json"
            ),  # Assistant tool request (serialized)
            {
                "role": "user",
                "content": mock_tool_results_params_turn1,
            },  # User tool result
        ]
        call2_kwargs = call_args_list[1].kwargs
        assert call2_kwargs["config"] == mock_agent_config
        assert call2_kwargs["llm_client"] == mock_llm_client
        assert call2_kwargs["host_instance"] == mock_mcp_host
        # Compare messages carefully
        actual_messages_turn2 = call2_kwargs["current_messages"]
        assert len(actual_messages_turn2) == 3
        # Check User Message (Turn 1)
        assert actual_messages_turn2[0] == expected_messages_turn2[0]
        # Check Assistant Message (Turn 1 - Tool Request) - This is the MessageParam format
        # Construct it manually like Agent.execute_agent does
        expected_assistant_msg_param_turn1 = {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_use_id,
                    "name": tool_name,
                    "input": tool_input,
                }
            ],
        }
        assert actual_messages_turn2[1] == expected_assistant_msg_param_turn1
        # Check User Message (Turn 2 - Tool Result)
        assert actual_messages_turn2[2] == expected_messages_turn2[2]

        assert call2_kwargs["tools_data"] == []
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
        assert (
            len(result.conversation) == 4
        )  # user -> assistant(tool) -> user(result) -> assistant(final)
        assert result.conversation[0].role == "user"
        assert (
            result.conversation[1] == mock_assistant_response_turn1
        )  # Check assistant turn 1
        assert result.conversation[2].role == "user"  # Check user turn 2 (tool result)
        # Check the content of the user message containing the tool result
        assert len(result.conversation[2].content) == 1
        tool_result_block = result.conversation[2].content[0]
        assert isinstance(tool_result_block, AgentOutputContentBlock)
        assert tool_result_block.type == "tool_result"
        assert tool_result_block.tool_use_id == tool_use_id
        # The raw content is stored in model_extra due to extra='allow'
        assert tool_result_block.model_extra is not None
        assert tool_result_block.model_extra.get("content") == tool_result_content_str

        assert (
            result.conversation[3] == mock_final_assistant_response_turn2
        )  # Check assistant turn 2

    @pytest.mark.anyio
    @patch("src.agents.agent.AgentTurnProcessor", autospec=True)  # Patch the class
    async def test_execute_agent_max_iterations_reached(
        self,
        MockAgentTurnProcessor: MagicMock,  # The patched class
        agent_instance: Agent,
        mock_mcp_host: MagicMock,
        initial_messages: List[MessageParam],
        mock_agent_config: AgentConfig,  # Use fixture, will check max_iterations
        mock_llm_client: MagicMock,
    ):
        """
        Tests that the agent execution loop terminates after reaching max_iterations.
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
        mock_turn_processor_instance.process_turn = AsyncMock(
            return_value=(
                mock_assistant_response_loop,  # Return a response object
                None,  # No tool results needed for this mock
                False,  # IMPORTANT: Never signal final turn
            )
        )
        # Configure other methods
        mock_turn_processor_instance.get_last_llm_response.return_value = (
            mock_assistant_response_loop
        )
        mock_turn_processor_instance.get_tool_uses_this_turn.return_value = []

        # --- Act ---
        result: AgentExecutionResult = await agent_instance.execute_agent(
            initial_messages=initial_messages,
            host_instance=mock_mcp_host,
            system_prompt=None,
        )

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

        # 4. Conversation history check (user + assistant * max_iters)
        assert len(result.conversation) == 1 + max_iters
        assert result.conversation[0].role == "user"
        for i in range(max_iters):
            assert result.conversation[i + 1] == mock_assistant_response_loop

    @pytest.mark.anyio
    @patch("src.agents.agent.AgentTurnProcessor", autospec=True)  # Patch the class
    async def test_execute_agent_schema_correction_loop(
        self,
        MockAgentTurnProcessor: MagicMock,  # The patched class
        agent_instance: Agent,
        mock_mcp_host: MagicMock,
        initial_messages: List[MessageParam],  # User: "Hello Agent"
        mock_agent_config: AgentConfig,  # Use fixture, but will modify it
        mock_llm_client: MagicMock,
    ):
        """
        Tests execute_agent handles the schema correction loop.
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
        result: AgentExecutionResult = await agent_instance.execute_agent(
            initial_messages=initial_messages,
            host_instance=mock_mcp_host,
            system_prompt=None,
        )

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

        # Call 2 Args (Should include initial user, invalid assistant, and correction user message)
        call2_kwargs = call_args_list[1].kwargs
        actual_messages_turn2 = call2_kwargs["current_messages"]
        assert len(actual_messages_turn2) == 3
        assert actual_messages_turn2[0]["role"] == "user"  # Initial user
        assert (
            actual_messages_turn2[1]["role"] == "assistant"
        )  # Invalid assistant response
        assert actual_messages_turn2[1]["content"][0]["text"] == invalid_json_text
        assert actual_messages_turn2[2]["role"] == "user"  # Correction message
        # Check the text content within the first block of the correction message
        assert len(actual_messages_turn2[2]["content"]) == 1
        assert actual_messages_turn2[2]["content"][0]["type"] == "text"
        assert (
            "must be a valid JSON object matching this schema"
            in actual_messages_turn2[2]["content"][0]["text"]
        )

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
        assert (
            result.conversation[1] == mock_assistant_response_turn1
        )  # Invalid response is logged
        assert result.conversation[2].role == "user"  # Correction message
        assert (
            "must be a valid JSON object matching this schema"
            in result.conversation[2].content[0].text
        )
        assert (
            result.conversation[3] == mock_final_assistant_response_turn2
        )  # Valid final response
