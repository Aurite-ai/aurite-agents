import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path

# Mark all tests in this module as belonging to the Orchestration layer and unit tests
pytestmark = [pytest.mark.orchestration, pytest.mark.unit, pytest.mark.anyio]

# Imports from the project
from aurite.host_manager import Aurite

# from aurite.host.host import MCPHost # No longer needed directly, mock provides spec
from aurite.config.config_models import (
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
)


@pytest.fixture
def unit_test_host_manager(
    mock_mcp_host: MagicMock,
) -> Aurite:  # Use shared fixture
    """
    Provides a Aurite instance initialized for unit testing.
    It uses a mock config path and has the shared mocked MCPHost instance injected.
    """
    # Use a dummy config path for initialization, as loading is bypassed
    dummy_config_path = Path("/fake/unit_test_config.json")
    manager = Aurite(config_path=dummy_config_path)

    # Manually inject the mock host
    manager.host = mock_mcp_host  # Inject the shared mock
    manager.execution = MagicMock()  # Mock the facade

    # To simulate an initialized state for unit tests of registration methods,
    # we need to ensure project_manager has an active_project_config.
    # Create a mock ProjectConfig.
    # We need to import ProjectConfig from aurite.config.config_models
    from aurite.config.config_models import ProjectConfig

    mock_project_config = MagicMock(spec=ProjectConfig)
    # Initialize the dictionaries within the mock_project_config spec
    # to allow item assignment (e.g., active_project.agents[name] = model)
    mock_project_config.agents = {}
    mock_project_config.llms = {}
    mock_project_config.simple_workflows = {}
    mock_project_config.custom_workflows = {}
    mock_project_config.clients = {}
    mock_project_config.name = "Unit Test Project"  # Give it a name for logging

    # Set this mock project config as the active one in the Aurite's ProjectManager
    # This bypasses needing to mock load_project and file system interactions for these unit tests.
    manager.project_manager.active_project_config = mock_project_config

    # The old manager.agent_configs etc. are gone, so tests will need to be updated
    # to assert against manager.project_manager.active_project_config.agent_configs etc.

    return manager


class TestAuriteAgentRegistration:
    """Tests for Aurite.register_agent."""

    # @pytest.mark.asyncio # Removed - covered by module-level pytestmark
    async def test_register_agent_success(self, unit_test_host_manager: Aurite):
        """Verify successful registration of a new agent."""
        manager = unit_test_host_manager
        agent_config = AgentConfig(name="NewAgent", client_ids=["existing_client_1"])

        # No patching needed, mock host's is_client_registered defaults to True
        await manager.register_agent(agent_config)

        # Verify the check was made using the new method
        manager.host.is_client_registered.assert_called_once_with("existing_client_1")

        assert "NewAgent" in manager.project_manager.active_project_config.agents
        assert (
            manager.project_manager.active_project_config.agents["NewAgent"]
            == agent_config
        )

    # @pytest.mark.asyncio # Removed
    async def test_register_agent_duplicate_name(
        self, unit_test_host_manager: Aurite
    ):
        """Verify registration fails if agent name already exists."""
        manager = unit_test_host_manager
        agent_config1 = AgentConfig(name="DuplicateAgent")
        agent_config2 = AgentConfig(name="DuplicateAgent", model="different-model")

        # Register first time
        await manager.register_agent(agent_config1)
        assert (
            "DuplicateAgent"
            in manager.project_manager.active_project_config.agents
        )
        original_agent_config_in_project = manager.project_manager.active_project_config.agents["DuplicateAgent"]
        assert original_agent_config_in_project.model is None # From agent_config1

        # Register again with the same name but different model
        await manager.register_agent(agent_config2)

        # Ensure the config was updated
        updated_agent_config_in_project = manager.project_manager.active_project_config.agents["DuplicateAgent"]
        assert updated_agent_config_in_project == agent_config2
        assert updated_agent_config_in_project.model == "different-model"

    # @pytest.mark.asyncio # Removed
    async def test_register_agent_invalid_client_id(
        self, unit_test_host_manager: Aurite
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
        assert (
            "AgentInvalidClient"
            not in manager.project_manager.active_project_config.agents
        )

    # @pytest.mark.asyncio # Removed
    async def test_register_agent_no_host_instance(self):
        """Verify registration fails if manager.host is None (not initialized)."""
        # Create a manager without injecting the mock host
        manager = Aurite(config_path=Path("/fake/path.json"))
        manager.host = None  # Explicitly set host to None

        agent_config = AgentConfig(name="AgentNoHost")

        with pytest.raises(ValueError, match="Aurite is not initialized."):
            await manager.register_agent(agent_config)

    # @pytest.mark.asyncio # Removed
    async def test_register_agent_with_valid_client_ids(
        self, unit_test_host_manager: Aurite
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

        assert (
            "AgentValidClients"
            in manager.project_manager.active_project_config.agents
        )
        assert (
            manager.project_manager.active_project_config.agents[
                "AgentValidClients"
            ]
            == agent_config
        )

    # @pytest.mark.asyncio # Removed
    async def test_register_agent_no_client_ids(
        self, unit_test_host_manager: Aurite
    ):
        """Verify successful registration when client_ids is None or empty."""
        manager = unit_test_host_manager

        # Test with None client_ids
        agent_config_none = AgentConfig(name="AgentNoClients")
        await manager.register_agent(agent_config_none)
        assert (
            "AgentNoClients"
            in manager.project_manager.active_project_config.agents
        )

        # Test with empty list client_ids
        agent_config_empty = AgentConfig(name="AgentEmptyClients", client_ids=[])
        await manager.register_agent(agent_config_empty)
        assert (
            "AgentEmptyClients"
            in manager.project_manager.active_project_config.agents
        )


# --- Placeholder Test Classes for Other Registration Methods ---


class TestAuriteWorkflowRegistration:
    """Tests for Aurite.register_workflow."""

    # @pytest.mark.asyncio # Removed
    async def test_register_workflow_success(self, unit_test_host_manager: Aurite):
        """Verify successful registration of a new simple workflow."""
        manager = unit_test_host_manager
        agent_name_for_step = "AgentForWorkflow"
        agent_config = AgentConfig(name=agent_name_for_step)

        # Configure component_manager mock to return the agent_config
        # when get_component_config is called for this agent.
        manager.component_manager.get_component_config = MagicMock(side_effect = lambda type, id: agent_config if type == "agents" and id == agent_name_for_step else None)

        # Now, Aurite.register_agent will be called internally by register_workflow's cascading logic.
        # We don't need to call it explicitly here anymore for the purpose of this test's setup for register_workflow.
        # However, the cascading register_agent will still need the component_manager to "find" the LLMConfig if specified.
        # For simplicity in this unit test, assume AgentForWorkflow does not specify an llm_config_id,
        # or mock get_component_config to also handle LLMConfig lookup if needed.
        # Let's assume no llm_config_id for AgentForWorkflow for this specific test.

        workflow_config = WorkflowConfig(name="NewWorkflow", steps=[agent_name_for_step])
        await manager.register_workflow(workflow_config)

        assert "NewWorkflow" in manager.project_manager.active_project_config.simple_workflows
        assert manager.project_manager.active_project_config.simple_workflows["NewWorkflow"] == workflow_config
        # Also assert that the agent was indeed registered in the active_project by the cascading call
        assert agent_name_for_step in manager.project_manager.active_project_config.agents

    # @pytest.mark.asyncio # Removed
    async def test_register_workflow_duplicate_name(
        self, unit_test_host_manager: Aurite
    ):
        """Verify registration updates if workflow name already exists."""
        manager = unit_test_host_manager
        agent_name_for_step = "AgentForWorkflowDup"
        agent_config = AgentConfig(name=agent_name_for_step)

        # Configure component_manager mock
        manager.component_manager.get_component_config = MagicMock(side_effect = lambda type, id: agent_config if type == "agents" and id == agent_name_for_step else None)

        workflow_config1 = WorkflowConfig(
            name="DuplicateWorkflow", steps=[agent_name_for_step], description="First version"
        )
        workflow_config2 = WorkflowConfig(
            name="DuplicateWorkflow", steps=[agent_name_for_step], description="Second version" # Same steps, different description
        )

        # Register first time
        await manager.register_workflow(workflow_config1)
        assert "DuplicateWorkflow" in manager.project_manager.active_project_config.simple_workflows
        assert manager.project_manager.active_project_config.simple_workflows["DuplicateWorkflow"].description == "First version"

        # Register again with the same name - should update
        await manager.register_workflow(workflow_config2)

        # Ensure the config was updated
        assert manager.project_manager.active_project_config.simple_workflows["DuplicateWorkflow"] == workflow_config2
        assert manager.project_manager.active_project_config.simple_workflows["DuplicateWorkflow"].description == "Second version"

    # @pytest.mark.asyncio # Removed
    async def test_register_workflow_unknown_agent_step(
        self, unit_test_host_manager: Aurite
    ):
        """Verify registration fails if steps reference non-existent agents."""
        manager = unit_test_host_manager
        # Do NOT pre-register "UnknownAgentStep"
        workflow_config = WorkflowConfig(
            name="WorkflowBadStep", steps=["UnknownAgentStep"]
        )

        with pytest.raises(ValueError, match=f"Agent step '{workflow_config.steps[0]}' for workflow '{workflow_config.name}' not found in ComponentManager."):
            await manager.register_workflow(workflow_config)

        assert (
            "WorkflowBadStep"
            not in manager.project_manager.active_project_config.simple_workflows
        )

    # @pytest.mark.asyncio # Removed
    async def test_register_workflow_no_host_instance(self):
        """Verify registration fails if manager.host is None."""
        manager = Aurite(config_path=Path("/fake/path.json"))
        manager.host = None
        workflow_config = WorkflowConfig(name="WorkflowNoHost", steps=[])

        with pytest.raises(ValueError, match="Aurite is not initialized."):
            await manager.register_workflow(workflow_config)

    # @pytest.mark.asyncio # Removed
    async def test_register_workflow_empty_steps(
        self, unit_test_host_manager: Aurite
    ):
        """Verify successful registration with empty steps list."""
        manager = unit_test_host_manager
        workflow_config = WorkflowConfig(name="WorkflowEmptySteps", steps=[])

        await manager.register_workflow(workflow_config)

        assert (
            "WorkflowEmptySteps"
            in manager.project_manager.active_project_config.simple_workflows
        )
        assert (
            manager.project_manager.active_project_config.simple_workflows[
                "WorkflowEmptySteps"
            ].steps
            == []
        )


class TestAuriteCustomWorkflowRegistration:
    """Tests for Aurite.register_custom_workflow."""

    # @pytest.mark.asyncio # Removed
    # Use patch to control Path methods for this test
    @patch("src.host_manager.Path.exists", return_value=True)
    @patch("pathlib.Path.resolve")  # Patching pathlib directly
    @patch(
        "src.host_manager.PROJECT_ROOT_DIR", Path("/fake/project/root")
    )  # Mock project root
    async def test_register_custom_workflow_success(
        self, mock_resolve, mock_exists, unit_test_host_manager: Aurite
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

        assert (
            "NewCustomWF"
            in manager.project_manager.active_project_config.custom_workflows
        )
        # Check that the stored config has the *original* path, not the mocked resolved one
        assert (
            manager.project_manager.active_project_config.custom_workflows[
                "NewCustomWF"
            ]
            == cwf_config
        )
        assert manager.project_manager.active_project_config.custom_workflows[
            "NewCustomWF"
        ].module_path == Path("workflows/my_workflow.py")

    # @pytest.mark.asyncio # Removed
    @patch(
        "src.host_manager.PROJECT_ROOT_DIR"
    )  # Mock the constant used in the function
    @patch("pathlib.Path.resolve")  # Mock the resolve method on the Path class
    async def test_register_custom_workflow_invalid_path_outside_project(
        self,
        mock_path_resolve,  # Mock for Path.resolve class method
        mock_project_root_dir_obj,  # Mock for the PROJECT_ROOT_DIR constant object
        unit_test_host_manager: Aurite,
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

        assert (
            "OutsideProjectWF"
            not in manager.project_manager.active_project_config.custom_workflows
        )

    # @pytest.mark.asyncio # Removed
    @patch("src.host_manager.PROJECT_ROOT_DIR")
    @patch("pathlib.Path.resolve")  # Keep this for now, might need adjustment
    @patch("pathlib.Path.exists")  # Also patch exists
    async def test_register_custom_workflow_path_does_not_exist(
        self,
        mock_path_exists,  # Mock for Path.exists
        mock_path_resolve,  # Mock for Path.resolve
        mock_project_root_dir_obj,  # Mock for PROJECT_ROOT_DIR
        unit_test_host_manager: Aurite,
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

        assert (
            "NonExistentWF"
            not in manager.project_manager.active_project_config.custom_workflows
        )

    # @pytest.mark.asyncio # Removed
    async def test_register_custom_workflow_no_host_instance(self):
        """Verify registration fails if manager.host is None."""
        manager = Aurite(config_path=Path("/fake/path.json"))
        manager.host = None
        cwf_config = CustomWorkflowConfig(
            name="CustomWFNoHost",
            module_path=Path("dummy.py"),  # Path doesn't matter here
            class_name="Dummy",
        )

        with pytest.raises(ValueError, match="Aurite is not initialized."):
            await manager.register_custom_workflow(cwf_config)
