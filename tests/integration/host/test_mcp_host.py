"""
Integration tests for the MCPHost class.
"""

import pytest
from unittest.mock import AsyncMock

from src.aurite.host.host import MCPHost
from src.aurite.config.config_models import HostConfig, ClientConfig

# Mark all tests in this file as 'integration' and 'host'
pytestmark = [pytest.mark.integration, pytest.mark.host]


@pytest.mark.anyio
async def test_mcp_host_initializes_and_connects_via_session_group(mocker):
    """
    Tests that MCPHost initializes, uses ClientSessionGroup to connect to servers,
    and properly shuts down.
    """
    # 1. Arrange
    client_config1 = ClientConfig(
        name="client1",
        transport_type="stdio",
        server_path="/bin/true",
        capabilities=["tools"],
    )
    client_config2 = ClientConfig(
        name="client2",
        transport_type="http_stream",
        http_endpoint="http://localhost:8000",
        capabilities=["tools"],
    )
    host_config = HostConfig(mcp_servers=[client_config1, client_config2])

    # Mock ClientSessionGroup
    mock_session_group_instance = AsyncMock()
    mock_session_group_instance.connect_to_server = AsyncMock()

    # We need to mock the __aenter__ and __aexit__ methods for the async context manager
    mock_session_group_instance.__aenter__.return_value = mock_session_group_instance
    mock_session_group_instance.__aexit__.return_value = AsyncMock()

    mock_client_session_group = mocker.patch(
        "src.aurite.host.host.ClientSessionGroup",
        return_value=mock_session_group_instance,
    )

    # 2. Act
    async with MCPHost(config=host_config) as host:
        # 3. Assert (during initialization)
        assert isinstance(host, MCPHost)

        # Check that ClientSessionGroup was instantiated
        mock_client_session_group.assert_called_once()

        # Check that we entered the session group's context
        mock_session_group_instance.__aenter__.assert_awaited_once()

        # Check that connect_to_server was called for each client
        assert mock_session_group_instance.connect_to_server.call_count == 2

        # We can inspect the calls if needed, but for now, count is sufficient
        # to prove delegation.

    # Assert (after shutdown)
    mock_session_group_instance.__aexit__.assert_awaited_once()
