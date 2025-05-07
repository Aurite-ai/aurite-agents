"""
Integration tests for the AnthropicLLM client making real API calls.

NOTE: These tests require a valid ANTHROPIC_API_KEY environment variable
      and will incur costs. They are marked with 'llm_integration' and
      skipped by default unless the key is present.
"""

import pytest
import os
from typing import List, Dict, Any

# Imports from the project
from src.llm.providers.anthropic_client import AnthropicLLM
from src.agents.agent_models import AgentOutputMessage
from anthropic.types import MessageParam

# --- Test Setup ---

# Skip all tests in this module if the API key is not set
API_KEY = os.environ.get("ANTHROPIC_API_KEY")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.llm_integration,  # Custom marker for LLM integration tests
    pytest.mark.skipif(not API_KEY, reason="ANTHROPIC_API_KEY not set in environment"),
    pytest.mark.anyio,  # For async tests
]

# Use a cheap and fast model for integration tests
TEST_INTEGRATION_MODEL = "claude-3-haiku-20240307"

# --- Test Class ---


class TestAnthropicLLMIntegration:
    """Integration tests for AnthropicLLM."""

    @pytest.mark.anyio
    async def test_anthropic_client_simple_api_call(self):
        """
        Tests a basic successful API call using the AnthropicLLM client.
        """
        # --- Arrange ---
        llm_client = AnthropicLLM(model_name=TEST_INTEGRATION_MODEL)

        messages_input: List[MessageParam] = [
            {"role": "user", "content": [{"type": "text", "text": "Hello Claude!"}]}
        ]

        # --- Act ---
        try:
            result_message: AgentOutputMessage = await llm_client.create_message(
                messages=messages_input,  # type: ignore[arg-type] # Ignore list[dict] vs list[MessageParam]
                tools=None,
            )
        except Exception as e:
            pytest.fail(f"Anthropic API call failed unexpectedly: {e}")

        # --- Assert ---
        assert isinstance(result_message, AgentOutputMessage)
        assert result_message.id is not None
        assert result_message.role == "assistant"
        assert result_message.model == TEST_INTEGRATION_MODEL
        assert result_message.stop_reason is not None  # e.g., 'end_turn'
        assert result_message.usage is not None
        assert result_message.usage.get("input_tokens", 0) > 0
        assert result_message.usage.get("output_tokens", 0) > 0

        assert isinstance(result_message.content, list)
        assert len(result_message.content) > 0
        assert result_message.content[0].type == "text"
        assert result_message.content[0].text is not None
        assert len(result_message.content[0].text) > 0
        # Check for common greeting patterns, case-insensitive
        assert (
            "hello" in result_message.content[0].text.lower()
            or "hi" in result_message.content[0].text.lower()
            or "greeting" in result_message.content[0].text.lower()
        )

    # TODO: Add integration test for tool use call
    # TODO: Add integration test for schema enforcement call (if applicable/testable)
