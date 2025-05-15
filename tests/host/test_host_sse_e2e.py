"""
End-to-end tests for MCPHost focusing on SSE client interactions.
"""

import pytest
import anyio # Import anyio
from anyio import Path

from src.host.host import MCPHost
from src.config.config_models import ClientConfig, RootConfig

# Assuming host_manager fixture is available from conftest.py or host_fixtures.py
# and it loads the 'testing_config.json' which now includes an SSE client.

pytestmark = pytest.mark.anyio


@pytest.mark.anyio(timeout=15) # Add a timeout to the test
@pytest.mark.host_integration
async def test_host_initializes_sse_client_successfully(
    host_manager,  # This fixture provides an initialized MCPHost
):
    """
    Tests that MCPHost can initialize an SSE client configured in testing_config.json.
    Assumes sse_example_server.py is running externally on http://localhost:8082/sse.
    """
    mcp_host: MCPHost = host_manager.host  # Get the MCPHost instance

    # Check if the SSE client is registered
    sse_client_id = "sse_example_client"
    assert mcp_host.is_client_registered(
        sse_client_id
    ), f"SSE client '{sse_client_id}' should be registered with the host."

    # Optionally, try to get the session to ensure it's active
    # This depends on ClientManager's get_session method
    session = mcp_host.client_manager.get_session(sse_client_id)
    assert session is not None, f"Session for SSE client '{sse_client_id}' should be active."
    assert not session.is_closed, f"Session for SSE client '{sse_client_id}' should not be closed."

    # Explicitly shut down the client to see if it helps the test terminate
    # This will also test if client_shutdown works correctly for SSE clients
    await mcp_host.client_shutdown(sse_client_id)

    # Give a moment for shutdown procedures to complete
    # May not be strictly necessary but can help in some async scenarios
    await anyio.sleep(0.1)

    # Further tests could involve trying to send a basic message or check capabilities
    # if the sse_example_server.py is enhanced to support more MCP features.
    # For now, successful registration and an active session are good indicators.

    # Example of how one might add a dynamic SSE client for more isolated testing
    # (though the current test relies on config file)
    # dynamic_sse_client_config = ClientConfig(
    # client_id="dynamic_sse_test_client",
    # transport_type="sse",
    # sse_url="http://localhost:8082/sse", # Ensure your example server is running
    # roots=[],
    # capabilities=["tools"], # Adjust as per your example server
    # timeout=5.0
    # )
    # await mcp_host.register_client(dynamic_sse_client_config)
    # assert mcp_host.is_client_registered("dynamic_sse_test_client")
    # await mcp_host.client_shutdown("dynamic_sse_test_client")
