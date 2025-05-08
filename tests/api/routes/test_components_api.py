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
    Tests successful execution of a configured custom workflow ('ExampleCustom').
    """
    # Fixture handles setup
    workflow_name = "ExampleCustom"  # Custom workflow defined in testing_config.json
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
    Tests attempting to register a client with an ID that already exists.
    Expects a 409 Conflict response.
    """
    # Fixture handles setup
    client_id_to_register = "duplicate_client_test"
    server_path = "tests/fixtures/servers/weather_mcp_server.py"

    client_payload = {
        "client_id": client_id_to_register,
        "server_path": server_path,
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
        "/clients/register", json=client_payload, headers=headers
    )
    assert response1.status_code == 201

    # Second registration attempt with the same client_id
    response2 = api_client.post(
        "/clients/register", json=client_payload, headers=headers
    )

    assert response2.status_code == 409  # Conflict
    response_data = response2.json()
    assert "detail" in response_data
    assert "already registered" in response_data["detail"].lower()


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
    Tests attempting to register an agent with a name that already exists.
    Expects a 409 Conflict response.
    """
    # Fixture handles setup
    agent_name_to_register = "Duplicate Agent Test"

    agent_payload = {
        "name": agent_name_to_register,
        "client_ids": ["weather_server"],
        "system_prompt": "First registration.",
    }

    # Explicitly add auth header
    headers = {"X-API-Key": api_client.test_api_key}
    # First registration (should succeed)
    response1 = api_client.post("/agents/register", json=agent_payload, headers=headers)
    assert response1.status_code == 201

    # Second registration attempt with the same name
    agent_payload["system_prompt"] = "Second registration attempt."  # Modify slightly
    response2 = api_client.post("/agents/register", json=agent_payload, headers=headers)

    assert response2.status_code == 409  # Conflict
    response_data = response2.json()
    assert "detail" in response_data
    assert "already registered" in response_data["detail"].lower()


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
    Tests attempting to register a workflow with a name that already exists.
    Expects a 409 Conflict response.
    """
    # Fixture handles setup
    workflow_name_to_register = "Duplicate Workflow Test"

    workflow_payload = {
        "name": workflow_name_to_register,
        "steps": ["Weather Agent"],
        "description": "First registration.",
    }

    # Explicitly add auth header
    headers = {"X-API-Key": api_client.test_api_key}
    # First registration (should succeed)
    response1 = api_client.post(
        "/workflows/register", json=workflow_payload, headers=headers
    )
    assert response1.status_code == 201

    # Second registration attempt with the same name
    workflow_payload["description"] = "Second registration attempt."  # Modify slightly
    response2 = api_client.post(
        "/workflows/register", json=workflow_payload, headers=headers
    )

    assert response2.status_code == 409  # Conflict
    response_data = response2.json()
    assert "detail" in response_data
    assert "already registered" in response_data["detail"].lower()


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
    assert "not found for workflow" in response_data["detail"].lower()
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
    expected_custom_workflows = ["ExampleCustom"]
    for cwf_name in expected_custom_workflows:
        assert cwf_name in custom_workflow_names
    assert len(custom_workflow_names) >= len(expected_custom_workflows)


def test_list_registered_custom_workflows_unauthorized(api_client: TestClient):
    """Tests listing registered custom workflows without API key."""
    response = api_client.get("/components/custom_workflows")  # No headers
    assert response.status_code == 401


# To test empty lists, we would need a HostManager fixture that loads an empty config
# or a config with no components of a specific type. For now, these tests assume
# testing_config.json provides at least one of each.
# If HostManager is cleared and re-initialized by api_client fixture per test,
# we could potentially have a test that registers nothing then calls these.
# However, the current fixture setup loads testing_config.json by default.
# The endpoints themselves return [] if manager.*_configs is empty, which is implicitly tested.
