import pytest
from fastapi.testclient import TestClient
import json
from pathlib import Path
import os

# Import PROJECT_ROOT for path manipulation in tests
from src.bin.dependencies import PROJECT_ROOT

# Marker for API integration tests
pytestmark = [
    pytest.mark.api_integration,
    pytest.mark.config_api,
    pytest.mark.anyio,
]


# Helper function to set up config directories/files for testing
from src.bin.api.routes.config_api import CONFIG_DIRS as API_CONFIG_DIRS # Import the actual mapping

def setup_test_config_file(component_type: str, filename: str, content: dict):
    """Creates a dummy config file in the actual project structure for testing GET/DELETE."""
    # Use the actual directory path from the API's CONFIG_DIRS mapping
    if component_type not in API_CONFIG_DIRS:
        raise ValueError(f"Invalid component_type '{component_type}' not found in API_CONFIG_DIRS for test setup.")

    actual_dir_name = API_CONFIG_DIRS[component_type] # This is a Path relative to PROJECT_ROOT/config
    target_dir = PROJECT_ROOT / actual_dir_name # API_CONFIG_DIRS already has "config/" prefix in its values

    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / filename
    with open(target_file, "w") as f:
        json.dump(content, f, indent=4)
    return target_file


def cleanup_test_config_file(file_path: Path):
    """Removes a dummy config file after testing."""
    if file_path and file_path.exists():
        try:
            os.remove(file_path)
            # Attempt to remove the directory if it's empty
            # try:
            #     file_path.parent.rmdir()
            # except OSError:
            #     pass # Directory not empty, ignore
        except Exception as e:
            print(
                f"Warning: Failed to cleanup test file {file_path}: {e}"
            )  # Use print for fixture cleanup


# --- Tests for GET /configs/{component_type} ---


<<<<<<< HEAD
@pytest.mark.parametrize("component_type", ["agents", "clients", "simple_workflows", "custom_workflows"])
=======
@pytest.mark.parametrize("component_type", ["agents", "clients", "workflows", "testing"])
>>>>>>> prompt-val-hotfix
def test_list_configs_success(api_client: TestClient, component_type: str):
    """Tests successfully listing config files for valid types."""
    # Ensure at least one file exists for the test
    filename = f"test_list_{component_type}.json"
    test_file_path = setup_test_config_file(component_type, filename, {"test": "data"})

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get(f"/configs/{component_type}", headers=headers)

    assert response.status_code == 200
    file_list = response.json()
    assert isinstance(file_list, list)
    assert filename in file_list  # Check if our test file is listed

    cleanup_test_config_file(test_file_path)  # Cleanup


def test_list_configs_empty(api_client: TestClient):
    """Tests listing configs when the directory is empty or doesn't exist."""
    component_type = "agents"
    # Ensure the directory is clean/doesn't exist initially if possible,
    # or just test against a known empty/non-existent one if setup is complex.
    # For simplicity, we assume the endpoint handles non-existent dirs gracefully.
    # If a file exists from a previous failed test, remove it.
    target_dir = PROJECT_ROOT / f"config/{component_type}"
    if target_dir.exists():
        # Clean up potential leftovers - adjust based on actual structure
        for item in target_dir.glob("*.json"):
            if item.is_file():
                item.unlink()

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get(f"/configs/{component_type}", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


def test_list_configs_invalid_type(api_client: TestClient):
    """Tests listing configs with an invalid component type."""
    component_type = "invalid_type"
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get(f"/configs/{component_type}", headers=headers)
    assert response.status_code == 400  # Expect Bad Request
    assert "invalid component type" in response.json()["detail"].lower()


def test_list_configs_unauthorized(api_client: TestClient):
    """Tests listing configs without API key."""
    response = api_client.get("/configs/agents", headers={})  # No auth header
    assert response.status_code == 401


# --- Tests for GET /configs/{component_type}/{filename} ---


def test_get_config_success(api_client: TestClient):
    """Tests successfully getting an existing config file."""
    component_type = "clients"
    filename = "test_get_client.json"
    content = {"client_id": "test_client", "server_path": "/path/to/server"}
    test_file_path = setup_test_config_file(component_type, filename, content)

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get(f"/configs/{component_type}/{filename}", headers=headers)

    assert response.status_code == 200
    assert response.json() == content

    cleanup_test_config_file(test_file_path)


def test_get_config_not_found(api_client: TestClient):
    """Tests getting a config file that does not exist."""
    component_type = "workflows"
    filename = "non_existent_workflow.json"
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get(f"/configs/{component_type}/{filename}", headers=headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    @pytest.mark.parametrize(
        "invalid_filename, expected_status, expected_detail_part",
        [
            # Case 1: '..' likely resolved by router before validation, hitting list endpoint validation
            ("../secrets.json", 400, "invalid component type specified"),
            # Case 2: Invalid extension caught by our validation
            ("test.txt", 400, "must end with .json"),
            # Case 3: Path separator caught by our validation
            ("folder/file.json", 400, "invalid filename (contains path separators)"),
        ],
    )
    def test_get_config_invalid_filename(
        api_client: TestClient,
        invalid_filename: str,
        expected_status: int,
        expected_detail_part: str,
    ):
        """Tests getting a config file with an invalid/disallowed filename."""
        component_type = "agents"
        headers = {"X-API-Key": api_client.test_api_key}
        response = api_client.get(
            f"/configs/{component_type}/{invalid_filename}", headers=headers
        )
        assert response.status_code == expected_status
        assert expected_detail_part in response.json()["detail"].lower()


def test_get_config_unauthorized(api_client: TestClient):
    """Tests getting a config file without API key."""
    response = api_client.get(
        "/configs/agents/some_agent.json", headers={}
    )  # No auth header
    assert response.status_code == 401


# --- Tests for POST /configs/{component_type}/{filename} ---


def test_upload_config_success_new_file(api_client: TestClient):
    """Tests successfully uploading a new config file."""
    component_type = "agents"
    filename = "test_new_agent_upload.json"
    config_content = {"name": "Test New Agent Upload", "model": "test-model"}
    payload = {"content": config_content}

    target_file = PROJECT_ROOT / f"config/{component_type}" / filename
    if target_file.exists():
        target_file.unlink()  # Ensure file doesn't exist before test

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )

    assert response.status_code == 201
    assert response.json() == {
        "status": "success",
        "filename": filename,
        "component_type": component_type,
    }

    # Verify file was created
    assert target_file.exists()
    with open(target_file, "r") as f:
        written_content = json.load(f)
    assert written_content == config_content

    cleanup_test_config_file(target_file)  # Cleanup


def test_upload_config_success_overwrite_file(api_client: TestClient):
    """Tests successfully uploading a config file that overwrites an existing one."""
    component_type = "workflows"
    filename = "test_overwrite_workflow.json"
    initial_content = {"name": "Initial Workflow", "steps": ["step1"]}
    new_content = {
        "name": "Overwritten Workflow",
        "steps": ["stepA", "stepB"],
        "description": "New",
    }
    payload = {"content": new_content}

    # Create the initial file
    test_file_path = setup_test_config_file(component_type, filename, initial_content)

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )

    assert response.status_code == 201  # POST should still return 201 even on overwrite
    assert response.json() == {
        "status": "success",
        "filename": filename,
        "component_type": component_type,
    }

    # Verify file was overwritten
    assert test_file_path.exists()
    with open(test_file_path, "r") as f:
        written_content = json.load(f)
    assert written_content == new_content  # Check for new content

    cleanup_test_config_file(test_file_path)


def test_upload_config_invalid_type(api_client: TestClient):
    """Tests uploading a config file with an invalid component type."""
    component_type = "invalid_type"
    filename = "test_invalid.json"
    payload = {"content": {"key": "value"}}
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )
    assert response.status_code == 400
    assert "invalid component type" in response.json()["detail"].lower()


@pytest.mark.parametrize(
    "invalid_filename, expected_status, expected_detail_part",
    [
        # Case 1: '..' likely resolved by router before validation, hitting no matching POST route
        ("../secrets.json", 405, "method not allowed"),  # Expect 405 now
        # Case 2: Invalid extension caught by our validation
        ("test.txt", 400, "must end with .json"),
        # Case 3: Path separator caught by our validation
        ("folder/file.json", 400, "invalid filename (contains path separators)"),
    ],
)
def test_upload_config_invalid_filename(
    api_client: TestClient,
    invalid_filename: str,
    expected_status: int,
    expected_detail_part: str,
):
    """Tests uploading a config file with an invalid filename."""
    component_type = "clients"
    payload = {"content": {"key": "value"}}
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        f"/configs/{component_type}/{invalid_filename}", json=payload, headers=headers
    )
    assert response.status_code == expected_status
    # For 405, detail might be simple "Method Not Allowed"
    assert expected_detail_part in response.json()["detail"].lower()


def test_upload_config_invalid_content(api_client: TestClient):
    """Tests uploading a config file with content that is not valid JSON (though FastAPI/Pydantic might catch this earlier)."""
    component_type = "agents"
    filename = "test_bad_content.json"
    # Pydantic model expects {"content": dict}, so send something else
    bad_payload = {"content": "this is not a dictionary"}
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        f"/configs/{component_type}/{filename}", json=bad_payload, headers=headers
    )
    # Expect 422 Unprocessable Entity from Pydantic validation
    assert response.status_code == 422


def test_upload_config_unauthorized(api_client: TestClient):
    """Tests uploading a config file without API key."""
    payload = {"content": {"key": "value"}}
    response = api_client.post(
        "/configs/agents/new_agent.json", json=payload, headers={}
    )  # No auth header
    assert response.status_code == 401


# --- Tests for PUT /configs/{component_type}/{filename} ---


def test_update_config_success(api_client: TestClient):
    """Tests successfully updating an existing config file."""
    component_type = "agents"
    filename = "test_update_agent.json"
    initial_content = {"name": "Update Agent", "model": "initial-model"}
    updated_content = {
        "name": "Update Agent",
        "model": "updated-model",
        "temperature": 0.8,
    }
    payload = {"content": updated_content}

    # Create the initial file
    test_file_path = setup_test_config_file(component_type, filename, initial_content)

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.put(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )

    assert response.status_code == 200  # Expect OK for update
    assert response.json() == {
        "status": "success",
        "filename": filename,
        "component_type": component_type,
    }

    # Verify file was updated
    assert test_file_path.exists()
    with open(test_file_path, "r") as f:
        written_content = json.load(f)
    assert written_content == updated_content

    cleanup_test_config_file(test_file_path)


def test_update_config_not_found(api_client: TestClient):
    """Tests attempting to update a config file that does not exist."""
    component_type = "clients"
    filename = "non_existent_client_for_update.json"
    payload = {"content": {"client_id": "update-fail"}}

    target_file = PROJECT_ROOT / f"config/{component_type}" / filename
    if target_file.exists():
        target_file.unlink()  # Ensure it doesn't exist

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.put(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )

    assert response.status_code == 404
    assert "not found for update" in response.json()["detail"].lower()


def test_update_config_invalid_type(api_client: TestClient):
    """Tests updating a config file with an invalid component type."""
    component_type = "invalid_type"
    filename = "test_update_invalid.json"
    payload = {"content": {"key": "value"}}
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.put(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )
    assert response.status_code == 400
    assert "invalid component type" in response.json()["detail"].lower()


@pytest.mark.parametrize(
    "invalid_filename, expected_status, expected_detail_part",
    [
        ("../secrets.json", 405, "method not allowed"),  # PUT likely also fails routing
        ("test.txt", 400, "must end with .json"),
        ("folder/file.json", 400, "invalid filename (contains path separators)"),
    ],
)
def test_update_config_invalid_filename(
    api_client: TestClient,
    invalid_filename: str,
    expected_status: int,
    expected_detail_part: str,
):
    """Tests updating a config file with an invalid filename."""
    component_type = "workflows"
    payload = {"content": {"key": "value"}}
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.put(
        f"/configs/{component_type}/{invalid_filename}", json=payload, headers=headers
    )
    assert response.status_code == expected_status
    assert expected_detail_part in response.json()["detail"].lower()


def test_update_config_invalid_content(api_client: TestClient):
    """Tests updating a config file with invalid content."""
    component_type = "agents"
    filename = "test_update_bad_content.json"
    initial_content = {"name": "Bad Content Agent"}
    test_file_path = setup_test_config_file(component_type, filename, initial_content)

    bad_payload = {"content": "not a dictionary"}
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.put(
        f"/configs/{component_type}/{filename}", json=bad_payload, headers=headers
    )
    assert response.status_code == 422  # Pydantic validation error

    cleanup_test_config_file(test_file_path)


def test_update_config_unauthorized(api_client: TestClient):
    """Tests updating a config file without API key."""
    payload = {"content": {"key": "value"}}
    response = api_client.put(
        "/configs/agents/agent_to_update.json", json=payload, headers={}
    )  # No auth header
    assert response.status_code == 401


# --- Tests for DELETE /configs/{component_type}/{filename} ---


def test_delete_config_success(api_client: TestClient):
    """Tests successfully deleting an existing config file."""
    component_type = "workflows"
    filename = "test_delete_workflow.json"
    content = {"name": "Delete Me", "steps": ["stepX"]}

    # Create the file to be deleted
    test_file_path = setup_test_config_file(component_type, filename, content)
    assert test_file_path.exists()  # Verify it exists before delete

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.delete(
        f"/configs/{component_type}/{filename}", headers=headers
    )

    assert response.status_code == 200  # Expect OK for successful delete
    response_data = response.json()
    assert response_data["status"] == "success"
    assert response_data["filename"] == filename
    assert "deleted successfully" in response_data["message"].lower()

    # Verify file no longer exists
    assert not test_file_path.exists()

    # No cleanup needed as the file is deleted by the test target


def test_delete_config_not_found(api_client: TestClient):
    """Tests attempting to delete a config file that does not exist."""
    component_type = "agents"
    filename = "non_existent_agent_for_delete.json"

    target_file = PROJECT_ROOT / f"config/{component_type}" / filename
    if target_file.exists():
        target_file.unlink()  # Ensure it doesn't exist

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.delete(
        f"/configs/{component_type}/{filename}", headers=headers
    )

    assert response.status_code == 404
    assert "not found for deletion" in response.json()["detail"].lower()


def test_delete_config_invalid_type(api_client: TestClient):
    """Tests deleting a config file with an invalid component type."""
    component_type = "invalid_type"
    filename = "test_delete_invalid.json"
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.delete(
        f"/configs/{component_type}/{filename}", headers=headers
    )
    assert response.status_code == 400
    assert "invalid component type" in response.json()["detail"].lower()


@pytest.mark.parametrize(
    "invalid_filename, expected_status, expected_detail_part",
    [
        (
            "../secrets.json",
            405,
            "method not allowed",
        ),  # DELETE likely also fails routing
        ("test.txt", 400, "must end with .json"),
        ("folder/file.json", 400, "invalid filename (contains path separators)"),
    ],
)
def test_delete_config_invalid_filename(
    api_client: TestClient,
    invalid_filename: str,
    expected_status: int,
    expected_detail_part: str,
):
    """Tests deleting a config file with an invalid filename."""
    component_type = "clients"
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.delete(
        f"/configs/{component_type}/{invalid_filename}", headers=headers
    )
    assert response.status_code == expected_status
    assert expected_detail_part in response.json()["detail"].lower()


def test_delete_config_unauthorized(api_client: TestClient):
    """Tests deleting a config file without API key."""
    response = api_client.delete(
        "/configs/agents/agent_to_delete.json", headers={}
    )  # No auth header
    assert response.status_code == 401
