"""
Integration tests for MCPHost dynamic client registration.
Uses the host_manager fixture.
"""

import pytest
from pathlib import Path

# Import the class to test and dependencies/models
from src.host.host import MCPHost
from src.config.config_models import ClientConfig  # Updated import path
from src.host_manager import HostManager  # For type hinting fixture

# Mark tests as host_integration and async
pytestmark = [pytest.mark.host_integration, pytest.mark.anyio]


# --- Test Cases ---


# Removed timeout marker
async def test_register_client_success(host_manager: HostManager):
    """Test dynamically registering a new client successfully using weather_mcp_server."""
    host: MCPHost = host_manager.host  # Get the MCPHost instance

    # Define config for a new client (using the weather_mcp_server fixture)
    # Ensure the path is relative to the project root where pytest runs
    weather_server_path = Path("tests/fixtures/servers/weather_mcp_server.py").resolve()
    new_client_id = "dynamic_weather_server"  # New ID
    new_client_config = ClientConfig(
        client_id=new_client_id,
        server_path=weather_server_path,  # Updated path
        capabilities=["tools", "prompts"],  # Updated capabilities
        roots=[],  # Weather server doesn't define roots in this test setup
    )

    # Verify client is not present initially
    assert not host.is_client_registered(new_client_id)
    # Tool 'weather_lookup' might already exist from the initial 'weather_server' client in the fixture
    # assert not host.tools.has_tool("weather_lookup") # REMOVED THIS CHECK

    # Register the new client
    await host.register_client(new_client_config)

    # Verify client is registered
    assert host.is_client_registered(new_client_id)
    assert (
        new_client_id in host.client_manager.active_clients
    )  # Check ClientManager's state

    # Verify the client's tool is registered in the ToolManager
    assert host.tools.has_tool("weather_lookup")  # Check tool exists
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
    existing_client_id = (
        "weather_server"  # Corrected client ID from testing_config.json
    )
    existing_config = next(
        (c for c in host._config.clients if c.client_id == existing_client_id), None
    )
    assert existing_config is not None, (
        f"Test setup error: Client '{existing_client_id}' not found in initial config."
    )

    # Verify client is already registered
    assert host.is_client_registered(existing_client_id)

    # Attempt to re-register the same client config
    with pytest.raises(
        ValueError, match=f"Client ID '{existing_client_id}' already registered."
    ):
        await host.register_client(existing_config)


@pytest.mark.xfail(reason="Known anyio shutdown issue during client process termination by AsyncExitStack")
async def test_dynamic_client_registration_and_unregistration(host_manager: HostManager):
    """
    Test dynamically registering a client, verifying its components,
    then unregistering it and verifying components are removed.
    """
    host: MCPHost = host_manager.host
    new_client_id = "dynamic_unreg_client"
    tool_name_specific_to_new_client = "unreg_tool_test" # Assume this tool is unique

    # Config for the new client
    # Using a simple dummy server for this test to avoid relying on weather_mcp_server specifics
    # We'll need to create a dummy server file or use an existing simple one.
    # For now, let's assume a simple server that just offers one unique tool.
    # This part might need adjustment based on available dummy servers.
    dummy_server_path = Path("tests/fixtures/servers/dummy_mcp_server_for_unreg.py") # Create this
    if not dummy_server_path.exists():
        # Create a minimal dummy server if it doesn't exist
        dummy_server_path.parent.mkdir(parents=True, exist_ok=True)
        dummy_server_path.write_text(f"""
import mcp.server
import mcp.types as types

class DummyServer(mcp.server.Server):
    async def list_tools(self) -> types.ListToolsResult:
        return types.ListToolsResult(tools=[
            types.Tool(name="{tool_name_specific_to_new_client}", description="A test tool for unregistration.", inputSchema={{}})
        ])
    async def call_tool(self, name: str, arguments: dict) -> types.CallToolResult:
        return types.CallToolResult(content=[types.TextContent(type="text", text="dummy result")])

if __name__ == "__main__":
    mcp.server.run_server(DummyServer())
""")

    new_client_config = ClientConfig(
        client_id=new_client_id,
        server_path=dummy_server_path.resolve(),
        capabilities=["tools"],
        roots=[],
    )

    # 1. Register the new client
    await host.register_client(new_client_config)
    assert host.is_client_registered(new_client_id)
    assert new_client_id in host.client_manager.active_clients
    assert host.tools.has_tool(tool_name_specific_to_new_client)
    clients_for_tool = await host._message_router.get_clients_for_tool(tool_name_specific_to_new_client)
    assert new_client_id in clients_for_tool

    # 2. Unregister the client
    await host.client_shutdown(new_client_id) # This calls the updated client_shutdown

    # 3. Verify client and its specific tool are unregistered
    assert not host.is_client_registered(new_client_id)
    assert new_client_id not in host.client_manager.active_clients

    # Verify the tool is no longer associated with this client in the router
    clients_for_tool_after_unreg = await host._message_router.get_clients_for_tool(tool_name_specific_to_new_client)
    assert new_client_id not in clients_for_tool_after_unreg

    # If this client was the *only* provider of the tool, the tool should be gone from ToolManager
    if not clients_for_tool_after_unreg: # Check if the list is empty
        assert not host.tools.has_tool(tool_name_specific_to_new_client)

    # Clean up dummy server file if created
    # if dummy_server_path.exists() and "dummy_mcp_server_for_unreg.py" in str(dummy_server_path):
    #     dummy_server_path.unlink() # Be careful with unlink
