"""
Unit tests for the AgentTurnProcessor class.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock # Added patch
from typing import List  # Import List

# Import necessary types and classes
from src.agents.agent_turn_processor import AgentTurnProcessor
from src.agents.agent_models import AgentOutputMessage, AgentOutputContentBlock
from src.config.config_models import AgentConfig
from src.host.host import MCPHost
from anthropic.types import MessageParam

# --- Test Fixtures ---


@pytest.fixture
def mock_agent_config() -> AgentConfig:
    """Provides a basic mock AgentConfig."""
    return AgentConfig(
        name="TestAgent",
        llm_config_id="test_llm",  # Assume an LLM config exists
        # No schema defined for basic tests
    )


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Provides a simplified mock LLM client for focused testing."""
    mock_client = MagicMock() # No spec for now to simplify stream_message mocking
    mock_client.create_message = AsyncMock()
    # stream_message will be configured directly in the test
    return mock_client


# --- Helper Fake LLM Client for Streaming Test ---
class FakeLLMClient:
    def __init__(self, event_sequence: List[dict]):
        self.event_sequence = event_sequence
        self.create_message = AsyncMock() # Keep create_message as an AsyncMock if other tests use it
        # stream_message will be a real async def method returning an async generator
        self.stream_message_call_args = None
        self.stream_message_call_count = 0

    async def stream_message(self, *args, **kwargs):
        self.stream_message_call_args = (args, kwargs)
        self.stream_message_call_count += 1
        for event in self.event_sequence:
            yield event

@pytest.fixture
def mock_mcp_host() -> MagicMock:
    """Provides a mock MCPHost instance."""
    mock_host = MagicMock(spec=MCPHost)
    mock_host.get_formatted_tools = MagicMock(return_value=[])  # No tools by default
    mock_host.execute_tool = AsyncMock()  # Make the method async
    # Mock the tool manager helper if needed later
    mock_host.tools = MagicMock()
    mock_host.tools.create_tool_result_blocks = MagicMock(
        return_value={
            "type": "tool_result",
            "tool_use_id": "mock_id",
            "content": "mock result",
        }
    )
    return mock_host


@pytest.fixture
def initial_messages() -> List[MessageParam]:
    """Provides a basic list of initial messages."""
    return [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}]


# --- Test Class ---


@pytest.mark.unit
@pytest.mark.orchestration  # Mark as orchestration layer test
class TestAgentTurnProcessorUnit:
    """Unit tests for AgentTurnProcessor."""

    @pytest.mark.anyio
    async def test_process_turn_success_no_tool_no_schema(
        self,
        mock_agent_config: AgentConfig,
        mock_llm_client: MagicMock,
        mock_mcp_host: MagicMock,
        initial_messages: List[MessageParam],
    ):
        """
        Tests a successful turn processing with a simple text response,
        no tool usage requested, and no schema validation configured.
        """
        # --- Arrange ---
        # Mock LLM response
        mock_llm_response_obj = AgentOutputMessage(
            id="llm_msg_1",
            role="assistant",
            model="test_model",
            content=[AgentOutputContentBlock(type="text", text="Hi there!")],
            stop_reason="end_turn",
            usage={"input_tokens": 10, "output_tokens": 5},
        )
        mock_llm_client.create_message.return_value = mock_llm_response_obj

        # Instantiate the processor
        turn_processor = AgentTurnProcessor(
            config=mock_agent_config,
            llm_client=mock_llm_client,
            host_instance=mock_mcp_host,
            current_messages=initial_messages,
            tools_data=None,  # No tools passed for this scenario
            effective_system_prompt="You are helpful.",
        )

        # --- Act ---
        final_response, tool_results, is_final = await turn_processor.process_turn()

        # --- Assert ---
        # LLM client called correctly
        mock_llm_client.create_message.assert_awaited_once_with(
            messages=initial_messages,
            tools=None,
            system_prompt_override="You are helpful.",
            schema=None,  # Agent config has no schema
            llm_config_override=None,  # Expecting default None
        )

        # Correct results returned
        assert (
            final_response == mock_llm_response_obj
        )  # Should return the LLM response directly
        assert tool_results is None  # No tool calls expected
        assert is_final is True  # Should be the final turn

        # Internal state check (optional but good)
        assert (
            turn_processor.get_last_llm_response() == mock_llm_response_obj
        )  # Should still store the raw response
        assert turn_processor.get_tool_uses_this_turn() == []

    @pytest.mark.anyio
    async def test_process_turn_tool_use_success(
        self,
        mock_agent_config: AgentConfig,
        mock_llm_client: MagicMock,
        mock_mcp_host: MagicMock,
        initial_messages: List[MessageParam],
    ):
        """
        Tests turn processing where the LLM requests a tool use and the
        tool execution via MCPHost is successful.
        """
        # --- Arrange ---
        tool_name = "get_weather"
        tool_input = {"location": "London"}
        tool_use_id = "tool_abc"
        tool_result_content = {"temperature": 15, "unit": "celsius"}

        # Mock LLM response requesting tool use
        mock_llm_response_obj = AgentOutputMessage(
            id="llm_msg_tool_req",
            role="assistant",
            model="test_model",
            content=[
                AgentOutputContentBlock(
                    type="tool_use",
                    id=tool_use_id,
                    name=tool_name,
                    input=tool_input,
                )
            ],
            stop_reason="tool_use",
            usage={"input_tokens": 30, "output_tokens": 20},
        )
        mock_llm_client.create_message.return_value = mock_llm_response_obj

        # Mock successful tool execution in MCPHost
        mock_mcp_host.execute_tool.return_value = tool_result_content

        # Mock the creation of the result block by the host's tool manager
        # This dict structure should match ToolResultBlockParam
        mock_tool_result_block_param = {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": [
                {"type": "text", "text": str(tool_result_content)}
            ],  # Example: stringified result
            # Or potentially: "content": tool_result_content if the result is simple JSON
        }
        mock_mcp_host.tools.create_tool_result_blocks.return_value = (
            mock_tool_result_block_param
        )

        # Define expected tool result message param for assertion
        expected_tool_result_message: MessageParam = {
            "role": "user",
            "content": [mock_tool_result_block_param],  # Use the mocked block structure
        }

        # Instantiate the processor
        turn_processor = AgentTurnProcessor(
            config=mock_agent_config,
            llm_client=mock_llm_client,
            host_instance=mock_mcp_host,
            current_messages=initial_messages,
            tools_data=[
                {"name": tool_name, "description": "desc", "input_schema": {}}
            ],  # Need tools_data for LLM call
            effective_system_prompt="You are helpful.",
        )

        # --- Act ---
        final_response, tool_results, is_final = await turn_processor.process_turn()

        # --- Assert ---
        # LLM client called correctly
        mock_llm_client.create_message.assert_awaited_once()  # Basic check

        # Host execute_tool called correctly
        mock_mcp_host.execute_tool.assert_awaited_once_with(
            tool_name=tool_name,
            arguments=tool_input,
            agent_config=mock_agent_config,
        )
        # Host create_tool_result_blocks called correctly
        mock_mcp_host.tools.create_tool_result_blocks.assert_called_once_with(
            tool_use_id=tool_use_id, tool_result=tool_result_content
        )

        # Correct results returned from process_turn
        assert final_response is None  # Not the final response yet
        assert tool_results is not None
        assert len(tool_results) == 1
        assert (
            tool_results[0] == expected_tool_result_message
        )  # Check content matches expected
        assert is_final is False  # Not the final turn

        # Internal state check
        assert turn_processor.get_last_llm_response() == mock_llm_response_obj
        assert turn_processor.get_tool_uses_this_turn() == [
            {"id": tool_use_id, "name": tool_name, "input": tool_input}
        ]

    @pytest.mark.anyio
    async def test_process_turn_tool_use_failure(
        self,
        mock_agent_config: AgentConfig,
        mock_llm_client: MagicMock,
        mock_mcp_host: MagicMock,
        initial_messages: List[MessageParam],
    ):
        """
        Tests turn processing where the LLM requests a tool use but the
        tool execution via MCPHost fails.
        """
        # --- Arrange ---
        tool_name = "flaky_tool"
        tool_input = {"param": "value"}
        tool_use_id = "tool_def"
        error_message = "Tool execution failed spectacularly!"

        # Mock LLM response requesting tool use
        mock_llm_response_obj = AgentOutputMessage(
            id="llm_msg_tool_fail",
            role="assistant",
            model="test_model",
            content=[
                AgentOutputContentBlock(
                    type="tool_use",
                    id=tool_use_id,
                    name=tool_name,
                    input=tool_input,
                )
            ],
            stop_reason="tool_use",
            usage={"input_tokens": 35, "output_tokens": 25},
        )
        mock_llm_client.create_message.return_value = mock_llm_response_obj

        # Mock failed tool execution in MCPHost
        mock_mcp_host.execute_tool.side_effect = Exception(error_message)

        # Mock the creation of the error result block by the host's tool manager
        mock_error_result_block_param = {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": [
                {
                    "type": "text",
                    "text": f"Error executing tool '{tool_name}': {error_message}",
                }
            ],
            "is_error": True,  # Assuming the helper sets this
        }
        # Adjust the mock return value for create_tool_result_blocks
        # It should be called with the error string as tool_result
        mock_mcp_host.tools.create_tool_result_blocks.return_value = (
            mock_error_result_block_param
        )

        # Define expected tool result message param for assertion
        expected_tool_error_message: MessageParam = {
            "role": "user",
            "content": [
                mock_error_result_block_param
            ],  # Use the mocked error block structure
        }

        # Instantiate the processor
        turn_processor = AgentTurnProcessor(
            config=mock_agent_config,
            llm_client=mock_llm_client,
            host_instance=mock_mcp_host,
            current_messages=initial_messages,
            tools_data=[{"name": tool_name, "description": "desc", "input_schema": {}}],
            effective_system_prompt="You are helpful.",
        )

        # --- Act ---
        final_response, tool_results, is_final = await turn_processor.process_turn()

        # --- Assert ---
        # LLM client called correctly
        mock_llm_client.create_message.assert_awaited_once()

        # Host execute_tool called correctly
        mock_mcp_host.execute_tool.assert_awaited_once_with(
            tool_name=tool_name,
            arguments=tool_input,
            agent_config=mock_agent_config,
        )
        # Host create_tool_result_blocks called correctly with the error
        mock_mcp_host.tools.create_tool_result_blocks.assert_called_once_with(
            tool_use_id=tool_use_id,
            tool_result=f"Error executing tool '{tool_name}': {error_message}",  # Verify error string passed
        )

        # Correct results returned from process_turn
        assert final_response is None  # Not the final response yet
        assert tool_results is not None
        assert len(tool_results) == 1
        # Check the structure and content of the error message block
        assert tool_results[0]["role"] == "user"
        assert len(tool_results[0]["content"]) == 1
        error_block = tool_results[0]["content"][0]
        assert error_block["type"] == "tool_result"
        assert error_block["tool_use_id"] == tool_use_id
        # Check if 'is_error' is present if the mock includes it
        # assert error_block.get("is_error") is True
        # Check the error message content (might need adjustment based on create_tool_result_blocks actual output)
        assert (
            f"Error executing tool '{tool_name}': {error_message}"
            in error_block["content"][0]["text"]
        )

        assert is_final is False  # Not the final turn

        # Internal state check
        assert turn_processor.get_last_llm_response() == mock_llm_response_obj
        assert turn_processor.get_tool_uses_this_turn() == [
            {
                "id": tool_use_id,
                "name": tool_name,
                "input": tool_input,
            }  # Still records the attempt
        ]

    @pytest.mark.anyio
    async def test_process_turn_schema_validation_failure(
        self,
        mock_agent_config: AgentConfig,  # Re-use basic config fixture
        mock_llm_client: MagicMock,
        mock_mcp_host: MagicMock,
        initial_messages: List[MessageParam],
    ):
        """
        Tests turn processing where a schema is defined but the LLM response
        contains invalid JSON or JSON not matching the schema.
        It should signal that the turn is not final.
        """
        # --- Arrange ---
        # Define a schema and INVALID JSON content (missing required field)
        test_schema = {
            "type": "object",
            "properties": {"result": {"type": "string"}},
            "required": ["result"],
        }
        invalid_json_text = '{"wrong_key": "failure"}'  # Missing 'result'

        # Update the mock agent config with the schema
        mock_agent_config.config_validation_schema = test_schema

        # Mock LLM response with invalid JSON
        mock_llm_response_obj = AgentOutputMessage(
            id="llm_msg_schema_invalid",
            role="assistant",
            model="test_model",
            content=[AgentOutputContentBlock(type="text", text=invalid_json_text)],
            stop_reason="end_turn",  # Stop reason is end_turn, but validation fails
            usage={"input_tokens": 25, "output_tokens": 10},
        )
        mock_llm_client.create_message.return_value = mock_llm_response_obj

        # Instantiate the processor
        turn_processor = AgentTurnProcessor(
            config=mock_agent_config,  # Use updated config
            llm_client=mock_llm_client,
            host_instance=mock_mcp_host,
            current_messages=initial_messages,
            tools_data=None,
            effective_system_prompt="You are helpful.",
        )

        # --- Act ---
        final_response, tool_results, is_final = await turn_processor.process_turn()

        # --- Assert ---
        # LLM client called correctly
        mock_llm_client.create_message.assert_awaited_once_with(
            messages=initial_messages,
            tools=None,
            system_prompt_override="You are helpful.",
            schema=test_schema,  # Schema was passed
            llm_config_override=None,  # Expecting default None
        )

        # Correct results returned - validation fails
        assert final_response is None  # Should be None as validation failed
        assert tool_results is None  # No tool calls expected
        assert is_final is False  # Should NOT be final turn, needs correction

        # Internal state check
        assert (
            turn_processor.get_last_llm_response() == mock_llm_response_obj
        )  # Should still store the raw response
        assert turn_processor.get_tool_uses_this_turn() == []

    @pytest.mark.anyio
    async def test_process_turn_success_no_tool_with_valid_schema(
        self,
        mock_agent_config: AgentConfig,  # Re-use basic config fixture
        mock_llm_client: MagicMock,
        mock_mcp_host: MagicMock,
        initial_messages: List[MessageParam],
    ):
        """
        Tests successful turn processing where a schema is defined and the
        LLM response contains valid JSON matching the schema.
        """
        # --- Arrange ---
        # Define a schema and valid JSON content
        test_schema = {
            "type": "object",
            "properties": {"result": {"type": "string"}},
            "required": ["result"],
        }
        valid_json_text = '{"result": "success"}'

        # Update the mock agent config with the schema
        mock_agent_config.config_validation_schema = test_schema

        # Mock LLM response with valid JSON
        mock_llm_response_obj = AgentOutputMessage(
            id="llm_msg_schema_valid",
            role="assistant",
            model="test_model",
            content=[AgentOutputContentBlock(type="text", text=valid_json_text)],
            stop_reason="end_turn",
            usage={"input_tokens": 20, "output_tokens": 15},
        )
        mock_llm_client.create_message.return_value = mock_llm_response_obj

        # Instantiate the processor
        turn_processor = AgentTurnProcessor(
            config=mock_agent_config,  # Use updated config
            llm_client=mock_llm_client,
            host_instance=mock_mcp_host,
            current_messages=initial_messages,
            tools_data=None,
            effective_system_prompt="You are helpful.",
        )

        # --- Act ---
        final_response, tool_results, is_final = await turn_processor.process_turn()

        # --- Assert ---
        # LLM client called correctly (should include schema in call)
        mock_llm_client.create_message.assert_awaited_once_with(
            messages=initial_messages,
            tools=None,
            system_prompt_override="You are helpful.",
            schema=test_schema,  # Verify schema was passed to LLM client
            llm_config_override=None,  # Expecting default None
        )

        # Correct results returned - validation passes, so return original response
        assert final_response == mock_llm_response_obj
        assert tool_results is None
        assert is_final is True  # Should be final turn as validation passed

        # Internal state check
        assert turn_processor.get_last_llm_response() == mock_llm_response_obj
        assert turn_processor.get_tool_uses_this_turn() == []

    @pytest.mark.anyio
    async def test_stream_turn_response_handles_sse_indices_correctly(
        self,
        mock_agent_config: AgentConfig,
        mock_llm_client: MagicMock,
        mock_mcp_host: MagicMock,
        initial_messages: List[MessageParam],
    ):
        """
        Tests that stream_turn_response correctly assigns unique and sequential
        frontend SSE indices when the LLM reuses indices for different conceptual blocks.
        Scenario: Thinking (LLM idx 0) -> Tool Use (LLM idx 1) -> Final Response (LLM idx 0 again)
        Expected Frontend Indices: Thinking (fidx 0), Tool (fidx 1), Final Response (fidx 2)
        """
        # --- Arrange ---
        # 1. The mock_llm_client fixture provides a client with stream_message
        #    already as an AsyncMock. We will reconfigure its side_effect for this specific test.

        # 2. Define the sequence of LLM events for this specific test
        # Note: llm_event_original_index is what the LLM client provides in event_data["index"]
        #       final_frontend_idx_to_yield is what we expect ATP to put in event_data["index"]

        llm_event_sequence = [
            # Block 1: Thinking (LLM index 0) -> Expected Frontend Index 0
            {"event_type": "text_block_start", "data": {"index": 0, "text": ""}},
            {"event_type": "text_delta", "data": {"index": 0, "delta": "Thinking..."}},
            {"event_type": "content_block_stop", "data": {"index": 0}},

            # Block 2: Tool Use (LLM index 1, tool_id T1) -> Expected Frontend Index 1
            {"event_type": "tool_use_start", "data": {"index": 1, "tool_id": "T1", "tool_name": "test_tool", "input_json_schema": {}}},
            {"event_type": "tool_use_input_delta", "data": {"index": 1, "json_chunk": '{"param":'}},
            {"event_type": "tool_use_input_delta", "data": {"index": 1, "json_chunk": ' "value"}'}},
            {"event_type": "content_block_stop", "data": {"index": 1}}, # LLM signals end of tool_use block specification

            # Block 3: Final Response (LLM index 0 again) -> Expected Frontend Index 2
            {"event_type": "text_block_start", "data": {"index": 0, "text": ""}}, # LLM reuses index 0
            {"event_type": "text_delta", "data": {"index": 0, "delta": '{"result": "done"}'}},
            {"event_type": "content_block_stop", "data": {"index": 0}},

            # End of LLM stream
            {"event_type": "stream_end", "data": {"stop_reason": "end_turn"}}
        ]

        async def mock_llm_stream_generator_func(*args, **kwargs): # Add *args, **kwargs to accept any call signature
            for event in llm_event_sequence:
                yield event

        # Instead of complex mocking, we'll use a FakeLLMClient instance.
        fake_llm_client = FakeLLMClient(event_sequence=llm_event_sequence)

        # 3. Mock mcp_host.execute_tool for the tool call
        mock_mcp_host.execute_tool.return_value = {"tool_output": "success"}
        # Mock the tool result block creation (simplified)
        mock_mcp_host.tools.create_tool_result_blocks.return_value = {
            "type": "tool_result", "tool_use_id": "T1", "content": "mock tool result"
        }


        # 4. Instantiate AgentTurnProcessor with the FakeLLMClient
        turn_processor = AgentTurnProcessor(
            config=mock_agent_config,
            llm_client=fake_llm_client, # Use the fake client
            host_instance=mock_mcp_host,
            current_messages=initial_messages,
            tools_data=[{"name": "test_tool", "description": "A test tool", "input_schema": {}}], # Ensure tool is in tools_data
            effective_system_prompt="You are helpful.",
        )

        # --- Act ---
        collected_sse_events = []
        async for sse_event in turn_processor.stream_turn_response():
            collected_sse_events.append(sse_event)

        # --- Assert ---
        # Verify the stream_message method on the fake client was called.
        assert fake_llm_client.stream_message_call_count == 1
        # We can also check call arguments if needed:
        # fake_llm_client.stream_message_call_args[1]["messages"] == initial_messages

        # Verify tool execution if a tool was used
        mock_mcp_host.execute_tool.assert_awaited_once_with(
            tool_name="test_tool", arguments={"param": "value"}, agent_config=mock_agent_config
        )

        # Expected frontend indices for conceptual blocks
        expected_frontend_indices = {
            "thinking_block_llm_idx_0": 0,
            "tool_block_llm_idx_1_id_T1": 1,
            "final_response_block_llm_idx_0": 2,
        }

        # Detailed assertions on yielded SSE events
        # We need to map the original LLM event to its expected frontend index
        # and check the 'index' in the 'data' of the yielded SSE.

        # Event 0: text_block_start (Thinking)
        assert collected_sse_events[0]["event_type"] == "text_block_start"
        assert collected_sse_events[0]["data"]["index"] == expected_frontend_indices["thinking_block_llm_idx_0"]

        # Event 1: text_delta (Thinking)
        assert collected_sse_events[1]["event_type"] == "text_delta"
        assert collected_sse_events[1]["data"]["index"] == expected_frontend_indices["thinking_block_llm_idx_0"]

        # Event 2: content_block_stop (Thinking)
        assert collected_sse_events[2]["event_type"] == "content_block_stop"
        assert collected_sse_events[2]["data"]["index"] == expected_frontend_indices["thinking_block_llm_idx_0"]

        # Event 3: tool_use_start (Tool T1)
        assert collected_sse_events[3]["event_type"] == "tool_use_start"
        assert collected_sse_events[3]["data"]["index"] == expected_frontend_indices["tool_block_llm_idx_1_id_T1"]
        assert collected_sse_events[3]["data"]["tool_id"] == "T1"

        # Event 4: tool_use_input_delta (Tool T1)
        assert collected_sse_events[4]["event_type"] == "tool_use_input_delta"
        assert collected_sse_events[4]["data"]["index"] == expected_frontend_indices["tool_block_llm_idx_1_id_T1"]

        # Event 5: tool_use_input_delta (Tool T1)
        assert collected_sse_events[5]["event_type"] == "tool_use_input_delta"
        assert collected_sse_events[5]["data"]["index"] == expected_frontend_indices["tool_block_llm_idx_1_id_T1"]

        # Event 6: content_block_stop (Tool T1 specification by LLM)
        assert collected_sse_events[6]["event_type"] == "content_block_stop"
        assert collected_sse_events[6]["data"]["index"] == expected_frontend_indices["tool_block_llm_idx_1_id_T1"]

        # Event 7: tool_use_input_complete (Generated by ATP after parsing tool input)
        assert collected_sse_events[7]["event_type"] == "tool_result"
        assert collected_sse_events[7]["data"]["index"] == expected_frontend_indices["tool_block_llm_idx_1_id_T1"]
        assert collected_sse_events[7]["data"]["input"] == {"param": "value"}

        # Event 8: tool_result (Generated by ATP after tool execution)
        assert collected_sse_events[8]["event_type"] == "tool_result"
        assert collected_sse_events[8]["data"]["index"] == expected_frontend_indices["tool_block_llm_idx_1_id_T1"]
        assert collected_sse_events[8]["data"]["tool_use_id"] == "T1"
        assert collected_sse_events[8]["data"]["output"] == {"tool_output": "success"} # From mock_mcp_host

        # Event 9: text_block_start (Final Response, LLM reuses index 0)
        assert collected_sse_events[9]["event_type"] == "text_block_start"
        assert collected_sse_events[9]["data"]["index"] == expected_frontend_indices["final_response_block_llm_idx_0"]

        # Event 10: text_delta (Final Response)
        assert collected_sse_events[10]["event_type"] == "text_delta"
        assert collected_sse_events[10]["data"]["index"] == expected_frontend_indices["final_response_block_llm_idx_0"]

        # Event 11: content_block_stop (Final Response)
        assert collected_sse_events[11]["event_type"] == "content_block_stop"
        assert collected_sse_events[11]["data"]["index"] == expected_frontend_indices["final_response_block_llm_idx_0"]

        # Event 12: llm_call_completed (Generated by ATP from LLM's stream_end)
        assert collected_sse_events[12]["event_type"] == "llm_call_completed"
        assert collected_sse_events[12]["data"]["stop_reason"] == "end_turn"

        # Check total number of events if precise
        assert len(collected_sse_events) == 13
