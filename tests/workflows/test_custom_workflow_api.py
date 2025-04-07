"""
Integration tests for the FastAPI custom workflow execution endpoint.
(/custom_workflows/{workflow_name}/execute)
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
import os
from typing import Any

# Use relative imports assuming tests run from aurite-mcp root
from src.main import (
    app,
    get_mcp_host,
    get_workflow_manager,
)  # Import app and dependency functions
from src.host.host import MCPHost
from src.workflows.manager import CustomWorkflowManager  # Import manager

# Read API Key from environment for test headers
TEST_API_KEY = os.environ.get("API_KEY", "fallback-test-key-if-not-set")
if TEST_API_KEY == "fallback-test-key-if-not-set":
    print("\nWARNING: API_KEY not found in environment for API tests. Using fallback.")

# --- Test Data ---
CUSTOM_WF_VALID_NAME = "ValidCustomWorkflow"
CUSTOM_WF_NOT_FOUND_NAME = "GhostCustomWorkflow"
CUSTOM_WF_HOST_ERROR_NAME = "HostErrorCustomWorkflow"  # Mock host error (e.g., import)
CUSTOM_WF_INTERNAL_ERROR_NAME = (
    "InternalErrorCustomWorkflow"  # Mock error within workflow
)

MOCK_INITIAL_INPUT = {"some_key": "some_value", "number": 123}
MOCK_SUCCESS_RESULT = {"output_key": "output_value", "processed": True}

# --- Fixtures ---


@pytest.fixture(scope="module")
def api_client() -> TestClient:
    """Provides a TestClient instance for making API requests."""
    return TestClient(app)


@pytest.fixture()  # Removed autouse=True
def mock_custom_workflow_dependencies(monkeypatch):
    """
    Automatically mock dependencies for custom workflow endpoint tests.
    Mocks MCPHost and CustomWorkflowManager dependencies.
    """
    # Mock MCPHost retrieval (still needed as input to manager)
    mock_host_instance = MagicMock(spec=MCPHost)
    app.dependency_overrides[get_mcp_host] = lambda: mock_host_instance

    # Mock CustomWorkflowManager retrieval and its execute_custom_workflow method
    mock_manager_instance = MagicMock(spec=CustomWorkflowManager)
    # Configure the side_effect for execute_custom_workflow within each test
    mock_manager_instance.execute_custom_workflow = AsyncMock()
    app.dependency_overrides[get_workflow_manager] = lambda: mock_manager_instance

    yield mock_manager_instance  # Provide mock manager for configuration in tests

    # Clean up dependency overrides
    app.dependency_overrides.pop(get_mcp_host, None)
    app.dependency_overrides.pop(get_workflow_manager, None)


# --- Test Class ---


@pytest.mark.integration
@pytest.mark.usefixtures(
    "mock_custom_workflow_dependencies"
)  # Apply mock fixture explicitly
class TestCustomWorkflowExecutionEndpoint:
    """Tests for the POST /custom_workflows/{workflow_name}/execute endpoint."""

    # This test now uses the mock_custom_workflow_dependencies fixture via the class mark
    def test_execute_custom_workflow_success(
        self,
        api_client: TestClient,
        mock_custom_workflow_dependencies,  # Fixture provides the mock manager
    ):
        """Test successful execution of a valid custom workflow."""
        mock_manager = mock_custom_workflow_dependencies  # Rename for clarity
        workflow_name = CUSTOM_WF_VALID_NAME
        request_body = {"initial_input": MOCK_INITIAL_INPUT}
        headers = {"X-API-Key": TEST_API_KEY}

        # Configure mock manager execute method for success
        mock_manager.execute_custom_workflow.return_value = MOCK_SUCCESS_RESULT

        response = api_client.post(
            f"/custom_workflows/{workflow_name}/execute",
            json=request_body,
            headers=headers,
        )

        # Assert response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["workflow_name"] == workflow_name
        assert response_data["status"] == "completed"
        assert response_data["result"] == MOCK_SUCCESS_RESULT
        assert response_data["error"] is None

        # Assert manager interaction (host_instance is checked implicitly by dependency injection)
        mock_manager.execute_custom_workflow.assert_awaited_once_with(
            workflow_name=workflow_name,
            initial_input=MOCK_INITIAL_INPUT,
            host_instance=mock_manager.execute_custom_workflow.call_args.kwargs[
                "host_instance"
            ],  # Verify host was passed
        )

    # This test now uses the mock_custom_workflow_dependencies fixture via the class mark
    def test_execute_custom_workflow_not_found(
        self,
        api_client: TestClient,
        mock_custom_workflow_dependencies,  # Fixture provides the mock manager
    ):
        """Test executing a non-existent custom workflow returns 404."""
        mock_manager = mock_custom_workflow_dependencies  # Rename for clarity
        workflow_name = CUSTOM_WF_NOT_FOUND_NAME
        request_body = {"initial_input": {}}
        headers = {"X-API-Key": TEST_API_KEY}

        # Configure mock manager execute method to raise KeyError
        mock_manager.execute_custom_workflow.side_effect = KeyError(
            f"Custom workflow configuration not found for name: {workflow_name}"
        )

        response = api_client.post(
            f"/custom_workflows/{workflow_name}/execute",
            json=request_body,
            headers=headers,
        )

        assert response.status_code == 404
        assert workflow_name in response.json().get("detail", "")
        mock_manager.execute_custom_workflow.assert_awaited_once()  # Still called

    # This test now uses the mock_custom_workflow_dependencies fixture via the class mark
    def test_execute_custom_workflow_host_setup_error(
        self,
        api_client: TestClient,
        mock_custom_workflow_dependencies,  # Fixture provides the mock manager
    ):
        """Test workflow returns 500 if manager fails during setup (e.g., import, attribute error)."""
        mock_manager = mock_custom_workflow_dependencies  # Rename for clarity
        workflow_name = CUSTOM_WF_HOST_ERROR_NAME
        request_body = {"initial_input": {}}
        headers = {"X-API-Key": TEST_API_KEY}
        error_message = "Simulated manager setup error (e.g., ImportError)"

        # Configure mock manager execute method to raise an error typical of setup issues
        mock_manager.execute_custom_workflow.side_effect = ImportError(error_message)

        response = api_client.post(
            f"/custom_workflows/{workflow_name}/execute",
            json=request_body,
            headers=headers,
        )

        # Assert response indicates server error during setup
        assert response.status_code == 500
        response_data = response.json()
        assert (
            f"Error setting up custom workflow '{workflow_name}'"
            in response_data.get("detail", "")
        )
        assert error_message in response_data.get("detail", "")

        # Assert manager interaction
        mock_manager.execute_custom_workflow.assert_awaited_once()

    # This test now uses the mock_custom_workflow_dependencies fixture via the class mark
    def test_execute_custom_workflow_internal_runtime_error(
        self,
        api_client: TestClient,
        mock_custom_workflow_dependencies,  # Fixture provides the mock manager
    ):
        """Test workflow returns 200 but failed status if the workflow itself raises RuntimeError."""
        mock_manager = mock_custom_workflow_dependencies  # Rename for clarity
        workflow_name = CUSTOM_WF_INTERNAL_ERROR_NAME
        request_body = {"initial_input": {}}
        headers = {"X-API-Key": TEST_API_KEY}
        error_message = (
            "Exception during custom workflow execution: Workflow failed internally"
        )

        # Configure mock manager execute method to raise RuntimeError
        mock_manager.execute_custom_workflow.side_effect = RuntimeError(error_message)

        response = api_client.post(
            f"/custom_workflows/{workflow_name}/execute",
            json=request_body,
            headers=headers,
        )

        # Assert response indicates failure status but 200 OK
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["workflow_name"] == workflow_name
        assert response_data["status"] == "failed"
        assert response_data["result"] is None
        assert error_message in response_data["error"]

        # Assert manager interaction
        mock_manager.execute_custom_workflow.assert_awaited_once()

    # This test does not need the host mock
    def test_execute_custom_workflow_missing_body(self, api_client: TestClient):
        """Test request without initial_input returns 422."""
        headers = {"X-API-Key": TEST_API_KEY}
        response = api_client.post(
            f"/custom_workflows/{CUSTOM_WF_VALID_NAME}/execute",
            json={},  # Missing initial_input
            headers=headers,
        )
        assert response.status_code == 422  # Unprocessable Entity

    # This test does not need the host mock
    def test_execute_custom_workflow_missing_api_key(self, api_client: TestClient):
        """Test request without API key returns 401."""
        response = api_client.post(
            f"/custom_workflows/{CUSTOM_WF_VALID_NAME}/execute",
            json={"initial_input": {}},
            # No headers
        )
        assert response.status_code == 401  # Unauthorized

    # This test does not need the host mock
    def test_execute_custom_workflow_invalid_api_key(self, api_client: TestClient):
        """Test request with invalid API key returns 403."""
        headers = {"X-API-Key": "invalid-key"}
        response = api_client.post(
            f"/custom_workflows/{CUSTOM_WF_VALID_NAME}/execute",
            json={"initial_input": {}},
            headers=headers,
        )
        assert response.status_code == 403  # Forbidden

    # --- E2E Test (Requires real host setup via fixture and API key) ---
    # This test uses the TestClient which implicitly uses the app's lifespan.
    # It should NOT use the mock_custom_workflow_dependencies fixture.
    # The `real_mcp_host` fixture (scoped function) will be used by the app lifespan
    # when tests are run with the e2e marker.
    @pytest.mark.e2e
    @pytest.mark.skipif(
        not TEST_API_KEY or TEST_API_KEY == "fallback-test-key-if-not-set",
        reason="Requires valid API_KEY in environment for E2E test",
    )
    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="Requires ANTHROPIC_API_KEY environment variable for agent call within workflow",
    )
    # Note: This test relies on the 'real_mcp_host' fixture.
    # We explicitly override the get_mcp_host dependency for this test
    # to ensure the correct host instance is used by the endpoint.
    def test_execute_example_custom_workflow_e2e(
        self, real_mcp_host: MCPHost
    ):  # Added real_mcp_host fixture
        """
        Test executing the example custom workflow end-to-end.
        Requires the real_mcp_host fixture (run with -m e2e).
        """
        workflow_name = "ExampleCustom"  # Defined in testing_config.json
        request_body = {
            "initial_input": "San Francisco"
        }  # Input for the example workflow
        headers = {"X-API-Key": TEST_API_KEY}

        # Instantiate TestClient directly for this test
        client = TestClient(app)

        # Override the dependency to return the specific host instance from the fixture
        app.dependency_overrides[get_mcp_host] = lambda: real_mcp_host
        try:
            # No mocking of host.execute_custom_workflow here - we want the real execution
            response = client.post(
                f"/custom_workflows/{workflow_name}/execute",
                json=request_body,
                headers=headers,
            )
        finally:
            # Clean up the dependency override
            app.dependency_overrides.pop(get_mcp_host, None)

        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["workflow_name"] == workflow_name
        assert response_data["status"] == "completed"
        assert response_data["error"] is None
        assert "result" in response_data
        assert isinstance(response_data["result"], dict)
        assert response_data["result"].get("status") == "success"
        assert response_data["result"].get("input_received") == "San Francisco"
        assert "agent_result_text" in response_data["result"]
        # We can't easily assert the exact weather text, but check it's a string
        assert isinstance(response_data["result"]["agent_result_text"], str)
        print(
            f"E2E Custom Workflow Result Text: {response_data['result']['agent_result_text']}"
        )  # Log for info
