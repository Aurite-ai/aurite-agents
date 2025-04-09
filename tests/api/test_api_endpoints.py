"""
Integration tests for the main FastAPI application endpoints.

These tests interact with the API endpoints using TestClient and rely on the
application's lifespan to manage the HostManager state.
"""

import pytest
import os
from fastapi.testclient import TestClient

# Use relative imports assuming tests run from aurite-mcp root
from src.main import app  # Import the FastAPI app instance
from src.host_manager import HostManager  # Import HostManager for type hint

# Read API Key from environment for test headers
TEST_API_KEY = os.environ.get("API_KEY", "fallback-test-key-if-not-set")
# Determine if API key is properly set for skipping tests
API_KEY_IS_SET = TEST_API_KEY != "fallback-test-key-if-not-set"
ANTHROPIC_API_KEY_IS_SET = bool(os.environ.get("ANTHROPIC_API_KEY"))


# --- Fixtures ---


@pytest.fixture(scope="function")
def api_client() -> TestClient:
    """
    Provides a function-scoped TestClient instance for making API requests.
    Ensures clean state and lifespan interaction for each test.
    """
    # TestClient uses the app instance, which includes the lifespan manager
    return TestClient(app)


# --- Test Classes ---


@pytest.mark.integration
class TestBasicEndpoints:
    """Tests for basic server endpoints like /health and /status."""

    def test_health_check(self, api_client: TestClient):
        """Test the /health endpoint."""
        response = api_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.skipif(not API_KEY_IS_SET, reason="Requires API_KEY in environment")
    def test_get_status_success(
        self, api_client: TestClient
    ):  # Removed host_manager fixture argument
        """
        Test the /status endpoint with a valid API key.
        Relies on TestClient handling the app lifespan correctly.
        """
        headers = {"X-API-Key": TEST_API_KEY}
        response = api_client.get("/status", headers=headers)
        assert response.status_code == 200
        # Check the structure based on the refactored main.py
        assert response.json() == {"status": "initialized", "manager_status": "active"}

    def test_get_status_missing_key(self, api_client: TestClient):
        """Test the /status endpoint without an API key."""
        response = api_client.get("/status")
        assert response.status_code == 401  # Unauthorized

    def test_get_status_invalid_key(self, api_client: TestClient):
        """Test the /status endpoint with an invalid API key."""
        headers = {"X-API-Key": "invalid-key"}
        response = api_client.get("/status", headers=headers)
        assert response.status_code == 403  # Forbidden


# --- Agent Endpoint Tests ---
@pytest.mark.integration
class TestAgentEndpoints:
    """Tests for the /agents/{agent_name}/execute endpoint."""

    AGENT_NAME = "Weather Agent"  # Agent from testing_config.json
    USER_MESSAGE = "What is the weather in Boston?"

    @pytest.mark.skipif(not API_KEY_IS_SET, reason="Requires API_KEY in environment")
    @pytest.mark.skipif(
        not ANTHROPIC_API_KEY_IS_SET, reason="Requires ANTHROPIC_API_KEY"
    )
    def test_execute_agent_success(
        self, api_client: TestClient, host_manager: HostManager
    ):
        """Test successful execution of a known agent."""
        # host_manager fixture ensures lifespan context is ready
        headers = {"X-API-Key": TEST_API_KEY, "Content-Type": "application/json"}
        body = {"user_message": self.USER_MESSAGE}

        response = api_client.post(
            f"/agents/{self.AGENT_NAME}/execute", json=body, headers=headers
        )

        assert response.status_code == 200
        result = response.json()
        assert "final_response" in result
        assert result.get("error") is None
        assert hasattr(result["final_response"], "content")  # Basic check

    def test_execute_agent_not_found(
        self, api_client: TestClient, host_manager: HostManager
    ):
        """Test executing an agent not found in config returns 404."""
        headers = {"X-API-Key": TEST_API_KEY, "Content-Type": "application/json"}
        body = {"user_message": "test"}
        agent_name = "NonExistentAgent"

        response = api_client.post(
            f"/agents/{agent_name}/execute", json=body, headers=headers
        )

        assert response.status_code == 404
        assert agent_name in response.json().get("detail", "")

    def test_execute_agent_missing_body(
        self, api_client: TestClient, host_manager: HostManager
    ):
        """Test request without user_message returns 422."""
        headers = {"X-API-Key": TEST_API_KEY, "Content-Type": "application/json"}

        response = api_client.post(
            f"/agents/{self.AGENT_NAME}/execute", json={}, headers=headers
        )
        assert response.status_code == 422  # Unprocessable Entity


# --- Workflow Endpoint Tests ---
@pytest.mark.integration
class TestWorkflowEndpoints:
    """Tests for the /workflows/{workflow_name}/execute endpoint."""

    WORKFLOW_NAME = "Example workflow using weather and planning servers"  # From testing_config.json
    INITIAL_MESSAGE = "Check weather in Chicago and make plan."

    @pytest.mark.skipif(not API_KEY_IS_SET, reason="Requires API_KEY in environment")
    @pytest.mark.skipif(
        not ANTHROPIC_API_KEY_IS_SET, reason="Requires ANTHROPIC_API_KEY"
    )
    def test_execute_workflow_success(
        self, api_client: TestClient, host_manager: HostManager
    ):
        """Test successful execution of a known simple workflow."""
        headers = {"X-API-Key": TEST_API_KEY, "Content-Type": "application/json"}
        body = {"initial_user_message": self.INITIAL_MESSAGE}

        response = api_client.post(
            f"/workflows/{self.WORKFLOW_NAME}/execute", json=body, headers=headers
        )

        assert response.status_code == 200
        result = response.json()
        assert result.get("workflow_name") == self.WORKFLOW_NAME
        assert result.get("status") == "completed"
        assert result.get("error") is None
        assert isinstance(result.get("final_message"), str)
        assert len(result["final_message"]) > 0

    def test_execute_workflow_not_found(
        self, api_client: TestClient, host_manager: HostManager
    ):
        """Test executing a workflow not found in config returns 404."""
        headers = {"X-API-Key": TEST_API_KEY, "Content-Type": "application/json"}
        body = {"initial_user_message": "test"}
        workflow_name = "NonExistentWorkflow"

        response = api_client.post(
            f"/workflows/{workflow_name}/execute", json=body, headers=headers
        )

        assert response.status_code == 404
        assert workflow_name in response.json().get("detail", "")

    def test_execute_workflow_missing_body(
        self, api_client: TestClient, host_manager: HostManager
    ):
        """Test request without initial_user_message returns 422."""
        headers = {"X-API-Key": TEST_API_KEY, "Content-Type": "application/json"}

        response = api_client.post(
            f"/workflows/{self.WORKFLOW_NAME}/execute", json={}, headers=headers
        )
        assert response.status_code == 422  # Unprocessable Entity


# --- Custom Workflow Endpoint Tests ---
@pytest.mark.integration
class TestCustomWorkflowEndpoints:
    """Tests for the /custom_workflows/{workflow_name}/execute endpoint."""

    WORKFLOW_NAME = "ExampleCustom"  # From testing_config.json
    INITIAL_INPUT = {"city": "Paris"}

    @pytest.mark.skipif(not API_KEY_IS_SET, reason="Requires API_KEY in environment")
    @pytest.mark.skipif(
        not ANTHROPIC_API_KEY_IS_SET, reason="Requires ANTHROPIC_API_KEY"
    )
    def test_execute_custom_workflow_success(
        self, api_client: TestClient, host_manager: HostManager
    ):
        """Test successful execution of a known custom workflow."""
        headers = {"X-API-Key": TEST_API_KEY, "Content-Type": "application/json"}
        body = {"initial_input": self.INITIAL_INPUT}

        response = api_client.post(
            f"/custom_workflows/{self.WORKFLOW_NAME}/execute",
            json=body,
            headers=headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert result.get("workflow_name") == self.WORKFLOW_NAME
        assert result.get("status") == "completed"
        assert result.get("error") is None
        assert "result" in result
        # Check structure of the example workflow's output
        assert result["result"].get("status") == "success"
        assert result["result"].get("input_received") == self.INITIAL_INPUT
        assert isinstance(result["result"].get("agent_result_text"), str)

    def test_execute_custom_workflow_not_found(
        self, api_client: TestClient, host_manager: HostManager
    ):
        """Test executing a custom workflow not found in config returns 404."""
        headers = {"X-API-Key": TEST_API_KEY, "Content-Type": "application/json"}
        body = {"initial_input": "test"}
        workflow_name = "NonExistentCustomWorkflow"

        response = api_client.post(
            f"/custom_workflows/{workflow_name}/execute", json=body, headers=headers
        )

        assert response.status_code == 404
        assert workflow_name in response.json().get("detail", "")

    def test_execute_custom_workflow_missing_body(
        self, api_client: TestClient, host_manager: HostManager
    ):
        """Test request without initial_input returns 422."""
        headers = {"X-API-Key": TEST_API_KEY, "Content-Type": "application/json"}

        response = api_client.post(
            f"/custom_workflows/{self.WORKFLOW_NAME}/execute", json={}, headers=headers
        )
        assert response.status_code == 422  # Unprocessable Entity
