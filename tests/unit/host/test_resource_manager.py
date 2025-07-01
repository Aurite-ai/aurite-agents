"""
Unit tests for the ResourceManager class.
"""

import pytest
import mcp.types as types
from pydantic import AnyUrl

from src.aurite.host.resources.resources import ResourceManager

# Mark all tests in this file as 'unit' and 'host'
pytestmark = [pytest.mark.unit, pytest.mark.host]


@pytest.mark.anyio
async def test_resource_manager_initialization(
    mock_message_router, mock_client_session_group
):
    """
    Test that the ResourceManager can be initialized successfully and registers resources.
    """
    # 1. Arrange
    resource = types.Resource(uri=AnyUrl("mcp://resource/1"), name="Test Resource")
    setattr(resource, "client_id", "test_client")
    mock_client_session_group.resources = {"mcp://resource/1": resource}

    # 2. Act
    resource_manager = ResourceManager(
        message_router=mock_message_router, session_group=mock_client_session_group
    )
    await resource_manager.initialize()

    # 3. Assert
    assert isinstance(resource_manager, ResourceManager)
    mock_message_router.register_resource.assert_awaited_once_with(
        resource_uri="mcp://resource/1", client_id="test_client"
    )


@pytest.mark.anyio
async def test_get_resource(mock_message_router, mock_client_session_group):
    """
    Test that get_resource retrieves a resource from the session group.
    """
    # 1. Arrange
    resource = types.Resource(uri=AnyUrl("mcp://resource/1"), name="Test Resource")
    mock_client_session_group.resources = {"mcp://resource/1": resource}
    resource_manager = ResourceManager(
        message_router=mock_message_router, session_group=mock_client_session_group
    )

    # 2. Act
    retrieved_resource = await resource_manager.get_resource("mcp://resource/1")

    # 3. Assert
    assert retrieved_resource == resource


@pytest.mark.anyio
async def test_list_resources(mock_message_router, mock_client_session_group):
    """
    Test that list_resources returns all resources from the session group.
    """
    # 1. Arrange
    resource1 = types.Resource(uri=AnyUrl("mcp://resource/1"), name="Test Resource 1")
    resource2 = types.Resource(uri=AnyUrl("mcp://resource/2"), name="Test Resource 2")
    mock_client_session_group.resources = {
        "mcp://resource/1": resource1,
        "mcp://resource/2": resource2,
    }
    resource_manager = ResourceManager(
        message_router=mock_message_router, session_group=mock_client_session_group
    )

    # 2. Act
    all_resources = await resource_manager.list_resources()

    # 3. Assert
    assert len(all_resources) == 2
    assert resource1 in all_resources
    assert resource2 in all_resources
