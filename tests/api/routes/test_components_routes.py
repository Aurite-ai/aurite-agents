import pytest
from fastapi.testclient import TestClient

# Marker for API integration tests, specifically for component routes
pytestmark = [
    pytest.mark.api_integration,
    pytest.mark.components_api,  # Add a specific marker if desired
    pytest.mark.anyio,
]

# --- Test Functions (Moved from test_api_integration.py) ---


def test_execute_agent_success(api_client: TestClient):
    """
    Tests successful execution of a configured agent ('Weather Agent').
    """
    # Fixture handles setup
    agent_name = "Weather Agent"  # Agent defined in testing_config.json
    user_message = "What is the weather in London?"

    payload = {"user_message": user_message}
    # Explicitly add auth header
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        f"/agents/{agent_name}/execute", json=payload, headers=headers
    )

    assert response.status_code == 200
    response_data = response.json()
    # Check for the presence of the expected output structure from Agent execution
    # With a real API key, the LLM call is expected to succeed.
    assert "final_response" in response_data
    final_response_data = response_data["final_response"]
    assert final_response_data is not None  # Expecting a response object
    assert isinstance(
        final_response_data, dict
    )  # Expecting a dictionary representing AgentOutputMessage
    assert final_response_data.get("role") == "assistant"
    assert "content" in final_response_data
    assert isinstance(final_response_data["content"], list)
    # Error should be None or not present if the call is successful
    assert response_data.get("error") is None


def test_execute_simple_workflow_success(api_client: TestClient):
    """
    Tests successful execution of a configured simple workflow ('main').
    """
    # Fixture handles setup
    workflow_name = "main"  # Workflow defined in testing_config.json
    initial_message = "Check weather in SF and save plan."

    # Ensure the payload key matches the API endpoint model (ExecuteWorkflowRequest)
    payload = {"initial_user_message": initial_message}
    # Explicitly add auth header
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        f"/workflows/{workflow_name}/execute", json=payload, headers=headers
    )

    assert response.status_code == 200
    response_data = response.json()
    # Check the structure returned by the simple workflow executor via the facade
    assert "workflow_name" in response_data
    assert response_data["workflow_name"] == workflow_name
    assert "status" in response_data
    # With a real API key, the workflow and its underlying agent calls are expected to succeed.
    assert (
        response_data["status"] == "completed"
    )  # Or "success" depending on your SimpleWorkflowExecutor
    assert "final_message" in response_data
    assert response_data["final_message"] is not None  # Expecting a final message
    assert isinstance(response_data["final_message"], str)
    # Error should be None or not present if the workflow is successful
    assert response_data.get("error") is None


def test_execute_custom_workflow_success(api_client: TestClient):
    """
    Tests successful execution of a configured custom workflow ('ExampleCustomWorkflow').
    """
    # Fixture handles setup
    workflow_name = "ExampleCustomWorkflow"  # Corrected name
    initial_input = {"city": "London"}  # Example input for the workflow

    # Payload structure for custom workflows
    payload = {"initial_input": initial_input}
    # Explicitly add auth header
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        f"/custom_workflows/{workflow_name}/execute", json=payload, headers=headers
    )

    assert response.status_code == 200
    response_data = response.json()
    # Check the structure returned by the custom workflow executor via the facade
    assert "workflow_name" in response_data
    assert response_data["workflow_name"] == workflow_name
    assert "status" in response_data
    # With a real API key, the custom workflow and its internal agent calls are expected to succeed.
    assert (
        response_data["status"] == "completed"
    )  # Or "success" depending on your CustomWorkflowExecutor
    assert "result" in response_data
    assert response_data["result"] is not None  # Expecting a result
    # Error should be None or not present if the custom workflow is successful
    assert response_data.get("error") is None


# --- Registration Endpoint Tests ---


def test_register_client_success(api_client: TestClient):
    """
    Tests successful dynamic registration of a new client.
    """
    # Fixture handles setup
    client_id_to_register = "dynamic_weather_client"
    # Ensure the server path is valid relative to the project root
    server_path = "tests/fixtures/servers/weather_mcp_server.py"

    # Client config payload
    client_payload = {
        "client_id": client_id_to_register,
        "server_path": server_path,
        "roots": [],
        "capabilities": ["tools"],
        "timeout": 10.0,
        "routing_weight": 0.5,
        "exclude": None,
        "gcp_secrets": None,  # Explicitly None if not used
    }

    # Explicitly add auth header
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        "/clients/register", json=client_payload, headers=headers
    )

    assert response.status_code == 201  # Created
    response_data = response.json()
    assert response_data == {
        "status": "success",
        "client_id": client_id_to_register,
    }

    # Optional: Verify the client is actually usable via another endpoint if needed,
    # though that might belong in more complex E2E tests.


def test_register_client_duplicate(api_client: TestClient):
    """
    Tests attempting to register a client with an ID that already exists,
    which should now update the existing client (upsert behavior).
    """
    # Fixture handles setup
    client_id_to_register = "duplicate_client_test"
    initial_server_path = "tests/fixtures/servers/weather_mcp_server.py"
    updated_server_path = "tests/fixtures/servers/dummy_mcp_server_for_unreg.py"  # Using a different valid server

    client_payload_initial = {
        "client_id": client_id_to_register,
        "server_path": initial_server_path,
        "roots": [],
        "capabilities": ["tools"],
        "timeout": 10.0,
        "routing_weight": 0.5,
        "exclude": None,
        "gcp_secrets": None,
    }

    # Explicitly add auth header
    headers = {"X-API-Key": api_client.test_api_key}
    # First registration (should succeed)
    response1 = api_client.post(
        "/clients/register", json=client_payload_initial, headers=headers
    )
    assert response1.status_code == 201
    assert response1.json()["client_id"] == client_id_to_register

    # Second registration attempt with the same client_id but different server_path (update)
    client_payload_updated = {
        "client_id": client_id_to_register,
        "server_path": updated_server_path,  # Changed server_path
        "roots": [],
        "capabilities": ["tools", "prompts"],  # Changed capabilities
        "timeout": 20.0,  # Changed timeout
        "routing_weight": 0.8,
        "exclude": None,
        "gcp_secrets": None,
    }
    response2 = api_client.post(
        "/clients/register", json=client_payload_updated, headers=headers
    )

    assert response2.status_code == 201  # Expect 201 for create/update
    response_data = response2.json()
    assert response_data["status"] == "success"
    assert response_data["client_id"] == client_id_to_register
    # To fully verify, one might need to inspect the Aurite's internal state
    # or have a GET endpoint for specific client configs.


def test_register_agent_success(api_client: TestClient):
    """
    Tests successful dynamic registration of a new agent.
    """
    # Fixture handles setup
    agent_name_to_register = "Dynamic Test Agent"

    # Agent config payload - references clients from testing_config.json
    agent_payload = {
        "name": agent_name_to_register,
        "client_ids": [
            "weather_server",
            "planning_server",
        ],  # Assumes these exist in base config
        "system_prompt": "You are a dynamically registered test agent.",
        "model": "claude-3-haiku-20240307",
        "temperature": 0.7,
        "max_tokens": 50,
        "max_iterations": 2,
        "include_history": False,
        "exclude_components": None,
    }

    # Explicitly add auth header
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post("/agents/register", json=agent_payload, headers=headers)

    assert response.status_code == 201  # Created
    response_data = response.json()
    assert response_data == {
        "status": "success",
        "agent_name": agent_name_to_register,
    }


def test_register_agent_duplicate_name(api_client: TestClient):
    """
    Tests attempting to register an agent with a name that already exists,
    which should now update the existing agent (upsert behavior).
    """
    # Fixture handles setup
    agent_name_to_register = "Duplicate Agent Test"
    initial_prompt = "First registration."
    updated_prompt = "Second registration attempt."

    agent_payload_initial = {
        "name": agent_name_to_register,
        "client_ids": ["weather_server"],  # Assumes this client exists
        "system_prompt": initial_prompt,
        "model": "claude-3-haiku-20240307",  # Added model for completeness
    }

    # Explicitly add auth header
    headers = {"X-API-Key": api_client.test_api_key}
    # First registration (should succeed)
    response1 = api_client.post(
        "/agents/register", json=agent_payload_initial, headers=headers
    )
    assert response1.status_code == 201
    assert response1.json()["agent_name"] == agent_name_to_register

    # Verify initial prompt (optional, but good for confirming state)
    # This would require a GET endpoint for a specific agent's config, which we don't have in components_routes
    # For now, we'll trust the registration.

    # Second registration attempt with the same name but different prompt (update)
    agent_payload_updated = {
        "name": agent_name_to_register,
        "client_ids": ["weather_server"],
        "system_prompt": updated_prompt,
        "model": "claude-3-haiku-20240307",
    }
    response2 = api_client.post(
        "/agents/register", json=agent_payload_updated, headers=headers
    )

    assert (
        response2.status_code == 201
    )  # Should still be 201 (or 200 if we prefer for updates)
    response_data = response2.json()
    assert response_data["status"] == "success"
    assert response_data["agent_name"] == agent_name_to_register

    # To fully verify the update, we'd ideally GET the agent config and check the prompt.
    # Since that endpoint isn't in this router, we rely on the Aurite logic
    # and the success status from the registration endpoint.
    # A more comprehensive test could involve using the /configs/{type}/id/{id} endpoint
    # if the dynamic registration also saves to a file that endpoint can read.
    # For now, this tests the API endpoint's response to a re-registration.


def test_register_agent_invalid_client_id(api_client: TestClient):
    """
    Tests attempting to register an agent referencing a non-existent client ID.
    Expects a 400 Bad Request response.
    """
    # Fixture handles setup
    agent_name_to_register = "Agent Invalid Client Test"
    invalid_client_id = "non_existent_client_id_123"

    agent_payload = {
        "name": agent_name_to_register,
        "client_ids": [invalid_client_id],  # Reference the invalid client
        "system_prompt": "This registration should fail.",
    }

    # Explicitly add auth header
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post("/agents/register", json=agent_payload, headers=headers)

    assert response.status_code == 400  # Bad Request
    response_data = response.json()
    assert "detail" in response_data
    assert "not found for agent" in response_data["detail"].lower()
    assert invalid_client_id in response_data["detail"]


def test_register_workflow_success(api_client: TestClient):
    """
    Tests successful dynamic registration of a new simple workflow.
    """
    # Fixture handles setup
    workflow_name_to_register = "Dynamic Test Workflow"

    # Workflow config payload - references agents from testing_config.json
    workflow_payload = {
        "name": workflow_name_to_register,
        "steps": [
            "Weather Agent",
            "Planning Agent",
        ],  # Assumes these exist in base config
        "description": "A dynamically registered test workflow.",
    }

    # Explicitly add auth header
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        "/workflows/register", json=workflow_payload, headers=headers
    )

    assert response.status_code == 201  # Created
    response_data = response.json()
    assert response_data == {
        "status": "success",
        "workflow_name": workflow_name_to_register,
    }


def test_register_workflow_duplicate_name(api_client: TestClient):
    """
    Tests attempting to register a workflow with a name that already exists,
    which should now update the existing workflow (upsert behavior).
    """
    # Fixture handles setup
    workflow_name_to_register = "Duplicate Workflow Test"
    initial_description = "First registration."
    updated_description = "Second registration attempt."

    workflow_payload_initial = {
        "name": workflow_name_to_register,
        "steps": ["Weather Agent"],  # Assumes this agent exists
        "description": initial_description,
    }

    # Explicitly add auth header
    headers = {"X-API-Key": api_client.test_api_key}
    # First registration (should succeed)
    response1 = api_client.post(
        "/workflows/register", json=workflow_payload_initial, headers=headers
    )
    assert response1.status_code == 201
    assert response1.json()["workflow_name"] == workflow_name_to_register

    # Second registration attempt with the same name but different description (update)
    workflow_payload_updated = {
        "name": workflow_name_to_register,
        "steps": ["Weather Agent"],  # Steps could also be updated
        "description": updated_description,
    }
    response2 = api_client.post(
        "/workflows/register", json=workflow_payload_updated, headers=headers
    )

    assert response2.status_code == 201  # Expect 201 for create/update
    response_data = response2.json()
    assert response_data["status"] == "success"
    assert response_data["workflow_name"] == workflow_name_to_register
    # Ideally, verify the description was updated by GETting the config,
    # but this test focuses on the registration endpoint's behavior.


def test_register_workflow_invalid_agent_name(api_client: TestClient):
    """
    Tests attempting to register a workflow referencing a non-existent agent name.
    Expects a 400 Bad Request response.
    """
    # Fixture handles setup
    workflow_name_to_register = "Workflow Invalid Agent Test"
    invalid_agent_name = "non_existent_agent_name_456"

    workflow_payload = {
        "name": workflow_name_to_register,
        "steps": [invalid_agent_name],  # Reference the invalid agent
        "description": "This registration should fail.",
    }

    # Explicitly add auth header
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        "/workflows/register", json=workflow_payload, headers=headers
    )

    assert response.status_code == 400  # Bad Request
    response_data = response.json()
    assert "detail" in response_data
    # Updated to check for the more specific part of the error message
    assert "not found in componentmanager" in response_data["detail"].lower()
    assert invalid_agent_name in response_data["detail"]


# --- Listing Registered Components Endpoint Tests ---


def test_list_registered_agents_success(api_client: TestClient):
    """Tests successfully listing registered agents."""
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get("/components/agents", headers=headers)
    assert response.status_code == 200
    agent_names = response.json()
    assert isinstance(agent_names, list)
    # Check for agents defined in testing_config.json
    expected_agents = [
        "Weather Agent",
        "Weather Planning Agent",
        "Weather Planning Workflow Step 1",
        "Weather Planning Workflow Step 2",
        "Filtering Test Agent",
        "Planning Agent",
        "Mapping Agent",
    ]
    for agent_name in expected_agents:
        assert agent_name in agent_names
    assert len(agent_names) >= len(
        expected_agents
    )  # Could be more if dynamically registered


def test_list_registered_agents_unauthorized(api_client: TestClient):
    """Tests listing registered agents without API key."""
    response = api_client.get("/components/agents")  # No headers
    assert response.status_code == 401


def test_list_registered_simple_workflows_success(api_client: TestClient):
    """Tests successfully listing registered simple workflows."""
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get("/components/workflows", headers=headers)
    assert response.status_code == 200
    workflow_names = response.json()
    assert isinstance(workflow_names, list)
    expected_workflows = ["main"]
    for wf_name in expected_workflows:
        assert wf_name in workflow_names
    assert len(workflow_names) >= len(expected_workflows)


def test_list_registered_simple_workflows_unauthorized(api_client: TestClient):
    """Tests listing registered simple workflows without API key."""
    response = api_client.get("/components/workflows")  # No headers
    assert response.status_code == 401


def test_list_registered_custom_workflows_success(api_client: TestClient):
    """Tests successfully listing registered custom workflows."""
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get("/components/custom_workflows", headers=headers)
    assert response.status_code == 200
    custom_workflow_names = response.json()
    assert isinstance(custom_workflow_names, list)
    expected_custom_workflows = ["ExampleCustomWorkflow"]  # Corrected name
    for cwf_name in expected_custom_workflows:
        assert cwf_name in custom_workflow_names
    assert len(custom_workflow_names) >= len(expected_custom_workflows)


def test_list_registered_custom_workflows_unauthorized(api_client: TestClient):
    """Tests listing registered custom workflows without API key."""
    response = api_client.get("/components/custom_workflows")  # No headers
    assert response.status_code == 401


# To test empty lists, we would need a Aurite fixture that loads an empty config
# or a config with no components of a specific type. For now, these tests assume
# testing_config.json provides at least one of each.
# If Aurite is cleared and re-initialized by api_client fixture per test,
# we could potentially have a test that registers nothing then calls these.
# However, the current fixture setup loads testing_config.json by default.
# The endpoints themselves return [] if manager.*_configs is empty, which is implicitly tested.
import json  # Ensure json is imported for SSE parsing
from typing import (
    Dict,
    Any,
    AsyncGenerator,
    List,
)  # For SSE parsing, FakeLLMClient, and List type hint


# Helper for parsing SSE
async def parse_sse_stream(
    response_content: AsyncGenerator[bytes, None],
) -> List[Dict[str, Any]]:
    events = []
    current_event_type = None
    current_data_lines = []
    async for line_bytes in response_content:
        line = line_bytes.decode("utf-8").strip()
        if not line:  # Empty line signifies end of an event
            if current_event_type and current_data_lines:
                try:
                    data_str = "".join(current_data_lines)
                    data_json = json.loads(data_str)
                    events.append({"event_type": current_event_type, "data": data_json})
                except json.JSONDecodeError as e:
                    print(f"SSE JSON Decode Error: {e} for data: {data_str}")  # Or log
            current_event_type = None
            current_data_lines = []
        elif line.startswith("event:"):
            current_event_type = line[len("event:") :].strip()
        elif line.startswith("data:"):
            current_data_lines.append(line[len("data:") :].strip())
        # Ignoring id and retry for this parser
    return events


# @pytest.mark.anyio
# async def test_execute_agent_stream_e2e(async_api_client, monkeypatch):
#     """
#     E2E test for the /agents/{agent_name}/execute-stream endpoint.
#     Verifies correct SSE index handling and event streaming.
#     """
#     # --- Arrange ---
#     test_api_key = async_api_client.test_api_key
#     headers = {"X-API-Key": test_api_key, "Accept": "text/event-stream"}

#     agent_name_e2e = "E2EStreamingAgent"
#     fake_llm_id_e2e = "fake_llm_for_e2e_streaming"

#     # 1. Define the event sequence for the FakeLLMClient
#     llm_event_sequence_for_test = [
#         {"event_type": "text_block_start", "data": {"index": 0, "text": ""}},
#         {"event_type": "text_delta", "data": {"index": 0, "delta": "Thinking (E2E)..."}},
#         {"event_type": "content_block_stop", "data": {"index": 0}},
#         {"event_type": "text_block_start", "data": {"index": 0, "text": ""}}, # LLM reuses index 0
#         {"event_type": "text_delta", "data": {"index": 0, "delta": '{"result": "done (E2E)"}'}},
#         {"event_type": "content_block_stop", "data": {"index": 0}},
#         {"event_type": "stream_end", "data": {"stop_reason": "end_turn"}}
#     ]

#     # This is the challenging part: How does the Aurite's LLM client resolution
#     # pick up a FakeLLMClient *configured with llm_event_sequence_for_test*?
#     # Option A: Patch Aurite.llm_manager.get_client (or similar) to return our configured FakeLLMClient.
#     # Option B: If FakeLLMClient provider is registered, ensure it can be configured (e.g. via a global test state).

#     # For now, let's use patching to inject our pre-configured FakeLLMClient instance.
#     # We need to find where the LLM client is instantiated for an agent.
#     # This is likely in ExecutionFacade, which gets it from Aurite.
#     # So, we patch the method on Aurite that provides the LLM client.

#     # Assume Aurite has a method like `get_llm_client_instance(llm_id: str)`
#     # or `resolve_llm_client_for_agent(agent_config: AgentConfig)`
#     # For this example, let's assume a simplified path:
#     # ExecutionFacade calls something on Aurite, which eventually calls LLMClient.stream_message.
#     # We will patch the `stream_message` method of the specific LLM client instance
#     # that gets resolved for our test agent. This is tricky because the instance is created dynamically.

#     # A more robust E2E approach:
#     # 1. Register a "fake_streaming_provider" LLMConfig.
#     # 2. Ensure the application's LLM loading mechanism can instantiate FakeLLMClient for this provider.
#     # 3. The FakeLLMClient needs a way to get its event_sequence for a given test.
#     #    This could be a class variable on FakeLLMClient that tests can set.

#     # Setting a class variable on FakeLLMClient for the test sequence:
#     FakeLLMClient.test_event_sequence = llm_event_sequence_for_test

#     # This requires FakeLLMClient to be modified to use this class variable if its instance one is None.
#     # Let's assume FakeLLMClient is modified like:
#     # class FakeLLMClient:
#     #     test_event_sequence = None # Class variable
#     #     def __init__(self, event_sequence=None, llm_id=None): # llm_id might be passed by manager
#     #         self.event_sequence = event_sequence or FakeLLMClient.test_event_sequence or []
#     #         ...
#     # This change would need to be made in tests/mocks/fake_llm_client.py

#     # Register a fake LLM config that uses a provider name our app can map to FakeLLMClient
#     fake_llm_config_payload = {
#         "llm_id": fake_llm_id_e2e,
#         "provider": "fake_streaming_provider", # App needs to know how to handle this
#         "model": "fake_model_for_streaming_e2e",
#         # Add other required LLMConfig fields if any, e.g., api_key_env_var
#         "api_key_env_var": "FAKE_API_KEY_UNUSED"
#     }
#     response = await async_api_client.post("/llm-configs/register", json=fake_llm_config_payload, headers={"X-API-Key": test_api_key})
#     assert response.status_code == 201

#     # Register an agent that uses this fake LLM
#     agent_payload_e2e = {
#         "name": agent_name_e2e,
#         "llm_config_id": fake_llm_id_e2e,
#         "system_prompt": "You are an E2E streaming test agent."
#     }
#     response = await async_api_client.post("/agents/register", json=agent_payload_e2e, headers={"X-API-Key": test_api_key})
#     assert response.status_code == 201

#     # --- Act ---
#     user_message_e2e = "Stream test message"
#     params = {"user_message": user_message_e2e, "system_prompt": "Test prompt"}

#     collected_events_raw = []
#     async with async_api_client.stream("GET", f"/agents/{agent_name_e2e}/execute-stream", params=params, headers=headers) as stream_response:
#         assert stream_response.status_code == 200
#         assert stream_response.headers["content-type"] == "text/event-stream"
#         async for line_bytes in stream_response.aiter_bytes():
#             collected_events_raw.append(line_bytes) # Collect raw bytes first

#     # Manually parse the raw byte stream into SSE events
#     parsed_sse_events = []
#     current_event_type = None
#     current_data_lines = []
#     for line_bytes in collected_events_raw:
#         line = line_bytes.decode('utf-8').strip()
#         if not line:
#             if current_event_type and current_data_lines:
#                 try:
#                     data_str = "".join(current_data_lines)
#                     data_json = json.loads(data_str)
#                     parsed_sse_events.append({"event": current_event_type, "data": data_json})
#                 except json.JSONDecodeError as e:
#                     pytest.fail(f"SSE JSON Decode Error: {e} for data: {data_str}")
#             current_event_type = None
#             current_data_lines = []
#         elif line.startswith("event:"):
#             current_event_type = line[len("event:"):].strip()
#         elif line.startswith("data:"):
#             current_data_lines.append(line[len("data:"):].strip())


#     # --- Assert ---
#     assert len(parsed_sse_events) > 0 # Ensure some events were received

#     # Expected frontend indices for conceptual blocks
#     # Based on llm_event_sequence_for_test:
#     # Block 1: Thinking (LLM idx 0) -> Expected Frontend Index 0
#     # Block 2: Final Response (LLM idx 0 again) -> Expected Frontend Index 1

#     # Filter for events that should have our managed index
#     indexed_events = [event for event in parsed_sse_events if event["event"] in ["text_block_start", "text_delta", "content_block_stop"]]

#     assert len(indexed_events) == 6 # 3 for thinking, 3 for final response

#     # Thinking block (fidx 0)
#     assert indexed_events[0]["event"] == "text_block_start"
#     assert indexed_events[0]["data"]["index"] == 0
#     assert indexed_events[1]["event"] == "text_delta"
#     assert indexed_events[1]["data"]["index"] == 0
#     assert indexed_events[1]["data"]["delta"] == "Thinking (E2E)..."
#     assert indexed_events[2]["event"] == "content_block_stop"
#     assert indexed_events[2]["data"]["index"] == 0

#     # Final response block (fidx 1)
#     assert indexed_events[3]["event"] == "text_block_start"
#     assert indexed_events[3]["data"]["index"] == 1 # This is the key assertion for new block index
#     assert indexed_events[4]["event"] == "text_delta"
#     assert indexed_events[4]["data"]["index"] == 1
#     assert indexed_events[4]["data"]["delta"] == '{"result": "done (E2E)"}'
#     assert indexed_events[5]["event"] == "content_block_stop"
#     assert indexed_events[5]["data"]["index"] == 1

#     # Check for the llm_call_completed event (which is yielded by ATP from LLM's stream_end)
#     llm_completed_events = [event for event in parsed_sse_events if event["event"] == "llm_call_completed"]
#     assert len(llm_completed_events) == 1
#     assert llm_completed_events[0]["data"]["stop_reason"] == "end_turn"

#     # Cleanup: Unregister agent and LLM config if the API supports it,
#     # or rely on test isolation if Aurite is reset per test.
#     # For now, assume test isolation or manual cleanup if needed.
#     # Reset class variable on FakeLLMClient
#     if hasattr(FakeLLMClient, 'test_event_sequence'):
#         del FakeLLMClient.test_event_sequence


# --- Listing Clients Endpoint Tests ---


def test_list_registered_clients_success(api_client: TestClient):
    """Tests successfully listing registered clients."""
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get("/components/clients", headers=headers)
    assert response.status_code == 200
    client_ids = response.json()
    assert isinstance(client_ids, list)
    # Check for clients defined in testing_config.json
    expected_clients = [
        "weather_server",
        "planning_server",
        "address_server",
    ]
    for client_id in expected_clients:
        assert client_id in client_ids
    # Allow for more clients if dynamically registered in other tests,
    # but ensure these core ones are present.
    assert len(client_ids) >= len(expected_clients)


def test_list_registered_clients_unauthorized(api_client: TestClient):
    """Tests listing registered clients without API key."""
    response = api_client.get("/components/clients")  # No headers
    assert response.status_code == 401


# --- Listing LLM Configs Endpoint Tests ---


def test_list_registered_llm_configs_success(api_client: TestClient):
    """
    Tests successfully listing registered LLM configurations.
    Assumes testing_config.json (or defaults loaded by ProjectManager)
    results in at least the LLM configs used by agents in testing_config.json.
    The ProjectManager log indicates "2 llm_configs" are loaded.
    """
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get("/components/llm-configs", headers=headers)
    assert response.status_code == 200
    llm_config_ids = response.json()
    assert isinstance(llm_config_ids, list)
    # Based on ProjectManager log: "ComponentManager loaded: ... 2 llm_configs"
    # We expect at least these two, though their exact IDs might be derived
    # from model names if not explicitly set in a config file.
    # For this test, we'll check that the list is not empty and contains strings.
    # A more precise test would require knowing the exact IDs of these 2 llm_configs.
    # If default_llms.json contains "anthropic_claude_3_opus" and "anthropic_claude_3_haiku",
    # those would be the expected IDs.
    # Let's check for the ones used by agents in testing_config.json,
    # assuming they are registered or aliased.
    # The actual LLM IDs might be "claude-3-opus-20240229" and "claude-3-haiku-20240307"
    # if they are directly used as IDs, or some other mapping.
    # For now, let's assert that we get a list of strings and it's not unexpectedly empty.
    # The log states "2 llm_configs", so we expect at least that many.
    # The default llm_configs are "anthropic_claude_3_opus" and "anthropic_claude_3_haiku"
    # from config/llms/default_llms.json
    expected_llm_configs = [
        "anthropic_claude_3_opus",
        "anthropic_claude_3_haiku",
    ]
    for llm_id in expected_llm_configs:
        assert llm_id in llm_config_ids
    assert len(llm_config_ids) >= len(expected_llm_configs)


def test_list_registered_llm_configs_unauthorized(api_client: TestClient):
    """Tests listing registered LLM configurations without API key."""
    response = api_client.get("/components/llm-configs")  # No headers
    assert response.status_code == 401
