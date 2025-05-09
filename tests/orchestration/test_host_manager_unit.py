"""
Unit tests for the HostManager class, focusing on registration logic.
"""

import pytest
import asyncio  # Added import
from unittest.mock import MagicMock, patch, call
from pathlib import Path

# Mark all tests in this module as belonging to the Orchestration layer and unit tests
pytestmark = [pytest.mark.orchestration, pytest.mark.unit, pytest.mark.anyio]

# Imports from the project
from src.host_manager import HostManager

# from src.host.host import MCPHost # No longer needed directly, mock provides spec
from src.config.config_models import (
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
    ClientConfig,
)

# Import the shared mock fixture

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

        # No patching needed, mock host's is_client_registered defaults to True
        await manager.register_agent(agent_config)

        # Verify the check was made using the new method
        manager.host.is_client_registered.assert_called_once_with("existing_client_1")

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

        # Configure the mock host to indicate the client is not registered
        manager.host.is_client_registered.return_value = False

        with pytest.raises(
            ValueError, match="Client ID 'non_existent_client' not found"
        ):
            await manager.register_agent(agent_config)

        # Verify the check was made
        manager.host.is_client_registered.assert_called_once_with("non_existent_client")
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

        # No patching needed, mock host's is_client_registered defaults to True
        await manager.register_agent(agent_config)

        # Verify the check was made using the new method for both clients
        manager.host.is_client_registered.assert_has_calls(
            [
                call("existing_client_1"),
                call("existing_client_2"),
            ],
            any_order=True,
        )

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


# --- Test Class for Unload Project ---


class TestHostManagerUnloadProject:
    """Tests for HostManager.unload_project."""

    async def test_unload_project_clears_state_and_shuts_down_host(
        self, unit_test_host_manager: HostManager
    ):
        """Verify unload_project calls host shutdown and clears project state."""
        manager = unit_test_host_manager
        mock_host = manager.host  # Get the mock host instance

        # Pre-populate some state to verify clearing
        manager.current_project = MagicMock()  # Simulate a loaded project
        manager.agent_configs = {"agent1": MagicMock()}
        manager.llm_configs = {"llm1": MagicMock()}
        manager.workflow_configs = {"wf1": MagicMock()}
        manager.custom_workflow_configs = {"cwf1": MagicMock()}

        # Call the method under test
        await manager.unload_project()

        # Verify host shutdown was called
        mock_host.shutdown.assert_awaited_once()

        # Verify state is cleared
        assert manager.host is None
        assert manager.current_project is None
        assert manager.agent_configs == {}
        assert manager.llm_configs == {}
        assert manager.workflow_configs == {}
        assert manager.custom_workflow_configs == {}

    async def test_unload_project_no_host(self, unit_test_host_manager: HostManager):
        """Verify unload_project works correctly when host is already None."""
        manager = unit_test_host_manager
        manager.host = None  # Ensure host is None initially
        # Pre-populate some state
        manager.current_project = MagicMock()
        manager.agent_configs = {"agent1": MagicMock()}

        # Call the method under test
        await manager.unload_project()

        # Verify state is cleared (host remains None)
        assert manager.host is None
        assert manager.current_project is None
        assert manager.agent_configs == {}
        # No error should be raised


# --- Test Class for Change Project ---


class TestHostManagerChangeProject:
    """Tests for HostManager.change_project."""

    @patch.object(
        HostManager, "unload_project", new_callable=MagicMock
    )  # Use MagicMock for async def
    @patch.object(
        HostManager, "initialize", new_callable=MagicMock
    )  # Use MagicMock for async def
    async def test_change_project_calls_unload_and_initialize(
        self,
        mock_initialize: MagicMock,
        mock_unload_project: MagicMock,
        unit_test_host_manager: HostManager,
    ):
        """Verify change_project calls unload_project then initialize, and updates config_path."""
        manager = unit_test_host_manager
        original_config_path = manager.config_path
        new_config_path = Path("/new/fake/project.json")

        # Configure async mocks
        mock_unload_project.return_value = asyncio.Future()
        mock_unload_project.return_value.set_result(None)
        mock_initialize.return_value = asyncio.Future()
        mock_initialize.return_value.set_result(None)

        await manager.change_project(new_config_path)

        mock_unload_project.assert_called_once()  # Corrected from assert_awaited_once
        assert (
            manager.config_path == new_config_path.resolve()
        )  # change_project resolves the path
        mock_initialize.assert_called_once()  # Corrected from assert_awaited_once

        # Verify the order of calls if possible (might need more complex mocking or call list inspection)
        # For now, individual calls are verified.

    @patch.object(HostManager, "unload_project", new_callable=MagicMock)
    @patch.object(
        HostManager, "initialize", side_effect=RuntimeError("Init failed")
    )  # Simulate init failure
    async def test_change_project_handles_initialization_failure(
        self,
        mock_initialize_fails: MagicMock,
        mock_unload_project_on_fail: MagicMock,
        unit_test_host_manager: HostManager,
    ):
        """Verify change_project calls unload_project again if initialize fails."""
        manager = unit_test_host_manager
        new_config_path = Path("/another/project.json")

        # Configure async mocks
        mock_unload_project_on_fail.return_value = asyncio.Future()
        mock_unload_project_on_fail.return_value.set_result(None)
        # mock_initialize_fails is already configured with side_effect

        with pytest.raises(RuntimeError, match="Init failed"):
            await manager.change_project(new_config_path)

        # unload_project should be called twice: once at the start, once after init failure
        assert mock_unload_project_on_fail.call_count == 2  # Corrected from await_count
        mock_initialize_fails.assert_called_once()  # Corrected from assert_awaited_once
        assert manager.config_path == new_config_path.resolve()
