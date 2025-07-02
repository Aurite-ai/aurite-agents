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
        (self.project_root / "config" / "agents").mkdir(parents=True, exist_ok=True)
        (self.project_root / "config" / "llms").mkdir(exist_ok=True)

        # Create dummy config files
        # Single agent file
        with open(
            self.project_root / "config" / "agents" / "single_agent.json", "w"
        ) as f:
            json.dump({"name": "single_agent"}, f)
        # List of agents file
        with open(
            self.project_root / "config" / "agents" / "agent_list.json", "w"
        ) as f:
            json.dump([{"name": "agent1"}, {"name": "agent2"}], f)
        # YAML file
        with open(self.project_root / "config" / "llms" / "test_llm.yaml", "w") as f:
            f.write("name: test_llm")

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
        """Test that the component index is built correctly, ignoring packaged defaults."""
        # Prevent loading of packaged defaults by making it seem like the dir doesn't exist
        mock_files.return_value.joinpath.return_value.is_dir.return_value = False

        manager = ConfigManager(project_root=self.project_root)

        # Check agents from both files
        self.assertIn("agents", manager._component_index)
        self.assertEqual(len(manager._component_index["agents"]), 3)
        self.assertIn("single_agent", manager._component_index["agents"])
        self.assertIn("agent1", manager._component_index["agents"])
        self.assertIn("agent2", manager._component_index["agents"])

        # Check llms
        self.assertIn("llms", manager._component_index)
        self.assertIn("test_llm", manager._component_index["llms"])
        # Check the content of the indexed component
        self.assertEqual(
            manager._component_index["llms"]["test_llm"].get("name"),
            "test_llm",
        )

    @patch("importlib.resources.files")
    def test_get_config(self, mock_files):
        """Test retrieving a single component's configuration."""
        mock_files.return_value.joinpath.return_value.is_dir.return_value = False
        manager = ConfigManager(project_root=self.project_root)

        # Test getting agent from list file
        agent1_config = manager.get_config("agents", "agent1")
        self.assertIsNotNone(agent1_config)
        assert agent1_config is not None
        self.assertEqual(agent1_config.get("name"), "agent1")

        # Test getting agent from single object file
        single_agent_config = manager.get_config("agents", "single_agent")
        self.assertIsNotNone(single_agent_config)
        assert single_agent_config is not None
        self.assertEqual(single_agent_config.get("name"), "single_agent")

        llm_config = manager.get_config("llms", "test_llm")
        self.assertIsNotNone(llm_config)
        assert llm_config is not None  # for type checker
        self.assertEqual(llm_config.get("name"), "test_llm")

        non_existent = manager.get_config("agents", "non_existent_agent")
        self.assertIsNone(non_existent)

    @patch("importlib.resources.files")
    def test_list_configs(self, mock_files):
        """Test listing all configurations for a component type."""
        mock_files.return_value.joinpath.return_value.is_dir.return_value = False
        manager = ConfigManager(project_root=self.project_root)

        agents = manager.list_configs("agents")
        self.assertEqual(len(agents), 3)
        agent_names = {a.get("name") for a in agents}
        self.assertEqual(agent_names, {"single_agent", "agent1", "agent2"})

        llms = manager.list_configs("llms")
        self.assertEqual(len(llms), 1)
        self.assertEqual(llms[0].get("name"), "test_llm")

        non_existent = manager.list_configs("non_existent_type")
        self.assertEqual(len(non_existent), 0)


if __name__ == "__main__":
    unittest.main()
