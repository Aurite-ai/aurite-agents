"""
Unit tests for the Aurite class, focusing on registration logic.
"""

import pytest
import asyncio  # Added import
from unittest.mock import MagicMock, patch
from pathlib import Path

# Mark all tests in this module as belonging to the Orchestration layer and unit tests
pytestmark = [pytest.mark.orchestration, pytest.mark.unit, pytest.mark.anyio]

# Imports from the project
from aurite.host_manager import Aurite

# from aurite.host.host import MCPHost # No longer needed directly, mock provides spec
from aurite.config.config_models import (
    ClientConfig,
)

# Import the shared mock fixture


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
    # to allow item assignment (e.g., active_project.agent_configs[name] = model)
    mock_project_config.agent_configs = {}
    mock_project_config.llm_configs = {}
    mock_project_config.simple_workflow_configs = {}
    mock_project_config.custom_workflow_configs = {}
    mock_project_config.clients = {}
    mock_project_config.name = "Unit Test Project"  # Give it a name for logging

    # Set this mock project config as the active one in the Aurite's ProjectManager
    # This bypasses needing to mock load_project and file system interactions for these unit tests.
    manager.project_manager.active_project_config = mock_project_config

    # The old manager.agent_configs etc. are gone, so tests will need to be updated
    # to assert against manager.project_manager.active_project_config.agent_configs etc.

    return manager


# --- Test Class for Agent Registration ---


class TestAuriteClientRegistration:
    """Tests for Aurite.register_client."""

    # TODO: Implement unit tests for client registration
    @pytest.mark.skip(reason="Not yet implemented")
    async def test_register_client_success(self, unit_test_host_manager: Aurite):
        # This mainly tests delegation to host.register_client
        manager = unit_test_host_manager
        client_config = ClientConfig(
            client_id="NewClient", server_path=Path("/fake/server.py"), roots=[]
        )
        await manager.register_client(client_config)
        manager.host.register_client.assert_awaited_once_with(client_config)

    @pytest.mark.skip(reason="Not yet implemented")
    async def test_register_client_duplicate_id(self, unit_test_host_manager: Aurite):
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
        manager = Aurite(config_path=Path("/fake/path.json"))
        manager.host = None
        client_config = ClientConfig(
            client_id="ClientNoHost", server_path=Path("/fake/server.py"), roots=[]
        )
        with pytest.raises(ValueError, match="Aurite is not initialized."):
            await manager.register_client(client_config)


# --- Test Class for Unload Project ---


class TestAuriteUnloadProject:
    """Tests for Aurite.unload_project."""

    async def test_unload_project_clears_state_and_shuts_down_host(
        self, unit_test_host_manager: Aurite
    ):
        """Verify unload_project calls host shutdown and clears project state."""
        manager = unit_test_host_manager
        mock_host = manager.host  # Get the mock host instance

        # Ensure project_manager.unload_active_project is a mock we can assert on
        # The project_manager itself is real, but its methods can be mocked for interaction testing.
        manager.project_manager.unload_active_project = MagicMock()

        # Call the method under test
        await manager.unload_project()

        # Verify host shutdown was called
        if mock_host:  # mock_host could be None if it was already cleared or not set
            mock_host.shutdown.assert_awaited_once()

        # Verify state is cleared
        assert manager.host is None
        assert manager.execution is None  # Check that facade is cleared
        manager.project_manager.unload_active_project.assert_called_once()  # Check PM interaction

    async def test_unload_project_no_host(self, unit_test_host_manager: Aurite):
        """Verify unload_project works correctly when host is already None."""
        manager = unit_test_host_manager
        manager.host = None  # Ensure host is None initially
        manager.execution = MagicMock()  # Simulate facade was there

        # Ensure project_manager.unload_active_project is a mock
        manager.project_manager.unload_active_project = MagicMock()

        # Call the method under test
        await manager.unload_project()

        # Verify state is cleared (host remains None)
        assert manager.host is None
        assert manager.execution is None  # Check that facade is cleared
        manager.project_manager.unload_active_project.assert_called_once()  # Check PM interaction
        # No error should be raised


# --- Test Class for Change Project ---


class TestAuriteChangeProject:
    """Tests for Aurite.change_project."""

    @patch.object(
        Aurite, "unload_project", new_callable=MagicMock
    )  # Use MagicMock for async def
    @patch.object(
        Aurite, "initialize", new_callable=MagicMock
    )  # Use MagicMock for async def
    async def test_change_project_calls_unload_and_initialize(
        self,
        mock_initialize: MagicMock,
        mock_unload_project: MagicMock,
        unit_test_host_manager: Aurite,
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

    @patch.object(Aurite, "unload_project", new_callable=MagicMock)
    @patch.object(
        Aurite, "initialize", side_effect=RuntimeError("Init failed")
    )  # Simulate init failure
    async def test_change_project_handles_initialization_failure(
        self,
        mock_initialize_fails: MagicMock,
        mock_unload_project_on_fail: MagicMock,
        unit_test_host_manager: Aurite,
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
