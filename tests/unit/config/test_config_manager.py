import os
from pathlib import Path

import pytest

from src.aurite.config.config_manager import ConfigManager


@pytest.fixture
def mock_config_structure(tmp_path: Path):
    """Creates a mock project/workspace structure for testing."""
    # Workspace
    workspace_path = tmp_path / "ws"
    workspace_path.mkdir()
    (workspace_path / ".aurite").write_text("""
[aurite]
type = "workspace"
projects = ["./proj_a", "./proj_b"]
include_configs = ["./ws_config"]
""")
    (workspace_path / "ws_config").mkdir()
    (workspace_path / "ws_config" / "ws_components.json").write_text("""
[
    {"type": "agent", "name": "ws_agent", "llm_config_id": "ws_model"},
    {"type": "llm", "name": "ws_model", "provider": "test"}
]
""")

    # Project A (current project)
    project_a_path = workspace_path / "proj_a"
    project_a_path.mkdir()
    (project_a_path / ".aurite").write_text("""
[aurite]
type = "project"
include_configs = ["./config"]
""")
    (project_a_path / "config").mkdir()
    (project_a_path / "config" / "proj_a_components.json").write_text("""
[
    {"type": "agent", "name": "proj_a_agent", "llm_config_id": "proj_a_model"},
    {"type": "llm", "name": "proj_a_model", "provider": "test"}
]
""")

    # Project B (peer project)
    project_b_path = workspace_path / "proj_b"
    project_b_path.mkdir()
    (project_b_path / ".aurite").write_text("""
[aurite]
type = "project"
include_configs = ["./config"]
""")
    (project_b_path / "config").mkdir()
    (project_b_path / "config" / "proj_b_components.json").write_text("""
[
    {"type": "agent", "name": "proj_b_agent", "llm_config_id": "proj_b_model"}
]
""")

    # Change CWD to project A for the test
    os.chdir(project_a_path)
    return {
        "workspace": workspace_path,
        "proj_a": project_a_path,
        "proj_b": project_b_path,
    }


def test_config_manager_initialization(mock_config_structure):
    """Tests that the ConfigManager correctly identifies roots."""
    # We start from within proj_a
    cm = ConfigManager(start_dir=mock_config_structure["proj_a"])

    # Test root paths
    assert cm.project_root == mock_config_structure["proj_a"]
    assert cm.workspace_root == mock_config_structure["workspace"]


def test_config_manager_component_loading_priority(mock_config_structure):
    """
    Tests that components are loaded correctly from the project, its peers,
    and the workspace.
    """
    # Initialize from the workspace root to ensure all projects are discovered
    cm = ConfigManager(start_dir=mock_config_structure["workspace"])

    # Test finding agents from different levels
    assert cm.get_config("agent", "proj_a_agent") is not None
    assert cm.get_config("agent", "ws_agent") is not None
    assert cm.get_config("agent", "proj_b_agent") is not None

    # Test finding a model from the workspace
    assert cm.get_config("llm", "ws_model") is not None


def test_config_manager_list_configs(mock_config_structure):
    """Tests listing all available configs from the current context."""
    # Initialize from the workspace root to get all components
    cm = ConfigManager(start_dir=mock_config_structure["workspace"])

    all_agents = cm.list_configs("agent")
    agent_names = {agent["name"] for agent in all_agents}

    assert "proj_a_agent" in agent_names
    assert "ws_agent" in agent_names
    assert "proj_b_agent" in agent_names
