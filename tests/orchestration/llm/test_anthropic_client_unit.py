"""
Unit tests for the AnthropicLLM client.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic import AsyncAnthropic  # Added RateLimitError
from anthropic.types import Message as AnthropicSDKMessage
from anthropic.types import TextBlock, ToolUseBlock, Usage

from aurite.components.agents.agent_models import AgentOutputContentBlock, AgentOutputMessage
from aurite.config.config_models import LLMConfig  # Added import
from aurite.components.llm.providers.anthropic_client import BASE_DEFAULT_MAX_TOKENS, AnthropicLLM

# Basic model name for tests
TEST_MODEL_NAME = "claude-test-model"
TEST_API_KEY = "test_anthropic_api_key"


@pytest.mark.unit
class TestAnthropicLLMUnit:
    """
    Unit tests for the AnthropicLLM client.
    """

    def test_initialization_with_env_var(self):
        """
        Tests successful initialization when ANTHROPIC_API_KEY is set in environment variables.
        """
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": TEST_API_KEY}):
            try:
                llm_client = AnthropicLLM(model_name=TEST_MODEL_NAME)
                assert llm_client is not None
                assert llm_client.model_name == TEST_MODEL_NAME
                assert isinstance(llm_client.anthropic_sdk_client, AsyncAnthropic)
                # Check if the API key was passed to the underlying client
                # The AsyncAnthropic client stores the api_key in _auth_headers or similar,
                # but direct access might be brittle. For now, successful instantiation implies key usage.
                # A more robust check would involve mocking AsyncAnthropic's __init__ if possible.
                # Attempting to access 'api_key' as suggested by the error.
                # Note: This still relies on internal details of the AsyncAnthropic client.
                assert llm_client.anthropic_sdk_client.api_key == TEST_API_KEY
            except ValueError:
                pytest.fail("AnthropicLLM initialization failed with env var set.")
            except Exception as e:
                pytest.fail(f"An unexpected error occurred during initialization: {e}")

    def test_initialization_with_direct_api_key(self):
        """
        Tests successful initialization when api_key is passed directly.
        """
        # Ensure env var is not set or different to confirm direct key is used
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "other_key"}, clear=True):
            try:
                llm_client = AnthropicLLM(
                    model_name=TEST_MODEL_NAME, api_key=TEST_API_KEY
                )
                assert llm_client is not None
                assert isinstance(llm_client.anthropic_sdk_client, AsyncAnthropic)
                assert llm_client.anthropic_sdk_client.api_key == TEST_API_KEY
            except ValueError:
                pytest.fail("AnthropicLLM initialization failed with direct API key.")
            except Exception as e:
                pytest.fail(f"An unexpected error occurred during initialization: {e}")

    def test_initialization_no_api_key_raises_value_error(self):
        """
        Tests that ValueError is raised if no API key is provided (neither direct nor env var).
        """
        with patch.dict(os.environ, {}, clear=True):  # Clear relevant env vars
            with pytest.raises(ValueError) as excinfo:
                AnthropicLLM(model_name=TEST_MODEL_NAME)
            assert "Anthropic API key is required" in str(excinfo.value)

    @pytest.mark.anyio
    async def test_create_message_simple_text_response(self):
        """
        Tests the create_message method for a simple text response from Anthropic.
        """
        mock_anthropic_sdk_client = MagicMock(spec=AsyncAnthropic)
        mock_sdk_response = AnthropicSDKMessage(
            id="msg_test123",
            type="message",
            role="assistant",
            model=TEST_MODEL_NAME,
            content=[TextBlock(type="text", text="Hello, world!")],
            stop_reason="end_turn",
            stop_sequence=None,
            usage=Usage(input_tokens=10, output_tokens=20),
        )
        # Create a mock for the 'messages' attribute first
        mock_messages_api = MagicMock()
        # Assign the AsyncMock for 'create' to the 'messages' mock
        mock_messages_api.create = AsyncMock(return_value=mock_sdk_response)
        # Assign the 'messages' mock to the main SDK client mock
        mock_anthropic_sdk_client.messages = mock_messages_api

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": TEST_API_KEY}):
            llm_client = AnthropicLLM(model_name=TEST_MODEL_NAME)
        llm_client.anthropic_sdk_client = mock_anthropic_sdk_client  # Inject mock

        messages_input = [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}]

        result_message: AgentOutputMessage = await llm_client.create_message(
            messages=messages_input, tools=None
        )

        mock_anthropic_sdk_client.messages.create.assert_called_once()
        call_args = mock_anthropic_sdk_client.messages.create.call_args
        assert call_args.kwargs["model"] == TEST_MODEL_NAME
        assert call_args.kwargs["messages"] == messages_input
        assert call_args.kwargs["max_tokens"] is not None  # Default or configured

        assert isinstance(result_message, AgentOutputMessage)
        assert result_message.id == "msg_test123"
        assert result_message.role == "assistant"
        assert result_message.model == TEST_MODEL_NAME
        assert len(result_message.content) == 1
        assert result_message.content[0].type == "text"
        assert result_message.content[0].text == "Hello, world!"
        assert result_message.stop_reason == "end_turn"
        assert result_message.usage == {"input_tokens": 10, "output_tokens": 20}

    @pytest.mark.anyio
    async def test_create_message_with_tool_use(self):
        """
        Tests the create_message method when the LLM response includes a tool use request.
        """
        mock_anthropic_sdk_client = MagicMock(spec=AsyncAnthropic)
        tool_input = {"location": "London", "unit": "celsius"}
        mock_sdk_response = AnthropicSDKMessage(
            id="msg_test_tool",
            type="message",
            role="assistant",
            model=TEST_MODEL_NAME,
            content=[
                ToolUseBlock(
                    type="tool_use", id="tool_abc", name="get_weather", input=tool_input
                )
            ],
            stop_reason="tool_use",
            stop_sequence=None,
            usage=Usage(input_tokens=50, output_tokens=30),
        )
        mock_messages_api = MagicMock()
        mock_messages_api.create = AsyncMock(return_value=mock_sdk_response)
        mock_anthropic_sdk_client.messages = mock_messages_api

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": TEST_API_KEY}):
            llm_client = AnthropicLLM(model_name=TEST_MODEL_NAME)
        llm_client.anthropic_sdk_client = mock_anthropic_sdk_client

        messages_input = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Weather in London?"}],
            }
        ]
        tools_input = [
            {
                "name": "get_weather",
                "description": "Get the weather",
                "input_schema": {"type": "object", "properties": {}},
            }
        ]

        result_message: AgentOutputMessage = await llm_client.create_message(
            messages=messages_input, tools=tools_input
        )

        mock_anthropic_sdk_client.messages.create.assert_called_once()
        call_args = mock_anthropic_sdk_client.messages.create.call_args
        assert call_args.kwargs["tools"] == tools_input  # Verify tools were passed

        assert isinstance(result_message, AgentOutputMessage)
        assert result_message.id == "msg_test_tool"
        assert result_message.role == "assistant"
        assert result_message.stop_reason == "tool_use"
        assert len(result_message.content) == 1
        content_block = result_message.content[0]
        assert isinstance(content_block, AgentOutputContentBlock)
        assert content_block.type == "tool_use"
        assert content_block.id == "tool_abc"
        assert content_block.name == "get_weather"
        assert content_block.input == tool_input
        assert result_message.usage == {"input_tokens": 50, "output_tokens": 30}

    @pytest.mark.anyio
    async def test_create_message_with_schema_injection(self):
        """
        Tests that the JSON schema is correctly injected into the system prompt.
        """
        mock_anthropic_sdk_client = MagicMock(spec=AsyncAnthropic)
        mock_sdk_response = AnthropicSDKMessage(
            id="msg_test_schema",
            type="message",
            role="assistant",
            model=TEST_MODEL_NAME,
            content=[
                TextBlock(type="text", text='{"key": "value"}')
            ],  # Mock JSON response
            stop_reason="end_turn",
            stop_sequence=None,
            usage=Usage(input_tokens=20, output_tokens=10),
        )
        mock_messages_api = MagicMock()
        # Use AsyncMock for the create method
        mock_create_method = AsyncMock(return_value=mock_sdk_response)
        mock_messages_api.create = mock_create_method
        mock_anthropic_sdk_client.messages = mock_messages_api

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": TEST_API_KEY}):
            llm_client = AnthropicLLM(
                model_name=TEST_MODEL_NAME, system_prompt="Base prompt."
            )
        llm_client.anthropic_sdk_client = mock_anthropic_sdk_client

        messages_input = [
            {"role": "user", "content": [{"type": "text", "text": "Give me JSON"}]}
        ]
        test_schema = {"type": "object", "properties": {"key": {"type": "string"}}}

        result_message: AgentOutputMessage = await llm_client.create_message(
            messages=messages_input, tools=None, schema=test_schema
        )

        # Assert that the mock was called
        mock_create_method.assert_called_once()
        call_args = mock_create_method.call_args

        # Assert schema injection in system prompt
        system_prompt_arg = call_args.kwargs.get("system")
        assert system_prompt_arg is not None
        assert "Base prompt." in system_prompt_arg  # Original prompt
        assert (
            "Your response must be valid JSON matching this schema:"
            in system_prompt_arg
        )
        assert '"type": "object"' in system_prompt_arg  # Part of the schema
        assert '"key": {' in system_prompt_arg  # Part of the schema

        # Assert basic response structure
        assert isinstance(result_message, AgentOutputMessage)
        assert result_message.id == "msg_test_schema"
        assert result_message.role == "assistant"
        assert result_message.content[0].text == '{"key": "value"}'

    # Add more tests here for other scenarios if needed

    # --- Additional Tests ---

    def test_initialization_sets_defaults(self):
        """Tests that default values are set correctly during initialization if not provided."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": TEST_API_KEY}):
            llm_client = AnthropicLLM(model_name=TEST_MODEL_NAME)
            assert llm_client.temperature == 0.7  # Default from base_client
            assert llm_client.max_tokens == 4096  # Default from base_client
            assert (
                llm_client.system_prompt == "You are a helpful assistant."
            )  # Default from base_client

    def test_initialization_overrides_defaults(self):
        """Tests that provided values override defaults during initialization."""
        temp = 0.9
        tokens = 1024
        prompt = "You are a test bot."
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": TEST_API_KEY}):
            llm_client = AnthropicLLM(
                model_name=TEST_MODEL_NAME,
                temperature=temp,
                max_tokens=tokens,
                system_prompt=prompt,
            )
            assert llm_client.temperature == temp
            assert llm_client.max_tokens == tokens
            assert llm_client.system_prompt == prompt

    @pytest.mark.anyio
    async def test_create_message_with_system_prompt_override(self):
        """
        Tests that providing system_prompt_override uses it instead of the default.
        """
        mock_anthropic_sdk_client = MagicMock(spec=AsyncAnthropic)
        mock_sdk_response = AnthropicSDKMessage(
            id="msg_test_override",
            type="message",
            role="assistant",
            model=TEST_MODEL_NAME,
            content=[TextBlock(type="text", text="Override successful.")],
            stop_reason="end_turn",
            stop_sequence=None,
            usage=Usage(input_tokens=5, output_tokens=5),
        )
        mock_messages_api = MagicMock()
        mock_create_method = AsyncMock(return_value=mock_sdk_response)
        mock_messages_api.create = mock_create_method
        mock_anthropic_sdk_client.messages = mock_messages_api

        default_prompt = "This is the default system prompt."
        override_prompt = "This is the OVERRIDE system prompt."

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": TEST_API_KEY}):
            llm_client = AnthropicLLM(
                model_name=TEST_MODEL_NAME, system_prompt=default_prompt
            )
        llm_client.anthropic_sdk_client = mock_anthropic_sdk_client

        messages_input = [
            {"role": "user", "content": [{"type": "text", "text": "Check prompt"}]}
        ]

        result_message: AgentOutputMessage = await llm_client.create_message(
            messages=messages_input, tools=None, system_prompt_override=override_prompt
        )

        mock_create_method.assert_called_once()
        call_args = mock_create_method.call_args

        system_prompt_arg = call_args.kwargs.get("system")
        assert system_prompt_arg is not None
        assert system_prompt_arg == override_prompt
        assert system_prompt_arg != default_prompt

        assert isinstance(result_message, AgentOutputMessage)
        assert result_message.id == "msg_test_override"
        assert result_message.content[0].text == "Override successful."

    @pytest.mark.anyio
    async def test_create_message_propagates_max_tokens_stop_reason(self):
        """
        Tests that a 'max_tokens' stop_reason from the SDK is correctly
        propagated to the AgentOutputMessage.
        """
        # Mock the response that the SDK's create method should return
        mock_sdk_response = AnthropicSDKMessage(
            id="msg_test_max_tokens_prop",
            type="message",
            role="assistant",
            model=TEST_MODEL_NAME,
            content=[TextBlock(type="text", text="Some truncated text.")],
            stop_reason="max_tokens",  # This is the key part to test
            stop_sequence=None,
            usage=Usage(input_tokens=10, output_tokens=50),
        )

        # This will be the mock for the .create() method
        mock_create_method = AsyncMock(return_value=mock_sdk_response)

        # Patch 'AsyncAnthropic' where it's imported in the module under test (llm.providers.anthropic_client)
        with patch(
            "aurite.llm.providers.anthropic_client.AsyncAnthropic", spec=AsyncAnthropic
        ) as MockAsyncAnthropicClass:
            # Configure the instance that MockAsyncAnthropicClass() will return when AnthropicLLM initializes it
            mock_sdk_client_instance = MagicMock(spec=AsyncAnthropic)
            mock_sdk_client_instance.messages = MagicMock()
            mock_sdk_client_instance.messages.create = mock_create_method
            MockAsyncAnthropicClass.return_value = mock_sdk_client_instance

            # AnthropicLLM initialization will now use the mocked AsyncAnthropic class
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": TEST_API_KEY}):
                llm_client = AnthropicLLM(model_name=TEST_MODEL_NAME)

            # Sanity check: Ensure the llm_client is using our mocked instance
            assert llm_client.anthropic_sdk_client is mock_sdk_client_instance, (
                "Patching strategy failed: llm_client.anthropic_sdk_client is not the expected mock instance."
            )

            messages_input = [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "A user message."}],
                }
            ]

            result_message: AgentOutputMessage = await llm_client.create_message(
                messages=messages_input, tools=None
            )

            # Assert that the create method on our controlled mock was called
            mock_create_method.assert_called_once()
            # Alternative assertion on the instance held by the client:
            # llm_client.anthropic_sdk_client.messages.create.assert_called_once()

            assert isinstance(result_message, AgentOutputMessage)
            assert (
                result_message.stop_reason == "max_tokens"
            )  # Verify correct propagation

    @pytest.mark.anyio
    async def test_create_message_propagates_stop_sequence(self):
        """
        Tests that a 'stop_sequence' from the SDK is correctly
        propagated to the AgentOutputMessage.
        """
        mock_anthropic_sdk_client = MagicMock(spec=AsyncAnthropic)
        stop_seq = "\nHuman:"
        mock_sdk_response = AnthropicSDKMessage(
            id="msg_test_stop_seq",
            type="message",
            role="assistant",
            model=TEST_MODEL_NAME,
            content=[TextBlock(type="text", text="Response stopped by sequence.")],
            stop_reason="stop_sequence",
            stop_sequence=stop_seq,  # This is the key part to test
            usage=Usage(input_tokens=15, output_tokens=25),
        )
        mock_messages_api = MagicMock()
        mock_create_method = AsyncMock(return_value=mock_sdk_response)
        mock_messages_api.create = mock_create_method
        mock_anthropic_sdk_client.messages = mock_messages_api

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": TEST_API_KEY}):
            llm_client = AnthropicLLM(model_name=TEST_MODEL_NAME)
        llm_client.anthropic_sdk_client = mock_anthropic_sdk_client

        messages_input = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Another user query."}],
            }
        ]

        result_message: AgentOutputMessage = await llm_client.create_message(
            messages=messages_input, tools=None
        )

        mock_create_method.assert_called_once()

        assert isinstance(result_message, AgentOutputMessage)
        assert result_message.stop_reason == "stop_sequence"
        assert result_message.stop_sequence == stop_seq  # Verify correct propagation

    @pytest.mark.anyio
    async def test_create_message_with_llm_config_override_all_values(self):
        """
        Tests create_message with llm_config_override providing all possible values.
        """
        mock_anthropic_sdk_client = MagicMock(spec=AsyncAnthropic)
        mock_sdk_response = AnthropicSDKMessage(
            id="msg_override_all",
            type="message",
            role="assistant",
            model="override-model-from-config",  # Expected overridden model
            content=[TextBlock(type="text", text="Override response")],
            stop_reason="end_turn",
            usage=Usage(input_tokens=5, output_tokens=5),
        )
        mock_messages_api = MagicMock()
        mock_create_method = AsyncMock(return_value=mock_sdk_response)
        mock_messages_api.create = mock_create_method
        mock_anthropic_sdk_client.messages = mock_messages_api

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": TEST_API_KEY}):
            llm_client = AnthropicLLM(
                model_name="client-default-model",
                temperature=0.1,
                max_tokens=100,
                system_prompt="Client default system prompt.",
            )
        llm_client.anthropic_sdk_client = mock_anthropic_sdk_client

        override_config = LLMConfig(
            llm_id="override_cfg",
            provider="anthropic",
            model_name="override-model-from-config",
            temperature=0.99,
            max_tokens=999,
            default_system_prompt="System prompt from LLMConfig override.",
        )
        messages_input = [
            {"role": "user", "content": [{"type": "text", "text": "Test override"}]}
        ]

        await llm_client.create_message(
            messages=messages_input, tools=None, llm_config_override=override_config
        )

        mock_create_method.assert_called_once()
        call_args = mock_create_method.call_args
        assert call_args.kwargs["model"] == "override-model-from-config"
        assert call_args.kwargs["temperature"] == 0.99
        assert call_args.kwargs["max_tokens"] == 999
        assert call_args.kwargs["system"] == "System prompt from LLMConfig override."

    @pytest.mark.anyio
    async def test_create_message_with_llm_config_override_partial_values(self):
        """
        Tests create_message with llm_config_override providing only some values,
        expecting others to fall back to client defaults.
        """
        mock_anthropic_sdk_client = MagicMock(spec=AsyncAnthropic)
        mock_sdk_response = AnthropicSDKMessage(
            id="msg_override_partial",
            type="message",
            role="assistant",
            model="client-default-model",  # Expect client default model
            content=[TextBlock(type="text", text="Partial override response")],
            stop_reason="end_turn",
            usage=Usage(input_tokens=5, output_tokens=5),
        )
        mock_messages_api = MagicMock()
        mock_create_method = AsyncMock(return_value=mock_sdk_response)
        mock_messages_api.create = mock_create_method
        mock_anthropic_sdk_client.messages = mock_messages_api

        client_default_temp = 0.15
        client_default_max_tokens = 150
        client_default_system_prompt = "Client default system prompt for partial test."

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": TEST_API_KEY}):
            llm_client = AnthropicLLM(
                model_name="client-default-model",
                temperature=client_default_temp,
                max_tokens=client_default_max_tokens,
                system_prompt=client_default_system_prompt,
            )
        llm_client.anthropic_sdk_client = mock_anthropic_sdk_client

        # Override only temperature and system prompt
        override_config = LLMConfig(
            llm_id="override_cfg_partial",
            provider="anthropic",
            model_name=None,  # Should use client's default model
            temperature=0.88,
            max_tokens=None,  # Should use client's default max_tokens
            default_system_prompt="Partial system prompt from LLMConfig.",
        )
        messages_input = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Test partial override"}],
            }
        ]

        await llm_client.create_message(
            messages=messages_input, tools=None, llm_config_override=override_config
        )

        mock_create_method.assert_called_once()
        call_args = mock_create_method.call_args
        assert call_args.kwargs["model"] == "client-default-model"  # Fell back
        assert call_args.kwargs["temperature"] == 0.88  # Overridden
        assert call_args.kwargs["max_tokens"] == client_default_max_tokens  # Fell back
        assert (
            call_args.kwargs["system"] == "Partial system prompt from LLMConfig."
        )  # Overridden

    @pytest.mark.anyio
    async def test_create_message_llm_config_override_system_prompt_hierarchy(self):
        """
        Tests system prompt hierarchy: method_override > llm_config_override > client_default.
        """
        mock_anthropic_sdk_client = MagicMock(spec=AsyncAnthropic)
        mock_sdk_response = AnthropicSDKMessage(
            id="msg_sys_hierarchy",
            type="message",
            role="assistant",
            model="client-default-model",
            content=[TextBlock(type="text", text="Hierarchy test")],
            stop_reason="end_turn",
            usage=Usage(input_tokens=5, output_tokens=5),
        )
        mock_messages_api = MagicMock()
        mock_create_method = AsyncMock(return_value=mock_sdk_response)
        mock_messages_api.create = mock_create_method
        mock_anthropic_sdk_client.messages = mock_messages_api

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": TEST_API_KEY}):
            llm_client = AnthropicLLM(
                model_name="client-default-model",
                system_prompt="Client Default System Prompt",
            )
        llm_client.anthropic_sdk_client = mock_anthropic_sdk_client

        llm_cfg_override = LLMConfig(
            llm_id="cfg",
            provider="anthropic",
            model_name="any",
            default_system_prompt="LLMConfig System Prompt",
        )
        method_sys_prompt_override = "Method Argument System Prompt"
        messages_input = [
            {"role": "user", "content": [{"type": "text", "text": "Test hierarchy"}]}
        ]

        # Case 1: Method override is present (highest priority)
        await llm_client.create_message(
            messages=messages_input,
            tools=None,
            llm_config_override=llm_cfg_override,
            system_prompt_override=method_sys_prompt_override,
        )
        assert (
            mock_create_method.call_args.kwargs["system"] == method_sys_prompt_override
        )
        mock_create_method.reset_mock()

        # Case 2: No method override, llm_config_override is present
        await llm_client.create_message(
            messages=messages_input,
            tools=None,
            llm_config_override=llm_cfg_override,
            system_prompt_override=None,
        )
        assert (
            mock_create_method.call_args.kwargs["system"] == "LLMConfig System Prompt"
        )
        mock_create_method.reset_mock()

        # Case 3: No method override, no llm_config_override default_system_prompt
        llm_cfg_override_no_prompt = LLMConfig(
            llm_id="cfg_no_prompt",
            provider="anthropic",
            model_name="any",
            default_system_prompt=None,
        )
        await llm_client.create_message(
            messages=messages_input,
            tools=None,
            llm_config_override=llm_cfg_override_no_prompt,
            system_prompt_override=None,
        )
        assert (
            mock_create_method.call_args.kwargs["system"]
            == "Client Default System Prompt"
        )
        mock_create_method.reset_mock()

        # Case 4: No method override, no llm_config_override at all
        await llm_client.create_message(
            messages=messages_input,
            tools=None,
            llm_config_override=None,
            system_prompt_override=None,
        )
        assert (
            mock_create_method.call_args.kwargs["system"]
            == "Client Default System Prompt"
        )

    @pytest.mark.xfail(
        reason="Known 'Event loop is closed' error during teardown with full suite run"
    )
    @pytest.mark.anyio
    async def test_create_message_llm_config_override_max_tokens_fallback_to_base_default(
        self,  # Added self back
    ):
        """
        Tests that if client.max_tokens is None and llm_config_override.max_tokens is None,
        it falls back to BASE_DEFAULT_MAX_TOKENS.
        """
        mock_anthropic_sdk_client = MagicMock(spec=AsyncAnthropic)
        mock_sdk_response = AnthropicSDKMessage(
            id="msg_max_tokens_fallback",
            type="message",
            role="assistant",
            model="default-model",
            content=[TextBlock(type="text", text="Fallback test")],
            stop_reason="end_turn",
            usage=Usage(input_tokens=5, output_tokens=5),
        )
        mock_messages_api = MagicMock()
        mock_create_method = AsyncMock(return_value=mock_sdk_response)
        mock_messages_api.create = mock_create_method
        mock_anthropic_sdk_client.messages = mock_messages_api

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": TEST_API_KEY}):
            llm_client = AnthropicLLM(
                model_name="default-model",
                max_tokens=None,  # Client's max_tokens is explicitly None
            )
        llm_client.anthropic_sdk_client = mock_anthropic_sdk_client

        # LLMConfig override also has max_tokens as None
        override_config_no_max_tokens = LLMConfig(
            llm_id="cfg_no_max",
            provider="anthropic",
            model_name="default-model",
            max_tokens=None,
        )
        messages_input = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Test max_tokens fallback"}],
            }
        ]

        await llm_client.create_message(
            messages=messages_input,
            tools=None,
            llm_config_override=override_config_no_max_tokens,
        )

        mock_create_method.assert_called_once()
        call_args = mock_create_method.call_args
        assert call_args.kwargs["max_tokens"] == BASE_DEFAULT_MAX_TOKENS
