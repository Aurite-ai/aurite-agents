"""Unit tests for the FileManager class."""

from pathlib import Path
from unittest.mock import patch

from aurite.lib.config.file_manager import FileManager


class TestFileManager:
    """Test cases for FileManager functionality."""

    def test_init(self):
        """Test FileManager initialization."""
        config_sources = [
            (Path("/workspace/config"), Path("/workspace")),
            (Path("/project/config"), Path("/project")),
        ]

        fm = FileManager(
            config_sources=config_sources,
            project_root=Path("/project"),
            workspace_root=Path("/workspace"),
            project_name="test_project",
            workspace_name="test_workspace",
        )

        assert fm.config_sources == config_sources
        assert fm.project_root == Path("/project")
        assert fm.workspace_root == Path("/workspace")
        assert fm.project_name == "test_project"
        assert fm.workspace_name == "test_workspace"

    def test_validate_path_valid(self):
        """Test path validation with valid paths."""
        config_sources = [
            (Path("/workspace/config"), Path("/workspace")),
        ]
        fm = FileManager(config_sources=config_sources)

        # Path within allowed directory
        valid_path = Path("/workspace/config/agents.json")
        assert fm._validate_path(valid_path) is True

    def test_validate_path_invalid(self):
        """Test path validation with invalid paths."""
        config_sources = [
            (Path("/workspace/config"), Path("/workspace")),
        ]
        fm = FileManager(config_sources=config_sources)

        # Path with parent directory reference
        invalid_path = Path("/workspace/config/../../../etc/passwd")
        assert fm._validate_path(invalid_path) is False

        # Path outside allowed directories
        outside_path = Path("/etc/passwd")
        assert fm._validate_path(outside_path) is False

    def test_detect_file_format(self):
        """Test file format detection."""
        fm = FileManager(config_sources=[])

        assert fm._detect_file_format(Path("config.json")) == "json"
        assert fm._detect_file_format(Path("config.yaml")) == "yaml"
        assert fm._detect_file_format(Path("config.yml")) == "yaml"
        assert fm._detect_file_format(Path("config.txt")) is None

    def test_list_config_sources(self):
        """Test listing configuration sources."""
        config_sources = [
            (Path("/workspace/shared"), Path("/workspace")),
            (Path("/project/config"), Path("/project")),
            (Path.home() / ".aurite", Path.home() / ".aurite"),
        ]

        fm = FileManager(
            config_sources=config_sources,
            project_root=Path("/project"),
            workspace_root=Path("/workspace"),
            project_name="my_project",
            workspace_name="my_workspace",
        )

        sources = fm.list_config_sources()

        assert len(sources) == 3

        # Check workspace source
        assert sources[0]["path"] == str(Path("/workspace/shared"))
        assert sources[0]["context"] == "workspace"
        assert "project_name" not in sources[0]
        assert sources[0]["workspace_name"] == "my_workspace"

        # Check project source
        assert sources[1]["path"] == str(Path("/project/config"))
        assert sources[1]["context"] == "project"
        assert sources[1]["project_name"] == "my_project"
        assert sources[1]["workspace_name"] == "my_workspace"

        # Check user source
        assert sources[2]["path"] == str(Path.home() / ".aurite")
        assert sources[2]["context"] == "user"
        assert "project_name" not in sources[2]
        assert "workspace_name" not in sources[2]

    @patch("pathlib.Path.is_dir")
    @patch("pathlib.Path.rglob")
    def test_list_config_files(self, mock_rglob, mock_is_dir):
        """Test listing configuration files for a specific source."""
        mock_is_dir.return_value = True
        mock_rglob.return_value = [
            Path("/workspace/shared/agents.json"),
            Path("/workspace/shared/llms/models.json"),
        ]

        config_sources = [
            (Path("/workspace/shared"), Path("/workspace")),
        ]

        fm = FileManager(config_sources=config_sources, workspace_root=Path("/workspace"), workspace_name="workspace")

        files = fm.list_config_files("workspace")

        assert len(files) == 2
        assert "agents.json" in files
        assert "llms/models.json" in files
        mock_rglob.assert_called()
