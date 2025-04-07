"""
Integration tests for the FastAPI API endpoints defined in src/main.py,
focusing on the agent execution endpoint.
"""

import os  # Import os to read environment variables
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

# Use relative imports assuming tests run from aurite-mcp root
from src.main import app  # Import the FastAPI app instance
from src.host.models import AgentConfig
from src.host.host import MCPHost

# Import fixtures (pytest will discover them from conftest and other fixture files)

# --- Test Data ---
MOCK_AGENT_NAME_MINIMAL = "TestAgentMinimal"
MOCK_AGENT_NAME_FILTERED = "TestAgentFiltered"
MOCK_AGENT_NAME_LLM = "TestAgentLLM"
NON_EXISTENT_AGENT_NAME = "GhostAgent"

MOCK_AGENT_CONFIGS = {
    MOCK_AGENT_NAME_MINIMAL: AgentConfig(name=MOCK_AGENT_NAME_MINIMAL, client_ids=None),
    MOCK_AGENT_NAME_FILTERED: AgentConfig(
        name=MOCK_AGENT_NAME_FILTERED, client_ids=["client-a", "client-c"]
    ),
    MOCK_AGENT_NAME_LLM: AgentConfig(
        name=MOCK_AGENT_NAME_LLM,
        model="test-model-override",
        temperature=0.5,
        client_ids=["client-b"],
    ),
}

MOCK_EXECUTE_RESULT = {
    "conversation": [{"role": "user", "content": "Test message"}],
    "final_response": "Mock agent response",
    "tool_uses": [],
}

# Read API Key from environment for test headers
# Assumes .env file is loaded correctly by pytest or the environment
TEST_API_KEY = os.environ.get("API_KEY", "fallback-test-key-if-not-set")
if TEST_API_KEY == "fallback-test-key-if-not-set":
    print("\nWARNING: API_KEY not found in environment for API tests. Using fallback.")


# --- Fixtures ---


@pytest.fixture(scope="module")
def api_client() -> TestClient:
    """Provides a TestClient instance for making API requests."""
    # We don't need the real lifespan here as we'll mock dependencies
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_dependencies(monkeypatch):
    """
    Automatically mock dependencies (get_api_key, get_mcp_host) for all tests
    in this module to isolate API endpoint logic.
    """
    # --- Mock dependencies ---
    # We will rely on the actual get_api_key dependency now,
    # assuming API_KEY is correctly set in the test environment (.env)

    # Mock MCPHost retrieval
    mock_host = MagicMock(spec=MCPHost)

    # Configure the mock host's get_agent_config method
    def _get_agent_config(agent_name: str):
        if agent_name in MOCK_AGENT_CONFIGS:
            return MOCK_AGENT_CONFIGS[agent_name]
        else:
            raise KeyError(f"Agent configuration not found for name: {agent_name}")

    # Assign a MagicMock and set its side_effect to the helper function
    mock_host.get_agent_config = MagicMock(side_effect=_get_agent_config)

    # Set the mock host directly on the app state for TestClient
    app.state.mcp_host = mock_host

    # Also patch Agent and its execute_agent method globally for this module
    mock_agent_execute = AsyncMock(return_value=MOCK_EXECUTE_RESULT)
    patcher = patch(
        "src.main.Agent", autospec=True
    )  # Patch Agent where it's used in main.py
    MockAgentClass = patcher.start()
    # Configure the instance's execute_agent method
    MockAgentClass.return_value.execute_agent = mock_agent_execute

    yield (
        mock_host,
        MockAgentClass,
        mock_agent_execute,
    )  # Provide mocks if needed by tests

    patcher.stop()  # Stop the patcher
    # Clean up app state
    if hasattr(app.state, "mcp_host"):
        del app.state.mcp_host


# --- Test Class ---


@pytest.mark.integration  # Mark as integration tests
class TestAgentExecutionEndpoint:
    """Tests for the POST /agents/{agent_name}/execute endpoint."""

    def test_execute_agent_success_minimal(
        self, api_client: TestClient, mock_dependencies
    ):
        """Test successful execution with minimal agent config (no filter)."""
        mock_host, MockAgentClass, mock_agent_execute = mock_dependencies
        agent_name = MOCK_AGENT_NAME_MINIMAL
        user_message = "Hello minimal agent"
        headers = {"X-API-Key": TEST_API_KEY}  # Use env API Key

        response = api_client.post(
            f"/agents/{agent_name}/execute",
            json={"user_message": user_message},
            headers=headers,  # Pass header
        )

        assert response.status_code == 200
        assert response.json() == MOCK_EXECUTE_RESULT

        # Verify host interaction
        mock_host.get_agent_config.assert_called_once_with(agent_name)

        # Verify Agent instantiation and execution call
        MockAgentClass.assert_called_once_with(config=MOCK_AGENT_CONFIGS[agent_name])
        mock_agent_execute.assert_awaited_once_with(
            user_message=user_message,
            host_instance=mock_host,
            filter_client_ids=None,  # Expect None for minimal config
        )

    def test_execute_agent_success_filtered(
        self, api_client: TestClient, mock_dependencies
    ):
        """Test successful execution with an agent config that has client_ids."""
        mock_host, MockAgentClass, mock_agent_execute = mock_dependencies
        agent_name = MOCK_AGENT_NAME_FILTERED
        user_message = "Hello filtered agent"
        expected_filter = MOCK_AGENT_CONFIGS[agent_name].client_ids
        headers = {"X-API-Key": TEST_API_KEY}  # Use env API Key

        response = api_client.post(
            f"/agents/{agent_name}/execute",
            json={"user_message": user_message},
            headers=headers,  # Pass header
        )

        assert response.status_code == 200
        assert response.json() == MOCK_EXECUTE_RESULT

        # Verify host interaction
        mock_host.get_agent_config.assert_called_once_with(agent_name)

        # Verify Agent instantiation and execution call
        MockAgentClass.assert_called_once_with(config=MOCK_AGENT_CONFIGS[agent_name])
        mock_agent_execute.assert_awaited_once_with(
            user_message=user_message,
            host_instance=mock_host,
            filter_client_ids=expected_filter,  # Expect the list from the config
        )

    def test_execute_agent_not_found(self, api_client: TestClient, mock_dependencies):
        """Test executing a non-existent agent name returns 404."""
        mock_host, MockAgentClass, mock_agent_execute = mock_dependencies
        agent_name = NON_EXISTENT_AGENT_NAME
        user_message = "Who are you?"
        headers = {"X-API-Key": TEST_API_KEY}  # Use env API Key

        response = api_client.post(
            f"/agents/{agent_name}/execute",
            json={"user_message": user_message},
            headers=headers,  # Pass header
        )

        assert response.status_code == 404
        assert agent_name in response.json().get("detail", "")

        # Verify host interaction (get_agent_config was called)
        mock_host.get_agent_config.assert_called_once_with(agent_name)

        # Verify Agent was NOT instantiated or executed
        MockAgentClass.assert_not_called()
        mock_agent_execute.assert_not_awaited()

    def test_execute_agent_missing_body(self, api_client: TestClient):
        """Test request without user_message returns 422 (Auth still required)."""
        headers = {"X-API-Key": TEST_API_KEY}  # Use env API Key
        response = api_client.post(
            f"/agents/{MOCK_AGENT_NAME_MINIMAL}/execute",
            json={},  # Missing user_message
            headers=headers,  # Pass header
        )
        assert response.status_code == 422  # Unprocessable Entity

    def test_execute_agent_invalid_body(self, api_client: TestClient):
        """Test request with incorrect body type returns 422 (Auth still required)."""
        headers = {"X-API-Key": TEST_API_KEY}  # Use env API Key
        response = api_client.post(
            f"/agents/{MOCK_AGENT_NAME_MINIMAL}/execute",
            json={"user_message": 123},  # Incorrect type
            headers=headers,  # Pass header
        )
        assert response.status_code == 422  # Unprocessable Entity

    # Security tests (API Key) are implicitly covered by mock_dependencies
    # If we wanted explicit tests, we'd need to manage the monkeypatch differently.
