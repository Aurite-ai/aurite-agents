"""
Unit tests for configuration loading utilities in src/config.py,
specifically focusing on load_host_config_from_json.
"""

import pytest
import json  # Add json import back
from pathlib import Path
from unittest.mock import patch, mock_open

# Mark all tests in this module as belonging to the Orchestration layer
pytestmark = pytest.mark.orchestration

# Use relative imports assuming tests run from aurite-mcp root
from src.config import load_host_config_from_json
from src.host.models import (
    HostConfig,
    AgentConfig,
    ClientConfig,
    WorkflowConfig,
    CustomWorkflowConfig,  # Import CustomWorkflowConfig
)


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
    "workflows": [  # Add workflow section
        {
            "name": "Workflow1",
            "description": "A test workflow",
            "steps": ["Agent1", "Agent2"],  # References agents defined above
        },
        {"name": "WorkflowEmpty", "steps": []},
    ],
    "custom_workflows": [  # Add custom workflow section
        {
            "name": "CustomWF1",
            "module_path": "custom/wf1.py",  # Relative path
            "class_name": "WorkflowClass1",
            "description": "My first custom workflow",
        },
        {
            "name": "CustomWF2_NoDesc",
            "module_path": "another/path/wf2.py",
            "class_name": "MyWF",
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
    # "workflows" key is also missing
}

VALID_CONFIG_DATA_NO_WORKFLOWS = {  # New test case
    "name": "TestHostNoWorkflows",
    "clients": [],
    "agents": [{"name": "AgentOnly"}],
    # "workflows" key is missing
    # "custom_workflows" key is also missing
}

VALID_CONFIG_DATA_NO_CUSTOM_WORKFLOWS = {  # New test case
    "name": "TestHostNoCustomWorkflows",
    "clients": [],
    "agents": [{"name": "AgentOnly"}],
    "workflows": [{"name": "RegularWF", "steps": ["AgentOnly"]}],
    # "custom_workflows" key is missing
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

INVALID_CONFIG_DATA_WORKFLOW_MISSING_NAME = {  # New test case
    "name": "TestHostInvalidWorkflow",
    "clients": [],
    "agents": [{"name": "AgentWF"}],
    "workflows": [
        {
            # "name": "WorkflowMissingName", # Name is missing
            "steps": ["AgentWF"]
        }
    ],
}

INVALID_CONFIG_DATA_WORKFLOW_UNKNOWN_AGENT = {  # New test case
    "name": "TestHostWorkflowUnknownAgent",
    "clients": [],
    "agents": [{"name": "KnownAgent"}],
    "workflows": [
        {
            "name": "WorkflowBadStep",
            "steps": ["KnownAgent", "UnknownAgent"],  # References an agent not defined
        }
    ],
}

INVALID_CONFIG_DATA_CUSTOM_WORKFLOW_MISSING_NAME = {
    "name": "TestHostInvalidCustomWF_NoName",
    "clients": [],
    "agents": [],
    "custom_workflows": [
        {
            # "name": "MissingName",
            "module_path": "path/to/file.py",
            "class_name": "MyClass",
        }
    ],
}

INVALID_CONFIG_DATA_CUSTOM_WORKFLOW_MISSING_PATH = {
    "name": "TestHostInvalidCustomWF_NoPath",
    "clients": [],
    "agents": [],
    "custom_workflows": [
        {
            "name": "MissingPath",
            # "module_path": "path/to/file.py",
            "class_name": "MyClass",
        }
    ],
}

INVALID_CONFIG_DATA_CUSTOM_WORKFLOW_MISSING_CLASS = {
    "name": "TestHostInvalidCustomWF_NoClass",
    "clients": [],
    "agents": [],
    "custom_workflows": [
        {
            "name": "MissingClass",
            "module_path": "path/to/file.py",
            # "class_name": "MyClass"
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
            # Unpack all four return values now
            (
                host_config,
                agent_configs_dict,
                workflow_configs_dict,
                custom_workflow_configs_dict,
            ) = load_host_config_from_json(config_path)

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

        # Assert WorkflowConfigs
        assert isinstance(workflow_configs_dict, dict)
        assert len(workflow_configs_dict) == 2
        assert "Workflow1" in workflow_configs_dict
        assert "WorkflowEmpty" in workflow_configs_dict

        wf1 = workflow_configs_dict["Workflow1"]
        assert isinstance(wf1, WorkflowConfig)
        assert wf1.name == "Workflow1"
        assert wf1.description == "A test workflow"
        assert wf1.steps == ["Agent1", "Agent2"]

        wf_empty = workflow_configs_dict["WorkflowEmpty"]
        assert isinstance(wf_empty, WorkflowConfig)
        assert wf_empty.name == "WorkflowEmpty"
        assert wf_empty.description is None
        assert wf_empty.steps == []

        # Assert CustomWorkflowConfigs
        assert isinstance(custom_workflow_configs_dict, dict)
        assert len(custom_workflow_configs_dict) == 2
        assert "CustomWF1" in custom_workflow_configs_dict
        assert "CustomWF2_NoDesc" in custom_workflow_configs_dict

        cwf1 = custom_workflow_configs_dict["CustomWF1"]
        assert isinstance(cwf1, CustomWorkflowConfig)
        assert cwf1.name == "CustomWF1"
        assert cwf1.module_path == Path(
            "/fake/project/root/custom/wf1.py"
        )  # Check resolved path
        assert cwf1.class_name == "WorkflowClass1"
        assert cwf1.description == "My first custom workflow"

        cwf2 = custom_workflow_configs_dict["CustomWF2_NoDesc"]
        assert isinstance(cwf2, CustomWorkflowConfig)
        assert cwf2.name == "CustomWF2_NoDesc"
        assert cwf2.module_path == Path(
            "/fake/project/root/another/path/wf2.py"
        )  # Check resolved path
        assert cwf2.class_name == "MyWF"
        assert cwf2.description is None

    @patch("src.config.Path.is_file", return_value=True)
    @patch("src.config.Path.exists", return_value=True)
    @patch("src.config.PROJECT_ROOT_DIR", Path("/fake/project/root"))
    def test_load_valid_config_no_agents(self, mock_exists, mock_is_file):
        """Test loading valid config JSON missing the 'agents' key."""
        config_path = Path("/fake/path/to/config_no_agents.json")
        m = mock_open(read_data=json.dumps(VALID_CONFIG_DATA_NO_AGENTS))
        with patch("builtins.open", m):
            # Unpack all four return values now
            (
                host_config,
                agent_configs_dict,
                workflow_configs_dict,
                custom_workflow_configs_dict,
            ) = load_host_config_from_json(config_path)

        # Assert HostConfig loaded correctly
        assert isinstance(host_config, HostConfig)
        assert host_config.name == "TestHostNoAgents"
        assert len(host_config.clients) == 1
        assert host_config.clients[0].client_id == "client_no_agent"

        # Assert agent_configs_dict is empty
        assert isinstance(agent_configs_dict, dict)
        assert len(agent_configs_dict) == 0
        # Assert workflow_configs_dict is also empty
        assert isinstance(workflow_configs_dict, dict)
        assert len(workflow_configs_dict) == 0
        # Assert custom_workflow_configs_dict is also empty
        assert isinstance(custom_workflow_configs_dict, dict)
        assert len(custom_workflow_configs_dict) == 0

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

    # --- Custom Workflow Loading Tests ---

    @patch("src.config.Path.is_file", return_value=True)
    @patch("src.config.Path.exists", return_value=True)
    @patch("src.config.PROJECT_ROOT_DIR", Path("/fake/project/root"))
    def test_load_valid_config_no_custom_workflows(self, mock_exists, mock_is_file):
        """Test loading valid config JSON missing the 'custom_workflows' key."""
        config_path = Path("/fake/path/to/config_no_custom_workflows.json")
        m = mock_open(read_data=json.dumps(VALID_CONFIG_DATA_NO_CUSTOM_WORKFLOWS))
        with patch("builtins.open", m):
            (
                host_config,
                agent_configs_dict,
                workflow_configs_dict,
                custom_workflow_configs_dict,
            ) = load_host_config_from_json(config_path)

        # Assert HostConfig, AgentConfig, WorkflowConfig loaded correctly
        assert isinstance(host_config, HostConfig)
        assert host_config.name == "TestHostNoCustomWorkflows"
        assert isinstance(agent_configs_dict, dict)
        assert len(agent_configs_dict) == 1
        assert "AgentOnly" in agent_configs_dict
        assert isinstance(workflow_configs_dict, dict)
        assert len(workflow_configs_dict) == 1
        assert "RegularWF" in workflow_configs_dict

        # Assert custom_workflow_configs_dict is empty
        assert isinstance(custom_workflow_configs_dict, dict)
        assert len(custom_workflow_configs_dict) == 0

    @patch("src.config.Path.is_file", return_value=True)
    @patch(
        "src.config.Path.exists", return_value=True
    )  # Mock path existence for this test
    @patch("src.config.PROJECT_ROOT_DIR", Path("/fake/project/root"))
    def test_load_invalid_custom_workflow_missing_name(self, mock_exists, mock_is_file):
        """Test loading config with a custom workflow missing the 'name' field."""
        config_path = Path("/fake/path/to/invalid_custom_wf_name.json")
        m = mock_open(
            read_data=json.dumps(INVALID_CONFIG_DATA_CUSTOM_WORKFLOW_MISSING_NAME)
        )
        with patch("builtins.open", m):
            with pytest.raises(
                RuntimeError, match="Custom workflow definition missing 'name'"
            ):
                load_host_config_from_json(config_path)

    @patch("src.config.Path.is_file", return_value=True)
    @patch("src.config.Path.exists", return_value=True)
    @patch("src.config.PROJECT_ROOT_DIR", Path("/fake/project/root"))
    def test_load_invalid_custom_workflow_missing_path(self, mock_exists, mock_is_file):
        """Test loading config with a custom workflow missing the 'module_path' field."""
        config_path = Path("/fake/path/to/invalid_custom_wf_path.json")
        m = mock_open(
            read_data=json.dumps(INVALID_CONFIG_DATA_CUSTOM_WORKFLOW_MISSING_PATH)
        )
        with patch("builtins.open", m):
            with pytest.raises(RuntimeError, match="missing 'module_path'"):
                load_host_config_from_json(config_path)

    @patch("src.config.Path.is_file", return_value=True)
    @patch("src.config.Path.exists", return_value=True)
    @patch("src.config.PROJECT_ROOT_DIR", Path("/fake/project/root"))
    def test_load_invalid_custom_workflow_missing_class(
        self, mock_exists, mock_is_file
    ):
        """Test loading config with a custom workflow missing the 'class_name' field."""
        config_path = Path("/fake/path/to/invalid_custom_wf_class.json")
        m = mock_open(
            read_data=json.dumps(INVALID_CONFIG_DATA_CUSTOM_WORKFLOW_MISSING_CLASS)
        )
        with patch("builtins.open", m):
            with pytest.raises(RuntimeError, match="missing 'class_name'"):
                load_host_config_from_json(config_path)

    @patch("src.config.Path.is_file", return_value=True)
    @patch("src.config.Path.exists", return_value=False)  # Mock path *not* existing
    @patch("src.config.PROJECT_ROOT_DIR", Path("/fake/project/root"))
    def test_load_custom_workflow_path_does_not_exist(self, mock_exists, mock_is_file):
        """Test loading config logs warning when custom workflow module_path doesn't exist."""
        config_path = Path("/fake/path/to/config.json")
        # Use VALID_CONFIG_DATA_FULL which includes custom workflows
        m = mock_open(read_data=json.dumps(VALID_CONFIG_DATA_FULL))
        # Mock logger to capture warnings
        with patch("builtins.open", m), patch("src.config.logger") as mock_logger:
            (
                host_config,
                agent_configs_dict,
                workflow_configs_dict,
                custom_workflow_configs_dict,
            ) = load_host_config_from_json(config_path)

            # Assert loading still succeeds
            assert "CustomWF1" in custom_workflow_configs_dict
            # Assert warning was logged
            # Assert warning was logged (at least once)
            mock_logger.warning.assert_called()
            # Check that *at least one* of the warning calls contains the expected path info
            warning_calls = mock_logger.warning.call_args_list
            assert any(
                "Custom workflow module path does not exist" in call[0][0]
                for call in warning_calls
            )
            assert any("custom/wf1.py" in call[0][0] for call in warning_calls)
            # Optionally, check for the second warning too
            assert any("another/path/wf2.py" in call[0][0] for call in warning_calls)

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

    # --- Workflow Loading Tests ---

    @patch("src.config.Path.is_file", return_value=True)
    @patch("src.config.Path.exists", return_value=True)
    @patch("src.config.PROJECT_ROOT_DIR", Path("/fake/project/root"))
    def test_load_valid_config_no_workflows(self, mock_exists, mock_is_file):
        """Test loading valid config JSON missing the 'workflows' key."""
        config_path = Path("/fake/path/to/config_no_workflows.json")
        m = mock_open(read_data=json.dumps(VALID_CONFIG_DATA_NO_WORKFLOWS))
        with patch("builtins.open", m):
            (
                host_config,
                agent_configs_dict,
                workflow_configs_dict,
                custom_workflow_configs_dict,
            ) = load_host_config_from_json(config_path)

        # Assert HostConfig and AgentConfig loaded correctly
        assert isinstance(host_config, HostConfig)
        assert host_config.name == "TestHostNoWorkflows"
        assert isinstance(agent_configs_dict, dict)
        assert len(agent_configs_dict) == 1
        assert "AgentOnly" in agent_configs_dict

        # Assert workflow_configs_dict is empty
        assert isinstance(workflow_configs_dict, dict)
        assert len(workflow_configs_dict) == 0
        # Assert custom_workflow_configs_dict is also empty
        assert isinstance(custom_workflow_configs_dict, dict)
        assert len(custom_workflow_configs_dict) == 0

    @patch("src.config.Path.is_file", return_value=True)
    @patch("src.config.Path.exists", return_value=True)
    @patch("src.config.PROJECT_ROOT_DIR", Path("/fake/project/root"))
    def test_load_invalid_config_workflow_missing_name(self, mock_exists, mock_is_file):
        """Test loading config with a workflow missing the 'name' field."""
        config_path = Path("/fake/path/to/invalid_workflow.json")
        m = mock_open(read_data=json.dumps(INVALID_CONFIG_DATA_WORKFLOW_MISSING_NAME))
        with patch("builtins.open", m):
            with pytest.raises(
                RuntimeError, match="Workflow definition missing 'name'"
            ):
                load_host_config_from_json(config_path)

    @patch("src.config.Path.is_file", return_value=True)
    @patch("src.config.Path.exists", return_value=True)
    @patch("src.config.PROJECT_ROOT_DIR", Path("/fake/project/root"))
    def test_load_invalid_config_workflow_unknown_agent(
        self, mock_exists, mock_is_file
    ):
        """
        Test loading config with a workflow referencing an unknown agent.
        load_host_config_from_json should SUCCEED here, as validation happens later.
        """
        config_path = Path("/fake/path/to/unknown_agent_workflow.json")
        m = mock_open(read_data=json.dumps(INVALID_CONFIG_DATA_WORKFLOW_UNKNOWN_AGENT))
        with patch("builtins.open", m):
            # Expect NO error during loading
            try:
                (
                    host_config,
                    agent_configs_dict,
                    workflow_configs_dict,
                    custom_workflow_configs_dict,
                ) = load_host_config_from_json(config_path)
            except Exception as e:
                pytest.fail(
                    f"load_host_config_from_json raised unexpected exception: {e}"
                )

            # Assert that the workflow was loaded, even with the unknown agent step
            assert "WorkflowBadStep" in workflow_configs_dict
            assert isinstance(workflow_configs_dict["WorkflowBadStep"], WorkflowConfig)
            assert workflow_configs_dict["WorkflowBadStep"].steps == [
                "KnownAgent",
                "UnknownAgent",
            ]
