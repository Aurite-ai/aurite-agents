"""
Integration tests for the AnthropicLLM client making real API calls.

NOTE: These tests require a valid ANTHROPIC_API_KEY environment variable
      and will incur costs. They are marked with 'llm_integration' and
      skipped by default unless the key is present.
"""

import pytest
import os
from typing import List, Dict, Any

import json  # Added for schema test parsing

# Imports from the project
from src.llm.providers.anthropic_client import AnthropicLLM
from src.agents.agent_models import AgentOutputMessage
from src.config.config_models import LLMConfig  # Added import
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


@pytest.mark.llm_integration  # Apply marker to the class as well
class TestAnthropicLLMIntegration:
    """Integration tests for AnthropicLLM."""

    @pytest.fixture(scope="class")
    async def llm_client(self):
        """Class-scoped fixture to create and properly close the LLM client."""
        client = AnthropicLLM(model_name=TEST_INTEGRATION_MODEL)
        yield client
        # Teardown: close the client after all tests in the class run
        if hasattr(client, "anthropic_sdk_client") and hasattr(
            client.anthropic_sdk_client, "aclose"
        ):
            await client.anthropic_sdk_client.aclose()

    @pytest.mark.anyio
    async def test_anthropic_client_simple_api_call(
        self, llm_client: AnthropicLLM
    ):  # Use fixture
        """
        Tests a basic successful API call using the AnthropicLLM client.
        """
        # --- Arrange ---
        # llm_client is now provided by the fixture

        messages_input: List[MessageParam] = [
            {"role": "user", "content": [{"type": "text", "text": "Hello Claude!"}]}
        ]

        # --- Act & Assert ---
        try:
            result_message: AgentOutputMessage = await llm_client.create_message(
                messages=messages_input,  # type: ignore[arg-type] # Ignore list[dict] vs list[MessageParam]
                tools=None,
            )
        except Exception as e:
            pytest.fail(f"Anthropic API call failed unexpectedly: {e}")
        # finally block removed as cleanup is handled by the fixture

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

    @pytest.mark.anyio
    async def test_anthropic_client_tool_use_call(
        self, llm_client: AnthropicLLM
    ):  # Use fixture
        """
        Tests an API call that should result in a tool_use stop reason.
        """
        # --- Arrange ---
        # llm_client is now provided by the fixture

        # Define a simple tool for the LLM to potentially use
        tools_input: List[Dict[str, Any]] = [
            {
                "name": "get_weather",
                "description": "Get the current weather in a given location.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        }
                    },
                    "required": ["location"],
                },
            }
        ]

        # A message that is likely to trigger the tool use
        messages_input: List[MessageParam] = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "What's the weather like in London? Please use a tool if you have one for this.",
                    }
                ],
            }
        ]

        # --- Act & Assert ---
        try:
            result_message: AgentOutputMessage = await llm_client.create_message(
                messages=messages_input,  # type: ignore[arg-type]
                tools=tools_input,
            )
        except Exception as e:
            pytest.fail(f"Anthropic API call with tool use failed unexpectedly: {e}")
        # finally block removed as cleanup is handled by the fixture

        # --- Assert ---
        assert isinstance(result_message, AgentOutputMessage)
        assert result_message.id is not None
        assert result_message.role == "assistant"
        assert result_message.model == TEST_INTEGRATION_MODEL
        assert result_message.stop_reason == "tool_use"  # Key assertion for this test
        assert result_message.usage is not None
        assert result_message.usage.get("input_tokens", 0) > 0
        assert (
            result_message.usage.get("output_tokens", 0) > 0
        )  # LLM still generates tokens for the tool_use block

        assert isinstance(result_message.content, list)
        assert len(result_message.content) > 0

        # Expecting at least one tool_use block
        tool_use_block_found = False
        for block in result_message.content:
            if block.type == "tool_use":
                tool_use_block_found = True
                assert block.id is not None
                assert block.name == "get_weather"  # Or whatever tool it decided to use
                assert block.input is not None
                assert (
                    "location" in block.input
                )  # Check if the required input is present
                # We can't be certain about the exact input value chosen by the LLM,
                # but we can check if it's a string.
                assert isinstance(block.input["location"], str)
                break
        assert tool_use_block_found, "No tool_use block found in the response content."

    @pytest.mark.anyio
    async def test_anthropic_client_schema_enforcement_call(
        self, llm_client: AnthropicLLM
    ):  # Use fixture
        """
        Tests an API call with a JSON schema to guide the response.
        Note: This test verifies the schema is sent and the LLM attempts to use it.
              Exact output adherence can vary with LLM behavior.
        """
        # --- Arrange ---
        # llm_client is now provided by the fixture

        # Define a simple schema for the LLM
        test_schema: Dict[str, Any] = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name of a person."},
                "age": {"type": "integer", "description": "The age of the person."},
                "city": {"type": "string", "description": "The city they live in."},
            },
            "required": ["name", "age"],
        }

        # A message prompting for a JSON response matching the schema
        messages_input: List[MessageParam] = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please provide information about a fictional character named Alex, who is 30 years old and lives in New York. Format your response as JSON according to the provided schema.",
                    }
                ],
            }
        ]

        # --- Act & Assert ---
        try:
            result_message: AgentOutputMessage = await llm_client.create_message(
                messages=messages_input,  # type: ignore[arg-type]
                tools=None,
                schema=test_schema,  # Pass the schema here
            )
        except Exception as e:
            pytest.fail(
                f"Anthropic API call with schema enforcement failed unexpectedly: {e}"
            )
        # finally block removed as cleanup is handled by the fixture

        # --- Assert ---
        assert isinstance(result_message, AgentOutputMessage)
        assert result_message.id is not None
        assert result_message.role == "assistant"
        assert result_message.model == TEST_INTEGRATION_MODEL
        # Stop reason might be 'end_turn' or potentially 'tool_use' if the LLM gets confused,
        # but for schema, 'end_turn' is more likely if it successfully generates JSON.
        assert result_message.stop_reason == "end_turn"
        assert result_message.usage is not None
        assert result_message.usage.get("input_tokens", 0) > 0
        assert result_message.usage.get("output_tokens", 0) > 0

        assert isinstance(result_message.content, list)
        assert len(result_message.content) > 0
        assert result_message.content[0].type == "text"
        assert result_message.content[0].text is not None

        # Attempt to parse the JSON response and validate its structure (basic check)
        try:
            import json

            response_json = json.loads(result_message.content[0].text)
            assert isinstance(response_json, dict)
            # Check for some expected keys based on the schema and prompt
            assert "name" in response_json
            assert "age" in response_json
            # 'city' is not strictly required by schema but likely included by prompt
            # assert "city" in response_json

            # Optionally, more rigorous schema validation if a library like jsonschema is available
            # from jsonschema import validate
            # validate(instance=response_json, schema=test_schema)
            # For this integration test, just checking key presence is often sufficient
            # as full schema validation is more of a unit test for the schema itself.

        except json.JSONDecodeError:
            pytest.fail(
                f"Response content was not valid JSON: {result_message.content[0].text}"
            )
        except AssertionError as ae:
            pytest.fail(
                f"JSON response did not meet basic structure expectations: {ae}. Response: {result_message.content[0].text}"
            )

    # --- Tests for llm_config_override ---

    @pytest.mark.anyio
    async def test_anthropic_client_with_llm_config_override_full(
        self, llm_client: AnthropicLLM
    ):
        """
        Tests using llm_config_override with all parameters set.
        We expect the override config's parameters to be used.
        """
        # Arrange
        override_config = LLMConfig(
            llm_id="integ_override_full",
            provider="anthropic",
            model_name=TEST_INTEGRATION_MODEL,  # Use the same model for testing cost
            temperature=0.95,
            max_tokens=55,  # Use a small number for testing
            default_system_prompt="System prompt from full LLMConfig override for integration test.",
        )
        messages_input: List[MessageParam] = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Test full override. Respond briefly."}
                ],
            }
        ]

        # Act
        try:
            result_message: AgentOutputMessage = await llm_client.create_message(
                messages=messages_input,  # type: ignore[arg-type]
                tools=None,
                llm_config_override=override_config,
            )
        except Exception as e:
            pytest.fail(f"Anthropic API call with full llm_config_override failed: {e}")

        # Assert
        assert isinstance(result_message, AgentOutputMessage)
        assert (
            result_message.model == TEST_INTEGRATION_MODEL
        )  # Model was overridden (though same as default here)
        assert result_message.stop_reason is not None  # Could be end_turn or max_tokens
        if result_message.stop_reason == "max_tokens":
            assert (
                result_message.usage["output_tokens"] <= 55
            )  # Check if max_tokens was respected
        assert result_message.usage["input_tokens"] > 0
        assert result_message.usage["output_tokens"] > 0
        assert len(result_message.content) > 0
        assert result_message.content[0].type == "text"
        # We can't easily assert temperature or exact system prompt effect,
        # but the call succeeding with the override implies parameters were accepted.

    @pytest.mark.anyio
    async def test_anthropic_client_with_llm_config_override_partial(
        self, llm_client: AnthropicLLM
    ):
        """
        Tests using llm_config_override with only some parameters set.
        Expect fallback to client defaults for unspecified parameters.
        """
        # Arrange
        # Client default is Haiku, temp=0.7, max_tokens=4096
        override_config = LLMConfig(
            llm_id="integ_override_partial",
            provider="anthropic",
            model_name=None,  # Should use client default (Haiku)
            temperature=0.15,  # Override temperature
            max_tokens=None,  # Should use client default (4096)
            default_system_prompt="System prompt from partial LLMConfig override.",  # Override prompt
        )
        messages_input: List[MessageParam] = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Test partial override. Respond very concisely.",
                    }
                ],
            }
        ]

        # Act
        try:
            result_message: AgentOutputMessage = await llm_client.create_message(
                messages=messages_input,  # type: ignore[arg-type]
                tools=None,
                llm_config_override=override_config,
            )
        except Exception as e:
            pytest.fail(
                f"Anthropic API call with partial llm_config_override failed: {e}"
            )

        # Assert
        assert isinstance(result_message, AgentOutputMessage)
        assert (
            result_message.model == TEST_INTEGRATION_MODEL
        )  # Client default model was used
        assert (
            result_message.stop_reason == "end_turn"
        )  # Expect end_turn as max_tokens is large
        assert result_message.usage["input_tokens"] > 0
        assert result_message.usage["output_tokens"] > 0
        assert len(result_message.content) > 0
        assert result_message.content[0].type == "text"
        # Can't directly assert temperature or max_tokens fallback easily,
        # but success implies parameters were accepted.

    @pytest.mark.anyio
    async def test_anthropic_client_system_prompt_hierarchy(
        self, llm_client: AnthropicLLM
    ):
        """
        Tests the system prompt override hierarchy: method > llm_config > client.
        """
        # Arrange
        client_default_prompt = (
            llm_client.system_prompt
        )  # Get the actual client default
        llm_config_prompt = "System prompt from LLMConfig override (hierarchy test)."
        method_override_prompt = (
            "System prompt from method argument override (hierarchy test)."
        )

        llm_config_override = LLMConfig(
            llm_id="integ_hierarchy",
            provider="anthropic",
            model_name=TEST_INTEGRATION_MODEL,
            default_system_prompt=llm_config_prompt,
        )
        messages_input: List[MessageParam] = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Test system prompt hierarchy. Who takes precedence?",
                    }
                ],
            }
        ]

        # --- Act & Assert ---

        # Case 1: Method override provided (should be used)
        try:
            result1: AgentOutputMessage = await llm_client.create_message(
                messages=messages_input,  # type: ignore[arg-type]
                tools=None,
                llm_config_override=llm_config_override,
                system_prompt_override=method_override_prompt,
            )
            # We can't directly verify which prompt was *used* by the LLM easily,
            # but we can assert the call succeeded.
            assert isinstance(result1, AgentOutputMessage)
            assert result1.content[0].text is not None
        except Exception as e:
            pytest.fail(f"Hierarchy Test Case 1 (Method Override) failed: {e}")

        # Case 2: No method override, llm_config override provided (llm_config should be used)
        try:
            result2: AgentOutputMessage = await llm_client.create_message(
                messages=messages_input,  # type: ignore[arg-type]
                tools=None,
                llm_config_override=llm_config_override,
                system_prompt_override=None,  # Explicitly None
            )
            assert isinstance(result2, AgentOutputMessage)
            assert result2.content[0].text is not None
        except Exception as e:
            pytest.fail(f"Hierarchy Test Case 2 (LLMConfig Override) failed: {e}")

        # Case 3: No method override, no llm_config override (client default should be used)
        try:
            result3: AgentOutputMessage = await llm_client.create_message(
                messages=messages_input,  # type: ignore[arg-type]
                tools=None,
                llm_config_override=None,  # Explicitly None
                system_prompt_override=None,  # Explicitly None
            )
            assert isinstance(result3, AgentOutputMessage)
            assert result3.content[0].text is not None
        except Exception as e:
            pytest.fail(f"Hierarchy Test Case 3 (Client Default) failed: {e}")

        # Basic check: Ensure responses are different (suggesting prompts might have had an effect)
        # This is weak but better than nothing for integration.
        assert (
            result1.content[0].text != result2.content[0].text
            or result1.content[0].text != result3.content[0].text
        )
