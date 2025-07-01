"""
Integration tests for the MCPHost class.
"""

import pytest

from src.aurite.host.host import MCPHost
from src.aurite.config.config_models import HostConfig

# Mark all tests in this file as 'integration' and 'host'
pytestmark = [pytest.mark.integration, pytest.mark.host]


@pytest.mark.anyio
async def test_mcp_host_initialization():
    """
    Test that the MCPHost can be initialized successfully with a basic config.
    """
    # 1. Arrange
    # For this integration test, we provide a minimal, valid host configuration.
    # The host should be able to initialize even with no servers defined.
    host_config = HostConfig(mcp_servers=[])

    # 2. Act
    mcp_host = MCPHost(config=host_config)
    await mcp_host.initialize()

    # 3. Assert
    assert isinstance(mcp_host, MCPHost)
    assert mcp_host._config == host_config
    # Ensure the main task group for clients was created
    assert mcp_host._client_runners_task_group is not None

    # Shut down the host to clean up any potential background tasks
    await mcp_host.shutdown()
    # Verify shutdown logic
    assert mcp_host._client_runners_task_group is None
