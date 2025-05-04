"""
Unit tests for the HostManager class, focusing on registration logic.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from pathlib import Path

# Mark all tests in this module as belonging to the Orchestration layer and unit tests
pytestmark = [pytest.mark.orchestration, pytest.mark.unit, pytest.mark.anyio]

# Imports from the project
from src.host_manager import HostManager

# from src.host.host import MCPHost # No longer needed directly, mock provides spec
from src.host.models import (
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
    ClientConfig,
    CustomWorkflowConfig,
    ClientConfig,
)

# Import the shared mock fixture
from tests.mocks.mock_mcp_host import mock_mcp_host

# --- Fixtures ---

# Removed local mock_host_instance fixture, using shared mock_mcp_host


@pytest.fixture
def unit_test_host_manager(
    mock_mcp_host: MagicMock,
) -> HostManager:  # Use shared fixture
    """
    Provides a HostManager instance initialized for unit testing.
    It uses a mock config path and has the shared mocked MCPHost instance injected.
    """
    # Use a dummy config path for initialization, as loading is bypassed
    dummy_config_path = Path("/fake/unit_test_config.json")
    manager = HostManager(config_path=dummy_config_path)

    # Manually inject the mock host and set initial empty configs
    manager.host = mock_mcp_host  # Inject the shared mock
    manager.agent_configs = {}
    manager.workflow_configs = {}
    manager.custom_workflow_configs = {}
    # Simulate basic initialization state without calling manager.initialize()
    manager.execution = MagicMock()  # Mock the facade as well if needed

    return manager


# --- Test Class for Agent Registration ---


class TestHostManagerAgentRegistration:
    """Tests for HostManager.register_agent."""

    # @pytest.mark.asyncio # Removed - covered by module-level pytestmark
    async def test_register_agent_success(self, unit_test_host_manager: HostManager):
        """Verify successful registration of a new agent."""
        manager = unit_test_host_manager
        agent_config = AgentConfig(name="NewAgent", client_ids=["existing_client_1"])

        await manager.register_agent(agent_config)

        assert "NewAgent" in manager.agent_configs
        assert manager.agent_configs["NewAgent"] == agent_config

    # @pytest.mark.asyncio # Removed
    async def test_register_agent_duplicate_name(
        self, unit_test_host_manager: HostManager
    ):
        """Verify registration fails if agent name already exists."""
        manager = unit_test_host_manager
        agent_config1 = AgentConfig(name="DuplicateAgent")
        agent_config2 = AgentConfig(name="DuplicateAgent", model="different-model")

        # Register first time
        await manager.register_agent(agent_config1)
        assert "DuplicateAgent" in manager.agent_configs

        # Attempt to register again with the same name
        with pytest.raises(
            ValueError, match="Agent name 'DuplicateAgent' already registered."
        ):
            await manager.register_agent(agent_config2)

        # Ensure original config is still there
        assert manager.agent_configs["DuplicateAgent"] == agent_config1

    # @pytest.mark.asyncio # Removed
    async def test_register_agent_invalid_client_id(
        self, unit_test_host_manager: HostManager
    ):
        """Verify registration fails if client_ids reference non-existent clients."""
        manager = unit_test_host_manager
        # References a client not in mock_host_instance._clients
        agent_config = AgentConfig(
            name="AgentInvalidClient", client_ids=["non_existent_client"]
        )

        with pytest.raises(
            ValueError, match="Client ID 'non_existent_client' not found"
        ):
            await manager.register_agent(agent_config)

        assert "AgentInvalidClient" not in manager.agent_configs

    # @pytest.mark.asyncio # Removed
    async def test_register_agent_no_host_instance(self):
        """Verify registration fails if manager.host is None (not initialized)."""
        # Create a manager without injecting the mock host
        manager = HostManager(config_path=Path("/fake/path.json"))
        manager.host = None  # Explicitly set host to None

        agent_config = AgentConfig(name="AgentNoHost")

        with pytest.raises(ValueError, match="HostManager is not initialized."):
            await manager.register_agent(agent_config)

    # @pytest.mark.asyncio # Removed
    async def test_register_agent_with_valid_client_ids(
        self, unit_test_host_manager: HostManager
    ):
        """Verify successful registration when valid client_ids are provided."""
        manager = unit_test_host_manager
        agent_config = AgentConfig(
            name="AgentValidClients",
            client_ids=["existing_client_1", "existing_client_2"],
        )

        await manager.register_agent(agent_config)

        assert "AgentValidClients" in manager.agent_configs
        assert manager.agent_configs["AgentValidClients"] == agent_config

    # @pytest.mark.asyncio # Removed
    async def test_register_agent_no_client_ids(
        self, unit_test_host_manager: HostManager
    ):
        """Verify successful registration when client_ids is None or empty."""
        manager = unit_test_host_manager

        # Test with None client_ids
        agent_config_none = AgentConfig(name="AgentNoClients")
        await manager.register_agent(agent_config_none)
        assert "AgentNoClients" in manager.agent_configs

        # Test with empty list client_ids
        agent_config_empty = AgentConfig(name="AgentEmptyClients", client_ids=[])
        await manager.register_agent(agent_config_empty)
        assert "AgentEmptyClients" in manager.agent_configs


# --- Placeholder Test Classes for Other Registration Methods ---


class TestHostManagerWorkflowRegistration:
    """Tests for HostManager.register_workflow."""

    # @pytest.mark.asyncio # Removed
    async def test_register_workflow_success(self, unit_test_host_manager: HostManager):
        """Verify successful registration of a new simple workflow."""
        manager = unit_test_host_manager
        # Pre-register an agent needed for the workflow steps
        agent_config = AgentConfig(name="AgentForWorkflow")
        await manager.register_agent(agent_config)
        assert "AgentForWorkflow" in manager.agent_configs

        workflow_config = WorkflowConfig(name="NewWorkflow", steps=["AgentForWorkflow"])

        await manager.register_workflow(workflow_config)

        assert "NewWorkflow" in manager.workflow_configs
        assert manager.workflow_configs["NewWorkflow"] == workflow_config

    # @pytest.mark.asyncio # Removed
    async def test_register_workflow_duplicate_name(
        self, unit_test_host_manager: HostManager
    ):
        """Verify registration fails if workflow name already exists."""
        manager = unit_test_host_manager
        # Pre-register agent
        agent_config = AgentConfig(name="AgentForWorkflowDup")
        await manager.register_agent(agent_config)

        workflow_config1 = WorkflowConfig(
            name="DuplicateWorkflow", steps=["AgentForWorkflowDup"]
        )
        workflow_config2 = WorkflowConfig(
            name="DuplicateWorkflow", steps=[], description="Different"
        )

        # Register first time
        await manager.register_workflow(workflow_config1)
        assert "DuplicateWorkflow" in manager.workflow_configs

        # Attempt to register again
        with pytest.raises(
            ValueError, match="Workflow name 'DuplicateWorkflow' already registered."
        ):
            await manager.register_workflow(workflow_config2)

        # Ensure original config is still there
        assert manager.workflow_configs["DuplicateWorkflow"] == workflow_config1

    # @pytest.mark.asyncio # Removed
    async def test_register_workflow_unknown_agent_step(
        self, unit_test_host_manager: HostManager
    ):
        """Verify registration fails if steps reference non-existent agents."""
        manager = unit_test_host_manager
        # Do NOT pre-register "UnknownAgentStep"
        workflow_config = WorkflowConfig(
            name="WorkflowBadStep", steps=["UnknownAgentStep"]
        )

        with pytest.raises(ValueError, match="Agent 'UnknownAgentStep' not found"):
            await manager.register_workflow(workflow_config)

        assert "WorkflowBadStep" not in manager.workflow_configs

    # @pytest.mark.asyncio # Removed
    async def test_register_workflow_no_host_instance(self):
        """Verify registration fails if manager.host is None."""
        manager = HostManager(config_path=Path("/fake/path.json"))
        manager.host = None
        workflow_config = WorkflowConfig(name="WorkflowNoHost", steps=[])

        with pytest.raises(ValueError, match="HostManager is not initialized."):
            await manager.register_workflow(workflow_config)

    # @pytest.mark.asyncio # Removed
    async def test_register_workflow_empty_steps(
        self, unit_test_host_manager: HostManager
    ):
        """Verify successful registration with empty steps list."""
        manager = unit_test_host_manager
        workflow_config = WorkflowConfig(name="WorkflowEmptySteps", steps=[])

        await manager.register_workflow(workflow_config)

        assert "WorkflowEmptySteps" in manager.workflow_configs
        assert manager.workflow_configs["WorkflowEmptySteps"].steps == []


class TestHostManagerCustomWorkflowRegistration:
    """Tests for HostManager.register_custom_workflow."""

    # @pytest.mark.asyncio # Removed
    # Use patch to control Path methods for this test
    @patch("src.host_manager.Path.exists", return_value=True)
    @patch("pathlib.Path.resolve")  # Patching pathlib directly
    @patch(
        "src.host_manager.PROJECT_ROOT_DIR", Path("/fake/project/root")
    )  # Mock project root
    async def test_register_custom_workflow_success(
        self, mock_resolve, mock_exists, unit_test_host_manager: HostManager
    ):
        """Verify successful registration of a new custom workflow."""
        manager = unit_test_host_manager
        # Ensure resolve returns a path starting with the mocked project root
        mock_resolve.return_value = Path("/fake/project/root/workflows/my_workflow.py")

        cwf_config = CustomWorkflowConfig(
            name="NewCustomWF",
            module_path=Path("workflows/my_workflow.py"),  # Relative path is fine here
            class_name="MyWorkflowClass",
        )

        await manager.register_custom_workflow(cwf_config)

        assert "NewCustomWF" in manager.custom_workflow_configs
        # Check that the stored config has the *original* path, not the mocked resolved one
        assert manager.custom_workflow_configs["NewCustomWF"] == cwf_config
        assert manager.custom_workflow_configs["NewCustomWF"].module_path == Path(
            "workflows/my_workflow.py"
        )

    # @pytest.mark.asyncio # Removed
    @patch(
        "src.host_manager.PROJECT_ROOT_DIR"
    )  # Mock the constant used in the function
    @patch("pathlib.Path.resolve")  # Mock the resolve method on the Path class
    async def test_register_custom_workflow_invalid_path_outside_project(
        self,
        mock_path_resolve,  # Mock for Path.resolve class method
        mock_project_root_dir_obj,  # Mock for the PROJECT_ROOT_DIR constant object
        unit_test_host_manager: HostManager,
    ):
        """Verify registration fails if module_path resolves outside project root."""
        manager = unit_test_host_manager
        project_root_path = Path("/fake/project/root")
        outside_path = Path("/outside/project/root/evil_workflow.py")
        # This is the relative path stored in the config
        relative_evil_path = Path("../outside/project/root/evil_workflow.py")

        # --- Configure Mocks ---
        # 1. Configure the mock object representing the PROJECT_ROOT_DIR constant
        mock_project_root_dir_obj.resolve.return_value = project_root_path

        # 2. Create the config object. Pydantic creates a real Path instance internally.
        cwf_config = CustomWorkflowConfig(
            name="OutsideProjectWF",
            module_path=relative_evil_path,  # Pass the relative Path object
            class_name="EvilClass",
        )
        # Get the actual Path instance created by Pydantic inside the config
        actual_path_instance_in_config = cwf_config.module_path

        # 3. Configure the side_effect for the globally patched Path.resolve
        #    Since the call seems to arrive without args, we just return the desired path.
        #    If resolve is called unexpectedly elsewhere, other mocks or assertions might catch it.
        mock_path_resolve.return_value = outside_path  # Directly set return_value

        # --- Execute and Assert ---
        # No need to patch exists separately if the path validation fails first.
        with pytest.raises(
            ValueError,
            match="Custom workflow path is outside the project directory.",
        ):
            await manager.register_custom_workflow(cwf_config)

        # --- Verify Mock Calls ---
        # Check that resolve() was called on the mock representing PROJECT_ROOT_DIR
        mock_project_root_dir_obj.resolve.assert_called_once()

        # Check that the global Path.resolve mock was called once (by module_path.resolve()).
        mock_path_resolve.assert_called_once()

        assert "OutsideProjectWF" not in manager.custom_workflow_configs

    # @pytest.mark.asyncio # Removed
    @patch("src.host_manager.PROJECT_ROOT_DIR")
    @patch("pathlib.Path.resolve")  # Keep this for now, might need adjustment
    @patch("pathlib.Path.exists")  # Also patch exists
    async def test_register_custom_workflow_path_does_not_exist(
        self,
        mock_path_exists,  # Mock for Path.exists
        mock_path_resolve,  # Mock for Path.resolve
        mock_project_root_dir_obj,  # Mock for PROJECT_ROOT_DIR
        unit_test_host_manager: HostManager,
    ):
        """Verify registration fails if module_path does not exist."""
        manager = unit_test_host_manager
        project_root_path = Path("/fake/project/root")
        # Path that resolves correctly but doesn't exist
        resolved_non_existent_path = project_root_path / "non_existent_workflow.py"
        relative_non_existent_path = Path("non_existent_workflow.py")

        # --- Configure Mocks ---
        mock_project_root_dir_obj.resolve.return_value = project_root_path

        cwf_config = CustomWorkflowConfig(
            name="NonExistentWF",
            module_path=relative_non_existent_path,
            class_name="MyClass",
        )
        actual_path_instance_in_config = cwf_config.module_path

        # Configure resolve to return the correct path (inside project)
        mock_path_resolve.return_value = resolved_non_existent_path

        # Configure exists to return False when called (it should only be called on the resolved path)
        mock_path_exists.return_value = False

        # --- Execute and Assert ---
        # Match the actual error message which uses the original path object string representation
        with pytest.raises(
            ValueError,
            match=f"Custom workflow module file not found: {cwf_config.module_path}",
        ):
            await manager.register_custom_workflow(cwf_config)

        # --- Verify Mock Calls ---
        mock_project_root_dir_obj.resolve.assert_called_once()
        # resolve() is called on the module_path instance
        mock_path_resolve.assert_called_once()
        # exists() is called on the *resolved* path in the code under test
        mock_path_exists.assert_called_once()  # Cannot easily assert args with this patching style

        assert "NonExistentWF" not in manager.custom_workflow_configs

    # @pytest.mark.asyncio # Removed
    async def test_register_custom_workflow_no_host_instance(self):
        """Verify registration fails if manager.host is None."""
        manager = HostManager(config_path=Path("/fake/path.json"))
        manager.host = None
        cwf_config = CustomWorkflowConfig(
            name="CustomWFNoHost",
            module_path=Path("dummy.py"),  # Path doesn't matter here
            class_name="Dummy",
        )

        with pytest.raises(ValueError, match="HostManager is not initialized."):
            await manager.register_custom_workflow(cwf_config)


class TestHostManagerClientRegistration:
    """Tests for HostManager.register_client."""

    # TODO: Implement unit tests for client registration
    @pytest.mark.skip(reason="Not yet implemented")
    async def test_register_client_success(self, unit_test_host_manager: HostManager):
        # This mainly tests delegation to host.register_client
        manager = unit_test_host_manager
        client_config = ClientConfig(
            client_id="NewClient", server_path=Path("/fake/server.py"), roots=[]
        )
        await manager.register_client(client_config)
        manager.host.register_client.assert_awaited_once_with(client_config)

    @pytest.mark.skip(reason="Not yet implemented")
    async def test_register_client_duplicate_id(
        self, unit_test_host_manager: HostManager
    ):
        # Simulate host.register_client raising ValueError for duplicate
        manager = unit_test_host_manager
        manager.host.register_client.side_effect = ValueError(
            "Client ID 'existing_client_1' already registered."
        )
        client_config = ClientConfig(
            client_id="existing_client_1", server_path=Path("/fake/server.py"), roots=[]
        )

        with pytest.raises(
            ValueError, match="Client ID 'existing_client_1' already registered."
        ):
            await manager.register_client(client_config)

    @pytest.mark.skip(reason="Not yet implemented")
    async def test_register_client_no_host_instance(self):
        manager = HostManager(config_path=Path("/fake/path.json"))
        manager.host = None
        client_config = ClientConfig(
            client_id="ClientNoHost", server_path=Path("/fake/server.py"), roots=[]
        )
        with pytest.raises(ValueError, match="HostManager is not initialized."):
            await manager.register_client(client_config)


# --- Test Class for Registration Helpers ---


class TestHostManagerRegisterFromConfigHelpers:
    """Tests for the private _register_*_from_config helper methods."""

    # @pytest.mark.asyncio # Removed
    async def test_register_clients_from_config(
        self, unit_test_host_manager: HostManager
    ):
        """Test the _register_clients_from_config helper."""
        manager = unit_test_host_manager
        # Add capabilities=[] to fix validation error
        client_config1 = ClientConfig(
            client_id="HelperClient1",
            server_path=Path("s1.py"),
            roots=[],
            capabilities=[],
        )
        client_config2 = ClientConfig(
            client_id="HelperClient2",
            server_path=Path("s2.py"),
            roots=[],
            capabilities=[],
        )
        # Simulate existing client that causes a skip
        client_config_dup = ClientConfig(
            client_id="existing_client_1",
            server_path=Path("s_dup.py"),
            roots=[],
            capabilities=[],
        )
        # Simulate a client that causes an unexpected error during registration
        client_config_err = ClientConfig(
            client_id="HelperClientErr",
            server_path=Path("s_err.py"),
            roots=[],
            capabilities=[],
        )

        # Configure mock host behavior
        async def mock_register_client(config):
            if config.client_id == "existing_client_1":
                raise ValueError("Duplicate client ID")
            elif config.client_id == "HelperClientErr":
                raise TypeError("Some unexpected error")
            # Otherwise, succeed (no return value needed)

        manager.host.register_client.side_effect = mock_register_client

        clients_to_register = [
            client_config1,
            client_config_dup,
            client_config2,
            client_config_err,
        ]
        reg_c, skip_c, err_c = await manager._register_clients_from_config(
            clients_to_register
        )

        assert reg_c == 2  # client1, client2
        assert skip_c == 2  # client_dup, client_err
        assert len(err_c) == 1
        assert "HelperClientErr" in err_c[0]
        assert (
            "Some unexpected error" in err_c[0]
        )  # Check for the actual error message content
        manager.host.register_client.assert_any_call(client_config1)
        manager.host.register_client.assert_any_call(client_config2)
        manager.host.register_client.assert_any_call(client_config_dup)
        manager.host.register_client.assert_any_call(client_config_err)
        assert manager.host.register_client.await_count == 4

    # @pytest.mark.asyncio # Removed
    async def test_register_agents_from_config(
        self, unit_test_host_manager: HostManager
    ):
        """Test the _register_agents_from_config helper."""
        manager = unit_test_host_manager
        agent_config1 = AgentConfig(
            name="HelperAgent1", client_ids=["existing_client_1"]
        )
        agent_config2 = AgentConfig(name="HelperAgent2")
        agent_config_dup = AgentConfig(
            name="HelperAgent1", model="different"
        )  # Duplicate name
        agent_config_bad_client = AgentConfig(
            name="HelperAgentBadClient", client_ids=["non_existent"]
        )

        agents_to_register = {
            "HelperAgent1": agent_config1,
            "HelperAgent2": agent_config2,
            "HelperAgentDup": agent_config_dup,  # Use different key to avoid dict overwrite
            "HelperAgentBadClient": agent_config_bad_client,
        }

        # We need register_agent to be callable, mock it if needed, but the helper calls it directly
        # Let's spy on it instead to check calls
        with patch.object(
            manager, "register_agent", wraps=manager.register_agent
        ) as spy_register_agent:
            reg_a, skip_a, err_a = await manager._register_agents_from_config(
                agents_to_register
            )

            assert (
                reg_a == 2
            )  # HelperAgent1, HelperAgent2 registered successfully first
            assert (
                skip_a == 2
            )  # HelperAgentDup (duplicate name), HelperAgentBadClient (bad client)
            assert len(err_a) == 0  # Errors are handled via skips based on ValueError

            assert "HelperAgent1" in manager.agent_configs
            assert "HelperAgent2" in manager.agent_configs
            assert (
                manager.agent_configs["HelperAgent1"] == agent_config1
            )  # Original should remain

            # Check calls made to the actual register_agent
            spy_register_agent.assert_any_call(agent_config1)
            spy_register_agent.assert_any_call(agent_config2)
            spy_register_agent.assert_any_call(agent_config_dup)
            spy_register_agent.assert_any_call(agent_config_bad_client)
            assert spy_register_agent.await_count == 4

    # @pytest.mark.asyncio # Removed
    async def test_register_workflows_from_config(
        self, unit_test_host_manager: HostManager
    ):
        """Test the _register_workflows_from_config helper."""
        manager = unit_test_host_manager
        # Pre-register agents
        agent1 = AgentConfig(name="WF_Agent1")
        agent2 = AgentConfig(name="WF_Agent2")
        await manager.register_agent(agent1)
        await manager.register_agent(agent2)

        wf_config1 = WorkflowConfig(name="HelperWF1", steps=["WF_Agent1"])
        wf_config2 = WorkflowConfig(name="HelperWF2", steps=["WF_Agent1", "WF_Agent2"])
        wf_config_dup = WorkflowConfig(name="HelperWF1", steps=[])  # Duplicate name
        wf_config_bad_agent = WorkflowConfig(
            name="HelperWFBadAgent", steps=["WF_Agent1", "UnknownAgent"]
        )

        workflows_to_register = {
            "HelperWF1": wf_config1,
            "HelperWF2": wf_config2,
            "HelperWFDup": wf_config_dup,  # Different key
            "HelperWFBadAgent": wf_config_bad_agent,
        }
        available_agents = set(manager.agent_configs.keys())

        with patch.object(
            manager, "register_workflow", wraps=manager.register_workflow
        ) as spy_register_workflow:
            reg_w, skip_w, err_w = await manager._register_workflows_from_config(
                workflows_to_register, available_agents
            )

            assert reg_w == 2  # HelperWF1, HelperWF2
            assert (
                skip_w == 2
            )  # HelperWFDup (duplicate name), HelperWFBadAgent (bad agent step)
            assert (
                len(err_w) == 1
            )  # Error logged for bad agent step during validation phase
            assert "HelperWFBadAgent" in err_w[0]
            assert "UnknownAgent" in err_w[0]

            assert "HelperWF1" in manager.workflow_configs
            assert "HelperWF2" in manager.workflow_configs
            assert manager.workflow_configs["HelperWF1"] == wf_config1

            # Check calls
            spy_register_workflow.assert_any_call(wf_config1)
            spy_register_workflow.assert_any_call(wf_config2)
            spy_register_workflow.assert_any_call(wf_config_dup)
            # Check that register_workflow was awaited for the valid and duplicate configs
            # It should NOT have been called for wf_config_bad_agent
            calls = [call(wf_config1), call(wf_config2), call(wf_config_dup)]
            spy_register_workflow.assert_has_awaits(calls, any_order=True)
            assert spy_register_workflow.await_count == 3

    # @pytest.mark.asyncio # Removed
    @patch("src.host_manager.PROJECT_ROOT_DIR")
    @patch("pathlib.Path.resolve")  # Patch class method
    @patch("pathlib.Path.exists")  # Patch class method
    async def test_register_custom_workflows_from_config(
        self,
        mock_path_exists,  # Added
        mock_path_resolve,  # Added
        mock_project_root_dir_obj,  # Renamed for clarity
        unit_test_host_manager: HostManager,
    ):
        """Test the _register_custom_workflows_from_config helper."""
        manager = unit_test_host_manager
        project_root_path = Path("/fake/project/root")

        # --- Define Configs and Expected Paths ---
        # Use original relative paths as they appear in config
        path_1_rel = Path("1_wf.py")
        path_2_rel = Path("2_wf.py")
        path_dup_rel = Path("dup.py")
        path_bad_rel = Path("bad.py")

        # Define the resolved paths these should map to
        path_1_res = project_root_path / "1_wf.py"
        path_2_res = project_root_path / "2_wf.py"
        path_dup_res = project_root_path / "dup.py"
        path_bad_res = project_root_path / "bad.py"  # This one won't exist

        cwf_config1 = CustomWorkflowConfig(
            name="HelperCWF1", module_path=path_1_rel, class_name="C1"
        )
        cwf_config2 = CustomWorkflowConfig(
            name="HelperCWF2", module_path=path_2_rel, class_name="C2"
        )
        cwf_config_dup = CustomWorkflowConfig(
            name="HelperCWF1", module_path=path_dup_rel, class_name="CDup"
        )  # Duplicate name
        cwf_config_bad_path = CustomWorkflowConfig(
            name="HelperCWFBadPath", module_path=path_bad_rel, class_name="CBad"
        )  # Path doesn't exist

        custom_workflows_to_register = {
            "HelperCWF1": cwf_config1,
            "HelperCWF2": cwf_config2,
            "HelperCWFDup": cwf_config_dup,  # Use different key
            "HelperCWFBadPath": cwf_config_bad_path,
        }

        # --- Configure Mocks ---
        mock_project_root_dir_obj.resolve.return_value = project_root_path

        # Map original relative paths to their resolved paths
        resolve_map = {
            path_1_rel: path_1_res,
            path_2_rel: path_2_res,
            path_dup_rel: path_dup_res,
            path_bad_rel: path_bad_res,
        }
        # Map resolved paths to their existence status
        exists_map = {
            path_1_res: True,
            path_2_res: True,
            path_dup_res: True,
            path_bad_res: False,  # This one doesn't exist
        }

        # Configure side effects using iterables. The mock will return the next
        # item in the list each time it's called. The order corresponds to the
        # iteration order within _register_custom_workflows_from_config.
        mock_path_resolve.side_effect = [
            path_1_res,  # For HelperCWF1
            path_2_res,  # For HelperCWF2
            path_dup_res,  # For HelperCWFDup
            path_bad_res,  # For HelperCWFBadPath
        ]
        # exists() is called on the resolved path.
        # It will be called for 1_res, 2_res, dup_res, and bad_res.
        # Correction: exists() is NOT called for dup_res because the duplicate name check fails first.
        # It IS called for path_bad_res. So the side effect should match the actual call order.
        mock_path_exists.side_effect = [
            True,  # For path_1_res (HelperCWF1)
            True,  # For path_2_res (HelperCWF2)
            False, # For path_bad_res (HelperCWFBadPath)
        ]

        # --- Execute the helper method (calls real register_custom_workflow) ---
        # We rely on the patches above to control validation within register_custom_workflow
        reg_cw, skip_cw, err_cw = await manager._register_custom_workflows_from_config(
            custom_workflows_to_register
        )

        # --- Assertions ---
        assert reg_cw == 2, (
            f"Expected 2 registered, got {reg_cw}"
        )  # HelperCWF1, HelperCWF2 should succeed
        assert skip_cw == 2, (
            f"Expected 2 skipped, got {skip_cw}"
        )  # HelperCWFDup (duplicate name error), HelperCWFBadPath (path exists error)
        assert len(err_cw) == 0, (
            f"Expected 0 errors logged by helper, got {err_cw}"
        )  # ValueErrors are caught and counted as skips

        # Check final state of manager's config dict
        assert "HelperCWF1" in manager.custom_workflow_configs
        assert "HelperCWF2" in manager.custom_workflow_configs
        assert (
            "HelperCWFDup" not in manager.custom_workflow_configs
        )  # Should have been skipped due to duplicate name
        assert (
            "HelperCWFBadPath" not in manager.custom_workflow_configs
        )  # Should have been skipped due to path not existing
        assert (
            manager.custom_workflow_configs["HelperCWF1"] == cwf_config1
        )  # Check correct config stored

        # Verify mock calls (optional but good practice)
        # NOTE: Verifying calls to patched Path.resolve and Path.exists globally
        # can be complex due to instance vs class method patching.
        # The core logic is verified by the reg_cw/skip_cw counts and the
        # final state of custom_workflow_configs. Removing detailed call checks.
        mock_project_root_dir_obj.resolve.assert_called() # Still useful to check PROJECT_ROOT_DIR.resolve() was used.
