"""
Integration tests for the FastAPI workflow execution endpoint.
(/workflows/{workflow_name}/execute)
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock, call
from fastapi.testclient import TestClient
import os

# Use relative imports assuming tests run from aurite-mcp root
from src.main import app  # Import the FastAPI app instance
from src.host.models import AgentConfig, WorkflowConfig
from src.host.host import MCPHost
from src.agents.agent import Agent

# Read API Key from environment for test headers
TEST_API_KEY = os.environ.get("API_KEY", "fallback-test-key-if-not-set")
if TEST_API_KEY == "fallback-test-key-if-not-set":
    print("\nWARNING: API_KEY not found in environment for API tests. Using fallback.")


# --- Test Data ---
AGENT_1_NAME = "AgentStep1"
AGENT_2_NAME = "AgentStep2"
WORKFLOW_VALID_NAME = "ValidWorkflow"
WORKFLOW_UNKNOWN_AGENT_NAME = "UnknownAgentWorkflow"
WORKFLOW_EMPTY_NAME = "EmptyWorkflow"
WORKFLOW_NOT_FOUND_NAME = "GhostWorkflow"

MOCK_AGENT_CONFIGS = {
    AGENT_1_NAME: AgentConfig(name=AGENT_1_NAME, client_ids=["client-a"]),
    AGENT_2_NAME: AgentConfig(name=AGENT_2_NAME, client_ids=["client-b", "client-c"]),
}

MOCK_WORKFLOW_CONFIGS = {
    WORKFLOW_VALID_NAME: WorkflowConfig(
        name=WORKFLOW_VALID_NAME, steps=[AGENT_1_NAME, AGENT_2_NAME]
    ),
    WORKFLOW_UNKNOWN_AGENT_NAME: WorkflowConfig(
        name=WORKFLOW_UNKNOWN_AGENT_NAME, steps=[AGENT_1_NAME, "AgentNotFound"]
    ),
    WORKFLOW_EMPTY_NAME: WorkflowConfig(name=WORKFLOW_EMPTY_NAME, steps=[]),
}

# Mock results for agent execution steps
MOCK_STEP_1_RESULT = {
    "conversation": [],
    "final_response": MagicMock(
        content=[MagicMock(type="text", text="Output from step 1")]
    ),
    "tool_uses": [],
}
MOCK_STEP_2_RESULT = {
    "conversation": [],
    "final_response": MagicMock(
        content=[MagicMock(type="text", text="Final output from step 2")]
    ),
    "tool_uses": [],
}
MOCK_AGENT_ERROR_RESULT = {"error": "Agent failed execution"}
MOCK_AGENT_NO_TEXT_RESULT = {  # Result missing text block in content
    "conversation": [],
    "final_response": MagicMock(content=[MagicMock(type="tool_use")]),
    "tool_uses": [],
}


# --- Fixtures ---


@pytest.fixture(scope="module")
def api_client() -> TestClient:
    """Provides a TestClient instance for making API requests."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_workflow_dependencies(monkeypatch):
    """
    Automatically mock dependencies for workflow endpoint tests.
    Mocks get_api_key, MCPHost, and Agent.execute_agent.
    """
    # Mock API Key check
    monkeypatch.setattr("src.main.get_api_key", lambda: "valid-test-key")

    # Mock MCPHost retrieval and its methods
    mock_host = MagicMock(spec=MCPHost)

    def _get_agent_config(agent_name: str):
        if agent_name in MOCK_AGENT_CONFIGS:
            return MOCK_AGENT_CONFIGS[agent_name]
        else:
            raise KeyError(f"Agent config not found: {agent_name}")

    mock_host.get_agent_config = MagicMock(side_effect=_get_agent_config)

    def _get_workflow_config(workflow_name: str):
        if workflow_name in MOCK_WORKFLOW_CONFIGS:
            return MOCK_WORKFLOW_CONFIGS[workflow_name]
        else:
            raise KeyError(f"Workflow config not found: {workflow_name}")

    mock_host.get_workflow_config = MagicMock(side_effect=_get_workflow_config)

    # Set the mock host directly on the app state
    app.state.mcp_host = mock_host

    # Patch Agent and its execute_agent method
    # We'll configure the side_effect within each test as needed
    mock_agent_execute = AsyncMock()
    patcher = patch("src.main.Agent", autospec=True)
    MockAgentClass = patcher.start()
    MockAgentClass.return_value.execute_agent = mock_agent_execute

    yield mock_host, MockAgentClass, mock_agent_execute

    patcher.stop()
    # Clean up app state
    if hasattr(app.state, "mcp_host"):
        del app.state.mcp_host


# --- Test Class ---


@pytest.mark.integration
class TestWorkflowExecutionEndpoint:
    """Tests for the POST /workflows/{workflow_name}/execute endpoint."""

    def test_execute_workflow_success(
        self, api_client: TestClient, mock_workflow_dependencies
    ):
        """Test successful execution of a valid multi-step workflow."""
        mock_host, MockAgentClass, mock_agent_execute = mock_workflow_dependencies
        workflow_name = WORKFLOW_VALID_NAME
        initial_message = "Start the workflow"
        headers = {"X-API-Key": TEST_API_KEY}

        # Configure mock agent execute side effect for the two steps
        mock_agent_execute.side_effect = [MOCK_STEP_1_RESULT, MOCK_STEP_2_RESULT]

        response = api_client.post(
            f"/workflows/{workflow_name}/execute",
            json={"initial_user_message": initial_message},
            headers=headers,
        )

        # Assert response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["workflow_name"] == workflow_name
        assert response_data["status"] == "completed"
        assert (
            response_data["final_message"] == "Final output from step 2"
        )  # From MOCK_STEP_2_RESULT
        assert response_data["error"] is None

        # Assert host interactions
        mock_host.get_workflow_config.assert_called_once_with(workflow_name)
        assert mock_host.get_agent_config.call_count == 2
        mock_host.get_agent_config.assert_has_calls(
            [call(AGENT_1_NAME), call(AGENT_2_NAME)], any_order=False
        )  # Ensure called in order

        # Assert Agent instantiation arguments
        assert MockAgentClass.call_count == 2
        # Check the arguments passed to the constructor (__init__)
        assert MockAgentClass.call_args_list == [
            call(config=MOCK_AGENT_CONFIGS[AGENT_1_NAME]),
            call(config=MOCK_AGENT_CONFIGS[AGENT_2_NAME]),
        ]

        # Assert Agent execution calls
        assert mock_agent_execute.await_count == 2
        mock_agent_execute.assert_has_awaits(
            [
                # Call 1 (Step 1)
                call(
                    user_message=initial_message,
                    host_instance=mock_host,
                    filter_client_ids=MOCK_AGENT_CONFIGS[AGENT_1_NAME].client_ids,
                ),
                # Call 2 (Step 2)
                call(
                    user_message="Output from step 1",  # Input is output of step 1
                    host_instance=mock_host,
                    filter_client_ids=MOCK_AGENT_CONFIGS[AGENT_2_NAME].client_ids,
                ),
            ],
            any_order=False,
        )

    def test_execute_workflow_not_found(
        self, api_client: TestClient, mock_workflow_dependencies
    ):
        """Test executing a non-existent workflow returns 404."""
        mock_host, MockAgentClass, mock_agent_execute = mock_workflow_dependencies
        workflow_name = WORKFLOW_NOT_FOUND_NAME
        initial_message = "Does this work?"
        headers = {"X-API-Key": TEST_API_KEY}

        response = api_client.post(
            f"/workflows/{workflow_name}/execute",
            json={"initial_user_message": initial_message},
            headers=headers,
        )

        assert response.status_code == 404
        assert workflow_name in response.json().get("detail", "")
        mock_host.get_workflow_config.assert_called_once_with(workflow_name)
        mock_host.get_agent_config.assert_not_called()
        MockAgentClass.assert_not_called()
        mock_agent_execute.assert_not_awaited()

    def test_execute_workflow_agent_step_fails(
        self, api_client: TestClient, mock_workflow_dependencies
    ):
        """Test workflow stops and returns error if an agent step fails."""
        mock_host, MockAgentClass, mock_agent_execute = mock_workflow_dependencies
        workflow_name = WORKFLOW_VALID_NAME
        initial_message = "Start workflow, expect failure"
        headers = {"X-API-Key": TEST_API_KEY}

        # Configure mock agent execute to fail on the first step
        mock_agent_execute.side_effect = [
            MOCK_AGENT_ERROR_RESULT  # Fail on first call
        ]

        response = api_client.post(
            f"/workflows/{workflow_name}/execute",
            json={"initial_user_message": initial_message},
            headers=headers,
        )

        # Assert response indicates failure
        assert (
            response.status_code == 200
        )  # Endpoint itself succeeds, but reports failure
        response_data = response.json()
        assert response_data["workflow_name"] == workflow_name
        assert response_data["status"] == "failed"
        assert response_data["final_message"] is None
        assert "Agent 'AgentStep1' (step 1) failed" in response_data["error"]
        assert MOCK_AGENT_ERROR_RESULT["error"] in response_data["error"]

        # Assert host interactions
        mock_host.get_workflow_config.assert_called_once_with(workflow_name)
        mock_host.get_agent_config.assert_called_once_with(
            AGENT_1_NAME
        )  # Only called for step 1

        # Assert Agent instantiation and execution calls
        MockAgentClass.assert_called_once_with(config=MOCK_AGENT_CONFIGS[AGENT_1_NAME])
        mock_agent_execute.assert_awaited_once_with(  # Only called once
            user_message=initial_message,
            host_instance=mock_host,
            filter_client_ids=MOCK_AGENT_CONFIGS[AGENT_1_NAME].client_ids,
        )

    def test_execute_workflow_output_extraction_fails(
        self, api_client: TestClient, mock_workflow_dependencies
    ):
        """Test workflow stops if output cannot be extracted from an agent step."""
        mock_host, MockAgentClass, mock_agent_execute = mock_workflow_dependencies
        workflow_name = WORKFLOW_VALID_NAME
        initial_message = "Start workflow, expect extraction failure"
        headers = {"X-API-Key": TEST_API_KEY}

        # Configure mock agent execute to return non-text content on step 1
        mock_agent_execute.side_effect = [
            MOCK_AGENT_NO_TEXT_RESULT  # No text block
        ]

        response = api_client.post(
            f"/workflows/{workflow_name}/execute",
            json={"initial_user_message": initial_message},
            headers=headers,
        )

        # Assert response indicates failure
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["workflow_name"] == workflow_name
        assert response_data["status"] == "failed"
        assert response_data["final_message"] is None
        assert "response content has no text block" in response_data["error"]

        # Assert host interactions
        mock_host.get_workflow_config.assert_called_once_with(workflow_name)
        mock_host.get_agent_config.assert_called_once_with(AGENT_1_NAME)

        # Assert Agent instantiation and execution calls
        MockAgentClass.assert_called_once_with(config=MOCK_AGENT_CONFIGS[AGENT_1_NAME])
        mock_agent_execute.assert_awaited_once()  # Called once

    def test_execute_workflow_empty_steps(
        self, api_client: TestClient, mock_workflow_dependencies
    ):
        """Test executing a workflow with no steps."""
        mock_host, MockAgentClass, mock_agent_execute = mock_workflow_dependencies
        workflow_name = WORKFLOW_EMPTY_NAME
        initial_message = "This should do nothing"
        headers = {"X-API-Key": TEST_API_KEY}

        response = api_client.post(
            f"/workflows/{workflow_name}/execute",
            json={"initial_user_message": initial_message},
            headers=headers,
        )

        # Assert response indicates completion but returns initial message
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["workflow_name"] == workflow_name
        assert response_data["status"] == "completed_empty"
        assert response_data["final_message"] == initial_message
        assert response_data["error"] is None

        # Assert host interactions
        mock_host.get_workflow_config.assert_called_once_with(workflow_name)
        mock_host.get_agent_config.assert_not_called()
        MockAgentClass.assert_not_called()
        mock_agent_execute.assert_not_awaited()
