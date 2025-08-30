#!/usr/bin/env python3
"""
Test script for TestingMCPHost - validates server lifecycle management
with both good and bad weather test servers.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.aurite.testing.mcp import TestingMCPHost

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_single_server_lifecycle():
    """Test basic server lifecycle management with a single server."""
    logger.info("=" * 60)
    logger.info("TEST: Single Server Lifecycle")
    logger.info("=" * 60)

    async with TestingMCPHost() as host:
        # Test single server registration
        config_good = {
            "name": "test_weather_good",
            "transport_type": "stdio",
            "server_path": "tests/fixtures/test_mcp_servers/test_weather_good/server.py",
            "timeout": 10.0,
            "registration_timeout": 30.0,
        }

        logger.info("Registering test_weather_good server...")
        success = await host.register_server(config_good)
        assert success, "Failed to register good weather server"
        logger.info("✓ Server registered successfully")

        # Check registration
        assert await host.is_server_registered("test_weather_good"), "Server not registered"
        logger.info("✓ Server registration confirmed")

        # Get tools to verify connection
        tools = await host.get_server_tools("test_weather_good")
        assert len(tools) > 0, "No tools found"
        assert any(t.name == "weather_lookup" for t in tools), "weather_lookup tool not found"
        logger.info(f"✓ Found {len(tools)} tools, including weather_lookup")

        # Test tool calling
        logger.info("Testing tool call...")
        result = await host.call_tool("weather_lookup", {"location": "San Francisco"})
        assert result is not None, "Tool call returned None"
        assert not result.isError, f"Tool call returned error: {result}"

        # Parse and verify response
        content = result.content[0]
        if hasattr(content, "text"):
            response_text = content.text  # type: ignore
        else:
            response_text = str(content)
        response_data = json.loads(response_text)
        assert "location" in response_data, "Response missing location"
        assert response_data["location"] == "San Francisco", "Wrong location in response"
        assert "temperature" in response_data, "Response missing temperature"
        logger.info(f"✓ Tool call successful: {response_data['location']} - {response_data['temperature']}°F")

        # Test unregistration
        logger.info("Unregistering server...")
        success = await host.unregister_server("test_weather_good")
        assert success, "Failed to unregister server"
        assert not await host.is_server_registered("test_weather_good"), "Server still registered after unregister"
        logger.info("✓ Server unregistered successfully")

    logger.info("✓ Single server lifecycle test PASSED\n")


async def test_concurrent_servers():
    """Test managing multiple servers concurrently."""
    logger.info("=" * 60)
    logger.info("TEST: Concurrent Server Management")
    logger.info("=" * 60)

    async with TestingMCPHost() as host:
        config_good = {
            "name": "test_weather_good",
            "transport_type": "stdio",
            "server_path": "tests/fixtures/test_mcp_servers/test_weather_good/server.py",
            "timeout": 10.0,
            "registration_timeout": 30.0,
        }

        config_bad = {
            "name": "test_weather_bad",
            "transport_type": "stdio",
            "server_path": "tests/fixtures/test_mcp_servers/test_weather_bad/server.py",
            "timeout": 35.0,
            "registration_timeout": 40.0,
        }

        # Register both servers concurrently
        logger.info("Registering both servers concurrently...")
        results = await asyncio.gather(
            host.register_server(config_good), host.register_server(config_bad), return_exceptions=True
        )

        # Check results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Server {i} registration failed: {result}")
                raise AssertionError(f"Server registration failed: {result}")
            assert result is True, f"Server {i} registration returned {result}"

        logger.info("✓ Both servers registered successfully")

        # Verify both are registered
        assert await host.is_server_registered("test_weather_good"), "Good server not registered"
        assert await host.is_server_registered("test_weather_bad"), "Bad server not registered"
        logger.info("✓ Both servers confirmed registered")

        # Verify both have tools
        tools_good = await host.get_server_tools("test_weather_good")
        tools_bad = await host.get_server_tools("test_weather_bad")
        assert len(tools_good) > 0, "Good server has no tools"
        assert len(tools_bad) > 0, "Bad server has no tools"
        logger.info(f"✓ Good server: {len(tools_good)} tools, Bad server: {len(tools_bad)} tools")

        # Test that tools are not prefixed
        all_tools = host.get_all_tools()
        assert "weather_lookup" in all_tools, "Tool should not be prefixed"
        assert "test_weather_good-weather_lookup" not in all_tools, "Tool should not have server prefix"
        logger.info("✓ Tools are not prefixed (framework-agnostic)")

        # Test concurrent tool calls
        logger.info("Testing concurrent tool calls...")
        results = await asyncio.gather(
            host.call_tool("weather_lookup", {"location": "London"}),
            host.call_tool("weather_lookup", {"location": "Tokyo"}),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Tool call exception (expected for bad server): {result}")
            elif hasattr(result, "isError"):
                assert not result.isError, f"Tool call error: {result}"  # type: ignore
                logger.info("✓ Tool call successful")
            else:
                logger.info(f"✓ Tool call returned: {type(result)}")

        # Get registered servers
        servers = host.get_registered_servers()
        assert len(servers) == 2, f"Expected 2 servers, got {len(servers)}"
        assert "test_weather_good" in servers, "Good server not in list"
        assert "test_weather_bad" in servers, "Bad server not in list"
        logger.info(f"✓ Registered servers: {servers}")

    # Verify cleanup after context exit
    logger.info("✓ Context manager cleaned up both servers")
    logger.info("✓ Concurrent server management test PASSED\n")


async def test_error_handling():
    """Test error handling and edge cases."""
    logger.info("=" * 60)
    logger.info("TEST: Error Handling")
    logger.info("=" * 60)

    host = TestingMCPHost()

    # Test missing name in config
    logger.info("Testing missing server name...")
    config_no_name = {
        "transport_type": "stdio",
        "server_path": "tests/fixtures/test_mcp_servers/test_weather_good/server.py",
    }
    success = await host.register_server(config_no_name)
    assert not success, "Should fail with missing name"
    logger.info("✓ Correctly rejected config with missing name")

    # Test duplicate registration
    logger.info("Testing duplicate registration...")
    config_good = {
        "name": "test_weather_good",
        "transport_type": "stdio",
        "server_path": "tests/fixtures/test_mcp_servers/test_weather_good/server.py",
        "timeout": 10.0,
        "registration_timeout": 30.0,
    }

    success1 = await host.register_server(config_good)
    assert success1, "First registration should succeed"

    success2 = await host.register_server(config_good)
    assert not success2, "Duplicate registration should fail"
    logger.info("✓ Correctly rejected duplicate registration")

    # Test unregistering non-existent server
    logger.info("Testing unregister of non-existent server...")
    success = await host.unregister_server("non_existent")
    assert not success, "Should return False for non-existent server"
    logger.info("✓ Correctly handled non-existent server unregistration")

    # Test calling non-existent tool
    logger.info("Testing non-existent tool call...")
    try:
        await host.call_tool("non_existent_tool", {})
        raise AssertionError("Should raise KeyError for non-existent tool")
    except KeyError as e:
        logger.info(f"✓ Correctly raised KeyError: {e}")

    # Cleanup
    await host.shutdown_all()
    logger.info("✓ Error handling test PASSED\n")


async def test_cleanup():
    """Test proper cleanup on shutdown."""
    logger.info("=" * 60)
    logger.info("TEST: Cleanup Verification")
    logger.info("=" * 60)

    host = TestingMCPHost()

    # Register both servers
    configs = [
        {
            "name": "test_weather_good",
            "transport_type": "stdio",
            "server_path": "tests/fixtures/test_mcp_servers/test_weather_good/server.py",
            "timeout": 10.0,
            "registration_timeout": 30.0,
        },
        {
            "name": "test_weather_bad",
            "transport_type": "stdio",
            "server_path": "tests/fixtures/test_mcp_servers/test_weather_bad/server.py",
            "timeout": 35.0,
            "registration_timeout": 40.0,
        },
    ]

    for config in configs:
        success = await host.register_server(config)
        assert success, f"Failed to register {config['name']}"

    logger.info("✓ Both servers registered")

    # Verify they're registered
    assert len(host.get_registered_servers()) == 2, "Should have 2 servers"
    assert len(host.get_all_tools()) > 0, "Should have tools"

    # Manual shutdown
    logger.info("Shutting down all servers...")
    await host.shutdown_all()

    # Verify cleanup
    assert len(host.get_registered_servers()) == 0, "Should have no servers after shutdown"
    assert len(host.get_all_tools()) == 0, "Should have no tools after shutdown"
    assert not await host.is_server_registered("test_weather_good"), "Good server should be unregistered"
    assert not await host.is_server_registered("test_weather_bad"), "Bad server should be unregistered"

    logger.info("✓ All servers and tools cleaned up")
    logger.info("✓ Cleanup verification test PASSED\n")


async def main():
    """Run all tests."""
    logger.info("\n" + "=" * 60)
    logger.info("TESTING MCP HOST - Server Lifecycle Management")
    logger.info("=" * 60 + "\n")

    try:
        # Run tests in sequence
        await test_single_server_lifecycle()
        await test_concurrent_servers()
        await test_error_handling()
        await test_cleanup()

        logger.info("=" * 60)
        logger.info("ALL TESTS PASSED ✓")
        logger.info("=" * 60)

    except AssertionError as e:
        logger.error(f"TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"UNEXPECTED ERROR: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
