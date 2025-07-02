"""
Unit tests for the LiteLLMClient.
"""

import pytest
from aurite.config.config_models import LLMConfig
from aurite.components.llm.providers.litellm_client import LiteLLMClient


@pytest.fixture
def basic_llm_config() -> LLMConfig:
    """Provides a basic LLMConfig for testing."""
    return LLMConfig(
        name="test_llm",
        provider="openai",
        model="gpt-4",
        temperature=0.7,
        max_tokens=150,
    )


def test_build_request_params_basic(basic_llm_config: LLMConfig):
    """
    Tests that _build_request_params correctly assembles basic parameters.
    """
    client = LiteLLMClient(config=basic_llm_config)
    messages = [{"role": "user", "content": "Hello"}]

    params = client._build_request_params(messages=messages, tools=None)

    assert params["model"] == "openai/gpt-4"
    assert params["temperature"] == 0.7
    assert params["max_tokens"] == 150
    assert len(params["messages"]) == 1
    assert params["messages"][0]["role"] == "user"
    assert "tools" not in params


def test_build_request_params_with_system_prompt(basic_llm_config: LLMConfig):
    """
    Tests that a system prompt from the config is correctly added.
    """
    basic_llm_config.default_system_prompt = "You are a helpful assistant."
    client = LiteLLMClient(config=basic_llm_config)
    messages = [{"role": "user", "content": "Hello"}]

    params = client._build_request_params(messages=messages, tools=None)

    assert len(params["messages"]) == 2
    assert params["messages"][0]["role"] == "system"
    assert params["messages"][0]["content"] == "You are a helpful assistant."
    assert params["messages"][1]["role"] == "user"


def test_build_request_params_with_override_system_prompt(basic_llm_config: LLMConfig):
    """
    Tests that a system prompt override takes precedence over the config's default.
    """
    basic_llm_config.default_system_prompt = "This should be ignored."
    client = LiteLLMClient(config=basic_llm_config)
    messages = [{"role": "user", "content": "Hello"}]
    override_prompt = "You are a test assistant."

    params = client._build_request_params(
        messages=messages, tools=None, system_prompt_override=override_prompt
    )

    assert len(params["messages"]) == 2
    assert params["messages"][0]["role"] == "system"
    assert params["messages"][0]["content"] == override_prompt


def test_build_request_params_with_tools(basic_llm_config: LLMConfig):
    """
    Tests that tool definitions are correctly formatted for the OpenAI API.
    """
    client = LiteLLMClient(config=basic_llm_config)
    messages = [{"role": "user", "content": "Hello"}]
    tools = [
        {
            "name": "get_weather",
            "description": "Get the current weather",
            "input_schema": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
            },
        }
    ]

    params = client._build_request_params(messages=messages, tools=tools)

    assert "tools" in params
    assert isinstance(params["tools"], list)
    assert len(params["tools"]) == 1
    assert params["tools"][0]["type"] == "function"
    assert params["tools"][0]["function"]["name"] == "get_weather"
    assert "parameters" in params["tools"][0]["function"]
    assert params["tool_choice"] == "auto"


def test_build_request_params_with_json_schema(basic_llm_config: LLMConfig):
    """
    Tests that a JSON schema for validation is correctly added to the system prompt.
    """
    client = LiteLLMClient(config=basic_llm_config)
    messages = [{"role": "user", "content": "Generate a user profile."}]
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
    }

    params = client._build_request_params(messages=messages, tools=None, schema=schema)

    assert len(params["messages"]) == 2
    assert params["messages"][0]["role"] == "system"
    assert (
        "Your response MUST be a single valid JSON object"
        in params["messages"][0]["content"]
    )
    assert '"name":' in params["messages"][0]["content"]
