"""
Unit tests for the MessageRouter.
"""

import pytest
from unittest.mock import AsyncMock

# Import the class to test
from src.host.foundation.routing import MessageRouter

# Mark tests as host_unit and async
pytestmark = [pytest.mark.host_unit, pytest.mark.anyio]


# --- Fixtures ---

@pytest.fixture
def message_router() -> MessageRouter:
    """Fixture to provide a clean MessageRouter instance for each test."""
    return MessageRouter()


# --- Test Cases ---

async def test_message_router_init(message_router: MessageRouter):
    """Test initial state of the MessageRouter."""
    assert message_router._server_capabilities == {}
    assert message_router._server_weights == {}
    assert message_router._tool_routes == {}
    assert message_router._prompt_routes == {}
    assert message_router._resource_routes == {}
    # assert message_router._lock is not None # Internal detail, less critical to test


async def test_register_server(message_router: MessageRouter):
    """Test registering a server."""
    server_id = "server_A"
    capabilities = {"tools", "prompts"}
    weight = 1.5

    await message_router.register_server(server_id, capabilities, weight)

    assert server_id in message_router._server_capabilities
    assert server_id in message_router._server_weights
    assert message_router._server_capabilities[server_id] == capabilities
    assert message_router._server_weights[server_id] == weight
    # Note: active_requests and error_count are not tracked in the current implementation


async def test_register_server_duplicate(message_router: MessageRouter):
    """Test registering the same server ID again updates its info."""
    server_id = "server_A"
    await message_router.register_server(server_id, {"tools"}, 1.0)
    await message_router.register_server(server_id, {"prompts"}, 2.0) # Register again

    assert server_id in message_router._server_capabilities
    assert server_id in message_router._server_weights
    assert message_router._server_capabilities[server_id] == {"prompts"} # Should be updated
    assert message_router._server_weights[server_id] == 2.0 # Should be updated


async def test_register_tool(message_router: MessageRouter):
    """Test registering a tool for a specific client."""
    tool_name = "tool_X"
    client_id = "client_1"

    # Need to register the client first (implicitly tested here)
    await message_router.register_server(client_id, {"tools"}, 1.0)
    await message_router.register_tool(tool_name, client_id)

    assert tool_name in message_router._tool_routes
    # _tool_routes maps tool_name -> List[client_id]
    assert message_router._tool_routes[tool_name] == [client_id]


async def test_register_tool_multiple_clients(message_router: MessageRouter):
    """Test registering the same tool for multiple clients."""
    tool_name = "tool_Y"
    client_1 = "client_A"
    client_2 = "client_B"

    await message_router.register_server(client_1, {"tools"}, 1.0)
    await message_router.register_server(client_2, {"tools"}, 1.0)
    await message_router.register_tool(tool_name, client_1)
    await message_router.register_tool(tool_name, client_2) # Register for second client

    assert tool_name in message_router._tool_routes
    # Check both clients are in the list for the tool
    assert set(message_router._tool_routes[tool_name]) == {client_1, client_2}


async def test_register_tool_client_not_registered(message_router: MessageRouter):
    """Test registering a tool for a non-existent client raises error (or handles gracefully)."""
    # Current implementation doesn't explicitly check if client exists before adding tool mapping.
    # This might be desired behavior (allow registering mapping even if server fails later)
    # or an area for potential improvement. For now, test current behavior.
    tool_name = "tool_Z"
    client_id = "non_existent_client"

    await message_router.register_tool(tool_name, client_id)

    assert tool_name in message_router._tool_routes
    assert message_router._tool_routes[tool_name] == [client_id]
    # Assert that the client itself is *not* in the server capability/weight dicts
    assert client_id not in message_router._server_capabilities
    assert client_id not in message_router._server_weights


# TODO: Add tests for register_prompt, register_resource
# TODO: Add tests for get_clients_for_tool, get_clients_for_prompt, get_clients_for_resource
# TODO: Add tests for _select_server logic (weights, active_requests, errors) - might need more complex setup/mocking
# TODO: Add tests for increment/decrement active_requests
# TODO: Add tests for record_error
# TODO: Add tests for shutdown
