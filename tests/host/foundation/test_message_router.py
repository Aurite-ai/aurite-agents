"""
Unit tests for the MessageRouter.
"""

import pytest

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
    await message_router.register_server(server_id, {"prompts"}, 2.0)  # Register again

    assert server_id in message_router._server_capabilities
    assert server_id in message_router._server_weights
    assert message_router._server_capabilities[server_id] == {
        "prompts"
    }  # Should be updated
    assert message_router._server_weights[server_id] == 2.0  # Should be updated


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
    await message_router.register_tool(
        tool_name, client_2
    )  # Register for second client

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


# --- Prompt Registration Tests ---


async def test_register_prompt(message_router: MessageRouter):
    """Test registering a prompt for a specific client."""
    prompt_name = "prompt_A"
    client_id = "client_1"
    await message_router.register_server(client_id, {"prompts"}, 1.0)
    await message_router.register_prompt(prompt_name, client_id)

    assert prompt_name in message_router._prompt_routes
    assert message_router._prompt_routes[prompt_name] == [client_id]
    assert client_id in message_router._client_prompts
    assert message_router._client_prompts[client_id] == {prompt_name}


async def test_register_prompt_multiple_clients(message_router: MessageRouter):
    """Test registering the same prompt for multiple clients."""
    prompt_name = "prompt_B"
    client_1 = "client_X"
    client_2 = "client_Y"
    await message_router.register_server(client_1, {"prompts"}, 1.0)
    await message_router.register_server(client_2, {"prompts"}, 1.0)
    await message_router.register_prompt(prompt_name, client_1)
    await message_router.register_prompt(prompt_name, client_2)

    assert prompt_name in message_router._prompt_routes
    assert set(message_router._prompt_routes[prompt_name]) == {client_1, client_2}
    assert message_router._client_prompts[client_1] == {prompt_name}
    assert message_router._client_prompts[client_2] == {prompt_name}


# --- Resource Registration Tests ---


async def test_register_resource(message_router: MessageRouter):
    """Test registering a resource for a specific client."""
    resource_uri = "file:///tmp/resource1.txt"
    client_id = "client_R"
    await message_router.register_server(client_id, {"resources"}, 1.0)
    await message_router.register_resource(resource_uri, client_id)

    assert resource_uri in message_router._resource_routes
    assert message_router._resource_routes[resource_uri] == [client_id]
    assert client_id in message_router._client_resources
    assert message_router._client_resources[client_id] == {resource_uri}


async def test_register_resource_multiple_clients(message_router: MessageRouter):
    """Test registering the same resource for multiple clients."""
    resource_uri = "http://example.com/data"
    client_1 = "client_S"
    client_2 = "client_T"
    await message_router.register_server(client_1, {"resources"}, 1.0)
    await message_router.register_server(client_2, {"resources"}, 1.0)
    await message_router.register_resource(resource_uri, client_1)
    await message_router.register_resource(resource_uri, client_2)

    assert resource_uri in message_router._resource_routes
    assert set(message_router._resource_routes[resource_uri]) == {client_1, client_2}
    assert message_router._client_resources[client_1] == {resource_uri}
    assert message_router._client_resources[client_2] == {resource_uri}


# --- Getter Tests ---


async def test_get_clients_for_tool(message_router: MessageRouter):
    """Test retrieving clients for a specific tool."""
    tool_name = "tool_Get"
    client_1 = "c1"
    client_2 = "c2"
    await message_router.register_server(client_1, {"tools"}, 1.0)
    await message_router.register_server(client_2, {"tools"}, 1.0)
    await message_router.register_tool(tool_name, client_1)
    await message_router.register_tool(tool_name, client_2)
    await message_router.register_tool("other_tool", client_1)

    clients = await message_router.get_clients_for_tool(tool_name)
    assert isinstance(clients, list)
    assert set(clients) == {client_1, client_2}

    # Test non-existent tool
    clients_none = await message_router.get_clients_for_tool("non_existent_tool")
    assert clients_none == []


async def test_get_clients_for_prompt(message_router: MessageRouter):
    """Test retrieving clients for a specific prompt."""
    prompt_name = "prompt_Get"
    client_1 = "c1"
    client_2 = "c2"
    await message_router.register_server(client_1, {"prompts"}, 1.0)
    await message_router.register_server(client_2, {"prompts"}, 1.0)
    await message_router.register_prompt(prompt_name, client_1)
    await message_router.register_prompt(prompt_name, client_2)
    await message_router.register_prompt("other_prompt", client_1)

    clients = await message_router.get_clients_for_prompt(prompt_name)
    assert isinstance(clients, list)
    assert set(clients) == {client_1, client_2}

    # Test non-existent prompt
    clients_none = await message_router.get_clients_for_prompt("non_existent_prompt")
    assert clients_none == []


async def test_get_clients_for_resource(message_router: MessageRouter):
    """Test retrieving clients for a specific resource."""
    resource_uri = "res:///data/item1"
    client_1 = "c1"
    client_2 = "c2"
    await message_router.register_server(client_1, {"resources"}, 1.0)
    await message_router.register_server(client_2, {"resources"}, 1.0)
    await message_router.register_resource(resource_uri, client_1)
    await message_router.register_resource(resource_uri, client_2)
    await message_router.register_resource("res:///other", client_1)

    clients = await message_router.get_clients_for_resource(resource_uri)
    assert isinstance(clients, list)
    assert set(clients) == {client_1, client_2}

    # Test non-existent resource
    clients_none = await message_router.get_clients_for_resource("non_existent_res")
    assert clients_none == []


# --- Shutdown Test ---


async def test_shutdown(message_router: MessageRouter):
    """Test that shutdown clears all internal registries."""
    # Register some data
    await message_router.register_server("s1", {"tools"}, 1.0)
    await message_router.register_tool("t1", "s1")
    await message_router.register_prompt("p1", "s1")
    await message_router.register_resource("r1", "s1")

    # Verify data exists before shutdown
    assert message_router._server_capabilities
    assert message_router._server_weights
    assert message_router._tool_routes
    assert message_router._prompt_routes
    assert message_router._resource_routes
    assert message_router._client_tools
    assert message_router._client_prompts
    assert message_router._client_resources

    # Shutdown
    await message_router.shutdown()

    # Verify all registries are cleared
    assert not message_router._server_capabilities
    assert not message_router._server_weights
    assert not message_router._tool_routes
    assert not message_router._prompt_routes
    assert not message_router._resource_routes
    assert not message_router._client_tools
    assert not message_router._client_prompts
    assert not message_router._client_resources


# --- Client Component Getter Tests ---


async def test_get_tools_for_client(message_router: MessageRouter):
    """Test retrieving tools for a specific client."""
    client_1 = "c1"
    client_2 = "c2"
    await message_router.register_server(client_1, {"tools", "prompts"}, 1.0)
    await message_router.register_server(client_2, {"tools"}, 1.0)
    await message_router.register_tool("tool_A", client_1)
    await message_router.register_tool("tool_B", client_1)
    await message_router.register_tool("tool_C", client_2)

    tools_c1 = await message_router.get_tools_for_client(client_1)
    assert tools_c1 == {"tool_A", "tool_B"}

    tools_c2 = await message_router.get_tools_for_client(client_2)
    assert tools_c2 == {"tool_C"}

    tools_c3 = await message_router.get_tools_for_client("non_existent_client")
    assert tools_c3 == set()


async def test_get_prompts_for_client(message_router: MessageRouter):
    """Test retrieving prompts for a specific client."""
    client_1 = "c1"
    client_2 = "c2"
    await message_router.register_server(client_1, {"prompts"}, 1.0)
    await message_router.register_server(client_2, {"prompts", "tools"}, 1.0)
    await message_router.register_prompt("prompt_A", client_1)
    await message_router.register_prompt("prompt_B", client_2)
    await message_router.register_prompt("prompt_C", client_2)

    prompts_c1 = await message_router.get_prompts_for_client(client_1)
    assert prompts_c1 == {"prompt_A"}

    prompts_c2 = await message_router.get_prompts_for_client(client_2)
    assert prompts_c2 == {"prompt_B", "prompt_C"}

    prompts_c3 = await message_router.get_prompts_for_client("non_existent_client")
    assert prompts_c3 == set()


async def test_get_resources_for_client(message_router: MessageRouter):
    """Test retrieving resources for a specific client."""
    client_1 = "c1"
    client_2 = "c2"
    res_1 = "res://1"
    res_2 = "res://2"
    await message_router.register_server(client_1, {"resources"}, 1.0)
    await message_router.register_server(client_2, {"resources"}, 1.0)
    await message_router.register_resource(res_1, client_1)
    await message_router.register_resource(res_2, client_2)

    resources_c1 = await message_router.get_resources_for_client(client_1)
    assert resources_c1 == {res_1}

    resources_c2 = await message_router.get_resources_for_client(client_2)
    assert resources_c2 == {res_2}

    resources_c3 = await message_router.get_resources_for_client("non_existent_client")
    assert resources_c3 == set()


# --- Server Management Tests (Including Unregistration) ---


async def test_get_server_capabilities(message_router: MessageRouter):
    """Test retrieving capabilities for a registered server."""
    server_id = "server_Cap"
    capabilities = {"tools", "resources"}
    await message_router.register_server(server_id, capabilities, 1.0)

    retrieved_caps = await message_router.get_server_capabilities(server_id)
    assert retrieved_caps == capabilities

    # Test non-existent server
    retrieved_caps_none = await message_router.get_server_capabilities("non_existent")
    assert retrieved_caps_none == set()


async def test_update_server_weight(message_router: MessageRouter):
    """Test updating the weight of a registered server."""
    server_id = "server_Weight"
    await message_router.register_server(server_id, {"tools"}, 1.0)
    assert message_router._server_weights[server_id] == 1.0

    await message_router.update_server_weight(server_id, 5.5)
    assert message_router._server_weights[server_id] == 5.5


async def test_update_server_weight_not_registered(message_router: MessageRouter):
    """Test updating weight for a non-existent server raises ValueError."""
    with pytest.raises(ValueError, match="Server not registered: non_existent"):
        await message_router.update_server_weight("non_existent", 2.0)


async def test_unregister_server(message_router: MessageRouter):
    """Test unregistering a server and removing all its associated registrations."""
    s1 = "server1"
    s2 = "server2"
    tool_a = "tool_A"
    tool_b = "tool_B"
    prompt_a = "prompt_A"
    res_a = "res://A"

    await message_router.register_server(s1, {"tools", "prompts", "resources"}, 1.0)
    await message_router.register_server(s2, {"tools"}, 1.0)

    await message_router.register_tool(tool_a, s1)
    await message_router.register_tool(tool_a, s2)  # Tool A provided by both
    await message_router.register_tool(tool_b, s1)  # Tool B only by s1
    await message_router.register_prompt(prompt_a, s1)
    await message_router.register_resource(res_a, s1)

    # Verify initial state
    assert s1 in message_router._server_capabilities
    assert s1 in message_router._server_weights
    assert tool_a in message_router._tool_routes
    assert set(message_router._tool_routes[tool_a]) == {s1, s2}
    assert tool_b in message_router._tool_routes
    assert message_router._tool_routes[tool_b] == [s1]
    assert prompt_a in message_router._prompt_routes
    assert res_a in message_router._resource_routes
    assert s1 in message_router._client_tools
    assert s1 in message_router._client_prompts
    assert s1 in message_router._client_resources

    # Unregister server 1
    await message_router.unregister_server(s1)

    # Verify s1 is removed
    assert s1 not in message_router._server_capabilities
    assert s1 not in message_router._server_weights
    assert s1 not in message_router._client_tools
    assert s1 not in message_router._client_prompts
    assert s1 not in message_router._client_resources

    # Verify routes are updated
    assert tool_a in message_router._tool_routes  # Tool A still exists (provided by s2)
    assert message_router._tool_routes[tool_a] == [s2]  # Only s2 remains
    assert tool_b not in message_router._tool_routes  # Tool B should be gone
    assert prompt_a not in message_router._prompt_routes
    assert res_a not in message_router._resource_routes

    # Verify s2 is untouched
    assert s2 in message_router._server_capabilities


async def test_unregister_non_existent_server(message_router: MessageRouter):
    """Test unregistering a non-existent server does nothing and doesn't raise error."""
    # Should execute without error
    await message_router.unregister_server("non_existent")
