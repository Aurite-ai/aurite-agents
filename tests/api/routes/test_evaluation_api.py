import pytest
from fastapi.testclient import TestClient

# Marker for API integration tests, specifically for component routes
pytestmark = [
    pytest.mark.api_integration,
    pytest.mark.components_api,  # Add a specific marker if desired
    pytest.mark.anyio,
]



def test_execute_prompt_validation_file_success(api_client: TestClient):
    """
    Tests successful execution of prompt validation using a config file
    """

    payload = {"config_file": "planning_agent_default.json"}
    # Explicitly add auth header
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        "/evaluation/prompt_validation/file", json=payload, headers=headers
    )

    assert response.status_code == 200
    response_data = response.json()
    # Check the structure returned by the custom workflow executor via the facade
    assert "workflow_name" in response_data
    assert response_data["workflow_name"] == "Prompt Validation Workflow"
    assert "status" in response_data
    assert response_data["status"] == "completed"
    assert "result" in response_data
    assert "status" in response_data["result"]
    assert response_data["result"]["status"] == "success"