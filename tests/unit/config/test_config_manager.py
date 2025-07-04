import pytest
from pathlib import Path
import os
from src.aurite.config.config_manager import ConfigManager


@pytest.fixture
def mock_config_structure(tmp_path: Path):
    """Creates a mock project/workspace structure for testing."""
    # Super-workspace
    super_workspace_path = tmp_path / "super_ws"
    super_workspace_path.mkdir()
    (super_workspace_path / ".aurite").write_text("""
[aurite]
type = "workspace"
projects = ["./ws"]

[env]
SUPER_VAR = "super_value"
DEFAULT_MODEL = "super_model"
""")
    (super_workspace_path / "config").mkdir()
    (super_workspace_path / "config" / "super_agents.json").write_text("""
{"agents": [{"name": "super_agent", "llm_config_id": "super_model"}]}
""")

    # Workspace
    workspace_path = super_workspace_path / "ws"
    workspace_path.mkdir()
    (workspace_path / ".aurite").write_text("""
[aurite]
type = "workspace"
projects = ["./proj_a", "./proj_b"]
include_configs = ["./shared_configs"]

[env]
WS_VAR = "ws_value"
DEFAULT_MODEL = "ws_model"
""")
    (workspace_path / "config").mkdir()
    (workspace_path / "config" / "ws_agents.json").write_text("""
{"agents": [{"name": "ws_agent", "llm_config_id": "ws_model"}]}
""")
    (workspace_path / "shared_configs").mkdir()
    (workspace_path / "shared_configs" / "shared_llms.json").write_text("""
{"llms": [{"name": "shared_llm", "provider": "test"}]}
""")

    # Project A (current project)
    project_a_path = workspace_path / "proj_a"
    project_a_path.mkdir()
    (project_a_path / ".aurite").write_text("""
[aurite]
type = "project"

[env]
PROJ_VAR = "proj_a_value"
DEFAULT_MODEL = "proj_a_model"
""")
    (project_a_path / "config").mkdir()
    (project_a_path / "config" / "proj_a_agents.json").write_text("""
{"agents": [{"name": "proj_a_agent", "llm_config_id": "proj_a_model"}]}
""")

    # Project B (peer project)
    project_b_path = workspace_path / "proj_b"
    project_b_path.mkdir()
    (project_b_path / ".aurite").write_text("""
[aurite]
type = "project"
""")
    (project_b_path / "config").mkdir()
    (project_b_path / "config" / "proj_b_agents.json").write_text("""
{"agents": [{"name": "proj_b_agent", "llm_config_id": "proj_b_model"}]}
""")

    # Change CWD to project A for the test
    os.chdir(project_a_path)
    return project_a_path


def test_config_manager_initialization(mock_config_structure):
    """Tests that the ConfigManager correctly identifies roots and merges settings."""
    cm = ConfigManager()

    # Test root paths
    assert cm.project_root == mock_config_structure
    assert cm.workspace_root == mock_config_structure.parent

    # Test environment variable merging
    assert os.environ["SUPER_VAR"] == "super_value"
    assert os.environ["WS_VAR"] == "ws_value"
    assert os.environ["PROJ_VAR"] == "proj_a_value"
    assert (
        os.environ["DEFAULT_MODEL"] == "proj_a_model"
    )  # Project overrides workspace and super-workspace


def test_config_manager_component_loading_priority(mock_config_structure):
    """Tests that components are loaded with the correct priority."""
    cm = ConfigManager()

    # Test finding agents from different levels
    assert cm.get_config("agents", "proj_a_agent") is not None
    assert cm.get_config("agents", "ws_agent") is not None
    assert cm.get_config("agents", "proj_b_agent") is not None
    assert (
        cm.get_config("agents", "super_agent") is None
    )  # Should not be found due to priority

    # Test finding a shared component
    assert cm.get_config("llms", "shared_llm") is not None


def test_config_manager_list_configs(mock_config_structure):
    """Tests listing all available configs from the current context."""
    cm = ConfigManager()

    all_agents = cm.list_configs("agents")
    agent_names = {agent["name"] for agent in all_agents}

    assert "proj_a_agent" in agent_names
    assert "ws_agent" in agent_names
    assert "proj_b_agent" in agent_names
    assert "super_agent" not in agent_names  # Should not be found
