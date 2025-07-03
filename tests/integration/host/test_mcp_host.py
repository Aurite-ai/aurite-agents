"""
Integration tests for the MCPHost class.
"""

import pytest

from src.aurite.host.host import MCPHost
from src.aurite.config.config_models import ClientConfig

# Mark all tests in this file as 'integration' and 'host'
pytestmark = [pytest.mark.integration, pytest.mark.host]


@pytest.mark.anyio
async def test_mcp_host_initializes_and_connects_via_session_group(
    mock_client_session_group, mocker
):
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

    mocker.patch(
        "src.aurite.host.host.ClientSessionGroup",
        return_value=mock_client_session_group,
    )

    # 2. Act
    async with MCPHost() as host:
        await host.register_client(client_config1)
        await host.register_client(client_config2)
        # 3. Assert (during initialization)
        assert isinstance(host, MCPHost)
        mock_client_session_group.__aenter__.assert_awaited_once()
        assert mock_client_session_group.connect_to_server.call_count == 2

    # Assert (after shutdown)
    mock_client_session_group.__aexit__.assert_awaited_once()


@pytest.mark.anyio
async def test_get_server_params_handles_env_vars_and_docker(
    mock_client_session_group, mocker
):
    """
    Tests that _get_server_params correctly resolves environment variables
    and handles the DOCKER_ENV case.
    """
    # 1. Arrange
    client_config = ClientConfig(
        name="http_client",
        transport_type="http_stream",
        http_endpoint="http://localhost:{PORT}",
        capabilities=["tools"],
    )

    mocker.patch(
        "src.aurite.host.host.ClientSessionGroup",
        return_value=mock_client_session_group,
    )
    mocker.patch.dict("os.environ", {"PORT": "8080", "DOCKER_ENV": "true"}, clear=True)

    # 2. Act
    async with MCPHost() as host:
        await host.register_client(client_config)
        # 3. Assert
        mock_client_session_group.connect_to_server.assert_awaited_once()
        call_args = mock_client_session_group.connect_to_server.call_args
        server_params = call_args.args[0]
        assert server_params.url == "http://host.docker.internal:8080"
