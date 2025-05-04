"""
Unit tests for the RootManager.
"""

import pytest

# Import the class to test and dependent models
from src.host.foundation.roots import RootManager
from src.host.models import RootConfig

# Mark tests as host_unit and async
pytestmark = [pytest.mark.host_unit, pytest.mark.anyio]


# --- Fixtures ---


@pytest.fixture
def root_manager() -> RootManager:
    """Fixture to provide a clean RootManager instance for each test."""
    return RootManager()


# --- Test Cases ---


async def test_root_manager_init(root_manager: RootManager):
    """Test initial state of the RootManager."""
    assert root_manager._client_roots == {}


async def test_register_roots_single_client(root_manager: RootManager):
    """Test registering roots for a single client."""
    client_id = "client_A"
    roots_config = [
        RootConfig(uri="file:///path/to/dir1", name="Dir1", capabilities=["read"]),
        RootConfig(
            uri="http://example.com", name="Example", capabilities=["read", "write"]
        ),
    ]

    await root_manager.register_roots(client_id, roots_config)

    assert client_id in root_manager._client_roots
    assert len(root_manager._client_roots[client_id]) == 2
    # Check if the RootConfig objects are stored correctly (or just check URIs/names)
    stored_uris = {str(r.uri) for r in root_manager._client_roots[client_id]}
    expected_uris = {str(r.uri) for r in roots_config}
    assert stored_uris == expected_uris


async def test_register_roots_multiple_clients(root_manager: RootManager):
    """Test registering roots for multiple clients."""
    client_A = "client_A"
    roots_A = [RootConfig(uri="file:///A", name="A", capabilities=["read"])]
    client_B = "client_B"
    roots_B = [RootConfig(uri="file:///B", name="B", capabilities=["write"])]

    await root_manager.register_roots(client_A, roots_A)
    await root_manager.register_roots(client_B, roots_B)

    assert client_A in root_manager._client_roots
    assert client_B in root_manager._client_roots
    assert len(root_manager._client_roots[client_A]) == 1
    assert len(root_manager._client_roots[client_B]) == 1
    assert str(root_manager._client_roots[client_A][0].uri) == "file:///A"
    assert str(root_manager._client_roots[client_B][0].uri) == "file:///B"


async def test_register_roots_empty_list(root_manager: RootManager):
    """Test registering an empty list of roots for a client."""
    client_id = "client_C"
    await root_manager.register_roots(client_id, [])

    assert client_id in root_manager._client_roots
    assert root_manager._client_roots[client_id] == []


async def test_get_client_roots(root_manager: RootManager):
    """Test retrieving the list of roots for a client."""
    client_id = "client_D"
    roots_config = [
        RootConfig(uri="file:///D1", name="D1", capabilities=[]),
        RootConfig(uri="file:///D2", name="D2", capabilities=[]),
    ]
    await root_manager.register_roots(client_id, roots_config)

    retrieved_roots = await root_manager.get_client_roots(client_id)
    # The order might not be preserved, compare sets of URIs or sort
    retrieved_uris = sorted([str(r.uri) for r in retrieved_roots])
    expected_uris = sorted([str(r.uri) for r in roots_config])
    assert retrieved_uris == expected_uris
    # Ensure it returns a copy, not the internal list (though difficult to test directly without modification)
    assert retrieved_roots is not root_manager._client_roots[client_id]


async def test_get_client_roots_not_registered(root_manager: RootManager):
    """Test retrieving roots for a non-existent client returns an empty list."""
    retrieved_roots = await root_manager.get_client_roots("non_existent")
    assert retrieved_roots == []


async def test_shutdown(root_manager: RootManager):
    """Test that shutdown clears the internal roots dictionary."""
    client_id = "client_E"
    roots_config = [RootConfig(uri="file:///E", name="E", capabilities=[])]
    await root_manager.register_roots(client_id, roots_config)
    assert root_manager._client_roots  # Ensure not empty before shutdown

    await root_manager.shutdown()

    assert not root_manager._client_roots  # Should be empty after shutdown


# TODO: Add tests for validate_access (requires mocking urlparse or careful URI setup)
