"""
Test script for host integration with prompts and tools
"""

import asyncio
import logging
import sys
from pathlib import Path

from src.host.host import MCPHost, HostConfig, ClientConfig

logging.basicConfig(
    level=logging.DEBUG, format="%(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_tools():
    """Test the weather and time tools."""
    # Get the absolute path to the server script
    current_dir = Path(__file__).parent.resolve()
    server_path = current_dir / "test_mcp_server.py"

    logger.info(f"Testing with server at: {server_path}")

    # Configure and initialize the host
    config = HostConfig(
        clients=[
            ClientConfig(
                client_id="test-client",
                server_path=server_path,
                roots=[],
                capabilities=["tools"],
                timeout=30.0,
            )
        ]
    )

    host = MCPHost(config)
    await host.initialize()

    try:
        # Test weather lookup
        logger.info("\nTesting weather lookup...")
        weather_result = await host.tools.execute_tool(
            "weather_lookup", {"location": "San Francisco", "units": "imperial"}
        )
        logger.info(f"Weather result: {weather_result[0].text}")

        # Test current time
        logger.info("\nTesting current time...")
        time_result = await host.tools.execute_tool(
            "current_time", {"timezone": "America/New_York"}
        )
        logger.info(f"Time result: {time_result[0].text}")

        return True

    except Exception as e:
        logger.error(f"Error in test: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        await host.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(test_tools())
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback

        traceback.print_exc()
