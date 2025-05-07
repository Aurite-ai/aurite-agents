"""
Integration tests for the Agent class orchestration with MCPHost.

These tests use a real MCPHost instance managed by the host_manager fixture,
which connects to mock MCP servers (like the weather server).
LLM calls are typically mocked to control agent behavior for testing host interactions.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any

# Mark all tests in this module
pytestmark = [pytest.mark.orchestration, pytest.mark.integration, pytest.mark.anyio]

# Imports from the project
from src.agents.agent_models import (
    AgentOutputMessage,
    AgentOutputContentBlock,
)
from src.llm.base_client import BaseLLM  # For mocking
from src.host_manager import HostManager  # For host_manager fixture type hint

# Import shared fixtures if needed (host_manager is usually sufficient)
# from ..fixtures.host_fixtures import host_manager # Assuming host_manager is available globally

# --- Test Class ---


class TestAgentIntegration:
    """Integration tests for Agent interacting with MCPHost."""

    @pytest.mark.anyio
    async def test_agent_integration_tool_call_mock_llm(
        self,
        host_manager: HostManager,  # Use the real host manager fixture
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
                    type="text", text="The weather in London is mocked."
                )
            ],
            stop_reason="end_turn",
            usage={"input_tokens": 20, "output_tokens": 5},
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
            "src.execution.facade.AnthropicLLM", return_value=mock_llm
        ) as MockAnthropicLLM:
            # --- Act ---
            # Execute agent via the facade
            assert host_manager.execution is not None, "Facade not initialized"
            result_dict: Dict[str, Any] = await host_manager.execution.run_agent(
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

            # 3. Check final result structure (now a dict)
            assert isinstance(result_dict, dict)
            assert result_dict.get("error") is None
            final_response = result_dict.get("final_response")
            assert final_response is not None
            assert final_response.get("role") == "assistant"
            # Find primary text in the dict structure
            primary_text = None
            if final_response.get("content"):
                for block in final_response["content"]:
                    if block.get("type") == "text":
                        primary_text = block.get("text")
                        break
            assert primary_text == "The weather in London is mocked."

            # 4. Check tool use was recorded in the result
            tool_uses = result_dict.get("tool_uses_in_final_turn", [])
            assert len(tool_uses) == 1
            assert tool_uses[0]["id"] == tool_use_id
            assert tool_uses[0]["name"] == tool_name
            assert tool_uses[0]["input"] == tool_input

            # 5. Check conversation history (list of dicts)
            conversation = result_dict.get("conversation", [])
            assert (
                len(conversation) == 4
            )  # user -> assistant(tool) -> user(result) -> assistant(final)
            assert conversation[0]["role"] == "user"
            assert conversation[1]["role"] == "assistant"
            assert conversation[1]["content"][0]["type"] == "tool_use"
            assert conversation[2]["role"] == "user"  # Tool result message
            # Check how the user message with tool result is serialized in history
            assert (
                conversation[2]["content"][0]["type"] == "tool_result"
            )  # Should be tool_result
            assert (
                conversation[2]["content"][0]["tool_use_id"] == tool_use_id
            )  # tool_use_id should be present
            # Check the actual result text from the mock weather server via MCPHost
            # The content of the tool_result block is a list containing text blocks
            tool_result_inner_content = conversation[2]["content"][0].get("content", [])
            assert isinstance(tool_result_inner_content, list)
            assert len(tool_result_inner_content) > 0
            assert tool_result_inner_content[0].get("type") == "text"
            tool_result_text = tool_result_inner_content[0].get("text", "")
            assert (
                "Weather for London:" in tool_result_text
            )  # Match actual mock server output format
            assert (
                "Temperature: 15" in tool_result_text  # Keep this check
            )  # Check within the text content

            assert conversation[3]["role"] == "assistant"
            # Find primary text in the last message
            final_primary_text = None
            if conversation[3].get("content"):
                for block in conversation[3]["content"]:
                    if block.get("type") == "text":
                        final_primary_text = block.get("text")
                        break
            assert final_primary_text == "The weather in London is mocked."

    # TODO: Add integration test with real LLM (optional, marked skip)
    # TODO: Add integration test involving schema validation
