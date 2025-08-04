from pathlib import Path

from src.aurite.lib.config.config_utils import find_anchor_files


def test_find_anchor_files_single_project(tmp_path: Path):
    """Tests finding a single .aurite file in the current directory."""
    (tmp_path / ".aurite").touch()

    anchor_files = find_anchor_files(tmp_path)

    assert len(anchor_files) == 1
    assert anchor_files[0] == tmp_path / ".aurite"


def test_find_anchor_files_nested(tmp_path: Path):
    """Tests finding .aurite files in a nested project/workspace structure."""
    workspace_path = tmp_path / "workspace"
    project_path = workspace_path / "project"
    project_path.mkdir(parents=True)

    (workspace_path / ".aurite").touch()
    (project_path / ".aurite").touch()

    # Search from the project directory
    anchor_files = find_anchor_files(project_path)

    assert len(anchor_files) == 2
    assert anchor_files[0] == project_path / ".aurite"
    assert anchor_files[1] == workspace_path / ".aurite"


def test_find_anchor_files_no_anchors(tmp_path: Path):
    """Tests that no anchor files are found when none exist."""
    anchor_files = find_anchor_files(tmp_path)
    assert len(anchor_files) == 0


def test_find_anchor_files_at_root(tmp_path: Path):
    """Tests finding an anchor file at the root of the temp directory."""
    (tmp_path / ".aurite").touch()
    nested_dir = tmp_path / "a" / "b" / "c"
    nested_dir.mkdir(parents=True)

    anchor_files = find_anchor_files(nested_dir)

    assert len(anchor_files) == 1
    assert anchor_files[0] == tmp_path / ".aurite"


def test_find_anchor_files_three_levels(tmp_path: Path):
    """Tests a three-level hierarchy."""
    super_workspace_path = tmp_path / "super"
    workspace_path = super_workspace_path / "workspace"
    project_path = workspace_path / "project"
    project_path.mkdir(parents=True)

    (super_workspace_path / ".aurite").touch()
    (workspace_path / ".aurite").touch()
    (project_path / ".aurite").touch()

    anchor_files = find_anchor_files(project_path)

    assert len(anchor_files) == 3
    assert anchor_files[0] == project_path / ".aurite"
    assert anchor_files[1] == workspace_path / ".aurite"
    assert anchor_files[2] == super_workspace_path / ".aurite"
