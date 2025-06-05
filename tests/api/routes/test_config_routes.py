import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
import json
from pathlib import Path

# Import the FastAPI app instance and dependencies
from aurite.bin.api.api import app
from aurite.bin.dependencies import get_component_manager
from aurite.config.component_manager import ComponentManager, COMPONENT_TYPES_DIRS
from aurite.config.config_models import (
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


# --- Helper to create temp config files ---
@pytest.fixture
def temp_config_file_factory(tmp_path_factory):
    def _create_temp_config_file(component_type_key: str, filename: str, content: dict):
        # Use COMPONENT_TYPES_DIRS to determine the correct base directory
        # but place it under a temp pytest directory to avoid polluting real config
        # This requires COMPONENT_TYPES_DIRS to be patched or for tests to manage paths carefully.
        # For simplicity in this test, we'll create it directly in a subfolder of tmp_path
        # and the test will need to ensure the API route looks there (e.g., by patching COMPONENT_TYPES_DIRS).

        # Create a temporary directory structure similar to real config
        # e.g., tmp_path / "agents" / filename
        component_dir_name = COMPONENT_TYPES_DIRS[
            component_type_key
        ].name  # e.g., "agents"
        temp_component_dir = (
            tmp_path_factory.mktemp("config_test_root") / component_dir_name
        )
        temp_component_dir.mkdir(parents=True, exist_ok=True)

        file_path = temp_component_dir / filename
        with open(file_path, "w") as f:
            json.dump(content, f)
        return (
            file_path,
            temp_component_dir.parent,
        )  # Return path to file and the root of this temp config structure

    return _create_temp_config_file


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
    from aurite.bin.api.routes.config_routes import API_TO_CM_TYPE_MAP

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


# --- Tests for GET /configs/{component_type}/id/{component_id_or_name} ---


@pytest.mark.parametrize("component_type_api", VALID_API_COMPONENT_TYPES)
def test_get_specific_component_config_by_id_success(
    api_client: TestClient, mock_cm: MagicMock, component_type_api: str
):
    """Tests successfully getting a component by ID using mocked CM."""
    from aurite.bin.api.routes.config_routes import API_TO_CM_TYPE_MAP, COMPONENT_META

    cm_internal_type = API_TO_CM_TYPE_MAP[component_type_api]
    _, id_field = COMPONENT_META[cm_internal_type]

    component_id = f"test_{cm_internal_type}_id"
    mock_data = {id_field: component_id, "data": "some_data_for_id_endpoint"}

    # Determine mock spec based on component_type_api for better type safety if needed
    # For simplicity, MagicMock without spec is used here.
    mock_model_instance = MagicMock()
    mock_model_instance.model_dump.return_value = mock_data
    mock_cm.get_component_config.return_value = mock_model_instance

    app.dependency_overrides[get_component_manager] = lambda: mock_cm
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get(
        f"/configs/{component_type_api}/id/{component_id}", headers=headers
    )

    assert response.status_code == 200
    assert response.json() == mock_data
    mock_cm.get_component_config.assert_called_once_with(cm_internal_type, component_id)
    app.dependency_overrides = {}


@pytest.mark.parametrize("component_type_api", VALID_API_COMPONENT_TYPES)
def test_get_specific_component_config_by_id_not_found(
    api_client: TestClient, mock_cm: MagicMock, component_type_api: str
):
    """Tests getting a component by ID when mocked CM returns None."""
    component_type_api = "agents"
    component_id = "non_existent_agent_id"
    mock_cm.get_component_config.return_value = None

    app.dependency_overrides[get_component_manager] = lambda: mock_cm
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get(
        f"/configs/{component_type_api}/id/{component_id}", headers=headers
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    mock_cm.get_component_config.assert_called_once_with("agents", component_id)
    app.dependency_overrides = {}


# --- Tests for GET /configs/{component_type}/{filename:path} (Raw File Content) ---


def test_get_raw_config_file_success(
    api_client: TestClient, temp_config_file_factory, monkeypatch
):
    """Tests successfully getting raw content of an existing config file."""
    component_type_api = "agents"  # API path component type
    cm_internal_type = "agents"  # ComponentManager internal key
    filename = "test_raw_agent.json"
    expected_content = {"name": "raw_agent_test", "model": "raw_model"}

    _, temp_config_root = temp_config_file_factory(
        cm_internal_type, filename, expected_content
    )

    # Patch COMPONENT_TYPES_DIRS in the route's module to point to our temp dir
    monkeypatch.setitem(
        COMPONENT_TYPES_DIRS,
        cm_internal_type,
        temp_config_root / COMPONENT_TYPES_DIRS[cm_internal_type].name,
    )

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get(
        f"/configs/{component_type_api}/{filename}", headers=headers
    )

    assert response.status_code == 200
    assert response.json() == expected_content
    # No CM mock needed as this route reads files directly


def test_get_raw_config_file_not_found(api_client: TestClient, tmp_path, monkeypatch):
    """Tests getting raw content of a non-existent config file."""
    component_type_api = "clients"
    cm_internal_type = "clients"
    filename = "non_existent_raw.json"

    # Point to an empty temp directory
    temp_component_dir_name = COMPONENT_TYPES_DIRS[cm_internal_type].name
    empty_config_root = tmp_path / "empty_config_root"
    (empty_config_root / temp_component_dir_name).mkdir(parents=True, exist_ok=True)
    monkeypatch.setitem(
        COMPONENT_TYPES_DIRS,
        cm_internal_type,
        empty_config_root / temp_component_dir_name,
    )

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get(
        f"/configs/{component_type_api}/{filename}", headers=headers
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_raw_config_file_invalid_json(
    api_client: TestClient, temp_config_file_factory, monkeypatch
):
    """Tests getting raw content of a file with invalid JSON."""
    component_type_api = "llm-configs"
    cm_internal_type = "llm_configs"
    filename = "invalid_format.json"

    # Create a file with invalid JSON
    _, temp_config_root = temp_config_file_factory(
        cm_internal_type, filename, {}
    )  # Create empty first
    file_to_corrupt = (
        temp_config_root / COMPONENT_TYPES_DIRS[cm_internal_type].name / filename
    )
    with open(file_to_corrupt, "w") as f:
        f.write(
            "{'invalid_json': True,}"
        )  # Invalid JSON (single quotes, trailing comma)

    monkeypatch.setitem(
        COMPONENT_TYPES_DIRS,
        cm_internal_type,
        temp_config_root / COMPONENT_TYPES_DIRS[cm_internal_type].name,
    )

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get(
        f"/configs/{component_type_api}/{filename}", headers=headers
    )

    assert (
        response.status_code == 500
    )  # Or 400 depending on desired behavior for malformed server files
    assert "invalid json" in response.json()["detail"].lower()


@pytest.mark.xfail(
    reason="URL normalization by FastAPI/Starlette bypasses this route for ../ type traversal."
)
def test_get_raw_config_file_path_traversal(
    api_client: TestClient, monkeypatch, tmp_path: Path
):
    """Tests attempting path traversal when getting raw config file."""
    component_type_api = "agents"
    cm_internal_type = "agents"  # For patching
    # Malicious filename attempting to go up one directory
    filename = "../../../etc/passwd"

    # Patch COMPONENT_TYPES_DIRS to a known safe temp location
    # The route itself should prevent traversal before even trying to use this path.
    safe_temp_dir = tmp_path / "safe_agents_config"  # Use the tmp_path fixture directly
    safe_temp_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setitem(COMPONENT_TYPES_DIRS, cm_internal_type, safe_temp_dir)

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.get(
        f"/configs/{component_type_api}/{filename}", headers=headers
    )

    assert response.status_code == 400  # Bad Request due to invalid path
    assert "invalid filename or path" in response.json()["detail"].lower()


# --- Old tests for GET /configs/{component_type}/{filename} (now covered by /id/ variant or new raw file tests) ---
# These can be removed or refactored if they were targeting the /id/ endpoint implicitly.
# For now, I'll comment them out to avoid redundancy and ensure new tests are primary.

# def test_get_config_success(api_client: TestClient, mock_cm: MagicMock): ...
# def test_get_config_not_found(api_client: TestClient, mock_cm: MagicMock): ...


@pytest.mark.parametrize(
    "invalid_filename, expected_status, expected_detail_part",
    [
        ("test.txt", 400, "must end with .json"),
    ],
)
def test_get_config_invalid_filename_format(  # Renamed to avoid conflict
    api_client: TestClient,
    mock_cm: MagicMock,
    invalid_filename: str,
    expected_status: int,
    expected_detail_part: str,
):
    """Tests getting a config file with an invalid filename format (for /id/ endpoint)."""
    component_type = "agents"
    # This test is for the /id/{component_id} endpoint where filename is used to derive ID.
    # The raw file endpoint /configs/{component_type}/{filename:path} has its own filename checks.
    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    # Test against the /id/ endpoint structure if that's what this was for
    # If it was for the raw file endpoint, it's covered by new tests.
    # Assuming it was for the ID-based one:
    response = api_client.get(
        f"/configs/{component_type}/id/{invalid_filename}",
        headers=headers,  # Using /id/ path
    )
    # If the ID itself (derived from filename) is invalid before CM lookup, it might be a 400.
    # If the ID is valid but CM returns not found, it's 404.
    # The original test checked for "must end with .json" which is part of _extract_component_id
    # used by POST/PUT/DELETE, but not directly by GET /id/{id}.
    # Let's adjust this test or clarify its target.
    # For now, assuming _extract_component_id is NOT called by GET /id/{id} path param.
    # If the test was for the raw file path, it's now covered by test_get_raw_config_file_path_traversal
    # or similar. The "must end with .json" for the filename in the path param of the raw file
    # endpoint is not explicitly enforced by the route itself, but by _extract_component_id in other routes.
    # The raw file GET route does not call _extract_component_id.
    # This test might be redundant or needs to target a specific validation that happens for /id/ path.
    # For now, let's assume it's for the filename validation in POST/PUT/DELETE.
    # If it's for GET /id/, then `invalid_filename` is the ID, and .json check doesn't apply to ID.
    # Re-evaluating: _extract_component_id is used by POST/PUT/DELETE.
    # GET /id/{id} takes id directly. GET /{type}/{filename:path} takes filename.
    # This test seems to be for a validation that happens in POST/PUT/DELETE.
    # Let's assume this test is actually for the filename validation in POST/PUT/DELETE context.
    # The original test_get_config_invalid_filename was for GET /{type}/{filename}
    # The route for GET /{type}/{filename:path} does not call _extract_component_id.
    # So, the "must end with .json" detail would not come from there.
    # This test is likely better suited for POST/PUT/DELETE filename validation.
    # I will move this specific parametrize to the POST tests.
    # For GET /id/{id}, an ID like "test.txt" is valid as an ID string.
    # For GET /{type}/{filename:path}, a filename "test.txt" is valid for the path param.
    # The error "must end with .json" comes from _extract_component_id.

    # Removing this test for now as its original target is unclear and covered elsewhere or invalid for GET.
    # If this was meant for the raw file GET, the filename "test.txt" would be sought, likely 404.
    # If it was meant for the /id/ GET, "test.txt" is a valid ID string.
    pytest.skip("Re-evaluating target of this parametrized test for GET routes.")

    app.dependency_overrides = {}


def test_get_config_unauthorized(
    api_client: TestClient,
):  # This was for the old /configs/{type}/{filename}
    """Tests getting a config file without API key (for /id/ endpoint)."""
    response = api_client.get(
        "/configs/agents/id/some_agent_id",
        headers={},  # Target /id/ endpoint
    )
    assert response.status_code == 401


def test_get_raw_config_file_unauthorized(api_client: TestClient):
    """Tests getting raw config file without API key."""
    response = api_client.get("/configs/agents/some_agent.json", headers={})
    assert response.status_code == 401


# --- Tests for POST /configs/{component_type}/{filename} ---


# Moved parametrize here from GET tests as _extract_component_id is used in POST
@pytest.mark.parametrize(
    "invalid_filename, expected_status, expected_detail_part",
    [
        ("test.txt", 400, "must end with .json"),
    ],
)
def test_create_config_invalid_filename_format(  # Renamed
    api_client: TestClient,
    mock_cm: MagicMock,
    invalid_filename: str,
    expected_status: int,
    expected_detail_part: str,
):
    """Tests creating a config file with an invalid filename format for POST."""
    component_type = "clients"
    payload = {"content": {"key": "value"}}  # Dummy payload
    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        f"/configs/{component_type}/{invalid_filename}", json=payload, headers=headers
    )
    assert response.status_code == expected_status
    assert expected_detail_part in response.json()["detail"].lower()
    mock_cm.create_component_file.assert_not_called()
    app.dependency_overrides = {}


def test_create_config_success_new_file(api_client: TestClient, mock_cm: MagicMock):
    """Tests successfully creating a new config file via POST using mocked CM."""
    component_type = "agents"
    filename = "test_new_agent.json"
    component_id = "test_new_agent"
    config_content = {
        "name": component_id,
        "model": "test-model",
    }
    payload = {"content": config_content}

    mock_agent_model = MagicMock(spec=AgentConfig)
    mock_agent_model.model_dump.return_value = config_content
    # Configure the mock to have the 'name' attribute
    setattr(mock_agent_model, "name", component_id)
    mock_cm.create_component_file.return_value = mock_agent_model

    app.dependency_overrides[get_component_manager] = lambda: mock_cm
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )

    assert response.status_code == 201
    assert response.json() == config_content

    # Check payload passed to CM. API route injects ID from filename if not present.
    expected_payload_to_cm = config_content.copy()
    # If 'name' wasn't in config_content, it would be added. Here it is.
    # If config_content['name'] != component_id, a warning is logged by API route.
    # cm.create_component_file is called with the (potentially modified) config_payload.
    mock_cm.create_component_file.assert_called_once_with(
        "agents",
        expected_payload_to_cm,
        overwrite=False,
    )
    app.dependency_overrides = {}


def test_create_config_list_payload_success(api_client: TestClient, mock_cm: MagicMock):
    """Tests creating a config file with a list payload."""
    component_type = "clients"
    filename = "multiple_clients.json"
    list_content = [
        {"client_id": "client1", "server_path": "/path1"},
        {"client_id": "client2", "server_path": "/path2"},
    ]
    payload = {"content": list_content}

    mock_client_models = [MagicMock(spec=ClientConfig) for _ in list_content]
    for i, mock_model in enumerate(mock_client_models):
        mock_model.model_dump.return_value = list_content[i]

    mock_cm.save_components_to_file.return_value = mock_client_models

    app.dependency_overrides[get_component_manager] = lambda: mock_cm
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )

    assert response.status_code == 201
    assert response.json() == [model.model_dump() for model in mock_client_models]
    mock_cm.save_components_to_file.assert_called_once_with(
        "clients", list_content, filename, overwrite=False
    )
    app.dependency_overrides = {}


def test_create_config_conflict(api_client: TestClient, mock_cm: MagicMock):
    """Tests POSTing a config file that already exists."""
    component_type = "agents"
    filename = "existing_agent.json"
    component_id = "existing_agent"
    config_content = {"name": component_id, "model": "test-model"}
    payload = {"content": config_content}

    mock_cm.create_component_file.side_effect = FileExistsError(
        f"File for {component_id} exists."
    )
    app.dependency_overrides[get_component_manager] = lambda: mock_cm
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )

    assert response.status_code == 409
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


def test_create_config_validation_error(api_client: TestClient, mock_cm: MagicMock):
    """Tests creating a config file where CM validation fails."""
    component_type = "agents"
    filename = "test_validation_error.json"
    component_id = "test_validation_error"
    config_content = {"model": "test-model"}  # Missing 'name'
    payload = {"content": config_content}

    mock_cm.create_component_file.side_effect = ValueError(
        "Configuration validation failed: missing field 'name'"
    )
    app.dependency_overrides[get_component_manager] = lambda: mock_cm
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )

    assert response.status_code == 400
    assert "invalid configuration data" in response.json()["detail"].lower()

    expected_payload_to_cm = config_content.copy()
    # The API route for POST /configs/{type}/{filename} when content is a dict
    # will inject the ID from the filename if not present in payload,
    # or warn if different.
    if "name" not in expected_payload_to_cm:  # 'name' is ID field for agents
        expected_payload_to_cm["name"] = component_id

    mock_cm.create_component_file.assert_called_once_with(
        "agents", expected_payload_to_cm, overwrite=False
    )
    app.dependency_overrides = {}


@pytest.mark.parametrize("component_type_api", VALID_API_COMPONENT_TYPES)
def test_create_config_list_payload_invalid_content(
    api_client: TestClient, mock_cm: MagicMock, component_type_api: str
):
    """Tests creating a config file with a list payload containing invalid items."""
    filename = f"invalid_list_{component_type_api}.json"
    # Valid item, then an invalid one (e.g., missing required field for that component type)
    # This requires knowing the ID field for each component type
    from aurite.bin.api.routes.config_routes import API_TO_CM_TYPE_MAP, COMPONENT_META

    cm_internal_type = API_TO_CM_TYPE_MAP[component_type_api]
    _, id_field = COMPONENT_META[cm_internal_type]

    list_content = [
        {
            id_field: "item1",
            "some_field": "valid",
        },  # Assume this would be valid if 'some_field' is expected
        {
            "wrong_id_field": "item2",
            "another_field": "invalid",
        },  # Missing the correct id_field
    ]
    if component_type_api == "clients":  # Example: client_id is required
        list_content = [
            {"client_id": "client1", "server_path": "/path1"},
            {"server_path": "/path2"},  # Missing client_id
        ]
    elif component_type_api == "agents":  # name is required
        list_content = [
            {"name": "agent1", "model": "model1"},
            {"model": "model2"},  # Missing name
        ]
    # Add more specific invalid cases per type if needed

    payload = {"content": list_content}

    # Mock save_components_to_file to simulate Pydantic ValidationError or ValueError
    # The route itself doesn't do per-item validation before calling CM, CM does.
    # So, cm.save_components_to_file should raise the error.
    mock_cm.save_components_to_file.side_effect = ValueError("Invalid item in list")

    app.dependency_overrides[get_component_manager] = lambda: mock_cm
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.post(
        f"/configs/{component_type_api}/{filename}", json=payload, headers=headers
    )

    assert response.status_code == 400  # Bad Request due to CM's validation error
    assert "invalid configuration data" in response.json()["detail"].lower()
    mock_cm.save_components_to_file.assert_called_once_with(
        cm_internal_type, list_content, filename, overwrite=False
    )
    app.dependency_overrides = {}


def test_create_config_unauthorized(api_client: TestClient):
    """Tests creating a config file without API key."""
    payload = {"content": {"key": "value"}}
    response = api_client.post(
        "/configs/agents/new_agent.json", json=payload, headers={}
    )
    assert response.status_code == 401


# --- Tests for PUT /configs/{component_type}/{filename} ---


@pytest.mark.parametrize(
    "invalid_filename, expected_status, expected_detail_part",
    [
        ("test.txt", 400, "must end with .json"),
    ],
)
def test_update_config_invalid_filename_format(  # Renamed
    api_client: TestClient,
    mock_cm: MagicMock,
    invalid_filename: str,
    expected_status: int,
    expected_detail_part: str,
):
    """Tests updating a config file with an invalid filename format for PUT."""
    component_type = "clients"
    payload = {"content": {"key": "value"}}  # Dummy payload
    app.dependency_overrides[get_component_manager] = lambda: mock_cm

    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.put(
        f"/configs/{component_type}/{invalid_filename}", json=payload, headers=headers
    )
    assert response.status_code == expected_status
    assert expected_detail_part in response.json()["detail"].lower()
    mock_cm.save_component_config.assert_not_called()
    mock_cm.save_components_to_file.assert_not_called()
    app.dependency_overrides = {}


def test_update_config_success(api_client: TestClient, mock_cm: MagicMock):
    """Tests successfully updating an existing config file via PUT using mocked CM."""
    component_type = "agents"
    filename = "test_update_agent.json"
    component_id = "test_update_agent"
    updated_content = {
        "name": component_id,  # Ensure ID matches filename-derived ID
        "model": "updated-model",
        "temperature": 0.8,
    }
    payload = {"content": updated_content}

    mock_agent_model = MagicMock(spec=AgentConfig)
    mock_agent_model.model_dump.return_value = updated_content
    # Configure the mock to have the 'name' attribute
    setattr(mock_agent_model, "name", component_id)
    mock_cm.save_component_config.return_value = mock_agent_model

    app.dependency_overrides[get_component_manager] = lambda: mock_cm
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.put(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )

    assert response.status_code == 200
    assert response.json() == updated_content
    mock_cm.save_component_config.assert_called_once_with("agents", updated_content)
    app.dependency_overrides = {}


def test_update_config_list_payload_success(api_client: TestClient, mock_cm: MagicMock):
    """Tests updating a config file with a list payload (overwrite)."""
    component_type = "clients"
    filename = "multiple_clients_to_update.json"
    list_content = [
        {"client_id": "client_updated_1", "server_path": "/updated_path1"},
        {"client_id": "client_updated_2", "server_path": "/updated_path2"},
    ]
    payload = {"content": list_content}

    mock_client_models = [MagicMock(spec=ClientConfig) for _ in list_content]
    for i, mock_model in enumerate(mock_client_models):
        mock_model.model_dump.return_value = list_content[i]

    mock_cm.save_components_to_file.return_value = mock_client_models

    app.dependency_overrides[get_component_manager] = lambda: mock_cm
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.put(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )

    assert response.status_code == 200
    assert response.json() == [model.model_dump() for model in mock_client_models]
    mock_cm.save_components_to_file.assert_called_once_with(
        "clients",
        list_content,
        filename,
        overwrite=True,  # Key difference for PUT
    )
    app.dependency_overrides = {}


def test_update_config_creates_if_not_found(api_client: TestClient, mock_cm: MagicMock):
    """Tests that PUT creates the file if it doesn't exist (upsert behavior)."""
    component_type = "clients"
    filename = "new_client_via_put.json"
    component_id = "new_client_via_put"
    config_content = {"client_id": component_id, "server_path": "/new/path"}
    payload = {"content": config_content}

    mock_client_model = MagicMock(spec=ClientConfig)
    mock_client_model.model_dump.return_value = config_content
    # Configure the mock to have the 'client_id' attribute
    setattr(mock_client_model, "client_id", component_id)
    mock_cm.save_component_config.return_value = mock_client_model

    app.dependency_overrides[get_component_manager] = lambda: mock_cm
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.put(
        f"/configs/{component_type}/{filename}", json=payload, headers=headers
    )

    assert response.status_code == 200
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


def test_update_config_validation_error(api_client: TestClient, mock_cm: MagicMock):
    """Tests updating a config file where CM validation fails."""
    component_type = "clients"
    filename = "test_update_validation_error.json"
    component_id = "test_update_validation_error"
    config_content = {"server_path": "/bad/path"}  # Missing 'client_id'
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
    # API route for PUT /configs/{type}/{filename} when content is dict
    # forces payload ID to match filename-derived ID.
    expected_payload_to_cm["client_id"] = component_id

    mock_cm.save_component_config.assert_called_once_with(
        "clients", expected_payload_to_cm
    )
    app.dependency_overrides = {}


@pytest.mark.parametrize("component_type_api", VALID_API_COMPONENT_TYPES)
def test_update_config_list_payload_invalid_content(
    api_client: TestClient, mock_cm: MagicMock, component_type_api: str
):
    """Tests updating a config file with a list payload containing invalid items."""
    filename = f"invalid_update_list_{component_type_api}.json"
    from aurite.bin.api.routes.config_routes import API_TO_CM_TYPE_MAP, COMPONENT_META

    cm_internal_type = API_TO_CM_TYPE_MAP[component_type_api]
    _, id_field = COMPONENT_META[cm_internal_type]

    list_content = [
        {id_field: "item1_updated", "some_field": "valid"},
        {"non_id_field": "item2_updated_invalid"},
    ]
    # More specific invalid data per type
    if component_type_api == "clients":
        list_content = [
            {"client_id": "client1_upd", "server_path": "/path1_upd"},
            {"server_path": "/path2_upd"},  # Missing client_id
        ]
    elif component_type_api == "agents":
        list_content = [
            {"name": "agent1_upd", "model": "model1_upd"},
            {"model": "model2_upd"},  # Missing name
        ]

    payload = {"content": list_content}
    mock_cm.save_components_to_file.side_effect = ValueError(
        "Invalid item in list for update"
    )

    app.dependency_overrides[get_component_manager] = lambda: mock_cm
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.put(
        f"/configs/{component_type_api}/{filename}", json=payload, headers=headers
    )

    assert response.status_code == 400
    assert "invalid configuration data" in response.json()["detail"].lower()
    mock_cm.save_components_to_file.assert_called_once_with(
        cm_internal_type, list_content, filename, overwrite=True
    )
    app.dependency_overrides = {}


def test_update_config_unauthorized(api_client: TestClient):
    """Tests updating a config file without API key."""
    payload = {"content": {"key": "value"}}
    response = api_client.put(
        "/configs/agents/agent_to_update.json", json=payload, headers={}
    )
    assert response.status_code == 401


# --- Tests for DELETE /configs/{component_type}/{filename} ---


@pytest.mark.parametrize(
    "invalid_filename, expected_status, expected_detail_part",
    [
        ("test.txt", 400, "must end with .json"),
    ],
)
def test_delete_config_invalid_filename_format(  # Renamed
    api_client: TestClient,
    mock_cm: MagicMock,
    invalid_filename: str,
    expected_status: int,
    expected_detail_part: str,
):
    """Tests deleting a config file with an invalid filename format for DELETE."""
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


def test_delete_config_success(api_client: TestClient, mock_cm: MagicMock):
    """Tests successfully deleting an existing config file using mocked CM."""
    component_type = "simple-workflows"
    filename = "test_delete_workflow.json"
    component_id = "test_delete_workflow"

    mock_cm.get_component_config.return_value = MagicMock()
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

    mock_cm.get_component_config.return_value = None
    mock_cm.list_component_files.return_value = []
    app.dependency_overrides[get_component_manager] = lambda: mock_cm
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.delete(
        f"/configs/{component_type}/{filename}", headers=headers
    )

    assert response.status_code == 404
    assert "not found for deletion" in response.json()["detail"].lower()
    mock_cm.get_component_config.assert_called_once_with("agents", component_id)
    mock_cm.list_component_files.assert_called_once_with("agents")
    mock_cm.delete_component_config.assert_not_called()
    app.dependency_overrides = {}


def test_delete_config_internal_error(api_client: TestClient, mock_cm: MagicMock):
    """Tests attempting to delete where CM indicates an internal error."""
    component_type = "clients"
    filename = "delete_fail_client.json"
    component_id = "delete_fail_client"

    mock_cm.get_component_config.return_value = MagicMock()
    mock_cm.delete_component_config.return_value = False
    app.dependency_overrides[get_component_manager] = lambda: mock_cm
    headers = {"X-API-Key": api_client.test_api_key}
    response = api_client.delete(
        f"/configs/{component_type}/{filename}", headers=headers
    )

    assert response.status_code == 500
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


def test_delete_config_unauthorized(api_client: TestClient):
    """Tests deleting a config file without API key."""
    response = api_client.delete("/configs/agents/agent_to_delete.json", headers={})
    assert response.status_code == 401
