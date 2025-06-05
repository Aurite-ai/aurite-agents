"""
Integration tests for the Agent class orchestration with MCPHost.

These tests use a real MCPHost instance managed by the host_manager fixture,
which connects to mock MCP servers (like the weather server).
LLM calls are typically mocked to control agent behavior for testing host interactions.
"""

import os  # Import os for environment variable check
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mark all tests in this module
pytestmark = [pytest.mark.orchestration, pytest.mark.integration, pytest.mark.anyio]

# Imports from the project
from aurite.components.agents.agent_models import (
    AgentOutputContentBlock,
    AgentOutputMessage,
    AgentExecutionResult,
)
from aurite.host_manager import Aurite  # For host_manager fixture type hint
from aurite.llm.base_client import BaseLLM  # For mocking

# Import shared fixtures if needed (host_manager is usually sufficient)
# from ..fixtures.host_fixtures import host_manager # Assuming host_manager is available globally

# --- Test Class ---


class TestAgentIntegration:
    """Integration tests for Agent interacting with MCPHost."""

    @pytest.mark.anyio
    async def test_agent_integration_tool_call_mock_llm(
        self,
        host_manager: Aurite,  # Use the real host manager fixture
    ):
        """
        Tests agent execution that involves calling a tool via the real MCPHost,
        using a mocked LLM client to trigger the tool call.
        """
        # --- Arrange ---
        # Get a relevant agent config using the new getter method
        agent_config = host_manager.get_agent_config("Weather Agent")
        assert agent_config is not None, (
            "Weather Agent config not found in host_manager"
        )

        # Create a mock LLM client
        mock_llm = MagicMock(spec=BaseLLM)

        # Define initial user message
        user_message = "What's the weather in London?"

        # Mock LLM response sequence
        tool_name = "weather_lookup"
        tool_use_id = "tool_weather_123"
        tool_input = {"location": "London", "unit": "celsius"}

        # Mock LLM Turn 1: Request tool use
        mock_llm_response_turn1 = AgentOutputMessage(
            id="llm_msg_tool_req",
            role="assistant",
            model="mock_model",
            content=[
                AgentOutputContentBlock(
                    type="tool_use", id=tool_use_id, name=tool_name, input=tool_input
                )
            ],
            stop_reason="tool_use",
            usage={"input_tokens": 10, "output_tokens": 10},
        )

        # Mock LLM Turn 2: Final response after tool result
        # The actual tool result comes from the mock server via MCPHost
        mock_llm_response_turn2 = AgentOutputMessage(
            id="llm_msg_final",
            role="assistant",
            model="mock_model",
            content=[
                AgentOutputContentBlock(
                    type="text",
                    text='{"weather_summary": "Mocked: The weather in London is clear.", "temperature": {"value": 15, "unit": "celsius"}, "recommendations": ["Enjoy your day!"]}',
                )
            ],
            stop_reason="end_turn",
            usage={
                "input_tokens": 20,
                "output_tokens": 50,
            },  # Adjusted token count for JSON
        )

        mock_llm.create_message = AsyncMock(
            side_effect=[mock_llm_response_turn1, mock_llm_response_turn2]
        )

        # Patch the LLM client instantiation within the facade for this specific agent run
        # This is tricky because the facade instantiates the LLM client internally.
        # A cleaner way might be dependency injection for the LLM client factory in the facade,
        # but for now, let's patch the specific client class it tries to instantiate.
        # We assume it will try to instantiate AnthropicLLM based on current facade logic.
        with patch(
            "aurite.execution.facade.AnthropicLLM", return_value=mock_llm
        ) as MockAnthropicLLM:
            # --- Act ---
            # Execute agent via the facade
            assert host_manager.execution is not None, "Facade not initialized"
            agent_result: AgentExecutionResult = await host_manager.execution.run_agent(
                agent_name="Weather Agent",
                user_message=user_message,
                system_prompt=None,  # Use agent default
                session_id=None,  # Not testing history here
            )

            # --- Assert ---
            # 1. Check LLM Client was instantiated (patched)
            # MockAnthropicLLM.assert_called_once() # Check args if needed

            # 2. Check LLM mock was called twice
            assert mock_llm.create_message.await_count == 2

            # 3. Check final result structure (now an AgentExecutionResult object)
            assert isinstance(agent_result, AgentExecutionResult)
            assert agent_result.error is None
            final_response_obj = agent_result.final_response
            assert final_response_obj is not None
            assert final_response_obj.role == "assistant"
            # Find primary text in the AgentOutputMessage
            primary_text = None
            if final_response_obj.content:
                for (
                    block
                ) in final_response_obj.content:  # block is AgentOutputContentBlock
                    if block.type == "text":
                        primary_text = block.text
                        break
            expected_primary_text = '{"weather_summary": "Mocked: The weather in London is clear.", "temperature": {"value": 15, "unit": "celsius"}, "recommendations": ["Enjoy your day!"]}'
            assert primary_text == expected_primary_text

            # 4. Check tool use was recorded in the result
            # tool_uses_in_final_turn is List[Dict[str, Any]]
            tool_uses = agent_result.tool_uses_in_final_turn
            assert len(tool_uses) == 1
            assert tool_uses[0]["id"] == tool_use_id
            assert tool_uses[0]["name"] == tool_name
            assert tool_uses[0]["input"] == tool_input

            # 5. Check conversation history (list of AgentOutputMessage objects)
            conversation_history = agent_result.conversation
            assert (
                len(conversation_history) == 4
            )  # user -> assistant(tool) -> user(result) -> assistant(final)
            assert conversation_history[0].role == "user"
            assert conversation_history[1].role == "assistant"
            assert conversation_history[1].content[0].type == "tool_use"
            assert conversation_history[2].role == "user"  # Tool result message
            # Check how the user message with tool result is structured
            tool_result_content_block = conversation_history[2].content[0]
            assert tool_result_content_block.type == "tool_result"
            assert tool_result_content_block.tool_use_id == tool_use_id
            # Check the actual result text from the mock weather server via MCPHost
            # The content of the tool_result block is a list of AgentOutputContentBlock
            assert tool_result_content_block.content is not None
            inner_content_blocks = tool_result_content_block.content
            assert isinstance(inner_content_blocks, list)
            assert len(inner_content_blocks) > 0
            assert inner_content_blocks[0].type == "text"
            tool_result_text = inner_content_blocks[0].text
            assert tool_result_text is not None
            assert (
                "Weather for London:" in tool_result_text
            )  # Match actual mock server output format
            assert (
                "Temp 15°C" in tool_result_text  # Check for new format
            )  # Check within the text content

            assert conversation_history[3].role == "assistant"
            # Find primary text in the last message
            final_primary_text = None
            if conversation_history[3].content:
                for block in conversation_history[3].content:
                    if block.type == "text":
                        final_primary_text = block.text
                        break
            assert final_primary_text == expected_primary_text

    @pytest.mark.anyio
    async def test_agent_integration_schema_validation_mock_llm(
        self,
        host_manager: Aurite,
    ):
        """
        Tests agent execution with schema validation where the LLM provides
        a valid response matching the schema (using mocked LLM).
        """
        # --- Arrange ---
        agent_name = "Weather Agent"  # This agent has a schema defined
        agent_config = host_manager.get_agent_config(agent_name)
        assert agent_config is not None, f"'{agent_name}' config not found"
        assert agent_config.config_validation_schema is not None, (
            f"'{agent_name}' should have a validation schema"
        )

        mock_llm = MagicMock(spec=BaseLLM)
        user_message = "Weather in Boston?"

        # Mock LLM response - valid JSON matching the Weather Agent's schema
        valid_json_response = {
            "weather_summary": "Mocked: Sunny and pleasant",
            "temperature": {"value": 22, "unit": "celsius"},  # Corrected structure
            "recommendations": ["Wear sunscreen", "Enjoy the day!"],
        }
        import json

        valid_json_text = json.dumps(valid_json_response)

        mock_llm_response = AgentOutputMessage(
            id="llm_msg_valid_schema",
            role="assistant",
            model="mock_model",
            content=[AgentOutputContentBlock(type="text", text=valid_json_text)],
            stop_reason="end_turn",
            usage={"input_tokens": 15, "output_tokens": 50},
        )
        mock_llm.create_message = AsyncMock(return_value=mock_llm_response)

        # Patch LLM client instantiation in the facade
        with patch(
            "aurite.execution.facade.AnthropicLLM", return_value=mock_llm
        ) as MockAnthropicLLM:
            # --- Act ---
            assert host_manager.execution is not None, "Facade not initialized"
            agent_result: AgentExecutionResult = await host_manager.execution.run_agent(
                agent_name=agent_name,
                user_message=user_message,
                session_id=None,
            )

            # --- Assert ---
            # 1. LLM mock called once
            assert mock_llm.create_message.await_count == 1
            # Check schema was passed to LLM client
            call_args = mock_llm.create_message.call_args.kwargs
            assert call_args.get("schema") == agent_config.config_validation_schema

            # 2. Final result is successful
            assert isinstance(agent_result, AgentExecutionResult)
            assert agent_result.error is None
            final_response_obj = agent_result.final_response
            assert final_response_obj is not None
            assert final_response_obj.role == "assistant"
            assert final_response_obj.stop_reason == "end_turn"

            # 3. Final response content matches the valid JSON text
            primary_text = None
            if final_response_obj.content:
                for (
                    block
                ) in final_response_obj.content:  # block is AgentOutputContentBlock
                    if block.type == "text":
                        primary_text = block.text
                        break
            assert primary_text == valid_json_text

            # 4. Conversation history should only have user -> assistant (no correction message)
            conversation_history = agent_result.conversation
            assert len(conversation_history) == 2
            assert conversation_history[0].role == "user"
            assert conversation_history[1].role == "assistant"
            assert (
                conversation_history[1].content[0].type == "text"
            )  # Ensure it's a text block
            assert conversation_history[1].content[0].text == valid_json_text

    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="Requires ANTHROPIC_API_KEY environment variable for real LLM calls",
    )
    @pytest.mark.anyio
    async def test_agent_integration_real_llm(
        self,
        host_manager: Aurite,
    ):
        """
        Tests agent execution using the real LLM API (Anthropic).
        This test requires the ANTHROPIC_API_KEY environment variable to be set.
        It verifies basic successful execution without mocking the LLM.
        """
        # --- Arrange ---
        agent_name = "Weather Agent"  # Use an agent expected to work with the real LLM
        agent_config = host_manager.get_agent_config(agent_name)
        assert agent_config is not None, f"'{agent_name}' config not found"

        user_message = "What is the weather like in Boston today? Use your tool."

        # --- Act ---
        # No LLM patching needed here
        assert host_manager.execution is not None, "Facade not initialized"
        try:
            agent_result: AgentExecutionResult = await host_manager.execution.run_agent(
                agent_name=agent_name,
                user_message=user_message,
                session_id=None,
            )
        except Exception as e:
            pytest.fail(f"Real LLM agent execution failed unexpectedly: {e}")

        # --- Assert ---
        # Basic checks for successful execution with real LLM
        assert isinstance(agent_result, AgentExecutionResult)
        assert agent_result.error is None, (
            f"Agent run failed with error: {agent_result.error}"
        )

        final_response_obj = agent_result.final_response
        assert final_response_obj is not None, "Final response should not be None"
        assert final_response_obj.role == "assistant"
        assert (
            final_response_obj.stop_reason is not None
        )  # e.g., 'end_turn' or 'tool_use'

        # Check that content exists
        assert final_response_obj.content is not None
        assert len(final_response_obj.content) > 0

        # Optional: Check if tool was likely used (based on conversation history)
        conversation_history = agent_result.conversation
        # Expecting user -> assistant (tool_use) -> user (tool_result) -> assistant (final)
        # Or potentially user -> assistant (final) if LLM didn't use tool
        assert len(conversation_history) >= 2

        # Check if a tool result message exists in the history
        tool_result_found = any(
            msg.role == "user" and msg.content and msg.content[0].type == "tool_result"
            for msg in conversation_history  # msg is AgentOutputMessage
        )
        print(f"Tool result found in history: {tool_result_found}")  # For debugging

        # Check final response text for keywords (less strict than JSON parsing for real LLM)
        primary_text = ""
        if final_response_obj.content:
            for block in final_response_obj.content:  # block is AgentOutputContentBlock
                if block.type == "text" and block.text is not None:
                    primary_text += block.text + " "
        primary_text = primary_text.strip()  # Keep original case for JSON parsing

        # Assert that the primary_text is valid JSON and contains expected structure
        try:
            import json

            parsed_json_response = json.loads(primary_text)
            assert "weather_summary" in parsed_json_response, (
                "JSON response missing 'weather_summary'"
            )
            assert "temperature" in parsed_json_response, (
                "JSON response missing 'temperature'"
            )
            assert "recommendations" in parsed_json_response, (
                "JSON response missing 'recommendations'"
            )
        except json.JSONDecodeError:
            pytest.fail(f"Final response text was not valid JSON: {primary_text}")

        # The check for "boston" is removed as the LLM is not required to include it
        # in the structured JSON output, only to use it for the tool call.
        # If tool use was expected, check for related terms
        # if tool_result_found:
        #     assert "weather" in primary_text.lower() or "temperature" in primary_text.lower()
