"""
Unit tests for the ResourceManager class.
"""

import pytest
from unittest.mock import Mock, AsyncMock
import mcp.types as types
from pydantic import AnyUrl

from src.aurite.host.resources.resources import ResourceManager

# Mark all tests in this file as 'unit' and 'host'
pytestmark = [pytest.mark.unit, pytest.mark.host]


@pytest.mark.anyio
async def test_resource_manager_initialization():
    """
    Test that the ResourceManager can be initialized successfully.
    """
    # 1. Arrange
    mock_message_router = Mock()

    # 2. Act
    resource_manager = ResourceManager(message_router=mock_message_router)
    await resource_manager.initialize()

    # 3. Assert
    assert isinstance(resource_manager, ResourceManager)
    assert resource_manager._message_router == mock_message_router
    assert resource_manager._resources == {}


@pytest.mark.anyio
async def test_register_client_resources_allowed():
    """
    Test that resources are registered when allowed by the filtering manager.
    """
    # 1. Arrange
    mock_router = AsyncMock()
    resource_manager = ResourceManager(message_router=mock_router)

    mock_filtering_manager = Mock()
    mock_filtering_manager.is_registration_allowed.return_value = True

    client_id = "test_client"
    # Create a mock that is an instance of the expected type
    mock_resource = types.Resource(uri=AnyUrl("mcp://resource/1"), name="Test Resource")
    resources_to_register = [mock_resource]
    mock_client_config = Mock()

    # 2. Act
    registered_resources = await resource_manager.register_client_resources(
        client_id=client_id,
        resources=resources_to_register,
        client_config=mock_client_config,
        filtering_manager=mock_filtering_manager,
    )

    # 3. Assert
    assert registered_resources == resources_to_register
    assert client_id in resource_manager._resources
    assert "mcp://resource/1" in resource_manager._resources[client_id]
    mock_filtering_manager.is_registration_allowed.assert_called_once_with(
        "mcp://resource/1", mock_client_config
    )
    mock_router.register_resource.assert_awaited_once_with(
        resource_uri="mcp://resource/1", client_id=client_id
    )


@pytest.mark.anyio
async def test_register_client_resources_denied():
    """
    Test that resources are not registered when denied by the filtering manager.
    """
    # 1. Arrange
    mock_router = AsyncMock()
    resource_manager = ResourceManager(message_router=mock_router)

    mock_filtering_manager = Mock()
    mock_filtering_manager.is_registration_allowed.return_value = False

    client_id = "test_client"
    mock_resource = types.Resource(uri=AnyUrl("mcp://resource/1"), name="Test Resource")
    resources_to_register = [mock_resource]
    mock_client_config = Mock()

    # 2. Act
    registered_resources = await resource_manager.register_client_resources(
        client_id=client_id,
        resources=resources_to_register,
        client_config=mock_client_config,
        filtering_manager=mock_filtering_manager,
    )

    # 3. Assert
    assert registered_resources == []
    # The current implementation creates an empty dict for the client even if no resources are registered.
    # This test verifies that behavior.
    assert client_id in resource_manager._resources
    assert resource_manager._resources[client_id] == {}
    mock_filtering_manager.is_registration_allowed.assert_called_once_with(
        "mcp://resource/1", mock_client_config
    )
    mock_router.register_resource.assert_not_awaited()
