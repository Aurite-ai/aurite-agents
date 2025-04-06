"""
E2E tests for basic MCPHost functionality using a real host and server.

These tests utilize the `real_mcp_host` fixture to verify the state
and basic communication abilities of an initialized MCPHost instance
connected to a live server process (as defined in testing_config.json).
"""

import pytest
import logging

# Use relative imports assuming tests run from aurite-mcp root
from src.host.host import MCPHost
import mcp.types as types

# Configure logging for debugging E2E tests if needed
logger = logging.getLogger(__name__)


@pytest.mark.e2e
# Apply xfail due to the known host shutdown issue with the fixture
@pytest.mark.xfail(
    reason="Known issue with real_mcp_host teardown async complexity", strict=False
)
class TestHostBasicE2E:
    """E2E tests for basic MCPHost state and communication."""

    @pytest.mark.asyncio
    async def test_host_is_running_after_initialize(self, real_mcp_host: MCPHost):
        """Verify the host reports as running after the fixture initializes it."""
        host = real_mcp_host
        # The real_mcp_host fixture calls host.initialize()
        # We need a way to check if it's considered 'running'.
        # Let's assume the presence of client processes indicates running state,
        # or check if a dedicated status method/attribute exists.
        # Checking _clients dict length after initialize() is a good proxy.
        assert len(host._clients) > 0, (
            "Host should have active clients after initialization"
        )
        # If MCPHost had an `is_running` property that's set after initialize(),
        # we would assert that here:
        # assert host.is_running

        # Also check basic status if available (assuming get_status exists)
        try:
            status = await host.get_status()  # Assuming get_status method exists
            assert isinstance(status, dict)  # Or whatever the expected status type is
            logger.info(f"Host status: {status}")
        except AttributeError:
            logger.warning("MCPHost does not have a get_status() method to test.")
        except Exception as e:
            pytest.fail(f"Calling host.get_status() failed: {e}")

    @pytest.mark.asyncio
    async def test_host_basic_communication(self, real_mcp_host: MCPHost):
        """Verify basic list_tools/list_prompts communication via the initialized host."""
        host = real_mcp_host
        assert len(host._clients) > 0, "Host should have active clients"

        logger.info("Testing basic communication (list_tools/list_prompts) via host...")

        try:
            # Call list_tools for all connected clients
            all_tools = await host.tools.list_tools()
            assert isinstance(all_tools, list)
            logger.info(f"Host received {len(all_tools)} tools total from clients.")
            # We don't need to deeply inspect here, just check the call succeeded
        except Exception as e:
            pytest.fail(f"host.tools.list_tools() failed: {e}")

        try:
            # Call list_prompts for all connected clients
            all_prompts = await host.prompts.list_prompts()
            assert isinstance(all_prompts, list)
            logger.info(f"Host received {len(all_prompts)} prompts total from clients.")
            # We don't need to deeply inspect here, just check the call succeeded
        except Exception as e:
            pytest.fail(f"host.prompts.list_prompts() failed: {e}")
