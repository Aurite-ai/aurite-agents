"""
Unit tests for the AgentTurnProcessor class.
"""

from typing import List  # Import List
from unittest.mock import AsyncMock, MagicMock  # Added patch

import pytest
from anthropic.types import MessageParam

from aurite.agents.agent_models import AgentOutputContentBlock, AgentOutputMessage

# Import necessary types and classes
from aurite.agents.agent_turn_processor import AgentTurnProcessor
from aurite.config.config_models import AgentConfig
from aurite.host.host import MCPHost

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
    mock_client = MagicMock()  # No spec for now to simplify stream_message mocking
    mock_client.create_message = AsyncMock()
    # stream_message will be configured directly in the test
    return mock_client


# --- Helper Fake LLM Client for Streaming Test ---
class FakeLLMClient:
    def __init__(self, event_sequence: List[dict]):
        self.event_sequence = event_sequence
        self.create_message = (
            AsyncMock()
        )  # Keep create_message as an AsyncMock if other tests use it
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
        assert turn_processor.get_last_llm_response() == mock_llm_response_obj
        assert turn_processor.get_tool_uses_this_turn() == []
