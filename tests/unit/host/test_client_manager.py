"""
Unit tests for the ClientManager class.
"""

import pytest
from unittest.mock import Mock

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
