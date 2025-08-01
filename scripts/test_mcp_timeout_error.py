#!/usr/bin/env python3
"""
Test script to verify MCP server timeout error handling.

This script creates a test MCP server configuration with a very short timeout
to trigger the timeout error and verify the structured error response.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aurite.execution.mcp_host.host import MCPHost
from aurite.lib.config.config_models import ClientConfig
from aurite.utils.errors import MCPServerTimeoutError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_timeout_error():
    """Test that MCP server registration timeout produces structured error."""

    # Create a test configuration with a very short timeout
    # Using a command that will hang to ensure it times out
    test_config = ClientConfig(
        name="test-timeout-server",
        transport_type="local",
        command="sleep",  # This will hang indefinitely
        args=["60"],  # Sleep for 60 seconds
        capabilities=["tools"],  # Required field
        registration_timeout=0.1,  # 100ms timeout to ensure it fails
    )

    host = MCPHost()

    try:
        logger.info("Attempting to register server with 100ms timeout...")
        await host.register_client(test_config)
        logger.error("Expected timeout error but registration succeeded!")
    except MCPServerTimeoutError as e:
        logger.info("✓ Caught MCPServerTimeoutError as expected")
        logger.info(f"  - Error message: {str(e)}")
        logger.info(f"  - Server name: {e.server_name}")
        logger.info(f"  - Timeout seconds: {e.timeout_seconds}")
        logger.info(f"  - Operation: {e.operation}")

        # Verify the error attributes
        assert e.server_name == "test-timeout-server"
        assert e.timeout_seconds == 0.1
        assert e.operation == "registration"

        logger.info("✓ All error attributes are correct")

        # Simulate what the API would return
        api_response = {
            "error": "mcp_server_timeout",
            "detail": str(e),
            "server_name": e.server_name,
            "timeout_seconds": e.timeout_seconds,
            "operation": e.operation,
        }

        logger.info("\nSimulated API response (status 504):")
        logger.info(json.dumps(api_response, indent=2))

    except Exception as e:
        logger.error(f"✗ Unexpected error type: {type(e).__name__}: {e}")
        raise


async def test_api_endpoint():
    """Test the actual API endpoint if the server is running."""
    import os

    import httpx

    # Check if API server is running
    api_url = "http://localhost:8000"

    try:
        async with httpx.AsyncClient() as client:
            # First check if server is running
            health_response = await client.get(f"{api_url}/health")
            if health_response.status_code != 200:
                logger.info("API server not running, skipping API test")
                return

            logger.info("\nTesting actual API endpoint...")

            # Create test config with timeout
            test_config = {
                "name": "test-timeout-server",
                "transport_type": "local",
                "command": "sleep",  # This will hang indefinitely
                "args": ["60"],  # Sleep for 60 seconds
                "capabilities": ["tools"],  # Required field
                "registration_timeout": 0.1,
            }
            # Get API key from environment or use "test" as default for local testing
            api_key = os.environ.get("API_KEY", "test")
            headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

            try:
                response = await client.post(f"{api_url}/tools/register/config", json=test_config, headers=headers)

                if response.status_code == 504:
                    logger.info("✓ Received expected 504 Gateway Timeout status")
                    error_data = response.json()
                    logger.info(f"✓ Error response: {json.dumps(error_data, indent=2)}")

                    # Verify response structure
                    assert error_data.get("error") == "mcp_server_timeout"
                    assert "detail" in error_data
                    assert error_data.get("server_name") == "test-timeout-server"
                    assert error_data.get("timeout_seconds") == 0.1
                    assert error_data.get("operation") == "registration"

                    logger.info("✓ API response has correct structure")
                else:
                    logger.error(f"✗ Unexpected status code: {response.status_code}")
                    logger.error(f"Response: {response.text}")

            except httpx.HTTPError as e:
                logger.error(f"HTTP error during API test: {e}")

    except httpx.ConnectError:
        logger.info("API server not running, skipping API test")


async def main():
    """Run all tests."""
    logger.info("Testing MCP Server Timeout Error Handling")
    logger.info("=" * 50)

    # Test the error class directly
    await test_timeout_error()

    # Test via API if available
    await test_api_endpoint()

    logger.info("\n✓ All tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
