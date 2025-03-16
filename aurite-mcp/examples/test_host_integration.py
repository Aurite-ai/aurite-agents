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


async def test_tools_and_prompts():
    """Test the weather/time tools and prompts."""
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
                capabilities=["tools", "prompts"],  # Added prompts capability
                timeout=30.0,
            )
        ]
    )

    host = MCPHost(config)
    await host.initialize()

    try:
        # Test tool execution
        logger.info("\n=== Testing Tools ===")

        logger.info("\nTesting weather lookup...")
        weather_result = await host.tools.execute_tool(
            "weather_lookup", {"location": "San Francisco", "units": "imperial"}
        )
        logger.info(f"Weather result: {weather_result[0].text}")

        logger.info("\nTesting current time...")
        time_result = await host.tools.execute_tool(
            "current_time", {"timezone": "America/New_York"}
        )
        logger.info(f"Time result: {time_result[0].text}")

        # Test prompt functionality
        logger.info("\n=== Testing Prompts ===")

        # Test getting available prompts
        prompts = await host.prompts.list_prompts("test-client")
        logger.info(f"\nAvailable prompts: {[p.name for p in prompts]}")

        # Test getting a specific prompt
        logger.info("\nTesting get_prompt...")
        prompt = await host.prompts.get_prompt("weather_assistant", "test-client")
        if prompt:
            logger.info(f"Found prompt: {prompt.name}")
            logger.info(f"Description: {prompt.description}")
            logger.info("Arguments:")
            for arg in prompt.arguments:
                logger.info(
                    f"  - {arg.name}: {arg.description} (required: {arg.required})"
                )

        # Test preparing a prompt with tools
        logger.info("\nTesting prepare_prompt_with_tools...")
        prompt_data = await host.prepare_prompt_with_tools(
            prompt_name="weather_assistant",
            prompt_arguments={"user_name": "Tester", "preferred_units": "imperial"},
            client_id="test-client",
            tool_names=["weather_lookup", "current_time"],
        )

        logger.info("Prompt preparation successful!")
        logger.info(f"System prompt: {prompt_data['system']}")
        logger.info(f"Number of tools: {len(prompt_data['tools'])}")
        for i, tool in enumerate(prompt_data["tools"]):
            logger.info(f"Tool {i+1}: {tool['name']} - {tool['description']}")

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
        asyncio.run(test_tools_and_prompts())
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback

        traceback.print_exc()
