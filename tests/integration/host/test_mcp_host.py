"""
Integration tests for the MCPHost class.
"""

from unittest.mock import AsyncMock

import pytest

from src.aurite.execution.mcp_host.host import MCPHost
from src.aurite.lib.config.config_models import ClientConfig

# Mark all tests in this file as 'integration' and 'host'
pytestmark = [pytest.mark.integration, pytest.mark.host]


@pytest.mark.anyio
async def test_mcp_host_registers_and_unregisters_clients(mocker):
    """
    Tests that MCPHost can register clients, which involves creating sessions
    and managing their lifecycles, and then properly unregister them.
    """
    # 1. Arrange
    client_config_stdio = ClientConfig(
        name="client1",
        transport_type="stdio",
        server_path="/bin/true",  # Added required server_path
        capabilities=["tools"],
    )
    client_config_http = ClientConfig(
        name="client2",
        transport_type="http_stream",
        http_endpoint="http://localhost:8000",
        capabilities=["tools"],
    )

    # Mock the underlying client connections and sessions
    mock_stdio_client = mocker.patch("src.aurite.execution.mcp_host.host.stdio_client", return_value=AsyncMock())
    # Ensure the mock returns a 2-tuple as expected by the code for stdio
    mock_stdio_client.return_value.__aenter__.return_value = (
        AsyncMock(),
        AsyncMock(),
    )

    mock_http_client = mocker.patch(
        "src.aurite.execution.mcp_host.host.streamablehttp_client", return_value=AsyncMock()
    )
    # Ensure the mock returns a 3-tuple as expected by the code for http_stream
    mock_http_client.return_value.__aenter__.return_value = (
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
    )

    # Mock mcp.ClientSession to behave like an async context manager
    mock_session_instance = AsyncMock()
    mock_session_instance.list_tools.return_value.tools = []
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session_instance

    mock_client_session_class = mocker.patch(
        "src.aurite.execution.mcp_host.host.mcp.ClientSession", return_value=mock_session_cm
    )

    # 2. Act & Assert
    async with MCPHost() as host:
        # Register clients
        await host.register_client(client_config_stdio)
        await host.register_client(client_config_http)

        # Assert registration
        assert "client1" in host.registered_server_names
        assert "client2" in host.registered_server_names
        assert len(host._sessions) == 2
        mock_stdio_client.assert_called_once()
        mock_http_client.assert_called_once()
        assert mock_client_session_class.call_count == 2

        # Unregister a client
        await host.unregister_client("client1")
        assert "client1" not in host.registered_server_names
        assert len(host._sessions) == 1

    # Host shutdown should unregister the remaining client
    assert len(host._sessions) == 0
    assert "client2" not in host.registered_server_names


@pytest.mark.anyio
async def test_register_client_resolves_env_vars(mocker):
    """
    Tests that register_client correctly resolves environment variables
    in client configurations.
    """
    # 1. Arrange
    client_config = ClientConfig(
        name="http_client",
        transport_type="http_stream",
        http_endpoint="http://localhost:{PORT}",
        capabilities=["tools"],
    )

    mocker.patch.dict("os.environ", {"PORT": "8080"}, clear=True)
    mock_http_client = mocker.patch(
        "src.aurite.execution.mcp_host.host.streamablehttp_client", return_value=AsyncMock()
    )
    # Ensure the mock returns a 3-tuple as expected
    mock_http_client.return_value.__aenter__.return_value = (
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
    )
    # Mock mcp.ClientSession to behave like an async context manager
    mock_session_instance = AsyncMock()
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session_instance
    mocker.patch("src.aurite.execution.mcp_host.host.mcp.ClientSession", return_value=mock_session_cm)

    # 2. Act
    async with MCPHost() as host:
        await host.register_client(client_config)

        # 3. Assert
        mock_http_client.assert_called_once()
        call_args = mock_http_client.call_args
        # The URL is passed as a keyword argument to streamablehttp_client
        assert call_args.kwargs["url"] == "http://localhost:8080"
