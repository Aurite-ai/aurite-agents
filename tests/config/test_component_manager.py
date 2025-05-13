import pytest
import json
from pathlib import Path

from src.config.component_manager import (
    ComponentManager,
    COMPONENT_TYPES_DIRS,
)
from src.config.config_models import (
    ClientConfig,
    AgentConfig,
)  # Import specific models for type checking
from src.config import PROJECT_ROOT_DIR  # To help with asserting path conversions

# Fixtures from tests.fixtures.config_fixtures
from ..fixtures.config_fixtures import (
    VALID_CLIENT_CONFIG_DATA_MINIMAL,
    VALID_AGENT_CONFIG_DATA,
    INVALID_CLIENT_CONFIG_MISSING_ID,
    INVALID_AGENT_CONFIG_BAD_TEMP_TYPE,
)


# Helper to set up a temporary component directory structure
@pytest.fixture
def temp_config_root(tmp_path: Path) -> Path:
    """Creates a temporary root directory similar to 'config/' for components."""
    config_root = tmp_path / "config"
    config_root.mkdir()
    # Create subdirectories for each component type
    for comp_type_key in COMPONENT_TYPES_DIRS.keys():
        # Use the actual sub-folder name (e.g., "clients", "agents")
        # COMPONENT_TYPES_DIRS maps to PROJECT_ROOT_DIR / "config" / type_dir_name
        # We want to replicate type_dir_name under our temp_config_root
        type_dir_name = COMPONENT_TYPES_DIRS[comp_type_key].name
        (config_root / type_dir_name).mkdir(parents=True, exist_ok=True)
    return config_root


@pytest.fixture
def component_manager_empty(temp_config_root: Path, monkeypatch) -> ComponentManager:
    """
    Provides a ComponentManager instance initialized with temporary, empty component directories.
    It also patches COMPONENT_TYPES_DIRS to point to these temporary directories.
    """
    # Create temporary directories based on the structure in COMPONENT_TYPES_DIRS
    temp_component_dirs = {
        key: temp_config_root / COMPONENT_TYPES_DIRS[key].name
        for key in COMPONENT_TYPES_DIRS
    }

    # Ensure these directories exist
    for path in temp_component_dirs.values():
        path.mkdir(parents=True, exist_ok=True)

    # Monkeypatch the global COMPONENT_TYPES_DIRS to use these temporary paths
    monkeypatch.setattr(
        "src.config.component_manager.COMPONENT_TYPES_DIRS", temp_component_dirs
    )

    # Also, ensure PROJECT_ROOT_DIR is patched if tests rely on it for path resolution
    # relative to the *actual* project structure when dealing with fixture data
    # For ComponentManager itself, it uses the patched COMPONENT_TYPES_DIRS.
    # The main concern for PROJECT_ROOT_DIR is if fixture data contains paths
    # like "fixtures/servers/dummy_server.py" which are relative to the *actual* project root.
    # The config_utils.resolve_path_fields will use the PROJECT_ROOT_DIR from src.config.
    # For tests, this should be fine as long as the fixture paths are valid relative to the real project root.

    cm = ComponentManager()  # Will load from the (empty) temp dirs
    return cm


def test_create_component_success(
    component_manager_empty: ComponentManager, temp_config_root: Path
):
    """Test successful creation of a new component file."""
    cm = component_manager_empty
    client_data = VALID_CLIENT_CONFIG_DATA_MINIMAL.copy()
    component_type = "clients"
    component_id = client_data["client_id"]

    created_model = cm.create_component_file(component_type, client_data)

    assert isinstance(created_model, ClientConfig)
    assert created_model.client_id == component_id
    assert cm.get_client(component_id) == created_model

    # Verify file was created
    expected_file_path = temp_config_root / "clients" / f"{component_id}.json"
    assert expected_file_path.is_file()
    with open(expected_file_path, "r") as f:
        saved_data = json.load(f)
    assert saved_data["client_id"] == component_id
    # Check if server_path was made relative if possible (it should be from fixture)
    # The fixture path is "fixtures/servers/dummy_server.py"
    # Assuming PROJECT_ROOT_DIR is the actual project root for this check.
    expected_relative_server_path = str(
        Path(VALID_CLIENT_CONFIG_DATA_MINIMAL["server_path"])
    )
    assert saved_data["server_path"] == expected_relative_server_path


def test_create_component_already_exists_error(
    component_manager_empty: ComponentManager,
):
    """Test FileExistsError when creating a component that already exists without overwrite."""
    cm = component_manager_empty
    client_data = VALID_CLIENT_CONFIG_DATA_MINIMAL.copy()
    component_type = "clients"

    cm.create_component_file(component_type, client_data)  # Create first time

    with pytest.raises(FileExistsError):
        cm.create_component_file(component_type, client_data, overwrite=False)


def test_create_component_overwrite_success(
    component_manager_empty: ComponentManager, temp_config_root: Path
):
    """Test overwriting an existing component successfully."""
    cm = component_manager_empty
    client_data = VALID_CLIENT_CONFIG_DATA_MINIMAL.copy()
    component_type = "clients"
    component_id = client_data["client_id"]

    cm.create_component_file(component_type, client_data)  # Create first time

    updated_client_data = client_data.copy()
    updated_client_data["timeout"] = 25.0  # Add a new field or change one

    overwritten_model = cm.create_component_file(
        component_type, updated_client_data, overwrite=True
    )

    assert overwritten_model.client_id == component_id
    assert overwritten_model.timeout == 25.0
    assert cm.get_client(component_id).timeout == 25.0

    expected_file_path = temp_config_root / "clients" / f"{component_id}.json"
    with open(expected_file_path, "r") as f:
        saved_data = json.load(f)
    assert saved_data["timeout"] == 25.0


def test_save_component_config_creates_new(
    component_manager_empty: ComponentManager, temp_config_root: Path
):
    """Test save_component_config creating a new component."""
    cm = component_manager_empty
    agent_data = VALID_AGENT_CONFIG_DATA.copy()
    component_type = "agents"
    component_id = agent_data["name"]

    saved_model = cm.save_component_config(component_type, agent_data)

    assert isinstance(saved_model, AgentConfig)
    assert saved_model.name == component_id
    assert cm.get_agent(component_id) == saved_model

    expected_file_path = temp_config_root / "agents" / f"{component_id}.json"
    assert expected_file_path.is_file()
    with open(expected_file_path, "r") as f:
        data_on_disk = json.load(f)
    assert data_on_disk["name"] == component_id
    assert (
        data_on_disk["temperature"] == VALID_AGENT_CONFIG_DATA["temperature"]
    )  # Check a value


def test_save_component_config_updates_existing(
    component_manager_empty: ComponentManager, temp_config_root: Path
):
    """Test save_component_config updating an existing component."""
    cm = component_manager_empty
    client_data = VALID_CLIENT_CONFIG_DATA_MINIMAL.copy()
    component_type = "clients"
    component_id = client_data["client_id"]

    cm.create_component_file(component_type, client_data)  # Create initial

    updated_data = client_data.copy()
    updated_data["capabilities"] = ["new_capability"]

    saved_model = cm.save_component_config(component_type, updated_data)

    assert saved_model.capabilities == ["new_capability"]
    assert cm.get_client(component_id).capabilities == ["new_capability"]

    expected_file_path = temp_config_root / "clients" / f"{component_id}.json"
    with open(expected_file_path, "r") as f:
        data_on_disk = json.load(f)
    assert data_on_disk["capabilities"] == ["new_capability"]


def test_delete_component_config_success(
    component_manager_empty: ComponentManager, temp_config_root: Path
):
    """Test successful deletion of a component."""
    cm = component_manager_empty
    client_data = VALID_CLIENT_CONFIG_DATA_MINIMAL.copy()
    component_type = "clients"
    component_id = client_data["client_id"]

    cm.create_component_file(component_type, client_data)
    assert cm.get_client(component_id) is not None
    expected_file_path = temp_config_root / "clients" / f"{component_id}.json"
    assert expected_file_path.is_file()

    delete_result = cm.delete_component_config(component_type, component_id)
    assert delete_result is True
    assert cm.get_client(component_id) is None
    assert not expected_file_path.exists()


def test_delete_component_config_not_found(component_manager_empty: ComponentManager):
    """Test deleting a component that doesn't exist."""
    cm = component_manager_empty
    delete_result = cm.delete_component_config("clients", "non_existent_client")
    # Depending on implementation, this might be True (if not in memory and file doesn't exist)
    # or False. Current CM returns True if not in memory and file doesn't exist.
    assert delete_result is True


def test_create_component_invalid_data_missing_id(
    component_manager_empty: ComponentManager,
):
    """Test creating a component with data missing the required ID field."""
    cm = component_manager_empty
    # INVALID_CLIENT_CONFIG_MISSING_ID is missing 'client_id'
    with pytest.raises(ValueError, match="Missing or invalid ID field"):
        cm.create_component_file("clients", INVALID_CLIENT_CONFIG_MISSING_ID)


def test_create_component_validation_error_bad_type(
    component_manager_empty: ComponentManager,
):
    """Test creating a component where data causes a Pydantic validation error."""
    cm = component_manager_empty
    # INVALID_AGENT_CONFIG_BAD_TEMP_TYPE has temperature as a string that can't be float
    # This will be caught by Pydantic during model_class(**data_to_validate)
    with pytest.raises(
        ValueError, match="Configuration validation failed"
    ):  # Wraps Pydantic's ValidationError
        cm.create_component_file("agents", INVALID_AGENT_CONFIG_BAD_TEMP_TYPE)


def test_load_all_components_after_creation(temp_config_root: Path, monkeypatch):
    """Test that _load_all_components correctly loads components created on disk."""
    # Setup temp dirs for CM
    temp_component_dirs = {
        key: temp_config_root / COMPONENT_TYPES_DIRS[key].name
        for key in COMPONENT_TYPES_DIRS
    }
    monkeypatch.setattr(
        "src.config.component_manager.COMPONENT_TYPES_DIRS", temp_component_dirs
    )

    # Manually create a component file in the temp location
    client_data = VALID_CLIENT_CONFIG_DATA_MINIMAL.copy()
    client_id = client_data["client_id"]
    client_file = temp_component_dirs["clients"] / f"{client_id}.json"
    with open(client_file, "w") as f:
        json.dump(client_data, f)

    # Now instantiate ComponentManager, which should load it
    cm = ComponentManager()
    loaded_client = cm.get_client(client_id)
    assert loaded_client is not None
    assert loaded_client.client_id == client_id
    # Check path resolution during load
    # The fixture path "fixtures/servers/dummy_server.py" is relative to actual PROJECT_ROOT_DIR
    # The loaded model should have this resolved to an absolute path.
    expected_abs_path = (PROJECT_ROOT_DIR / client_data["server_path"]).resolve()
    assert loaded_client.server_path == expected_abs_path


def test_list_components_and_files(component_manager_empty: ComponentManager):
    """Test listing components and component files."""
    cm = component_manager_empty
    client_data1 = VALID_CLIENT_CONFIG_DATA_MINIMAL.copy()
    client_data2 = VALID_CLIENT_CONFIG_DATA_MINIMAL.copy()
    client_data2["client_id"] = "client_beta"

    agent_data = VALID_AGENT_CONFIG_DATA.copy()

    cm.create_component_file("clients", client_data1)
    cm.create_component_file("clients", client_data2)
    cm.create_component_file("agents", agent_data)

    clients = cm.list_clients()
    assert len(clients) == 2
    assert {c.client_id for c in clients} == {
        client_data1["client_id"],
        client_data2["client_id"],
    }

    agents = cm.list_agents()
    assert len(agents) == 1
    assert agents[0].name == agent_data["name"]

    client_files = cm.list_component_files("clients")
    assert len(client_files) == 2
    assert sorted(client_files) == sorted(
        [f"{client_data1['client_id']}.json", f"{client_data2['client_id']}.json"]
    )

    agent_files = cm.list_component_files("agents")
    assert len(agent_files) == 1
    assert agent_files[0] == f"{agent_data['name']}.json"

    assert cm.list_component_files("non_existent_type") == []
    assert cm.list_llm_configs() == []  # No LLMs created
