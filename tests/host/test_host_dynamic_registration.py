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

async def test_register_client_success(host_manager: HostManager):
    """Test dynamically registering a new client successfully."""
    host: MCPHost = host_manager.host # Get the MCPHost instance

    # Define config for a new client (using the env_check_server fixture)
    # Ensure the path is relative to the project root where pytest runs
    env_check_server_path = Path("tests/fixtures/servers/env_check_server.py").resolve()
    new_client_id = "env_checker"
    new_client_config = ClientConfig(
        client_id=new_client_id,
        server_path=env_check_server_path,
        capabilities=["tools"],
        roots=[RootConfig(name="env_root", uri="env://", capabilities=[])],
    )

    # Verify client and its tool are not present initially
    assert not host.is_client_registered(new_client_id)
    assert not host.tools.has_tool("check_env")

    # Register the new client
    await host.register_client(new_client_config)

    # Verify client is registered
    assert host.is_client_registered(new_client_id)
    assert new_client_id in host._clients # Check internal state

    # Verify the client's tool is now registered
    assert host.tools.has_tool("check_env")
    tool_def = host.tools.get_tool("check_env")
    assert tool_def is not None
    assert tool_def.name == "check_env"

    # Verify the tool can be executed (optional sanity check)
    # Note: This relies on the dummy server implementation
    result = await host.execute_tool(tool_name="check_env", arguments={"var_name": "USER"})
    assert isinstance(result, list)
    assert len(result) > 0
    assert isinstance(result[0], types.TextContent)
    # We don't know the exact value of USER, just that it should return something
    assert len(result[0].text) > 0


async def test_register_client_duplicate_id(host_manager: HostManager):
    """Test that registering a client with a duplicate ID raises an error."""
    host: MCPHost = host_manager.host

    # Get an existing client config from the host's loaded config
    existing_client_id = "weather_client" # Assumes this exists from testing_config.json
    existing_config = next((c for c in host._config.clients if c.client_id == existing_client_id), None)
    assert existing_config is not None, f"Test setup error: Client '{existing_client_id}' not found in initial config."

    # Verify client is already registered
    assert host.is_client_registered(existing_client_id)

    # Attempt to re-register the same client config
    with pytest.raises(ValueError, match=f"Client ID '{existing_client_id}' already registered."):
        await host.register_client(existing_config)
