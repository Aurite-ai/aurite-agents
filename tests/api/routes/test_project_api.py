import pytest
from fastapi.testclient import TestClient
from pathlib import Path

# Marker for API integration tests, specifically for project routes
pytestmark = [
    pytest.mark.api_integration,
    pytest.mark.project_api,
    pytest.mark.anyio,
]

# Define the path to the default testing config and the new minimal project config
DEFAULT_TESTING_CONFIG_PATH = "config/testing_config.json"
MINIMAL_PROJECT_CONFIG_PATH = "config/projects/minimal_project_for_test.json"


def list_registered_agents(api_client: TestClient) -> list[str]:
    """Helper function to list registered agents via API."""
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get("/components/agents", headers=headers)
    response.raise_for_status()  # Raise an exception for bad status codes
    return response.json()


def test_change_project_success(api_client: TestClient):
    """
    Tests successful changing of the active project.
    Verifies that the host manager's context (e.g., available agents)
    updates according to the new project configuration.
    """
    headers = {"X-API-Key": api_client.test_api_key}

    # --- Step 1: Verify initial state (using default testing_config.json) ---
    initial_agents = list_registered_agents(api_client)
    assert "Weather Agent" in initial_agents  # From testing_config.json
    assert "Minimal Test Agent" not in initial_agents

    # --- Step 2: Change project to the minimal test project ---
    change_payload = {"project_config_path": MINIMAL_PROJECT_CONFIG_PATH}
    response_change = api_client.post(
        "/projects/change", json=change_payload, headers=headers
    )
    assert response_change.status_code == 200
    change_data = response_change.json()
    assert change_data["status"] == "success"
    assert change_data["message"].startswith(
        "Successfully changed project to Minimal Test Project"
    )
    # Ensure the path in response is absolute and correct
    # Assuming PROJECT_ROOT is the parent of 'config/'
    from src.config import PROJECT_ROOT_DIR

    expected_new_path = (PROJECT_ROOT_DIR / MINIMAL_PROJECT_CONFIG_PATH).resolve()
    assert Path(change_data["current_project_path"]).resolve() == expected_new_path

    # --- Step 3: Verify state after changing to minimal_project_for_test.json ---
    agents_after_minimal_project_load = list_registered_agents(api_client)
    assert "Minimal Test Agent" in agents_after_minimal_project_load
    assert (
        "Weather Agent" not in agents_after_minimal_project_load
    )  # Should be unloaded

    # --- Step 4: Change project back to the default testing_config.json to restore state for other tests ---
    # This is important if tests share the same app instance and state across runs,
    # though with function-scoped fixtures, this might be less critical but good for explicit cleanup.
    change_back_payload = {"project_config_path": DEFAULT_TESTING_CONFIG_PATH}
    response_change_back = api_client.post(
        "/projects/change", json=change_back_payload, headers=headers
    )
    assert response_change_back.status_code == 200
    change_back_data = response_change_back.json()
    assert change_back_data["status"] == "success"
    assert change_back_data["message"].startswith(
        "Successfully changed project to DefaultMCPHost"
    )  # Name from testing_config.json

    # --- Step 5: Verify state after changing back to default ---
    agents_after_reverting = list_registered_agents(api_client)
    assert "Weather Agent" in agents_after_reverting
    assert "Minimal Test Agent" not in agents_after_reverting
