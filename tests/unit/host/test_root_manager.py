"""
Unit tests for the RootManager class.
"""

import pytest

from src.aurite.config.config_models import RootConfig
from src.aurite.host.foundation.roots import RootManager

# Mark all tests in this file as 'unit' and 'host'
pytestmark = [pytest.mark.unit, pytest.mark.host]


@pytest.mark.anyio
async def test_root_manager_initialization():
    """
    Test that the RootManager can be initialized successfully.
    """
    # 1. Arrange & 2. Act
    root_manager = RootManager()
    await root_manager.initialize()

    # 3. Assert
    assert isinstance(root_manager, RootManager)
    assert root_manager._client_roots == {}
    assert root_manager._client_uris == {}


@pytest.mark.anyio
async def test_register_roots_happy_path():
    """
    Test that valid roots can be registered for a client.
    """
    # 1. Arrange
    root_manager = RootManager()
    client_id = "test_client"
    roots_to_register = [
        RootConfig(
            name="mcp_root",
            uri="mcp://resource/",
            capabilities=["tools", "prompts"],
        ),
        RootConfig(
            name="file_root",
            uri="file:///home/user/",
            capabilities=["resources"],
        ),
    ]

    # 2. Act
    await root_manager.register_roots(client_id, roots_to_register)

    # 3. Assert
    assert client_id in root_manager._client_roots
    assert root_manager._client_roots[client_id] == roots_to_register
    assert root_manager._client_uris[client_id] == {
        "mcp://resource/",
        "file:///home/user/",
    }


@pytest.mark.anyio
async def test_register_roots_invalid_uri():
    """
    Test that registering a root with an invalid URI raises a ValueError.
    """
    # 1. Arrange
    root_manager = RootManager()
    client_id = "test_client"
    # This root is invalid because it lacks a scheme
    invalid_roots = [RootConfig(name="invalid_root", uri="not-a-valid-uri", capabilities=["tools"])]

    # 2. Act & Assert
    with pytest.raises(ValueError, match="Root URI not-a-valid-uri must have a scheme"):
        await root_manager.register_roots(client_id, invalid_roots)


@pytest.mark.anyio
async def test_validate_access():
    """
    Test the validate_access method for known and unknown clients.
    """
    # 1. Arrange
    root_manager = RootManager()
    client_id = "known_client"
    await root_manager.register_roots(
        client_id,
        [RootConfig(name="test_root", uri="mcp://root/", capabilities=["tools"])],
    )

    # 2. Act
    access_known = await root_manager.validate_access(client_id)
    access_unknown = await root_manager.validate_access("unknown_client")

    # 3. Assert
    assert access_known is True
    assert access_unknown is False
