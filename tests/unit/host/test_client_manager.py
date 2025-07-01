"""
Unit tests for the ClientManager class.
"""

import pytest
from unittest.mock import Mock
import anyio

from src.aurite.host.foundation.clients import ClientManager

# Mark all tests in this file as 'unit' and 'host'
pytestmark = [pytest.mark.unit, pytest.mark.host]


def test_client_manager_initialization():
    """
    Test that the ClientManager can be initialized successfully.
    """
    # 1. Arrange & 2. Act
    client_manager = ClientManager()

    # 3. Assert
    assert isinstance(client_manager, ClientManager)
    assert client_manager.active_clients == {}


def test_get_session():
    """
    Test retrieving a session for a specific client ID.
    """
    # 1. Arrange
    client_manager = ClientManager()
    mock_session = Mock()
    client_id = "test_client"
    client_manager.active_clients[client_id] = mock_session

    # 2. Act
    session = client_manager.get_session(client_id)

    # 3. Assert
    assert session == mock_session


def test_get_all_sessions():
    """
    Test retrieving all active sessions.
    """
    # 1. Arrange
    client_manager = ClientManager()
    mock_session1 = Mock()
    mock_session2 = Mock()
    client_manager.active_clients["client1"] = mock_session1
    client_manager.active_clients["client2"] = mock_session2

    # 2. Act
    all_sessions = client_manager.get_all_sessions()

    # 3. Assert
    assert all_sessions == {"client1": mock_session1, "client2": mock_session2}
    # Ensure it returns a copy
    assert all_sessions is not client_manager.active_clients


@pytest.mark.anyio
async def test_manage_client_lifecycle_happy_path(mocker):
    """
    Tests the 'happy path' of the client lifecycle:
    - The task starts successfully.
    - It acquires the transport and session contexts.
    - It reports the session back via task_status.
    - It adds the session to active_clients.
    - It waits until cancelled.
    - On cancellation, it cleans up by removing the client.
    """
    # 1. Arrange
    client_manager = ClientManager()
    client_id = "test_lifecycle_client"

    # Mock the session object that will be returned by the ClientSession context manager
    mock_session_instance = mocker.AsyncMock()

    # Mock the ClientSession class to behave as an async context manager
    mock_client_session_class = mocker.patch(
        "src.aurite.host.foundation.clients.ClientSession"
    )
    mock_client_session_class.return_value.__aenter__.return_value = (
        mock_session_instance
    )

    # Mock the transport context manager
    mock_reader, mock_writer = mocker.AsyncMock(), mocker.AsyncMock()
    mock_transport_context = mocker.AsyncMock()
    mock_transport_context.__aenter__.return_value = (mock_reader, mock_writer)

    # 2. Act & Assert
    client_scope = anyio.CancelScope()
    async with anyio.create_task_group() as tg:
        # Start the lifecycle task. `tg.start` will wait until `task_status.started()` is called.
        session_from_task = await tg.start(
            client_manager.manage_client_lifecycle,
            client_id,
            mock_transport_context,
            client_scope,
        )

        # Assertions after the task has started
        assert session_from_task is mock_session_instance
        assert client_id in client_manager.active_clients
        assert client_manager.get_session(client_id) is mock_session_instance

        # Ensure the context managers were entered
        mock_transport_context.__aenter__.assert_awaited_once()
        mock_client_session_class.assert_called_once_with(mock_reader, mock_writer)
        mock_client_session_class.return_value.__aenter__.assert_awaited_once()

        # Now, cancel the dedicated scope to allow the task to exit its loop
        client_scope.cancel()

    # After the task group has exited, assert that cleanup was successful
    assert client_id not in client_manager.active_clients
    mock_client_session_class.return_value.__aexit__.assert_awaited_once()
    mock_transport_context.__aexit__.assert_awaited_once()
