"""
Unit tests for the ResourceManager.
"""

import pytest
from unittest.mock import MagicMock, call
from typing import List  # Added List import

# Import the class to test and dependencies/models
from src.host.resources.resources import ResourceManager

# Import foundation classes for type hinting shared fixtures
# Import models
from src.config.config_models import ClientConfig, RootConfig  # Updated import path

# Import mcp types
import mcp.types as types

# Mark tests as host_unit and async
pytestmark = [pytest.mark.host_unit, pytest.mark.anyio]


# --- Fixtures ---

# Removed local mock_message_router, mock_filtering_manager, mock_root_manager fixtures
# They are now imported from tests.fixtures.host_fixtures


@pytest.fixture
def resource_manager(
    mock_message_router: MagicMock, mock_root_manager: MagicMock
) -> ResourceManager:
    """Fixture to provide a clean ResourceManager instance with mocked dependencies."""
    # ResourceManager __init__ only takes message_router
    return ResourceManager(message_router=mock_message_router)


@pytest.fixture
def sample_client_config() -> ClientConfig:
    """Fixture for a sample ClientConfig."""
    return ClientConfig(
        client_id="client_R",
        server_path="path/to/server_r.py",
        capabilities=["resources"],
        # Corrected RootConfig: use 'uri' and add 'capabilities'
        roots=[RootConfig(name="root1", uri="file:///data/", capabilities=[])],
    )


@pytest.fixture
def sample_resource() -> types.Resource:
    """Fixture for a sample Resource."""
    return types.Resource(
        uri="file:///data/resource1.txt",
        name="resource1",
        description="Sample text resource",
        metadata={"type": "text"},
    )


# --- Test Cases ---


# Test __init__
def test_resource_manager_init(
    resource_manager: ResourceManager,
    mock_message_router: MagicMock,
    mock_root_manager: MagicMock,
):
    """Test initial state of the ResourceManager."""
    assert resource_manager._resources == {}
    assert resource_manager._message_router == mock_message_router
    # Removed assertion for _root_manager as it's not stored


# --- Tests for register_client_resources ---


async def test_register_client_resources_success(
    resource_manager: ResourceManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
    sample_resource: types.Resource,
):
    """Test registering resources successfully for a client."""
    client_id = sample_client_config.client_id
    resource2 = types.Resource(uri="file:///data/resource2.json", name="resource2")
    resources_to_register = [sample_resource, resource2]

    # Ensure filtering allows registration
    mock_filtering_manager.is_registration_allowed.return_value = True

    registered = await resource_manager.register_client_resources(
        client_id=client_id,
        resources=resources_to_register,
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    assert len(registered) == 2
    assert sample_resource in registered
    assert resource2 in registered

    # Check internal state (using URI strings as keys)
    assert client_id in resource_manager._resources
    assert (
        resource_manager._resources[client_id][str(sample_resource.uri)]
        == sample_resource
    )
    assert resource_manager._resources[client_id][str(resource2.uri)] == resource2

    # Check calls to dependencies (using URI strings)
    mock_filtering_manager.is_registration_allowed.assert_has_calls(
        [
            call(str(sample_resource.uri), sample_client_config),
            call(str(resource2.uri), sample_client_config),
        ],
        any_order=True,
    )
    # Check router calls (using resource_uri and URI strings)
    mock_message_router.register_resource.assert_has_calls(
        [
            call(resource_uri=str(sample_resource.uri), client_id=client_id),
            call(resource_uri=str(resource2.uri), client_id=client_id),
        ],
        any_order=True,
    )


async def test_register_client_resources_filtered(
    resource_manager: ResourceManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
    sample_resource: types.Resource,  # Allowed resource
):
    """Test that resources are filtered by FilteringManager during registration."""
    client_id = sample_client_config.client_id
    excluded_resource = types.Resource(
        uri="file:///other/excluded.dat", name="excluded_resource"
    )
    resources_to_register = [sample_resource, excluded_resource]

    # Configure mock FilteringManager to exclude the second resource based on URI string
    def filter_side_effect(uri_str, config):
        return uri_str != str(excluded_resource.uri)  # Compare URI string

    mock_filtering_manager.is_registration_allowed.side_effect = filter_side_effect

    registered = await resource_manager.register_client_resources(
        client_id=client_id,
        resources=resources_to_register,
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    # Assert only allowed resource was registered and returned
    assert len(registered) == 1
    assert sample_resource in registered
    assert excluded_resource not in registered

    # Check internal state (using URI strings as keys)
    assert client_id in resource_manager._resources
    assert str(sample_resource.uri) in resource_manager._resources[client_id]
    assert str(excluded_resource.uri) not in resource_manager._resources[client_id]

    # Check calls to dependencies (using URI strings)
    mock_filtering_manager.is_registration_allowed.assert_has_calls(
        [
            call(str(sample_resource.uri), sample_client_config),
            call(str(excluded_resource.uri), sample_client_config),
        ],
        any_order=True,
    )
    # Ensure router was only called for the allowed resource (using resource_uri)
    mock_message_router.register_resource.assert_called_once_with(
        resource_uri=str(sample_resource.uri), client_id=client_id
    )


async def test_register_client_resources_empty(
    resource_manager: ResourceManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
):
    """Test registering an empty list of resources."""
    client_id = sample_client_config.client_id
    registered = await resource_manager.register_client_resources(
        client_id=client_id,
        resources=[],
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    assert registered == []
    # Check that the client ID *was* added, but maps to an empty dict
    assert client_id in resource_manager._resources
    assert resource_manager._resources[client_id] == {}
    mock_filtering_manager.is_registration_allowed.assert_not_called()
    mock_message_router.register_resource.assert_not_called()


# --- Tests for get_resource ---


async def test_get_resource_success(
    resource_manager: ResourceManager,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
    sample_resource: types.Resource,
):
    """Test retrieving an existing resource successfully."""
    client_id = sample_client_config.client_id
    await resource_manager.register_client_resources(
        client_id=client_id,
        resources=[sample_resource],
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    # Use await and 'uri' argument
    retrieved_resource = await resource_manager.get_resource(
        client_id=client_id, uri="file:///data/resource1.txt"
    )
    assert retrieved_resource == sample_resource


async def test_get_resource_client_not_found(
    resource_manager: ResourceManager,
):  # Make async
    """Test retrieving a resource from a non-existent client."""
    # Use await and 'uri' argument
    retrieved_resource = await resource_manager.get_resource(
        client_id="non_existent_client", uri="file:///data/resource1.txt"
    )
    assert retrieved_resource is None


async def test_get_resource_resource_not_found(
    resource_manager: ResourceManager,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
    sample_resource: types.Resource,
):
    """Test retrieving a non-existent resource from an existing client."""
    client_id = sample_client_config.client_id
    await resource_manager.register_client_resources(
        client_id=client_id,
        resources=[sample_resource],
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    # Use await and 'uri' argument
    retrieved_resource = await resource_manager.get_resource(
        client_id=client_id, uri="file:///non/existent.txt"
    )
    assert retrieved_resource is None


# --- Tests for list_resources ---


async def test_list_resources_empty(resource_manager: ResourceManager):
    """Test listing resources when none are registered."""
    assert await resource_manager.list_resources() == []


async def test_list_resources_single_client(
    resource_manager: ResourceManager,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
    sample_resource: types.Resource,
):
    """Test listing resources for a single registered client."""
    client_id = sample_client_config.client_id
    resource2 = types.Resource(uri="file:///data/resource2.json", name="resource2")
    await resource_manager.register_client_resources(
        client_id=client_id,
        resources=[sample_resource, resource2],
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    # Test listing all
    all_resources = await resource_manager.list_resources()
    assert len(all_resources) == 2
    assert sample_resource in all_resources
    assert resource2 in all_resources

    # Test listing for the specific client
    client_resources = await resource_manager.list_resources(client_id=client_id)
    assert len(client_resources) == 2
    assert sample_resource in client_resources
    assert resource2 in client_resources

    # Test listing for a non-existent client
    non_existent_resources = await resource_manager.list_resources(
        client_id="non_existent"
    )
    assert non_existent_resources == []


async def test_list_resources_multiple_clients(
    resource_manager: ResourceManager,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,  # Client R
    sample_resource: types.Resource,  # Resource R1
):
    """Test listing resources for multiple registered clients."""
    client_id_r = sample_client_config.client_id
    resource_r2 = types.Resource(uri="file:///data/resource_r2.txt", name="resource_r2")
    await resource_manager.register_client_resources(
        client_id=client_id_r,
        resources=[sample_resource, resource_r2],
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    # Client S
    client_id_s = "client_S"
    client_config_s = ClientConfig(
        client_id=client_id_s,
        server_path="path/s",
        capabilities=["resources"],
        roots=[],
    )
    resource_s1 = types.Resource(
        uri="file:///other/resource_s1.csv", name="resource_s1"
    )
    # Reset mock side effect if necessary
    mock_filtering_manager.is_registration_allowed.side_effect = None
    mock_filtering_manager.is_registration_allowed.return_value = True
    await resource_manager.register_client_resources(
        client_id=client_id_s,
        resources=[resource_s1],
        client_config=client_config_s,
        filtering_manager=mock_filtering_manager,
    )

    # Test listing all
    all_resources = await resource_manager.list_resources()
    assert len(all_resources) == 3
    assert sample_resource in all_resources
    assert resource_r2 in all_resources
    assert resource_s1 in all_resources

    # Test listing for Client R
    client_r_resources = await resource_manager.list_resources(client_id=client_id_r)
    assert len(client_r_resources) == 2
    assert sample_resource in client_r_resources
    assert resource_r2 in client_r_resources

    # Test listing for Client S
    client_s_resources = await resource_manager.list_resources(client_id=client_id_s)
    assert len(client_s_resources) == 1
    assert resource_s1 in client_s_resources


# --- Tests for get_clients_for_resource ---


async def test_get_clients_for_resource_found(
    resource_manager: ResourceManager,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,  # Client R
):
    """Test finding clients that provide a specific resource URI."""
    client_id_r = sample_client_config.client_id
    client_id_s = "client_S"
    client_config_s = ClientConfig(
        client_id=client_id_s,
        server_path="path/s",
        capabilities=["resources"],
        roots=[],
    )

    resource_common = types.Resource(uri="file:///common/data.txt", name="common")
    resource_r_only = types.Resource(uri="file:///data/r_only.txt", name="r_only")
    resource_s_only = types.Resource(uri="file:///other/s_only.csv", name="s_only")

    # Register for Client R
    await resource_manager.register_client_resources(
        client_id=client_id_r,
        resources=[resource_common, resource_r_only],
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )
    # Register for Client S
    mock_filtering_manager.is_registration_allowed.side_effect = None
    mock_filtering_manager.is_registration_allowed.return_value = True
    await resource_manager.register_client_resources(
        client_id=client_id_s,
        resources=[resource_common, resource_s_only],
        client_config=client_config_s,
        filtering_manager=mock_filtering_manager,
    )

    clients_common = resource_manager.get_clients_for_resource(str(resource_common.uri))
    clients_r = resource_manager.get_clients_for_resource(str(resource_r_only.uri))
    clients_s = resource_manager.get_clients_for_resource(str(resource_s_only.uri))

    assert sorted(clients_common) == sorted([client_id_r, client_id_s])
    assert clients_r == [client_id_r]
    assert clients_s == [client_id_s]


def test_get_clients_for_resource_not_found(resource_manager: ResourceManager):
    """Test finding clients for a resource URI that no client provides."""
    clients = resource_manager.get_clients_for_resource("file:///non/existent.zip")
    assert clients == []


# --- Tests for validate_resource_access ---


@pytest.mark.parametrize(
    "resource_uri, client_roots, expected_result",
    [
        # Exact match
        (
            "file:///data/resource1.txt",
            [RootConfig(name="root1", uri="file:///data/", capabilities=[])],
            True,
        ),
        # Subdirectory match
        (
            "file:///data/subdir/resource2.txt",
            [RootConfig(name="root1", uri="file:///data/", capabilities=[])],
            True,
        ),
        # Different root
        (
            "file:///other/resource3.txt",
            [RootConfig(name="root1", uri="file:///data/", capabilities=[])],
            False,
        ),
        # No matching root among multiple
        (
            "file:///unmatched/resource4.txt",
            [
                RootConfig(name="root1", uri="file:///data/", capabilities=[]),
                RootConfig(name="root2", uri="file:///archive/", capabilities=[]),
            ],
            False,
        ),
        # Matching root among multiple
        (
            "file:///archive/resource5.zip",
            [
                RootConfig(name="root1", uri="file:///data/", capabilities=[]),
                RootConfig(name="root2", uri="file:///archive/", capabilities=[]),
            ],
            True,
        ),
        # Client has no roots defined
        ("file:///data/resource1.txt", [], False),
        # Custom scheme match
        (
            "weather://san_francisco/forecast",
            [RootConfig(name="weather", uri="weather://", capabilities=[])],
            True,
        ),
        # Custom scheme mismatch
        (
            "weather://new_york/alerts",
            [RootConfig(name="geo", uri="geo://", capabilities=[])],
            False,
        ),
    ],
)
async def test_validate_resource_access(
    resource_manager: ResourceManager,
    mock_root_manager: MagicMock,
    resource_uri: str,
    client_roots: List[RootConfig],
    expected_result: bool,
):
    """Test resource access validation against various root configurations."""
    client_id = "client_Validate"

    # Configure the mock RootManager to return the specified roots for this client
    mock_root_manager.get_client_roots.return_value = client_roots

    if expected_result:
        # Expect the validation to pass (return True)
        result = await resource_manager.validate_resource_access(
            uri=resource_uri,
            client_id=client_id,
            root_manager=mock_root_manager,
        )
        assert result is True
        mock_root_manager.get_client_roots.assert_called_once_with(client_id)
    else:
        # Expect the validation to fail (raise ValueError)
        with pytest.raises(ValueError) as excinfo:
            await resource_manager.validate_resource_access(
                uri=resource_uri,
                client_id=client_id,
                root_manager=mock_root_manager,
            )
        assert f"Resource {resource_uri} is not accessible" in str(excinfo.value)
        mock_root_manager.get_client_roots.assert_called_once_with(client_id)


# --- Test for shutdown ---


async def test_shutdown(
    resource_manager: ResourceManager,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig,
    sample_resource: types.Resource,
):
    """Test the shutdown process clears internal state."""
    client_id = sample_client_config.client_id
    # Register a resource first
    await resource_manager.register_client_resources(
        client_id=client_id,
        resources=[sample_resource],
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )

    # Ensure it was registered
    assert client_id in resource_manager._resources
    assert str(sample_resource.uri) in resource_manager._resources[client_id]

    # Call shutdown
    await resource_manager.shutdown()

    # Assert internal state is cleared
    assert resource_manager._resources == {}
    # No interaction with MessageRouter expected during ResourceManager shutdown


async def test_unregister_client_resources(
    resource_manager: ResourceManager,
    mock_message_router: MagicMock,
    mock_filtering_manager: MagicMock,
    sample_client_config: ClientConfig, # Client R
):
    """Test unregistering resources for a specific client."""
    client_id_r = sample_client_config.client_id
    client_id_s = "client_S"
    client_config_s = ClientConfig(
        client_id=client_id_s, server_path="path/s", capabilities=["resources"], roots=[]
    )

    resource_r1 = types.Resource(uri="file:///data/r1.txt", name="r1")
    resource_s1 = types.Resource(uri="file:///other/s1.txt", name="s1")

    # Register resources for client R
    await resource_manager.register_client_resources(
        client_id=client_id_r,
        resources=[resource_r1],
        client_config=sample_client_config,
        filtering_manager=mock_filtering_manager,
    )
    # Register resources for client S
    mock_filtering_manager.is_registration_allowed.side_effect = None # Reset for next call
    mock_filtering_manager.is_registration_allowed.return_value = True
    await resource_manager.register_client_resources(
        client_id=client_id_s,
        resources=[resource_s1],
        client_config=client_config_s,
        filtering_manager=mock_filtering_manager,
    )

    assert client_id_r in resource_manager._resources
    assert client_id_s in resource_manager._resources

    # Unregister resources for client R
    await resource_manager.unregister_client_resources(client_id_r)

    assert client_id_r not in resource_manager._resources
    assert client_id_s in resource_manager._resources # Client S should remain
    assert str(resource_r1.uri) not in resource_manager._resources.get(client_id_s, {})

    # Unregister resources for a non-existent client (should not error)
    await resource_manager.unregister_client_resources("non_existent_client")
    assert client_id_s in resource_manager._resources # Client S should still remain
