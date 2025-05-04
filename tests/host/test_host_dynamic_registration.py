"""
Integration tests for MCPHost dynamic client registration.
Uses the host_manager fixture.
"""

import pytest
from pathlib import Path

# Import the class to test and dependencies/models
from src.host.host import MCPHost
from src.host.models import ClientConfig, RootConfig
from src.host_manager import HostManager # For type hinting fixture
import mcp.types as types # Add this import

# Mark tests as host_integration and async
pytestmark = [pytest.mark.host_integration, pytest.mark.anyio]


# --- Test Cases ---

# Removed timeout marker
async def test_register_client_success(host_manager: HostManager):
    """Test dynamically registering a new client successfully using weather_mcp_server."""
    host: MCPHost = host_manager.host # Get the MCPHost instance

    # Define config for a new client (using the weather_mcp_server fixture)
    # Ensure the path is relative to the project root where pytest runs
    weather_server_path = Path("tests/fixtures/servers/weather_mcp_server.py").resolve()
    new_client_id = "dynamic_weather_server" # New ID
    new_client_config = ClientConfig(
        client_id=new_client_id,
        server_path=weather_server_path, # Updated path
        capabilities=["tools", "prompts"], # Updated capabilities
        roots=[], # Weather server doesn't define roots in this test setup
    )

    # Verify client is not present initially
    assert not host.is_client_registered(new_client_id)
    # Tool 'weather_lookup' might already exist from the initial 'weather_server' client in the fixture
    # assert not host.tools.has_tool("weather_lookup") # REMOVED THIS CHECK

    # Register the new client
    await host.register_client(new_client_config)

    # Verify client is registered
    assert host.is_client_registered(new_client_id)
    assert new_client_id in host._clients # Check internal state

    # Verify the client's tool is registered in the ToolManager
    assert host.tools.has_tool("weather_lookup") # Check tool exists
    tool_def = host.tools.get_tool("weather_lookup")
    assert tool_def is not None
    assert tool_def.name == "weather_lookup"

    # Verify the *new* client is now associated with the tool in the MessageRouter
    clients_for_tool = await host._message_router.get_clients_for_tool("weather_lookup")
    assert new_client_id in clients_for_tool
    # Also verify the original client is still there
    assert "weather_server" in clients_for_tool

async def test_register_client_duplicate_id(host_manager: HostManager):
    """Test that registering a client with a duplicate ID raises an error."""
    host: MCPHost = host_manager.host

    # Get an existing client config from the host's loaded config
    existing_client_id = "weather_server" # Corrected client ID from testing_config.json
    existing_config = next((c for c in host._config.clients if c.client_id == existing_client_id), None)
    assert existing_config is not None, f"Test setup error: Client '{existing_client_id}' not found in initial config."

    # Verify client is already registered
    assert host.is_client_registered(existing_client_id)

    # Attempt to re-register the same client config
    with pytest.raises(ValueError, match=f"Client ID '{existing_client_id}' already registered."):
        await host.register_client(existing_config)
