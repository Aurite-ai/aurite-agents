"""
Unit tests for the LiteLLMClient.
"""

import pytest

from aurite.lib.components.llm.litellm_client import LiteLLMClient
from aurite.lib.config.config_models import LLMConfig


@pytest.fixture
def basic_llm_config() -> LLMConfig:
    """Provides a basic LLMConfig for testing."""
    return LLMConfig(
        name="test_llm",
        provider="openai",
        model="gpt-4",
    )


def test_initialization_success(basic_llm_config: LLMConfig):
    """Tests that the client initializes correctly with a valid config."""
    client = LiteLLMClient(config=basic_llm_config)
    assert client.config == basic_llm_config


def test_initialization_failure():
    """Tests that ValueError is raised for an incomplete config."""
    with pytest.raises(ValueError, match="LLM provider and model must be specified"):
        LiteLLMClient(config=LLMConfig(name="test_llm", provider="openai", model=""))
    with pytest.raises(ValueError, match="LLM provider and model must be specified"):
        LiteLLMClient(config=LLMConfig(name="test_llm", provider="", model="gpt-4"))


def test_convert_tools_to_openai_format_with_type(basic_llm_config: LLMConfig):
    """
    Tests that the tool schema is preserved if 'type' is already present.
    """
    client = LiteLLMClient(config=basic_llm_config)
    tools = [
        {
            "name": "get_weather",
            "inputSchema": {"type": "object", "properties": {}},
        }
    ]
    formatted_tools = client._convert_tools_to_openai_format(tools)
    assert formatted_tools is not None
    assert formatted_tools[0]["function"]["parameters"]["type"] == "object"


def test_convert_tools_to_openai_format_without_type(basic_llm_config: LLMConfig):
    """
    Tests that 'type' is defaulted to 'object' if missing in the input_schema.
    """
    client = LiteLLMClient(config=basic_llm_config)
    tools = [{"name": "get_weather", "inputSchema": {"properties": {}}}]
    formatted_tools = client._convert_tools_to_openai_format(tools)
    assert formatted_tools is not None
    assert formatted_tools[0]["function"]["parameters"]["type"] == "object"


def test_build_request_params_model_formatting(basic_llm_config: LLMConfig):
    """
    Tests that the model parameter is correctly formatted as 'provider/model'.
    """
    client = LiteLLMClient(config=basic_llm_config)
    params = client._build_request_params(messages=[], tools=None)
    assert params["model"] == "openai/gpt-4"
