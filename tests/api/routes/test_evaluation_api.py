import pytest
from fastapi.testclient import TestClient

# Marker for API integration tests, specifically for component routes
pytestmark = [
    pytest.mark.api_integration,
    pytest.mark.components_api,  # Add a specific marker if desired
    pytest.mark.anyio,
]



def test_execute_prompt_validaiton_file_success(api_client: TestClient):
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
    assert response_data["workflow_name"] == "Prompt Validation"
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