"""
Unit tests for configuration loading utilities in src/config.py,
specifically focusing on load_host_config_from_json.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, mock_open

# Use relative imports assuming tests run from aurite-mcp root
from src.config import load_host_config_from_json
from src.host.models import HostConfig, AgentConfig, ClientConfig


# --- Test Data ---

VALID_CONFIG_DATA_FULL = {
    "name": "TestHostFromJson",
    "clients": [
        {
            "client_id": "client1",
            "server_path": "dummy_server1.py",  # Path relative to project root
            "capabilities": ["tools"],
            "roots": [],
        }
    ],
    "agents": [
        {
            "name": "Agent1",
            "system_prompt": "Prompt for Agent1",
            "client_ids": ["client1"],
            "model": "model-a",
            "temperature": "0.8",  # String to test conversion
            "max_tokens": "2000",  # String to test conversion
            "max_iterations": "8",  # String to test conversion
            "include_history": "false",  # String to test conversion
        },
        {
            "name": "Agent2",
            "client_ids": [
                "client1",
                "client2",
            ],  # client2 doesn't exist in clients, but that's ok for loading
            "model": "model-b",
            # Other params missing, should use defaults or None
        },
    ],
}

VALID_CONFIG_DATA_NO_AGENTS = {
    "name": "TestHostNoAgents",
    "clients": [
        {
            "client_id": "client_no_agent",
            "server_path": "dummy_server_na.py",
            "capabilities": ["prompts"],
            "roots": [],
        }
    ],
    # "agents" key is missing
}

INVALID_CONFIG_DATA_AGENT_MISSING_NAME = {
    "name": "TestHostInvalidAgent",
    "clients": [],
    "agents": [
        {
            # "name": "AgentMissingName", # Name is missing
            "system_prompt": "This agent is invalid",
            "client_ids": [],
        }
    ],
}

INVALID_CONFIG_DATA_AGENT_BAD_TYPE = {
    "name": "TestHostInvalidAgentType",
    "clients": [],
    "agents": [
        {
            "name": "AgentBadTemp",
            "temperature": "not-a-number",  # Invalid type
        }
    ],
}


# --- Test Class ---


@pytest.mark.unit
class TestConfigLoading:
    """Tests for configuration loading functions."""

    @patch("src.config.Path.is_file", return_value=True)  # Mock file existence
    @patch("src.config.Path.exists", return_value=True)  # Mock server_path existence
    @patch(
        "src.config.PROJECT_ROOT_DIR", Path("/fake/project/root")
    )  # Mock project root
    def test_load_valid_config_full(self, mock_exists, mock_is_file):
        """Test loading a valid config JSON with clients and agents."""
        config_path = Path("/fake/path/to/config.json")
        # Use mock_open to simulate reading the JSON data
        m = mock_open(read_data=json.dumps(VALID_CONFIG_DATA_FULL))
        with patch("builtins.open", m):
            host_config, agent_configs_dict = load_host_config_from_json(config_path)

        # Assert HostConfig
        assert isinstance(host_config, HostConfig)
        assert host_config.name == "TestHostFromJson"
        assert len(host_config.clients) == 1
        assert isinstance(host_config.clients[0], ClientConfig)
        assert host_config.clients[0].client_id == "client1"
        # Check resolved path (relative to mocked project root)
        assert host_config.clients[0].server_path == Path(
            "/fake/project/root/dummy_server1.py"
        )

        # Assert AgentConfigs
        assert isinstance(agent_configs_dict, dict)
        assert len(agent_configs_dict) == 2
        assert "Agent1" in agent_configs_dict
        assert "Agent2" in agent_configs_dict

        agent1 = agent_configs_dict["Agent1"]
        assert isinstance(agent1, AgentConfig)
        assert agent1.name == "Agent1"
        assert agent1.system_prompt == "Prompt for Agent1"
        assert agent1.client_ids == ["client1"]
        assert agent1.model == "model-a"
        assert agent1.temperature == 0.8  # Check conversion
        assert agent1.max_tokens == 2000  # Check conversion
        assert agent1.max_iterations == 8  # Check conversion
        assert agent1.include_history is False  # Check conversion

        agent2 = agent_configs_dict["Agent2"]
        assert isinstance(agent2, AgentConfig)
        assert agent2.name == "Agent2"
        assert agent2.client_ids == ["client1", "client2"]
        assert agent2.model == "model-b"
        assert agent2.system_prompt is None  # Check default
        assert agent2.temperature is None  # Check default
        assert agent2.max_tokens is None  # Check default
        assert agent2.max_iterations is None  # Check default
        assert agent2.include_history is None  # Check default

    @patch("src.config.Path.is_file", return_value=True)
    @patch("src.config.Path.exists", return_value=True)
    @patch("src.config.PROJECT_ROOT_DIR", Path("/fake/project/root"))
    def test_load_valid_config_no_agents(self, mock_exists, mock_is_file):
        """Test loading valid config JSON missing the 'agents' key."""
        config_path = Path("/fake/path/to/config_no_agents.json")
        m = mock_open(read_data=json.dumps(VALID_CONFIG_DATA_NO_AGENTS))
        with patch("builtins.open", m):
            host_config, agent_configs_dict = load_host_config_from_json(config_path)

        # Assert HostConfig loaded correctly
        assert isinstance(host_config, HostConfig)
        assert host_config.name == "TestHostNoAgents"
        assert len(host_config.clients) == 1
        assert host_config.clients[0].client_id == "client_no_agent"

        # Assert agent_configs_dict is empty
        assert isinstance(agent_configs_dict, dict)
        assert len(agent_configs_dict) == 0

    @patch("src.config.Path.is_file", return_value=True)
    @patch("src.config.Path.exists", return_value=True)
    @patch("src.config.PROJECT_ROOT_DIR", Path("/fake/project/root"))
    def test_load_invalid_config_agent_missing_name(self, mock_exists, mock_is_file):
        """Test loading config with an agent missing the 'name' field."""
        config_path = Path("/fake/path/to/invalid_config.json")
        m = mock_open(read_data=json.dumps(INVALID_CONFIG_DATA_AGENT_MISSING_NAME))
        with patch("builtins.open", m):
            with pytest.raises(RuntimeError, match="Agent definition missing 'name'"):
                load_host_config_from_json(config_path)

    @patch("src.config.Path.is_file", return_value=True)
    @patch("src.config.Path.exists", return_value=True)
    @patch("src.config.PROJECT_ROOT_DIR", Path("/fake/project/root"))
    def test_load_invalid_config_agent_bad_type(self, mock_exists, mock_is_file):
        """Test loading config with an agent having invalid parameter type."""
        config_path = Path("/fake/path/to/invalid_type_config.json")
        m = mock_open(read_data=json.dumps(INVALID_CONFIG_DATA_AGENT_BAD_TYPE))
        with patch("builtins.open", m):
            with pytest.raises(
                RuntimeError, match="Invalid parameter type for agent 'AgentBadTemp'"
            ):
                load_host_config_from_json(config_path)

    @patch("src.config.Path.is_file", return_value=False)  # Mock file NOT existing
    def test_load_config_file_not_found(self, mock_is_file):
        """Test loading raises FileNotFoundError when config file doesn't exist."""
        config_path = Path("/non/existent/path/config.json")
        with pytest.raises(FileNotFoundError):
            load_host_config_from_json(config_path)

    @patch("src.config.Path.is_file", return_value=True)
    def test_load_config_invalid_json(self, mock_is_file):
        """Test loading raises RuntimeError for invalid JSON."""
        config_path = Path("/fake/path/to/bad_json.json")
        # Simulate reading invalid JSON data
        m = mock_open(read_data="{ invalid json data")
        with patch("builtins.open", m):
            with pytest.raises(RuntimeError, match="Error parsing configuration file"):
                load_host_config_from_json(config_path)

    # TODO: Add test case for missing 'server_path' in client config (should raise KeyError -> RuntimeError)
    # TODO: Add test case for client 'server_path' not existing (should log warning, but load successfully)
