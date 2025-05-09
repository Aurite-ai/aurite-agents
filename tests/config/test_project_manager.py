import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock

from src.config.project_manager import ProjectManager
from src.config.component_manager import ComponentManager
from src.config.config_models import (
    ProjectConfig,
    ClientConfig,
    AgentConfig,
    LLMConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
    RootConfig,  # Added RootConfig for ClientConfig instantiation
)
from src.config import PROJECT_ROOT_DIR

# Fixtures from tests.fixtures.config_fixtures
from ..fixtures.config_fixtures import (
    VALID_PROJECT_CONFIG_INLINE_DEFS,
    VALID_PROJECT_CONFIG_WITH_REFS,
    VALID_CLIENT_CONFIG_DATA_MINIMAL,
    VALID_AGENT_CONFIG_DATA,
    VALID_LLM_CONFIG_DATA,
    VALID_SIMPLE_WORKFLOW_CONFIG_DATA,
    VALID_CUSTOM_WORKFLOW_CONFIG_DATA,
)


@pytest.fixture
def mock_component_manager() -> MagicMock:
    """Provides a MagicMock for ComponentManager."""
    mock_cm = MagicMock(spec=ComponentManager)

    client1_data = VALID_CLIENT_CONFIG_DATA_MINIMAL.copy()
    # Ensure 'roots' is present for ClientConfig instantiation
    client1_data.setdefault("roots", [])
    client1_model = ClientConfig(**client1_data)

    agent_data = VALID_AGENT_CONFIG_DATA.copy()
    agent_model = AgentConfig(**agent_data)

    llm_data = VALID_LLM_CONFIG_DATA.copy()
    llm_model = LLMConfig(**llm_data)

    simple_wf_data = VALID_SIMPLE_WORKFLOW_CONFIG_DATA.copy()
    simple_wf_model = WorkflowConfig(**simple_wf_data)

    custom_wf_data = VALID_CUSTOM_WORKFLOW_CONFIG_DATA.copy()
    custom_wf_path_resolved = (
        PROJECT_ROOT_DIR / custom_wf_data["module_path"]
    ).resolve()
    custom_wf_data_resolved = custom_wf_data.copy()
    custom_wf_data_resolved["module_path"] = custom_wf_path_resolved
    custom_wf_model = CustomWorkflowConfig(**custom_wf_data_resolved)

    def get_component_side_effect(component_type, component_id):
        if component_type == "clients":
            if component_id == client1_model.client_id:
                resolved_client_data = client1_data.copy()
                resolved_client_data["server_path"] = (
                    PROJECT_ROOT_DIR / client1_data["server_path"]
                ).resolve()
                resolved_client_data.setdefault(
                    "roots", []
                )  # Ensure roots for instantiation
                return ClientConfig(**resolved_client_data)
            elif component_id == "test_client_full":
                return ClientConfig(
                    client_id="test_client_full",
                    server_path=Path("/dummy/path.py"),
                    capabilities=[],
                    roots=[],
                )
        elif component_type == "agents" and component_id == agent_model.name:
            return agent_model
        elif component_type == "llm_configs" and component_id == llm_model.llm_id:
            return llm_model
        elif (
            component_type == "simple_workflows"
            and component_id == simple_wf_model.name
        ):
            return simple_wf_model
        elif (
            component_type == "custom_workflows"
            and component_id == custom_wf_model.name
        ):
            return custom_wf_model
        return None

    mock_cm.get_component_config.side_effect = get_component_side_effect
    return mock_cm


@pytest.fixture
def project_manager(mock_component_manager: MagicMock) -> ProjectManager:
    """Provides a ProjectManager instance initialized with a mocked ComponentManager."""
    return ProjectManager(component_manager=mock_component_manager)


# --- Tests for the new create_project_file method ---


def test_new_create_project_file_success(
    project_manager: ProjectManager, tmp_path: Path
):
    """Test successful creation of a project file with the new signature."""
    project_file_path = tmp_path / "new_test_project.json"
    project_name = "MyNewProject"
    project_description = "A brand new project."

    client_data_dict = VALID_CLIENT_CONFIG_DATA_MINIMAL.copy()
    client_data_dict["client_id"] = "client_for_new_proj"
    client_data_dict.setdefault("roots", [])  # Ensure roots for ClientConfig
    client_configs_list = [ClientConfig(**client_data_dict)]

    llm_data_dict = VALID_LLM_CONFIG_DATA.copy()
    llm_data_dict["llm_id"] = "llm_for_new_proj"
    llm_configs_list = [LLMConfig(**llm_data_dict)]

    created_project_config = project_manager.create_project_file(
        project_name=project_name,
        project_file_path=project_file_path,
        project_description=project_description,
        client_configs=client_configs_list,
        llm_configs=llm_configs_list,
    )

    assert project_file_path.is_file()
    assert isinstance(created_project_config, ProjectConfig)
    assert created_project_config.name == project_name
    assert created_project_config.description == project_description
    assert len(created_project_config.clients) == 1
    assert "client_for_new_proj" in created_project_config.clients
    # Pydantic converts string path to Path object on model creation
    assert created_project_config.clients["client_for_new_proj"].server_path == Path(
        client_data_dict["server_path"]
    )
    assert len(created_project_config.llm_configs) == 1
    assert "llm_for_new_proj" in created_project_config.llm_configs

    with open(project_file_path, "r") as f:
        data_on_disk = json.load(f)

    assert data_on_disk["name"] == project_name
    assert data_on_disk["description"] == project_description
    assert len(data_on_disk["clients"]) == 1
    assert (
        data_on_disk["clients"]["client_for_new_proj"]["client_id"]
        == "client_for_new_proj"
    )
    assert data_on_disk["clients"]["client_for_new_proj"]["server_path"] == str(
        Path(client_data_dict["server_path"])
    )


def test_new_create_project_file_already_exists_error(
    project_manager: ProjectManager, tmp_path: Path
):
    """Test FileExistsError with the new create_project_file."""
    project_file_path = tmp_path / "new_exists.json"
    project_name = "ExistingProject"

    project_manager.create_project_file(
        project_name=project_name, project_file_path=project_file_path
    )

    with pytest.raises(FileExistsError):
        project_manager.create_project_file(
            project_name=project_name,
            project_file_path=project_file_path,
            overwrite=False,
        )


def test_new_create_project_file_overwrite_success(
    project_manager: ProjectManager, tmp_path: Path
):
    """Test overwriting with the new create_project_file."""
    project_file_path = tmp_path / "new_overwrite.json"

    project_manager.create_project_file(
        project_name="InitialName",
        project_file_path=project_file_path,
        project_description="Initial desc.",
    )

    updated_name = "UpdatedName"
    updated_description = "Updated desc."
    llm_data_dict = VALID_LLM_CONFIG_DATA.copy()
    llm_data_dict["llm_id"] = "llm_for_overwrite"
    llm_configs_list = [LLMConfig(**llm_data_dict)]

    overwritten_config = project_manager.create_project_file(
        project_name=updated_name,
        project_file_path=project_file_path,
        project_description=updated_description,
        llm_configs=llm_configs_list,
        overwrite=True,
    )

    assert overwritten_config.name == updated_name
    assert overwritten_config.description == updated_description
    assert len(overwritten_config.llm_configs) == 1
    assert "llm_for_overwrite" in overwritten_config.llm_configs

    with open(project_file_path, "r") as f:
        data_on_disk = json.load(f)
    assert data_on_disk["name"] == updated_name
    assert data_on_disk["description"] == updated_description
    assert len(data_on_disk["llm_configs"]) == 1


# --- Old tests for create_project_file (now adapted or to be removed) ---
# The old tests are being removed as their functionality is covered by the new tests
# and the method signature has changed significantly.

# def test_create_project_file_success(project_manager: ProjectManager, tmp_path: Path):
#     """Test successful creation of a project file."""
#     project_file_path = tmp_path / "test_project.json"
#     project_name = "MyTestProject"
#     project_description = "A test."
#     # Expected content after ProjectConfig model serializes with defaults for empty lists
#     expected_content_on_disk = {
#         "name": project_name,
#         "description": project_description,
#         "clients": {},
#         "llm_configs": {},
#         "agent_configs": {},
#         "simple_workflow_configs": {},
#         "custom_workflow_configs": {}
#     }

#     created_config = project_manager.create_project_file(
#         project_name=project_name,
#         project_file_path=project_file_path,
#         project_description=project_description
#     )
#     assert isinstance(created_config, ProjectConfig)
#     assert created_config.name == project_name
#     assert project_file_path.is_file()
#     with open(project_file_path, "r") as f:
#         data_on_disk = json.load(f)
#     assert data_on_disk == expected_content_on_disk

# def test_create_project_file_already_exists_error(
#     project_manager: ProjectManager, tmp_path: Path
# ):
#     """Test FileExistsError when creating a project file that already exists."""
#     project_file_path = tmp_path / "test_project_exists.json"
#     project_name = "MyExistingProject"

#     project_manager.create_project_file(project_name=project_name, project_file_path=project_file_path)  # Create first time

#     with pytest.raises(FileExistsError):
#         project_manager.create_project_file(project_name=project_name, project_file_path=project_file_path, overwrite=False)


# def test_create_project_file_overwrite_success(
#     project_manager: ProjectManager, tmp_path: Path
# ):
#     """Test overwriting an existing project file successfully."""
#     project_file_path = tmp_path / "test_project_overwrite.json"
#     initial_name = "InitialProject"
#     initial_desc = "Initial Version"

#     project_manager.create_project_file(project_name=initial_name, project_file_path=project_file_path, project_description=initial_desc)

#     updated_name = "UpdatedProject"
#     updated_desc = "Version 2"
#     updated_config = project_manager.create_project_file(
#         project_name=updated_name, project_file_path=project_file_path, project_description=updated_desc, overwrite=True
#     )
#     assert updated_config.name == updated_name
#     assert updated_config.description == updated_desc
#     with open(project_file_path, "r") as f:
#         data_on_disk = json.load(f)
#     assert data_on_disk["name"] == updated_name
#     assert data_on_disk["description"] == updated_desc


def test_load_project_with_inline_definitions(
    project_manager: ProjectManager, tmp_path: Path
):
    """Test loading a project with inline component definitions."""
    project_data = VALID_PROJECT_CONFIG_INLINE_DEFS.copy()
    project_file = tmp_path / "inline_project.json"
    with open(project_file, "w") as f:
        json.dump(project_data, f)

    project_manager.component_manager.get_component_config.return_value = None

    loaded_project_config = project_manager.load_project(project_file)

    assert isinstance(loaded_project_config, ProjectConfig)
    assert loaded_project_config.name == project_data["name"]
    assert len(loaded_project_config.clients) == len(project_data["clients"])
    assert loaded_project_config.clients["client1"].client_id == "client1"
    inline_client_path_str = project_data["clients"][0]["server_path"]
    expected_resolved_path = (PROJECT_ROOT_DIR / inline_client_path_str).resolve()
    assert (
        loaded_project_config.clients["client1"].server_path == expected_resolved_path
    )
    assert len(loaded_project_config.agent_configs) == len(
        project_data["agent_configs"]
    )
    assert loaded_project_config.agent_configs["Agent1"].name == "Agent1"


def test_load_project_with_references(
    project_manager: ProjectManager, tmp_path: Path, mock_component_manager: MagicMock
):
    """Test loading a project that references component files via ComponentManager."""
    project_data = VALID_PROJECT_CONFIG_WITH_REFS.copy()
    project_file = tmp_path / "ref_project.json"
    with open(project_file, "w") as f:
        json.dump(project_data, f)

    loaded_project_config = project_manager.load_project(project_file)

    assert isinstance(loaded_project_config, ProjectConfig)
    assert loaded_project_config.name == project_data["name"]
    assert len(loaded_project_config.clients) == 2
    assert "test_client_min" in loaded_project_config.clients
    assert (
        loaded_project_config.clients["test_client_min"].client_id == "test_client_min"
    )
    client1_fixture_data = VALID_CLIENT_CONFIG_DATA_MINIMAL
    expected_client1_path = (
        PROJECT_ROOT_DIR / client1_fixture_data["server_path"]
    ).resolve()
    assert (
        loaded_project_config.clients["test_client_min"].server_path
        == expected_client1_path
    )
    assert "test_client_full" in loaded_project_config.clients
    assert len(loaded_project_config.agent_configs) == 1
    assert "test_agent_fixture" in loaded_project_config.agent_configs
    assert (
        loaded_project_config.agent_configs["test_agent_fixture"].name
        == "test_agent_fixture"
    )
    assert len(loaded_project_config.llm_configs) == 1
    assert "test_llm_fixture" in loaded_project_config.llm_configs
    assert len(loaded_project_config.simple_workflow_configs) == 1
    assert (
        "test_simple_workflow_fixture" in loaded_project_config.simple_workflow_configs
    )
    assert len(loaded_project_config.custom_workflow_configs) == 1
    assert (
        "test_custom_workflow_fixture" in loaded_project_config.custom_workflow_configs
    )
    custom_wf_model_in_proj = loaded_project_config.custom_workflow_configs[
        "test_custom_workflow_fixture"
    ]
    expected_custom_wf_path = (
        PROJECT_ROOT_DIR / VALID_CUSTOM_WORKFLOW_CONFIG_DATA["module_path"]
    ).resolve()
    assert custom_wf_model_in_proj.module_path == expected_custom_wf_path


def test_load_project_missing_reference_error(
    project_manager: ProjectManager, tmp_path: Path
):
    """Test error when a referenced component ID is not found by ComponentManager."""
    project_data = {
        "name": "ProjectWithMissingRef",
        "clients": ["non_existent_client_id"],
    }
    project_file = tmp_path / "missing_ref_project.json"
    with open(project_file, "w") as f:
        json.dump(project_data, f)

    project_manager.component_manager.get_component_config.side_effect = (
        lambda type, id: None if id == "non_existent_client_id" else MagicMock()
    )

    with pytest.raises(
        ValueError, match="Client component ID 'non_existent_client_id' not found"
    ):
        project_manager.load_project(project_file)


def test_load_project_inline_def_validation_error(
    project_manager: ProjectManager, tmp_path: Path
):
    """Test error when an inline component definition fails Pydantic validation."""
    project_data = {
        "name": "ProjectWithInvalidInline",
        "llm_configs": [
            {
                "llm_id": "bad_llm",
                "temperature": "not-a-float",
            }
        ],
    }
    project_file = tmp_path / "invalid_inline_project.json"
    with open(project_file, "w") as f:
        json.dump(project_data, f)

    with pytest.raises(ValueError, match="Invalid inline LLMConfig definition"):
        project_manager.load_project(project_file)


def test_load_project_file_not_found_error(
    project_manager: ProjectManager, tmp_path: Path
):
    """Test FileNotFoundError when project file doesn't exist."""
    non_existent_file = tmp_path / "this_file_does_not_exist.json"
    with pytest.raises(FileNotFoundError):
        project_manager.load_project(non_existent_file)


def test_load_project_invalid_json_error(
    project_manager: ProjectManager, tmp_path: Path
):
    """Test RuntimeError when project file contains invalid JSON."""
    invalid_json_file = tmp_path / "invalid.json"
    with open(invalid_json_file, "w") as f:
        f.write("{'name': 'bad json, quotes not double'}")

    with pytest.raises(RuntimeError, match="Error parsing project configuration file"):
        project_manager.load_project(invalid_json_file)
