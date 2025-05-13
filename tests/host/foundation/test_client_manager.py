"""
Unit tests for the ClientManager class.
"""

import pytest
from unittest.mock import AsyncMock


# Adjust imports based on your project structure
from src.host.foundation.clients import ClientManager
from src.config.config_models import ClientConfig, GCPSecretConfig
from src.host.foundation.security import SecurityManager
from mcp import ClientSession


# mock_exit_stack fixture is no longer needed as ClientManager.__init__ changed.

@pytest.fixture
def mock_security_manager():
    """Fixture for a mocked SecurityManager."""
    manager = AsyncMock(spec=SecurityManager)
    manager.resolve_gcp_secrets = AsyncMock(return_value={})
    return manager


@pytest.fixture
def sample_client_config():
    """Fixture for a sample ClientConfig."""
    return ClientConfig(
        client_id="test_client_1",
        server_path="/path/to/server.py",
        capabilities=["tools", "prompts"],
        roots=[],
        gcp_secrets=[
            GCPSecretConfig(
                project_id="proj", secret_id="secret", env_var_name="MY_SECRET"
            )
        ],
    )


@pytest.fixture
def sample_client_config_no_secrets():
    """Fixture for a sample ClientConfig without GCP secrets."""
    return ClientConfig(
        client_id="test_client_no_secret",
        server_path="/path/to/another_server.py",
        capabilities=["tools"],
        roots=[],
    )


@pytest.mark.asyncio
async def test_client_manager_initialization():
    """Test ClientManager initializes correctly."""
    manager = ClientManager() # Updated instantiation
    assert manager.active_clients == {}
    # assert manager.client_processes == {} # This attribute was removed


# Tests for start_client, shutdown_client, shutdown_all_clients are removed
# as these methods were removed from ClientManager.
# Testing of manage_client_lifecycle will be primarily through integration tests
# with MCPHost, as it's hard to unit test effectively due to TaskStatus.

# @pytest.mark.asyncio
# @patch("src.host.foundation.clients.stdio_client") # Example of how a test for manage_client_lifecycle might start
# @patch("src.host.foundation.clients.ClientSession", new_callable=AsyncMock)
# async def test_manage_client_lifecycle_success(
#     MockClientSessionCM,
#     mock_stdio_client,
#     mock_security_manager,
#     sample_client_config
# ):
#     """
#     Placeholder for a potential unit test for manage_client_lifecycle.
#     This would be complex to set up correctly with mocks for anyio.CancelScope
#     and anyio.abc.TaskStatus.
#     """
#     manager = ClientManager()
#     mock_cancel_scope = AsyncMock(spec=anyio.CancelScope)
#     mock_task_status = AsyncMock(spec=TaskStatus)
#     mock_task_status.started = MagicMock()

    # # Mock stdio_client context manager
    # mock_stdio_cm_instance = AsyncMock()
    # mock_stdio_cm_instance.__aenter__.return_value = (AsyncMock(), AsyncMock()) # reader, writer
    # mock_stdio_client.return_value = mock_stdio_cm_instance

    # # Mock ClientSession context manager
    # mock_session_instance = AsyncMock(spec=ClientSession)
    # MockClientSessionCM.return_value.__aenter__.return_value = mock_session_instance

    # # This test would need to simulate the anyio.TaskGroup.start() behavior
    # # which is non-trivial.
    # pass


@pytest.mark.asyncio
async def test_get_session(sample_client_config): # Removed mock_exit_stack
    """Test retrieving an active session."""
    manager = ClientManager() # Updated instantiation
    mock_session = AsyncMock(spec=ClientSession)
    manager.active_clients[sample_client_config.client_id] = mock_session

    session = manager.get_session(sample_client_config.client_id)
    assert session == mock_session

    assert manager.get_session("non_existent_client") is None


@pytest.mark.asyncio
async def test_get_all_sessions(sample_client_config): # Removed mock_exit_stack
    """Test retrieving all active sessions."""
    manager = ClientManager() # Updated instantiation
    mock_session_1 = AsyncMock(spec=ClientSession)
    manager.active_clients[sample_client_config.client_id] = mock_session_1

    mock_session_2 = AsyncMock(spec=ClientSession)
    manager.active_clients["client_2"] = mock_session_2

    all_sessions = manager.get_all_sessions()
    assert len(all_sessions) == 2
    assert all_sessions[sample_client_config.client_id] == mock_session_1
    assert all_sessions["client_2"] == mock_session_2

    # Ensure it's a copy
    all_sessions.pop(sample_client_config.client_id)
    assert sample_client_config.client_id in manager.active_clients
