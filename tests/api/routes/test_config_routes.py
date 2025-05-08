import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, ANY
from pydantic import ValidationError

# Import the FastAPI app instance and dependencies
from src.bin.api.api import app
from src.bin.dependencies import get_component_manager
from src.config.component_manager import ComponentManager
from src.config.config_models import (
    AgentConfig,
    ClientConfig,
)  # Import models for mocking

# Marker for API integration tests
pytestmark = [
    pytest.mark.api_integration,
    pytest.mark.config_api,
    pytest.mark.anyio,
]

# Define valid component types based on the API mapping
VALID_API_COMPONENT_TYPES = [
    "agents",
    "clients",
    "llm-configs",
    "simple-workflows",
    "custom-workflows",
]


# --- Mock ComponentManager Fixture ---
@pytest.fixture
def mock_cm():
    """Provides a MagicMock instance for ComponentManager."""
    cm = MagicMock(spec=ComponentManager)
    # Pre-configure some default behaviors if needed, or configure per-test
    cm.list_component_files.return_value = []
    cm.get_component_config.return_value = None
    # Configure CRUD methods to return mock models or raise errors as needed by tests
    # Example:
    # cm.create_component_file.return_value = MagicMock(spec=AgentConfig, name="MockAgent")
    # cm.save_component_config.return_value = MagicMock(spec=ClientConfig, name="MockClient")
    # cm.delete_component_config.return_value = True
    return cm


# --- Tests for GET /configs/{component_type} ---


@pytest.mark.parametrize("component_type", VALID_API_COMPONENT_TYPES)
def test_list_configs_success(
    api_client: TestClient, mock_cm: MagicMock, component_type: str
):
    """Tests successfully listing config files for valid types using mocked CM."""
    expected_files = [f"{component_type}_file1.json", f"{component_type}_file2.json"]
    mock_cm.list_component_files.return_value = expected_files

    # Override the dependency for this test
    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get(f"/configs/{component_type}", headers=headers)

    assert response.status_code == 200
    assert response.json() == expected_files
    # Verify mock was called with the correctly mapped internal type key
    # This requires knowing the mapping used in the route (_get_cm_component_type)
    from src.bin.api.routes.config_api import API_TO_CM_TYPE_MAP

    expected_cm_type = API_TO_CM_TYPE_MAP[component_type]
    mock_cm.list_component_files.assert_called_once_with(expected_cm_type)

    # Clear overrides after test
    app.dependency_overrides = {}


def test_list_configs_empty(api_client: TestClient, mock_cm: MagicMock):
    """Tests listing configs when the mocked CM returns an empty list."""
    component_type = "agents"
    mock_cm.list_component_files.return_value = []
    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get(f"/configs/{component_type}", headers=headers)

    assert response.status_code == 200
    assert response.json() == []
    mock_cm.list_component_files.assert_called_once_with(
        "agents"
    )  # Assuming 'agents' maps to 'agents'

    app.dependency_overrides = {}


def test_list_configs_invalid_type(api_client: TestClient, mock_cm: MagicMock):
    """Tests listing configs with an invalid component type (validation before CM)."""
    component_type = "invalid_type"
    app.dependency_overrides[get_component_manager] = lambda: mock_cm  # Override anyway

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get(f"/configs/{component_type}", headers=headers)

    assert response.status_code == 400
    assert "invalid component type" in response.json()["detail"].lower()
    mock_cm.list_component_files.assert_not_called()  # CM should not be called

    app.dependency_overrides = {}


def test_list_configs_unauthorized(api_client: TestClient):
    """Tests listing configs without API key."""
    response = api_client.get("/configs/agents", headers={})  # No auth header
    assert response.status_code == 401


# --- Tests for GET /configs/{component_type}/{filename} ---


def test_get_config_success(api_client: TestClient, mock_cm: MagicMock):
    """Tests successfully getting an existing config file using mocked CM."""
    component_type = "clients"
    filename = "test_get_client.json"
    component_id = "test_get_client"
    # Mock the return value of get_component_config
    mock_client_model = MagicMock(spec=ClientConfig)
    mock_client_model.model_dump.return_value = {
        "client_id": component_id,
        "server_path": "/mock/path",
    }
    mock_cm.get_component_config.return_value = mock_client_model

    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get(f"/configs/{component_type}/{filename}", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"client_id": component_id, "server_path": "/mock/path"}
    mock_cm.get_component_config.assert_called_once_with("clients", component_id)

    app.dependency_overrides = {}


def test_get_config_not_found(api_client: TestClient, mock_cm: MagicMock):
    """Tests getting a config file when mocked CM returns None."""
    component_type = "simple-workflows"
    filename = "non_existent_workflow.json"
    component_id = "non_existent_workflow"
    mock_cm.get_component_config.return_value = None  # Simulate not found

    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get(f"/configs/{component_type}/{filename}", headers=headers)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    mock_cm.get_component_config.assert_called_once_with(
        "simple_workflows", component_id
    )

    app.dependency_overrides = {}


@pytest.mark.parametrize(
    "invalid_filename, expected_status, expected_detail_part",
    [
        # Case 1: Invalid extension caught by API validation
        ("test.txt", 400, "must end with .json"),
        # Case 2: Path separators are now allowed by FastAPI path param, but should ideally be handled if problematic downstream
        # For now, we assume ComponentManager handles IDs with '/' if necessary, or API validation is sufficient.
        # Let's test the .json check primarily.
        # ("folder/file.json", 400, "invalid filename"), # This check was removed from API
    ],
)
def test_get_config_invalid_filename(
    api_client: TestClient,
    mock_cm: MagicMock,  # Add mock_cm fixture
    invalid_filename: str,
    expected_status: int,
    expected_detail_part: str,
):
    """Tests getting a config file with an invalid filename format."""
    component_type = "agents"
    app.dependency_overrides[get_component_manager] = lambda: mock_cm  # Override anyway

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get(
        f"/configs/{component_type}/{invalid_filename}", headers=headers
    )
    assert response.status_code == expected_status
    assert expected_detail_part in response.json()["detail"].lower()
    mock_cm.get_component_config.assert_not_called()  # CM should not be called if filename validation fails

    app.dependency_overrides = {}


def test_get_config_unauthorized(api_client: TestClient):
    """Tests getting a config file without API key."""
    response = api_client.get(
        "/configs/agents/some_agent.json", headers={}
    )  # No auth header
    assert response.status_code == 401


# --- Tests for POST /configs/{component_type}/{filename} ---


def test_create_config_success_new_file(api_client: TestClient, mock_cm: MagicMock):
    """Tests successfully creating a new config file via POST using mocked CM."""
    component_type = "agents"
    filename = "test_new_agent.json"
    component_id = "test_new_agent"
    config_content = {
        "name": component_id,
        "model": "test-model",
    }  # Ensure ID field 'name' is present
    payload = {"content": config_content}

    # Mock the return value of create_component_file
    mock_agent_model = MagicMock(spec=AgentConfig)
    mock_agent_model.model_dump.return_value = (
        config_content  # Return the same content for simplicity
    )
    mock_cm.create_component_file.return_value = mock_agent_model

    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )

    assert response.status_code == 201
    assert response.json() == config_content  # API returns the created model dump
    mock_cm.create_component_file.assert_called_once_with(
        "agents",  # Mapped type
        config_content,  # Payload passed to CM
        overwrite=False,
    )

    app.dependency_overrides = {}


def test_create_config_conflict(api_client: TestClient, mock_cm: MagicMock):
    """Tests POSTing a config file that already exists."""
    component_type = "agents"
    filename = "existing_agent.json"
    component_id = "existing_agent"
    config_content = {"name": component_id, "model": "test-model"}
    payload = {"content": config_content}

    # Configure mock to raise FileExistsError
    mock_cm.create_component_file.side_effect = FileExistsError(
        f"File for {component_id} exists."
    )

    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )

    assert response.status_code == 409  # Conflict
    assert "already exists" in response.json()["detail"].lower()
    mock_cm.create_component_file.assert_called_once_with(
        "agents", config_content, overwrite=False
    )

    app.dependency_overrides = {}


def test_create_config_invalid_type(api_client: TestClient, mock_cm: MagicMock):
    """Tests creating a config file with an invalid component type."""
    component_type = "invalid_type"
    filename = "test_invalid.json"
    payload = {"content": {"key": "value"}}
    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )
    assert response.status_code == 400
    assert "invalid component type" in response.json()["detail"].lower()
    mock_cm.create_component_file.assert_not_called()

    app.dependency_overrides = {}


@pytest.mark.parametrize(
    "invalid_filename, expected_status, expected_detail_part",
    [
        ("test.txt", 400, "must end with .json"),
        # Path separators allowed by FastAPI path param, not tested here as invalid
    ],
)
def test_create_config_invalid_filename(
    api_client: TestClient,
    mock_cm: MagicMock,
    invalid_filename: str,
    expected_status: int,
    expected_detail_part: str,
):
    """Tests creating a config file with an invalid filename format."""
    component_type = "clients"
    payload = {"content": {"key": "value"}}
    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        f"/configs/{component_type}/{invalid_filename}", json=payload, headers=headers
    )
    assert response.status_code == expected_status
    assert expected_detail_part in response.json()["detail"].lower()
    mock_cm.create_component_file.assert_not_called()

    app.dependency_overrides = {}


def test_create_config_validation_error(api_client: TestClient, mock_cm: MagicMock):
    """Tests creating a config file where CM validation fails."""
    component_type = "agents"
    filename = "test_validation_error.json"
    component_id = "test_validation_error"
    # Payload missing required 'name' field for AgentConfig
    config_content = {"model": "test-model"}
    payload = {"content": config_content}

    # Configure mock to raise validation error
    # Need to simulate the error structure Pydantic/CM might raise
    mock_cm.create_component_file.side_effect = ValueError(
        "Configuration validation failed: missing field 'name'"
    )

    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )

    assert response.status_code == 400  # Bad Request due to validation
    assert "invalid configuration data" in response.json()["detail"].lower()
    # Check that the payload passed to CM included the injected ID
    expected_payload_to_cm = config_content.copy()
    expected_payload_to_cm["name"] = component_id  # API injects ID from path
    mock_cm.create_component_file.assert_called_once_with(
        "agents", expected_payload_to_cm, overwrite=False
    )

    app.dependency_overrides = {}


def test_create_config_unauthorized(api_client: TestClient):
    """Tests creating a config file without API key."""
    payload = {"content": {"key": "value"}}
    response = api_client.post(
        "/configs/agents/new_agent.json", json=payload, headers={}
    )  # No auth header
    assert response.status_code == 401


# --- Tests for PUT /configs/{component_type}/{filename} ---


def test_update_config_success(api_client: TestClient, mock_cm: MagicMock):
    """Tests successfully updating an existing config file via PUT using mocked CM."""
    component_type = "agents"
    filename = "test_update_agent.json"
    component_id = "test_update_agent"
    updated_content = {
        "name": component_id,
        "model": "updated-model",
        "temperature": 0.8,
    }
    payload = {"content": updated_content}

    # Mock the return value of save_component_config
    mock_agent_model = MagicMock(spec=AgentConfig)
    mock_agent_model.model_dump.return_value = updated_content
    mock_cm.save_component_config.return_value = mock_agent_model

    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.put(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )

    assert response.status_code == 200  # OK for update/upsert
    assert response.json() == updated_content
    mock_cm.save_component_config.assert_called_once_with("agents", updated_content)

    app.dependency_overrides = {}


def test_update_config_creates_if_not_found(api_client: TestClient, mock_cm: MagicMock):
    """Tests that PUT creates the file if it doesn't exist (upsert behavior)."""
    component_type = "clients"
    filename = "new_client_via_put.json"
    component_id = "new_client_via_put"
    config_content = {"client_id": component_id, "server_path": "/new/path"}
    payload = {"content": config_content}

    # Mock save_component_config (which handles upsert)
    mock_client_model = MagicMock(spec=ClientConfig)
    mock_client_model.model_dump.return_value = config_content
    mock_cm.save_component_config.return_value = mock_client_model

    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.put(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )

    assert response.status_code == 200  # PUT returns 200 even on creation via upsert
    assert response.json() == config_content
    mock_cm.save_component_config.assert_called_once_with("clients", config_content)

    app.dependency_overrides = {}


def test_update_config_invalid_type(api_client: TestClient, mock_cm: MagicMock):
    """Tests updating a config file with an invalid component type."""
    component_type = "invalid_type"
    filename = "test_update_invalid.json"
    payload = {"content": {"key": "value"}}
    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.put(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )
    assert response.status_code == 400
    assert "invalid component type" in response.json()["detail"].lower()
    mock_cm.save_component_config.assert_not_called()

    app.dependency_overrides = {}


@pytest.mark.parametrize(
    "invalid_filename, expected_status, expected_detail_part",
    [
        ("test.txt", 400, "must end with .json"),
    ],
)
def test_update_config_invalid_filename(
    api_client: TestClient,
    mock_cm: MagicMock,
    invalid_filename: str,
    expected_status: int,
    expected_detail_part: str,
):
    """Tests updating a config file with an invalid filename format."""
    component_type = "simple-workflows"
    payload = {"content": {"key": "value"}}
    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.put(
        f"/configs/{component_type}/{invalid_filename}", json=payload, headers=headers
    )
    assert response.status_code == expected_status
    assert expected_detail_part in response.json()["detail"].lower()
    mock_cm.save_component_config.assert_not_called()

    app.dependency_overrides = {}


def test_update_config_validation_error(api_client: TestClient, mock_cm: MagicMock):
    """Tests updating a config file where CM validation fails."""
    component_type = "clients"
    filename = "test_update_validation_error.json"
    component_id = "test_update_validation_error"
    # Payload missing required 'client_id' field
    config_content = {"server_path": "/bad/path"}
    payload = {"content": config_content}

    mock_cm.save_component_config.side_effect = ValueError(
        "Validation failed: missing client_id"
    )
    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.put(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )

    assert response.status_code == 400
    assert "invalid configuration data" in response.json()["detail"].lower()
    expected_payload_to_cm = config_content.copy()
    expected_payload_to_cm["client_id"] = component_id  # API injects ID
    mock_cm.save_component_config.assert_called_once_with(
        "clients", expected_payload_to_cm
    )

    app.dependency_overrides = {}


def test_update_config_unauthorized(api_client: TestClient):
    """Tests updating a config file without API key."""
    payload = {"content": {"key": "value"}}
    response = api_client.put(
        "/configs/agents/agent_to_update.json", json=payload, headers={}
    )  # No auth header
    assert response.status_code == 401


# --- Tests for DELETE /configs/{component_type}/{filename} ---


def test_delete_config_success(api_client: TestClient, mock_cm: MagicMock):
    """Tests successfully deleting an existing config file using mocked CM."""
    component_type = "simple-workflows"
    filename = "test_delete_workflow.json"
    component_id = "test_delete_workflow"

    # Configure mock CM for delete success
    mock_cm.get_component_config.return_value = MagicMock()  # Simulate component exists
    mock_cm.delete_component_config.return_value = True

    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.delete(
        f"/configs/{component_type}/{filename}", headers=headers
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "success"
    assert response_data["filename"] == filename
    assert "deleted successfully" in response_data["message"].lower()
    mock_cm.delete_component_config.assert_called_once_with(
        "simple_workflows", component_id
    )

    app.dependency_overrides = {}


def test_delete_config_not_found(api_client: TestClient, mock_cm: MagicMock):
    """Tests attempting to delete a config file that does not exist using mocked CM."""
    component_type = "agents"
    filename = "non_existent_agent_for_delete.json"
    component_id = "non_existent_agent_for_delete"

    # Configure mock CM for not found
    mock_cm.get_component_config.return_value = None
    mock_cm.list_component_files.return_value = []  # Ensure file also not listed

    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.delete(
        f"/configs/{component_type}/{filename}", headers=headers
    )

    assert response.status_code == 404
    assert "not found for deletion" in response.json()["detail"].lower()
    mock_cm.get_component_config.assert_called_once_with("agents", component_id)
    mock_cm.list_component_files.assert_called_once_with("agents")
    mock_cm.delete_component_config.assert_not_called()  # Should not be called if not found

    app.dependency_overrides = {}


def test_delete_config_internal_error(api_client: TestClient, mock_cm: MagicMock):
    """Tests attempting to delete where CM indicates an internal error."""
    component_type = "clients"
    filename = "delete_fail_client.json"
    component_id = "delete_fail_client"

    # Configure mock CM for deletion failure
    mock_cm.get_component_config.return_value = MagicMock()  # Simulate component exists
    mock_cm.delete_component_config.return_value = False  # Simulate internal failure

    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.delete(
        f"/configs/{component_type}/{filename}", headers=headers
    )

    assert response.status_code == 500  # Internal Server Error
    assert "internal error" in response.json()["detail"].lower()
    mock_cm.delete_component_config.assert_called_once_with("clients", component_id)

    app.dependency_overrides = {}


def test_delete_config_invalid_type(api_client: TestClient, mock_cm: MagicMock):
    """Tests deleting a config file with an invalid component type."""
    component_type = "invalid_type"
    filename = "test_delete_invalid.json"
    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.delete(
        f"/configs/{component_type}/{filename}", headers=headers
    )
    assert response.status_code == 400
    assert "invalid component type" in response.json()["detail"].lower()
    mock_cm.delete_component_config.assert_not_called()

    app.dependency_overrides = {}


@pytest.mark.parametrize(
    "invalid_filename, expected_status, expected_detail_part",
    [
        ("test.txt", 400, "must end with .json"),
    ],
)
def test_delete_config_invalid_filename(
    api_client: TestClient,
    mock_cm: MagicMock,
    invalid_filename: str,
    expected_status: int,
    expected_detail_part: str,
):
    """Tests deleting a config file with an invalid filename format."""
    component_type = "clients"
    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.delete(
        f"/configs/{component_type}/{invalid_filename}", headers=headers
    )
    assert response.status_code == expected_status
    assert expected_detail_part in response.json()["detail"].lower()
    mock_cm.delete_component_config.assert_not_called()

    app.dependency_overrides = {}


def test_delete_config_unauthorized(api_client: TestClient):
    """Tests deleting a config file without API key."""
    response = api_client.delete(
        "/configs/agents/agent_to_delete.json", headers={}
    )  # No auth header
    assert response.status_code == 401
