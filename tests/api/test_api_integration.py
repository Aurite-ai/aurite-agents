import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app instance from its new location

# Marker for API integration tests
pytestmark = [
    pytest.mark.api_integration,
    pytest.mark.anyio,  # Assuming endpoints might be async
]


# --- Test Functions ---


# Use the api_client fixture which handles setup and provides the TestClient instance
def test_api_health_check(api_client: TestClient):
    """
    Tests the /health endpoint for a 200 OK response.
    """
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_status_unauthorized(api_client: TestClient):
    """
    Tests the /status endpoint without providing an API key.
    Expects a 401 Unauthorized response.
    """
    # The fixture sets a default API key, so we need to make a request without it
    headers_without_auth = {
        k: v for k, v in api_client.headers.items() if k.lower() != "x-api-key"
    }
    response = api_client.get("/status", headers=headers_without_auth)
    # The API key middleware should return 401 if key is missing
    assert response.status_code == 401
    # Detail message might vary slightly based on FastAPI/middleware version
    # Make assertion less specific
    assert (
        "api key required"  # Check for the core part of the message
        in response.json().get("detail", "").lower()
    )


def test_api_status_authorized(api_client: TestClient):
    """
    Tests the /status endpoint with a valid API key (provided by fixture).
    Expects a 200 OK response with the correct status message.
    """
    # Fixture handles setup (env vars, cache clear, client creation)
    # Explicitly add auth header for this test
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get("/status", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"status": "initialized", "manager_status": "active"}


# --- New Test for SSE Tool Streaming ---

TEST_LLM_CONFIG_STREAM_TOOL = {
    "config_id": "test_llm_for_stream_tool_test",
    "config_type": "llm",
    "model_name": "claude-3-opus-20240229",  # Or any model, it will be mocked
    "provider": "anthropic",  # Important for patch target
    "temperature": 0.7,
    "max_tokens": 1000,
    "default_system_prompt": "You are a helpful testing assistant.",
}

TEST_AGENT_CONFIG_STREAM_TOOL = {
    "config_id": "test_agent_for_stream_tool_test",
    "config_type": "agent",
    "llm_config_id": "test_llm_for_stream_tool_test",
    "name": "TestStreamToolAgent",
    "description": "Agent for testing SSE tool streaming.",
    "system_prompt_template": "System prompt for {agent_name}.",
    "tools": ["get_weather"],  # Assume a 'get_weather' tool is defined for the LLM
    "config_validation_schema": None,
    "max_iterations": 5,
    "max_execution_time_seconds": 60,
    "retry_attempts": 1,
    "retry_delay_seconds": 2,
    "project_id": None,
}


async def mock_llm_stream_tool_call_response(*args, **kwargs):
    """
    Mocks the BaseLLM.stream_message (specifically AnthropicLLM's for this test)
    to simulate an LLM generating a tool call and streaming its input.
    This mock yields events as AgentTurnProcessor expects them from the LLM client.
    """
    tool_id = "tool_abc123"
    tool_name = "get_weather"
    # These are the chunks as Anthropic's input_json_delta might provide them
    # Our AnthropicLLM client passes these through as "json_chunk"
    input_chunks_from_llm_sdk = ['{"location": "Lon', 'don", "unit": "cels', 'ius"}']

    yield {
        "event_type": "message_start",
        "data": {
            "message_id": "msg_123",
            "role": "assistant",
            "model": TEST_LLM_CONFIG_STREAM_TOOL["model_name"],
            "input_tokens": 10,
        },
    }
    yield {
        "event_type": "tool_use_start",
        "data": {"index": 0, "tool_id": tool_id, "tool_name": tool_name},
    }

    for chunk in input_chunks_from_llm_sdk:
        # This is what AnthropicLLM.stream_message yields for Anthropic's input_json_delta
        yield {
            "event_type": "tool_use_input_delta",
            "data": {"index": 0, "json_chunk": chunk},
        }

    yield {
        "event_type": "content_block_stop",
        "data": {"index": 0},
    }  # LLM signals end of this tool_use block
    yield {
        "event_type": "message_delta",
        "data": {"stop_reason": "tool_use", "output_tokens": 5},
    }  # Corresponds to Anthropic's message_delta
    yield {
        "event_type": "stream_end",
        "data": {"stop_reason": "tool_use"},
    }  # Corresponds to Anthropic's message_stop


@pytest.mark.anyio
async def test_agent_execute_stream_tool_use_sse_format(
    api_client: TestClient, anyio_backend
):
    """
    Tests the /agents/{agent_name}/execute-stream endpoint for correct SSE event format
    when an agent uses a tool, specifically ensuring:
    - No 'tool_use_input_delta' events are sent from AgentTurnProcessor to the client.
    - 'content_block_stop' for a tool includes 'tool_id', 'content_type="tool_use"',
      and 'full_tool_input' with the complete JSON.
    """
    agent_name = TEST_AGENT_CONFIG_STREAM_TOOL["config_id"]
    # llm_name = TEST_LLM_CONFIG_STREAM_TOOL["config_id"] # Not directly used for endpoint

    # 1. Register LLM and Agent configurations
    headers = {"X-API-Key": api_client.test_api_key}
    # Ensure components are fresh for the test if they might persist across test runs
    # For this test, we assume the fixture or global setup handles clean state or we register unique IDs.
    # Using unique IDs (like test_..._stream_tool_test) helps.

    # Clean up existing configs if they might interfere (optional, better handled by fixtures if needed globally)
    # api_client.delete(f"/components/agents/{agent_name}", headers=headers)
    # api_client.delete(f"/components/llms/{TEST_LLM_CONFIG_STREAM_TOOL['config_id']}", headers=headers)

    response_llm_reg = api_client.post(
        f"/configs/llms/{TEST_LLM_CONFIG_STREAM_TOOL['config_id']}.json",
        json={"content": TEST_LLM_CONFIG_STREAM_TOOL},
        headers=headers,
    )
    if response_llm_reg.status_code not in [201, 409]:  # 409 if already exists
        pytest.fail(
            f"LLM reg failed: {response_llm_reg.status_code} - {response_llm_reg.text}"
        )

    response_agent_reg = api_client.post(
        f"/configs/agents/{TEST_AGENT_CONFIG_STREAM_TOOL['config_id']}.json",
        json={"content": TEST_AGENT_CONFIG_STREAM_TOOL},
        headers=headers,
    )
    if response_agent_reg.status_code not in [201, 409]:  # 409 if already exists
        pytest.fail(
            f"Agent reg failed: {response_agent_reg.status_code} - {response_agent_reg.text}"
        )

    # 2. Mock LLM streaming and tool execution
    mock_stream_message = AsyncMock(side_effect=mock_llm_stream_tool_call_response)
    mock_execute_tool = AsyncMock(
        return_value="Weather is sunny."
    )  # Tool execution result

    # Patch the stream_message method of the AnthropicLLM client, as that's what
    # our TEST_LLM_CONFIG_STREAM_TOOL specifies as the provider.
    # Also patch MCPHost.execute_tool where it's called by AgentTurnProcessor.
    with (
        patch(
            "src.aurite.llm.providers.anthropic_client.AnthropicLLM.stream_message",
            mock_stream_message,
        ),
        patch("src.aurite.host.host.MCPHost.execute_tool", mock_execute_tool),
    ):
        # 3. Make the streaming API call
        user_message = "What's the weather in London?"
        # Use a context manager for the stream to ensure it's closed
        with api_client.stream(
            "GET",
            f"/api/agents/{agent_name}/execute-stream?user_message={user_message}",
            headers=headers,
        ) as response:
            assert response.status_code == 200, (
                f"API call failed. Status: {response.status_code}"
            )  # Removed .text
            response.raise_for_status()  # Ensure we have a successful stream connection

            # 4. Process SSE response and collect events
            sse_events = []
            raw_response_lines = []  # For debugging
            for line in response.iter_lines():
                raw_response_lines.append(line)
                if line.startswith("data: "):
                    try:
                        event_data_json = line[len("data: ") :]
                        event_data = json.loads(event_data_json)
                        sse_events.append(event_data)
                    except json.JSONDecodeError:
                        raw_content_for_debug = "\n".join(raw_response_lines)
                        pytest.fail(
                            f"Failed to parse SSE event data: '{event_data_json}'.\nRaw response lines:\n{raw_content_for_debug}"
                        )

        # For debugging: print collected events
        # print("\nCollected SSE Events for test_agent_execute_stream_tool_use_sse_format:")
        # for evt_idx, evt in enumerate(sse_events):
        #     print(f"Event {evt_idx}: {json.dumps(evt, indent=2)}")

        # 5. Perform assertions
        assert sse_events, "No SSE events received"

        # Verify no 'tool_use_input_delta' events are sent from AgentTurnProcessor to the client
        # The mock_llm_stream_tool_call_response *does* yield these, but AgentTurnProcessor should filter them out.
        client_facing_tool_use_input_delta_events = [
            e for e in sse_events if e.get("event_type") == "tool_use_input_delta"
        ]
        assert not client_facing_tool_use_input_delta_events, (
            f"Found unexpected 'tool_use_input_delta' events sent to client: {json.dumps(client_facing_tool_use_input_delta_events, indent=2)}"
        )

        # Verify 'tool_use_start' (this one comes from AgentTurnProcessor, originating from LLM client)
        tool_use_start_events = [
            e for e in sse_events if e.get("event_type") == "tool_use_start"
        ]
        assert len(tool_use_start_events) == 1, (
            f"Expected one 'tool_use_start' event. Found: {len(tool_use_start_events)}"
        )
        tool_use_start_data = tool_use_start_events[0].get("data", {})
        assert tool_use_start_data.get("tool_id") == "tool_abc123"
        assert tool_use_start_data.get("tool_name") == "get_weather"

        # Verify 'content_block_stop' for the tool call (this is the key event we modified in AgentTurnProcessor)
        content_block_stop_tool_events = [
            e
            for e in sse_events
            if e.get("event_type") == "content_block_stop"
            and e.get("data", {}).get("content_type") == "tool_use"
        ]
        assert len(content_block_stop_tool_events) == 1, (
            f"Expected one 'content_block_stop' event for tool_use. Found: {len(content_block_stop_tool_events)} events: {json.dumps(content_block_stop_tool_events, indent=2)}"
        )

        tool_stop_data = content_block_stop_tool_events[0].get("data", {})
        assert tool_stop_data.get("tool_id") == "tool_abc123", (
            f"Tool ID mismatch in content_block_stop. Data: {json.dumps(tool_stop_data, indent=2)}"
        )

        expected_full_input_str = '{"location": "London", "unit": "celsius"}'  # Reconstructed from input_chunks_from_llm_sdk
        assert tool_stop_data.get("full_tool_input") == expected_full_input_str, (
            f"full_tool_input mismatch. Expected: '{expected_full_input_str}', Got: '{tool_stop_data.get('full_tool_input')}'. Data: {json.dumps(tool_stop_data, indent=2)}"
        )

        # Verify 'tool_result' (from AgentTurnProcessor after executing the tool)
        tool_result_events = [
            e for e in sse_events if e.get("event_type") == "tool_result"
        ]
        assert len(tool_result_events) == 1, (
            f"Expected one 'tool_result' event. Found: {len(tool_result_events)}"
        )
        tool_result_data = tool_result_events[0].get("data", {})
        assert tool_result_data.get("tool_use_id") == "tool_abc123"
        assert tool_result_data.get("status") == "success"
        assert tool_result_data.get("output") == "Weather is sunny."

        # Verify 'llm_call_completed' (this is yielded by AgentTurnProcessor when the LLM client's stream_end is received)
        llm_call_completed_events = [
            e for e in sse_events if e.get("event_type") == "llm_call_completed"
        ]
        assert len(llm_call_completed_events) == 1, (
            f"Expected one 'llm_call_completed' event. Found: {len(llm_call_completed_events)}"
        )
        assert (
            llm_call_completed_events[0].get("data", {}).get("stop_reason")
            == "tool_use"
        )

    # Note: No explicit cleanup of registered components here.
    # Test isolation should ideally be handled by pytest fixtures (e.g., session or function scoped)
    # that manage the lifecycle of test data or by ensuring unique names for test components.
    # that manage the lifecycle of test data or by ensuring unique names for test components.
