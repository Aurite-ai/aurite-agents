import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app instance from your API module
# Adjust the import path based on your project structure
from src.bin.api import app

# Marker for API integration tests
pytestmark = [
    pytest.mark.api_integration,
    pytest.mark.anyio,  # Assuming endpoints might be async
]


# --- Test Fixtures (Optional - TestClient handles basic app lifecycle) ---
# If more complex setup is needed (e.g., specific configs, DB state),
# fixtures can be defined here or in a tests/api/conftest.py


# --- Test Functions ---


def test_api_health_check():
    """
    Tests the /health endpoint for a 200 OK response.
    """
    # TestClient handles the application lifespan (startup/shutdown)
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_api_status_unauthorized():
    """
    Tests the /status endpoint without providing an API key.
    Expects a 401 Unauthorized response.
    """
    with TestClient(app) as client:
        response = client.get("/status")
        # The API key middleware should return 401 if key is missing
        assert response.status_code == 401
        # Detail message might vary slightly based on FastAPI/middleware version
        assert (
            "api key required in x-api-key header"
            in response.json().get("detail", "").lower()
        )


def test_api_status_authorized(monkeypatch):
    """
    Tests the /status endpoint with a valid API key.
    Expects a 200 OK response with the correct status message.
    """
    # Set required environment variables for the test context
    # NOTE: Assumes testing_config.json exists and is valid
    test_api_key = "test_integration_api_key"
    test_config_path = "config/testing_config.json"

    # Use monkeypatch to set environment variables for this test only
    monkeypatch.setenv("API_KEY", test_api_key)
    monkeypatch.setenv("HOST_CONFIG_PATH", test_config_path)
    # Ensure DB is disabled unless specifically testing DB features
    monkeypatch.setenv("AURITE_ENABLE_DB", "false")
    # Add other necessary env vars if your config/app requires them (e.g., ANTHROPIC_API_KEY)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy_anthropic_key")

    # Clear lru_cache for get_server_config to ensure it re-reads env vars
    # This is crucial if TestClient runs in the same process and imports happened before monkeypatch
    from src.bin.api import get_server_config

    get_server_config.cache_clear()
    # Also clear cache for HostManager's config loading if it uses caching
    # (Assuming it might, although current code doesn't show it explicitly)
    # from src.config import load_host_config_from_json # Adjust import if needed
    # load_host_config_from_json.cache_clear() # If caching is added there

    # Re-import or ensure the app uses the patched environment
    # TestClient should pick up the patched environment when initializing the app lifespan
    with TestClient(app) as client:
        headers = {"X-API-Key": test_api_key}
        response = client.get("/status", headers=headers)

        assert response.status_code == 200
        assert response.json() == {"status": "initialized", "manager_status": "active"}


def test_execute_agent_success(monkeypatch):
    """
    Tests successful execution of a configured agent ('Weather Agent').
    """
    test_api_key = "test_integration_api_key"
    test_config_path = "config/testing_config.json"
    agent_name = "Weather Agent"  # Agent defined in testing_config.json
    user_message = "What is the weather in London?"

    monkeypatch.setenv("API_KEY", test_api_key)
    monkeypatch.setenv("HOST_CONFIG_PATH", test_config_path)
    monkeypatch.setenv("AURITE_ENABLE_DB", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy_anthropic_key")  # Required by Agent

    from src.bin.api import get_server_config

    get_server_config.cache_clear()

    with TestClient(app) as client:
        headers = {"X-API-Key": test_api_key, "Content-Type": "application/json"}
        payload = {"user_message": user_message}
        response = client.post(
            f"/agents/{agent_name}/execute", headers=headers, json=payload
        )

        assert response.status_code == 200
        response_data = response.json()
        # Check for the presence of the expected output structure from Agent execution
        # In this integration test, the underlying LLM call is expected to fail due to the dummy key.
        # The agent should handle this and return a structure indicating failure, often with final_response=None.
        assert "final_response" in response_data
        assert response_data["final_response"] is None
        # We can also check if an error message is present, if the agent returns one
        assert "error" in response_data
        assert "Anthropic API call failed" in response_data["error"]


def test_execute_simple_workflow_success(monkeypatch):
    """
    Tests successful execution of a configured simple workflow ('main').
    """
    test_api_key = "test_integration_api_key"
    test_config_path = "config/testing_config.json"
    workflow_name = "main"  # Workflow defined in testing_config.json
    initial_message = "Check weather in SF and save plan."

    monkeypatch.setenv("API_KEY", test_api_key)
    monkeypatch.setenv("HOST_CONFIG_PATH", test_config_path)
    monkeypatch.setenv("AURITE_ENABLE_DB", "false")
    monkeypatch.setenv(
        "ANTHROPIC_API_KEY", "dummy_anthropic_key"
    )  # Required by agents in workflow

    from src.bin.api import get_server_config

    get_server_config.cache_clear()

    with TestClient(app) as client:
        headers = {"X-API-Key": test_api_key, "Content-Type": "application/json"}
        # Ensure the payload key matches the API endpoint model (ExecuteWorkflowRequest)
        payload = {"initial_user_message": initial_message}
        response = client.post(
            f"/workflows/{workflow_name}/execute", headers=headers, json=payload
        )

        assert response.status_code == 200
        response_data = response.json()
        # Check the structure returned by the simple workflow executor via the facade
        assert "workflow_name" in response_data
        assert response_data["workflow_name"] == workflow_name
        assert "status" in response_data
        # Even if underlying agents fail LLM calls, the workflow itself might complete.
        # Check for 'failed' status, as the underlying agent call fails due to the dummy key,
        # and the SimpleWorkflowExecutor propagates this failure.
        assert response_data["status"] == "failed"
        assert (
            "final_message" in response_data
        )  # Final message might be None or contain error info depending on executor
        # Check that the error field contains the expected error from the failed agent step
        assert "error" in response_data
        assert response_data["error"] is not None
        assert (
            "Agent 'Weather Planning Workflow Step 1' (step 1) failed"
            in response_data["error"]
        )
        assert "Anthropic API call failed" in response_data["error"]


def test_execute_custom_workflow_success(monkeypatch):
    """
    Tests successful execution of a configured custom workflow ('ExampleCustom').
    """
    test_api_key = "test_integration_api_key"
    test_config_path = "config/testing_config.json"
    workflow_name = "ExampleCustom"  # Custom workflow defined in testing_config.json
    initial_input = {"city": "London"}  # Example input for the workflow

    monkeypatch.setenv("API_KEY", test_api_key)
    monkeypatch.setenv("HOST_CONFIG_PATH", test_config_path)
    monkeypatch.setenv("AURITE_ENABLE_DB", "false")
    # Include dummy Anthropic key just in case the custom workflow calls an agent internally
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy_anthropic_key")

    from src.bin.api import get_server_config

    get_server_config.cache_clear()

    with TestClient(app) as client:
        headers = {"X-API-Key": test_api_key, "Content-Type": "application/json"}
        # Payload structure for custom workflows
        payload = {"initial_input": initial_input}
        response = client.post(
            f"/custom_workflows/{workflow_name}/execute", headers=headers, json=payload
        )

        assert response.status_code == 200
        response_data = response.json()
        # Check the structure returned by the custom workflow executor via the facade
        assert "workflow_name" in response_data
        assert response_data["workflow_name"] == workflow_name
        assert "status" in response_data
        # Expect 'failed' status because the internal agent call fails, and the API endpoint logic
        # correctly reports this failure at the top level based on the facade's return.
        assert response_data["status"] == "failed"
        # The 'result' field is likely None when the top-level status is 'failed'.
        assert "result" in response_data
        # Check that the top-level error field contains the relevant error message propagated by the API endpoint.
        assert "error" in response_data
        assert response_data["error"] is not None
        # The specific error message comes from the agent failure within the custom workflow
        assert "Anthropic API call failed" in response_data["error"]


# --- Registration Endpoint Tests ---


def test_register_client_success(monkeypatch):
    """
    Tests successful dynamic registration of a new client.
    """
    test_api_key = "test_registration_api_key"  # Use a different key if desired
    test_config_path = "config/testing_config.json"  # Base config
    client_id_to_register = "dynamic_weather_client"
    # Ensure the server path is valid relative to the project root
    server_path = "tests/fixtures/servers/weather_mcp_server.py"

    monkeypatch.setenv("API_KEY", test_api_key)
    monkeypatch.setenv("HOST_CONFIG_PATH", test_config_path)
    monkeypatch.setenv("AURITE_ENABLE_DB", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy_anthropic_key")

    from src.bin.api import get_server_config

    get_server_config.cache_clear()

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

    with TestClient(app) as client:
        headers = {"X-API-Key": test_api_key, "Content-Type": "application/json"}
        response = client.post(
            "/clients/register", headers=headers, json=client_payload
        )

        assert response.status_code == 201  # Created
        response_data = response.json()
        assert response_data == {
            "status": "success",
            "client_id": client_id_to_register,
        }

        # Optional: Verify the client is actually usable via another endpoint if needed,
        # though that might belong in more complex E2E tests.


def test_register_client_duplicate(monkeypatch):
    """
    Tests attempting to register a client with an ID that already exists.
    Expects a 409 Conflict response.
    """
    test_api_key = "test_registration_api_key"
    test_config_path = "config/testing_config.json"
    client_id_to_register = "duplicate_client_test"
    server_path = "tests/fixtures/servers/weather_mcp_server.py"

    monkeypatch.setenv("API_KEY", test_api_key)
    monkeypatch.setenv("HOST_CONFIG_PATH", test_config_path)
    monkeypatch.setenv("AURITE_ENABLE_DB", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy_anthropic_key")

    from src.bin.api import get_server_config

    get_server_config.cache_clear()

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

    with TestClient(app) as client:
        headers = {"X-API-Key": test_api_key, "Content-Type": "application/json"}

        # First registration (should succeed)
        response1 = client.post(
            "/clients/register", headers=headers, json=client_payload
        )
        assert response1.status_code == 201

        # Second registration attempt with the same client_id
        response2 = client.post(
            "/clients/register", headers=headers, json=client_payload
        )

        assert response2.status_code == 409  # Conflict
        response_data = response2.json()
        assert "detail" in response_data
        assert "already registered" in response_data["detail"].lower()


def test_register_agent_success(monkeypatch):
    """
    Tests successful dynamic registration of a new agent.
    """
    test_api_key = "test_registration_api_key"
    test_config_path = "config/testing_config.json"  # Base config
    agent_name_to_register = "Dynamic Test Agent"

    monkeypatch.setenv("API_KEY", test_api_key)
    monkeypatch.setenv("HOST_CONFIG_PATH", test_config_path)
    monkeypatch.setenv("AURITE_ENABLE_DB", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy_anthropic_key")

    from src.bin.api import get_server_config

    get_server_config.cache_clear()

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

    with TestClient(app) as client:
        headers = {"X-API-Key": test_api_key, "Content-Type": "application/json"}
        response = client.post("/agents/register", headers=headers, json=agent_payload)

        assert response.status_code == 201  # Created
        response_data = response.json()
        assert response_data == {
            "status": "success",
            "agent_name": agent_name_to_register,
        }


def test_register_agent_duplicate_name(monkeypatch):
    """
    Tests attempting to register an agent with a name that already exists.
    Expects a 409 Conflict response.
    """
    test_api_key = "test_registration_api_key"
    test_config_path = "config/testing_config.json"
    agent_name_to_register = "Duplicate Agent Test"

    monkeypatch.setenv("API_KEY", test_api_key)
    monkeypatch.setenv("HOST_CONFIG_PATH", test_config_path)
    monkeypatch.setenv("AURITE_ENABLE_DB", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy_anthropic_key")

    from src.bin.api import get_server_config

    get_server_config.cache_clear()

    agent_payload = {
        "name": agent_name_to_register,
        "client_ids": ["weather_server"],
        "system_prompt": "First registration.",
    }

    with TestClient(app) as client:
        headers = {"X-API-Key": test_api_key, "Content-Type": "application/json"}

        # First registration (should succeed)
        response1 = client.post("/agents/register", headers=headers, json=agent_payload)
        assert response1.status_code == 201

        # Second registration attempt with the same name
        agent_payload["system_prompt"] = (
            "Second registration attempt."  # Modify slightly
        )
        response2 = client.post("/agents/register", headers=headers, json=agent_payload)

        assert response2.status_code == 409  # Conflict
        response_data = response2.json()
        assert "detail" in response_data
        assert "already registered" in response_data["detail"].lower()


def test_register_agent_invalid_client_id(monkeypatch):
    """
    Tests attempting to register an agent referencing a non-existent client ID.
    Expects a 400 Bad Request response.
    """
    test_api_key = "test_registration_api_key"
    test_config_path = "config/testing_config.json"
    agent_name_to_register = "Agent Invalid Client Test"
    invalid_client_id = "non_existent_client_id_123"

    monkeypatch.setenv("API_KEY", test_api_key)
    monkeypatch.setenv("HOST_CONFIG_PATH", test_config_path)
    monkeypatch.setenv("AURITE_ENABLE_DB", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy_anthropic_key")

    from src.bin.api import get_server_config

    get_server_config.cache_clear()

    agent_payload = {
        "name": agent_name_to_register,
        "client_ids": [invalid_client_id],  # Reference the invalid client
        "system_prompt": "This registration should fail.",
    }

    with TestClient(app) as client:
        headers = {"X-API-Key": test_api_key, "Content-Type": "application/json"}
        response = client.post("/agents/register", headers=headers, json=agent_payload)

        assert response.status_code == 400  # Bad Request
        response_data = response.json()
        assert "detail" in response_data
        assert "not found for agent" in response_data["detail"].lower()
        assert invalid_client_id in response_data["detail"]


def test_register_workflow_success(monkeypatch):
    """
    Tests successful dynamic registration of a new simple workflow.
    """
    test_api_key = "test_registration_api_key"
    test_config_path = "config/testing_config.json"  # Base config
    workflow_name_to_register = "Dynamic Test Workflow"

    monkeypatch.setenv("API_KEY", test_api_key)
    monkeypatch.setenv("HOST_CONFIG_PATH", test_config_path)
    monkeypatch.setenv("AURITE_ENABLE_DB", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy_anthropic_key")

    from src.bin.api import get_server_config

    get_server_config.cache_clear()

    # Workflow config payload - references agents from testing_config.json
    workflow_payload = {
        "name": workflow_name_to_register,
        "steps": [
            "Weather Agent",
            "Planning Agent",
        ],  # Assumes these exist in base config
        "description": "A dynamically registered test workflow.",
    }

    with TestClient(app) as client:
        headers = {"X-API-Key": test_api_key, "Content-Type": "application/json"}
        response = client.post(
            "/workflows/register", headers=headers, json=workflow_payload
        )

        assert response.status_code == 201  # Created
        response_data = response.json()
        assert response_data == {
            "status": "success",
            "workflow_name": workflow_name_to_register,
        }


def test_register_workflow_duplicate_name(monkeypatch):
    """
    Tests attempting to register a workflow with a name that already exists.
    Expects a 409 Conflict response.
    """
    test_api_key = "test_registration_api_key"
    test_config_path = "config/testing_config.json"
    workflow_name_to_register = "Duplicate Workflow Test"

    monkeypatch.setenv("API_KEY", test_api_key)
    monkeypatch.setenv("HOST_CONFIG_PATH", test_config_path)
    monkeypatch.setenv("AURITE_ENABLE_DB", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy_anthropic_key")

    from src.bin.api import get_server_config

    get_server_config.cache_clear()

    workflow_payload = {
        "name": workflow_name_to_register,
        "steps": ["Weather Agent"],
        "description": "First registration.",
    }

    with TestClient(app) as client:
        headers = {"X-API-Key": test_api_key, "Content-Type": "application/json"}

        # First registration (should succeed)
        response1 = client.post(
            "/workflows/register", headers=headers, json=workflow_payload
        )
        assert response1.status_code == 201

        # Second registration attempt with the same name
        workflow_payload["description"] = (
            "Second registration attempt."  # Modify slightly
        )
        response2 = client.post(
            "/workflows/register", headers=headers, json=workflow_payload
        )

        assert response2.status_code == 409  # Conflict
        response_data = response2.json()
        assert "detail" in response_data
        assert "already registered" in response_data["detail"].lower()


def test_register_workflow_invalid_agent_name(monkeypatch):
    """
    Tests attempting to register a workflow referencing a non-existent agent name.
    Expects a 400 Bad Request response.
    """
    test_api_key = "test_registration_api_key"
    test_config_path = "config/testing_config.json"
    workflow_name_to_register = "Workflow Invalid Agent Test"
    invalid_agent_name = "non_existent_agent_name_456"

    monkeypatch.setenv("API_KEY", test_api_key)
    monkeypatch.setenv("HOST_CONFIG_PATH", test_config_path)
    monkeypatch.setenv("AURITE_ENABLE_DB", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy_anthropic_key")

    from src.bin.api import get_server_config

    get_server_config.cache_clear()

    workflow_payload = {
        "name": workflow_name_to_register,
        "steps": [invalid_agent_name],  # Reference the invalid agent
        "description": "This registration should fail.",
    }

    with TestClient(app) as client:
        headers = {"X-API-Key": test_api_key, "Content-Type": "application/json"}
        response = client.post(
            "/workflows/register", headers=headers, json=workflow_payload
        )

        assert response.status_code == 400  # Bad Request
        response_data = response.json()
        assert "detail" in response_data
        assert "not found for workflow" in response_data["detail"].lower()
        assert invalid_agent_name in response_data["detail"]
