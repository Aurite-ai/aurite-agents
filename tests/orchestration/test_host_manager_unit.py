"""
Unit tests for the HostManager class, focusing on registration logic.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path

# Mark all tests in this module as belonging to the Orchestration layer and unit tests
pytestmark = [pytest.mark.orchestration, pytest.mark.unit, pytest.mark.anyio]

# Imports from the project
from src.host_manager import HostManager
from src.host.host import MCPHost
from src.host.models import (
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
    ClientConfig,
)

# --- Fixtures ---


@pytest.fixture
def mock_host_instance() -> MagicMock:
    """Provides a MagicMock for the MCPHost instance."""
    host = MagicMock(spec=MCPHost)
    # Mock internal structures needed for registration checks
    host._clients = {"existing_client_1": MagicMock(), "existing_client_2": MagicMock()}
    host.register_client = AsyncMock()  # Mock the async method
    return host


@pytest.fixture
def unit_test_host_manager(mock_host_instance: MagicMock) -> HostManager:
    """
    Provides a HostManager instance initialized for unit testing.
    It uses a mock config path and has a mocked MCPHost instance injected.
    """
    # Use a dummy config path for initialization, as loading is bypassed
    dummy_config_path = Path("/fake/unit_test_config.json")
    manager = HostManager(config_path=dummy_config_path)

    # Manually inject the mock host and set initial empty configs
    manager.host = mock_host_instance
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

    # TODO: Implement unit tests for simple workflow registration
    @pytest.mark.skip(reason="Not yet implemented")
    async def test_register_workflow_success(self, unit_test_host_manager: HostManager):
        pass

    @pytest.mark.skip(reason="Not yet implemented")
    async def test_register_workflow_duplicate_name(
        self, unit_test_host_manager: HostManager
    ):
        pass

    @pytest.mark.skip(reason="Not yet implemented")
    async def test_register_workflow_unknown_agent_step(
        self, unit_test_host_manager: HostManager
    ):
        pass

    @pytest.mark.skip(reason="Not yet implemented")
    async def test_register_workflow_no_host_instance(self):
        pass


class TestHostManagerCustomWorkflowRegistration:
    """Tests for HostManager.register_custom_workflow."""

    # TODO: Implement unit tests for custom workflow registration
    @pytest.mark.skip(reason="Not yet implemented")
    async def test_register_custom_workflow_success(
        self, unit_test_host_manager: HostManager
    ):
        pass

    @pytest.mark.skip(reason="Not yet implemented")
    async def test_register_custom_workflow_duplicate_name(
        self, unit_test_host_manager: HostManager
    ):
        pass

    @pytest.mark.skip(reason="Not yet implemented")
    async def test_register_custom_workflow_invalid_path_outside_project(
        self, unit_test_host_manager: HostManager
    ):
        # Needs careful mocking of PROJECT_ROOT_DIR and Path checks
        pass

    @pytest.mark.skip(reason="Not yet implemented")
    async def test_register_custom_workflow_path_does_not_exist(
        self, unit_test_host_manager: HostManager
    ):
        # Needs careful mocking of Path checks
        pass

    @pytest.mark.skip(reason="Not yet implemented")
    async def test_register_custom_workflow_no_host_instance(self):
        pass


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
