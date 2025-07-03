import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

from aurite.config.config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    """Unit tests for the ConfigManager."""

    def setUp(self):
        """Set up a temporary directory for config files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)

        # Create a dummy project structure
        (self.project_root / "config").mkdir(parents=True, exist_ok=True)

        # Create a monolithic config file
        monolithic_config = {
            "agents": [
                {"name": "agent1"},
                {"name": "agent2"},
            ],
            "llms": [
                {"name": "llm1"},
            ],
        }
        with open(self.project_root / "config" / "project.json", "w") as f:
            json.dump(monolithic_config, f)

    def tearDown(self):
        """Clean up the temporary directory."""
        self.temp_dir.cleanup()

    def test_initialization(self):
        """Test that the ConfigManager can be initialized."""
        manager = ConfigManager()
        self.assertIsInstance(manager, ConfigManager)

    def test_initialize_sources_with_project_root(self):
        """Test that project root is added to sources if it exists."""
        manager = ConfigManager(project_root=self.project_root)
        self.assertIn(self.project_root / "config", manager._config_sources)

    @patch("importlib.resources.files")
    def test_build_component_index(self, mock_files):
        """Test that the component index is built correctly from a monolithic file."""
        mock_files.return_value.joinpath.return_value.is_dir.return_value = False
        manager = ConfigManager(project_root=self.project_root)

        # Check agents
        self.assertIn("agents", manager._component_index)
        self.assertEqual(len(manager._component_index["agents"]), 2)
        self.assertIn("agent1", manager._component_index["agents"])
        self.assertIn("agent2", manager._component_index["agents"])

        # Check llms
        self.assertIn("llms", manager._component_index)
        self.assertEqual(len(manager._component_index["llms"]), 1)
        self.assertIn("llm1", manager._component_index["llms"])
        self.assertEqual(manager._component_index["llms"]["llm1"].get("name"), "llm1")

    @patch("importlib.resources.files")
    def test_get_config(self, mock_files):
        """Test retrieving a single component's configuration."""
        mock_files.return_value.joinpath.return_value.is_dir.return_value = False
        manager = ConfigManager(project_root=self.project_root)

        agent1_config = manager.get_config("agents", "agent1")
        self.assertIsNotNone(agent1_config)
        assert agent1_config is not None
        self.assertEqual(agent1_config.get("name"), "agent1")

        llm1_config = manager.get_config("llms", "llm1")
        self.assertIsNotNone(llm1_config)
        assert llm1_config is not None
        self.assertEqual(llm1_config.get("name"), "llm1")

        non_existent = manager.get_config("agents", "non_existent_agent")
        self.assertIsNone(non_existent)

    @patch("importlib.resources.files")
    def test_list_configs(self, mock_files):
        """Test listing all configurations for a component type."""
        mock_files.return_value.joinpath.return_value.is_dir.return_value = False
        manager = ConfigManager(project_root=self.project_root)

        agents = manager.list_configs("agents")
        self.assertEqual(len(agents), 2)
        agent_names = {a.get("name") for a in agents}
        self.assertEqual(agent_names, {"agent1", "agent2"})

        llms = manager.list_configs("llms")
        self.assertEqual(len(llms), 1)
        self.assertEqual(llms[0].get("name"), "llm1")

        non_existent = manager.list_configs("non_existent_type")
        self.assertEqual(len(non_existent), 0)


if __name__ == "__main__":
    unittest.main()
