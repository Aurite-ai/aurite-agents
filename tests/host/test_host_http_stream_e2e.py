"""
End-to-end tests for MCPHost focusing on HTTP Stream client interactions.
"""

import pytest
import anyio # Import anyio
from anyio import Path

from src.host.host import MCPHost
from src.config.config_models import ClientConfig, RootConfig # Keep this if used in commented out example

# Assuming host_manager fixture is available from conftest.py or host_fixtures.py
# and it loads the 'testing_config.json' which now includes an http_stream_example_client.

pytestmark = pytest.mark.anyio


@pytest.mark.anyio(timeout=15)
@pytest.mark.host_integration
async def test_host_initializes_http_stream_client_successfully(
    host_manager,  # This fixture provides an initialized MCPHost
):
    """
    Tests that MCPHost can initialize an HTTP Stream client configured in testing_config.json.
    Assumes mcp_http_example_server.py is running externally on http://localhost:8083/mcp_stream_example/mcp.
    """
    mcp_host: MCPHost = host_manager.host

    http_client_id = "http_stream_example_client" # Updated client ID
    assert mcp_host.is_client_registered(
        http_client_id
    ), f"HTTP Stream client '{http_client_id}' should be registered with the host."

    session = mcp_host.client_manager.get_session(http_client_id)
    assert session is not None, f"Session for HTTP Stream client '{http_client_id}' should be active."
    assert not session.is_closed, f"Session for HTTP Stream client '{http_client_id}' should not be closed."

    # Verify tool discovery
    # The mcp_http_example_server provides 'uppercase_text' and 'add_numbers'
    # ToolManager is accessible via mcp_host.tools
    registered_tools = mcp_host.tools.get_all_tools_for_client(http_client_id)
    tool_names = {tool.name for tool in registered_tools}

    assert "uppercase_text" in tool_names, f"Tool 'uppercase_text' not discovered for client '{http_client_id}'"
    assert "add_numbers" in tool_names, f"Tool 'add_numbers' not discovered for client '{http_client_id}'"
    assert len(tool_names) == 2, f"Expected 2 tools for client '{http_client_id}', found {len(tool_names)}"

    # Explicitly shut down the client to see if it helps the test terminate cleanly
    await mcp_host.client_shutdown(http_client_id)
    await anyio.sleep(0.1) # Give a moment for shutdown
