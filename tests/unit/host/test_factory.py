"""
Unit tests for the ClientFactory.
"""

import pytest
from unittest.mock import Mock, patch

from src.aurite.host.foundation.factory import create_transport_context
from src.aurite.config.config_models import ClientConfig

pytestmark = [pytest.mark.unit, pytest.mark.host]


@pytest.mark.anyio
@patch("src.aurite.host.foundation.factory.stdio_client")
async def test_create_transport_context_stdio(mock_stdio_client):
    """
    Test that the factory creates an stdio_client for 'stdio' transport.
    """
    # 1. Arrange
    config = ClientConfig(
        name="test",
        transport_type="stdio",
        server_path="/fake/path/server.py",
        capabilities=[],
    )
    mock_security_manager = Mock()

    # 2. Act
    await create_transport_context(config, mock_security_manager)

    # 3. Assert
    mock_stdio_client.assert_called_once()


@pytest.mark.anyio
@patch("src.aurite.host.foundation.factory.streamablehttp_client")
async def test_create_transport_context_http_stream(mock_http_client):
    """
    Test that the factory creates a streamablehttp_client for 'http_stream' transport.
    """
    # 1. Arrange
    config = ClientConfig(
        name="test",
        transport_type="http_stream",
        http_endpoint="http://localhost:8000",
        capabilities=[],
    )
    mock_security_manager = Mock()

    # 2. Act
    await create_transport_context(config, mock_security_manager)

    # 3. Assert
    mock_http_client.assert_called_once_with("http://localhost:8000")


@pytest.mark.anyio
@patch("src.aurite.host.foundation.factory.stdio_client")
async def test_create_transport_context_local(mock_stdio_client):
    """
    Test that the factory creates an stdio_client for 'local' transport.
    """
    # 1. Arrange
    config = ClientConfig(
        name="test",
        transport_type="local",
        command="echo",
        args=["hello"],
        capabilities=[],
    )
    mock_security_manager = Mock()

    # 2. Act
    await create_transport_context(config, mock_security_manager)

    # 3. Assert
    mock_stdio_client.assert_called_once()


@pytest.mark.anyio
async def test_create_transport_context_unsupported(mocker):
    """
    Test that the factory raises a ValueError for an unsupported transport type.
    """
    # 1. Arrange
    # Create a valid config and then patch its transport_type for the test
    config = ClientConfig(
        name="test", transport_type="local", command="c", args=["a"], capabilities=[]
    )
    mocker.patch.object(config, "transport_type", "invalid_transport")
    mock_security_manager = Mock()

    # 2. Act & Assert
    with pytest.raises(
        ValueError, match="Unsupported transport_type: invalid_transport"
    ):
        await create_transport_context(config, mock_security_manager)
