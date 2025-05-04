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
    @patch("src.host_manager.Path.exists", return_value=True)
    @patch("pathlib.Path.resolve")  # Patching pathlib directly
    @patch("src.host_manager.PROJECT_ROOT_DIR", Path("/fake/project/root"))
    async def test_register_custom_workflow_duplicate_name(
        self, mock_resolve, mock_exists, unit_test_host_manager: HostManager
    ):
        """Verify registration fails if custom workflow name already exists."""
        manager = unit_test_host_manager
        mock_resolve.return_value = Path("/fake/project/root/workflows/dup_workflow.py")

        cwf_config1 = CustomWorkflowConfig(
            name="DuplicateCustomWF",
            module_path=Path("workflows/dup_workflow.py"),
            class_name="Class1",
        )
        cwf_config2 = CustomWorkflowConfig(
            name="DuplicateCustomWF",
            module_path=Path("workflows/another.py"),  # Different path
            class_name="Class2",
        )

        # Register first time
        await manager.register_custom_workflow(cwf_config1)
        assert "DuplicateCustomWF" in manager.custom_workflow_configs

        # Attempt to register again
        with pytest.raises(
            ValueError,
            match="Custom Workflow name 'DuplicateCustomWF' already registered.",
        ):
            await manager.register_custom_workflow(cwf_config2)

        # Ensure original config is still there
        assert manager.custom_workflow_configs["DuplicateCustomWF"] == cwf_config1

    # @pytest.mark.asyncio # Removed
    @patch("src.host_manager.PROJECT_ROOT_DIR")  # Mock the PROJECT_ROOT_DIR object
    async def test_register_custom_workflow_invalid_path_outside_project(
        self, mock_project_root_dir, unit_test_host_manager: HostManager
    ):
        """Verify registration fails if module_path resolves outside project root."""
        manager = unit_test_host_manager

        # Configure the mocked PROJECT_ROOT_DIR's resolve() method
        mock_project_root_dir.resolve.return_value = Path("/fake/project/root")

        # Create the path instance for the workflow
        evil_path = Path("../outside/project/root/evil_workflow.py")

        # Patch the resolve() method *specifically on this instance*
        with patch.object(
            evil_path,
            "resolve",
            return_value=Path("/outside/project/root/evil_workflow.py"),
        ) as mock_evil_resolve:
            # Patch exists on the instance as well, although it shouldn't be reached if resolve check fails
            with patch.object(evil_path, "exists", return_value=True):
                cwf_config = CustomWorkflowConfig(
                    name="OutsideProjectWF",
                    module_path=evil_path,
                    class_name="EvilClass",
                )

                with pytest.raises(
                    ValueError,
                    match="Custom workflow path is outside the project directory.",
                ):
                    await manager.register_custom_workflow(cwf_config)

                # Ensure resolve was called on our specific path object
                mock_evil_resolve.assert_called_once()

        assert "OutsideProjectWF" not in manager.custom_workflow_configs

    # @pytest.mark.asyncio # Removed
    @patch("src.host_manager.Path.exists", return_value=False)  # Mock path NOT existing
    @patch("pathlib.Path.resolve")  # Patching pathlib directly
    @patch("src.host_manager.PROJECT_ROOT_DIR", Path("/fake/project/root"))
    async def test_register_custom_workflow_path_does_not_exist(
        self, mock_resolve, mock_exists, unit_test_host_manager: HostManager
    ):
        """Verify registration fails if module_path does not exist."""
        manager = unit_test_host_manager
        # Resolve needs to return something for the exists check to be called on it
        resolved_path = Path("/fake/project/root/non_existent_workflow.py")
        mock_resolve.return_value = resolved_path

        cwf_config = CustomWorkflowConfig(
            name="NonExistentWF",
            module_path=Path("non_existent_workflow.py"),
            class_name="MyClass",
        )

        # Match the actual error message which uses the original path object string representation
        with pytest.raises(
            ValueError,
            match=f"Custom workflow module file not found: {cwf_config.module_path}",
        ):
            await manager.register_custom_workflow(cwf_config)

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
    @patch("src.host_manager.Path.exists")  # Mock exists globally for this test class
    @patch("pathlib.Path.resolve")  # Patching pathlib directly
    @patch("src.host_manager.PROJECT_ROOT_DIR", Path("/fake/project/root"))
    async def test_register_custom_workflows_from_config(
        self, mock_resolve, mock_exists, unit_test_host_manager: HostManager
    ):
        """Test the _register_custom_workflows_from_config helper."""
        manager = unit_test_host_manager

        # Setup mock return values for resolve to simulate paths inside the project root
        # The side_effect function will receive the Path instance as its first argument (self)
        def resolve_side_effect(
            self_path_instance,
        ):  # Correctly defined to accept the instance
            # Construct path relative to mocked root based on original path string
            # Use self_path_instance to access attributes like name
            return Path(f"/fake/project/root/{self_path_instance.name}")

        mock_resolve.side_effect = resolve_side_effect

        cwf_config1 = CustomWorkflowConfig(
            name="HelperCWF1", module_path=Path("1_wf.py"), class_name="C1"
        )
        cwf_config2 = CustomWorkflowConfig(
            name="HelperCWF2", module_path=Path("2_wf.py"), class_name="C2"
        )
        cwf_config_dup = CustomWorkflowConfig(
            name="HelperCWF1", module_path=Path("dup.py"), class_name="CDup"
        )
        cwf_config_bad_path = CustomWorkflowConfig(
            name="HelperCWFBadPath", module_path=Path("bad.py"), class_name="CBad"
        )

        custom_workflows_to_register = {
            "HelperCWF1": cwf_config1,
            "HelperCWF2": cwf_config2,
            "HelperCWFDup": cwf_config_dup,  # Different key
            "HelperCWFBadPath": cwf_config_bad_path,
        }

        # Make the 'bad' path not exist
        def exists_side_effect(*args, **kwargs):
            instance = args[0]  # The Path instance `exists` is called on
            if "bad.py" in str(instance):
                return False
            return True

        mock_exists.side_effect = exists_side_effect

        with patch.object(
            manager, "register_custom_workflow", wraps=manager.register_custom_workflow
        ) as spy_register_cwf:
            (
                reg_cw,
                skip_cw,
                err_cw,
            ) = await manager._register_custom_workflows_from_config(
                custom_workflows_to_register
            )

            assert reg_cw == 2  # HelperCWF1, HelperCWF2
            assert (
                skip_cw == 2
            )  # HelperCWFDup (duplicate name), HelperCWFBadPath (path doesn't exist)
            assert len(err_cw) == 0  # Errors handled via skips

            assert "HelperCWF1" in manager.custom_workflow_configs
            assert "HelperCWF2" in manager.custom_workflow_configs
            assert manager.custom_workflow_configs["HelperCWF1"] == cwf_config1

            # Check calls
            spy_register_cwf.assert_any_call(cwf_config1)
            spy_register_cwf.assert_any_call(cwf_config2)
            spy_register_cwf.assert_any_call(cwf_config_dup)
            spy_register_cwf.assert_any_call(cwf_config_bad_path)
            assert spy_register_cwf.await_count == 4
