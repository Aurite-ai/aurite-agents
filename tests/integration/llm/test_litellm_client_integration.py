"""
Integration tests for the LiteLLMClient using a mock HTTP server.
"""

import openai
import pytest
from pytest_httpserver import HTTPServer

from aurite.components.llm.litellm_client import LiteLLMClient
from aurite.config.config_models import LLMConfig

# --- Fixtures ---


@pytest.fixture
def mock_llm_config(httpserver: HTTPServer) -> LLMConfig:
    """Provides an LLMConfig pointing to the mock HTTP server."""
    return LLMConfig(
        name="mock_llm",
        provider="openai",  # Provider can be anything, as api_base overrides it
        model="gpt-test",
        api_base=httpserver.url_for("/"),
        api_key="fake-key",
    )


# --- Test Cases ---


@pytest.mark.anyio
async def test_create_message_success(httpserver: HTTPServer, mock_llm_config: LLMConfig):
    """
    Tests a successful API call to create_message.
    Verifies that the request is correctly formatted and a valid response is processed.
    """
    # Arrange: Set up the mock server to expect a POST and return a valid OpenAI response
    httpserver.expect_request("/chat/completions", method="POST").respond_with_json(
        {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "gpt-test",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello there!",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 9, "completion_tokens": 12, "total_tokens": 21},
        }
    )

    client = LiteLLMClient(config=mock_llm_config)
    messages = [{"role": "user", "content": "Hello"}]

    # Act: Call the method under test
    response_message = await client.create_message(messages=messages, tools=None)

    # Assert: Check the response
    assert response_message is not None
    assert response_message.role == "assistant"
    assert response_message.content == "Hello there!"

    # Assert: Check that the server received the expected request
    recorded_request, _ = httpserver.log[0]
    assert recorded_request.method == "POST"
    assert recorded_request.json is not None
    assert recorded_request.json["model"] == "gpt-test"
    assert recorded_request.json["messages"][0]["content"] == "Hello"


@pytest.mark.anyio
async def test_create_message_api_error_handling(httpserver: HTTPServer, mock_llm_config: LLMConfig):
    """
    Tests that the client correctly handles a 429 RateLimitError from the API.
    """
    # Arrange: Set up the mock server to return a 429 error
    httpserver.expect_request("/chat/completions", method="POST").respond_with_json(
        {"error": {"message": "Rate limit exceeded"}}, status=429
    )

    client = LiteLLMClient(config=mock_llm_config)
    messages = [{"role": "user", "content": "Hello"}]

    # Act & Assert: Expect a RateLimitError to be raised
    with pytest.raises(openai.RateLimitError) as excinfo:
        await client.create_message(messages=messages, tools=None)

    # Assert that the exception contains the expected status code
    assert excinfo.value.status_code == 429


@pytest.mark.anyio
async def test_create_message_bad_request_error(httpserver: HTTPServer, mock_llm_config: LLMConfig):
    """
    Tests that the client correctly handles a 400 BadRequestError from the API.
    """
    # Arrange: Set up the mock server to return a 400 error
    httpserver.expect_request("/chat/completions", method="POST").respond_with_json(
        {"error": {"message": "Invalid request"}}, status=400
    )

    client = LiteLLMClient(config=mock_llm_config)
    messages = [{"role": "user", "content": "This is a bad request"}]

    # Act & Assert: Expect a BadRequestError to be raised
    with pytest.raises(openai.BadRequestError) as excinfo:
        await client.create_message(messages=messages, tools=None)

    assert excinfo.value.status_code == 400
