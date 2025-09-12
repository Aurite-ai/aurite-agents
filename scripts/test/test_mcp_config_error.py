#!/usr/bin/env python3
"""
Test script to verify that missing MCP server configurations are properly caught and reported.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from aurite.execution.aurite_engine import AuriteEngine
from aurite.execution.mcp_host.mcp_host import MCPHost
from aurite.lib.config.config_manager import ConfigManager
from aurite.utils.errors import ConfigurationError

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def test_missing_mcp_server():
    """Test that a missing MCP server configuration is properly caught."""

    # Initialize the framework components
    config_manager = ConfigManager()
    host = MCPHost()
    engine = AuriteEngine(config_manager=config_manager, host_instance=host)

    # Create a test agent config with a non-existent MCP server
    test_agent_config = {
        "name": "test_agent_with_missing_mcp",
        "type": "agent",
        "llm_config_id": "default",
        "mcp_servers": ["non_existent_server"],  # This server doesn't exist
        "system_prompt": "You are a test agent.",
    }

    # Register the test agent in memory
    config_manager.register_component_in_memory("agent", test_agent_config)

    # Create a test workflow that uses this agent
    test_workflow_config = {
        "name": "test_workflow",
        "type": "linear_workflow",
        "steps": ["test_agent_with_missing_mcp"],
    }

    # Register the test workflow in memory
    config_manager.register_component_in_memory("linear_workflow", test_workflow_config)

    logger.info("Testing missing MCP server configuration error handling...")

    try:
        # Try to run the workflow - this should fail with a clear error
        result = await engine.run_linear_workflow(workflow_name="test_workflow", initial_input="Test input")

        # Check if the error was properly caught
        if result.status == "failed" and result.error and "Configuration error" in result.error:
            logger.info("✅ SUCCESS: Configuration error was properly caught and reported!")
            logger.info(f"Error message: {result.error}")
            return True
        else:
            logger.error("❌ FAILURE: Error was not properly caught")
            logger.error(f"Result status: {result.status}")
            logger.error(f"Error message: {result.error}")
            return False

    except ConfigurationError as e:
        logger.info("✅ SUCCESS: ConfigurationError was raised as expected!")
        logger.info(f"Error message: {str(e)}")
        return True
    except Exception as e:
        logger.error(f"❌ FAILURE: Unexpected error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        return False


async def test_direct_agent_run():
    """Test that running an agent directly also properly reports the error."""

    # Initialize the framework components
    config_manager = ConfigManager()
    host = MCPHost()
    engine = AuriteEngine(config_manager=config_manager, host_instance=host)

    # Create a test agent config with a non-existent MCP server
    test_agent_config = {
        "name": "test_agent_direct",
        "type": "agent",
        "llm_config_id": "default",
        "mcp_servers": ["missing_planning_server"],  # This server doesn't exist
        "system_prompt": "You are a test agent.",
    }

    # Register the test agent in memory
    config_manager.register_component_in_memory("agent", test_agent_config)

    logger.info("\nTesting direct agent run with missing MCP server...")

    try:
        # Try to run the agent directly - this should fail with a clear error
        await engine.run_agent(agent_name="test_agent_direct", user_message="Test message")

        logger.error("❌ FAILURE: Agent run should have raised an error")
        return False

    except ConfigurationError as e:
        if "MCP Server 'missing_planning_server' required by agent 'test_agent_direct' not found" in str(e):
            logger.info("✅ SUCCESS: ConfigurationError was raised with the correct message!")
            logger.info(f"Error message: {str(e)}")
            return True
        else:
            logger.error("❌ FAILURE: ConfigurationError raised but with wrong message")
            logger.error(f"Error message: {str(e)}")
            return False
    except Exception as e:
        logger.error(f"❌ FAILURE: Unexpected error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        return False


async def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Testing MCP Server Configuration Error Handling")
    logger.info("=" * 60)

    # Run tests
    test1_passed = await test_missing_mcp_server()
    test2_passed = await test_direct_agent_run()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary:")
    logger.info("=" * 60)

    if test1_passed and test2_passed:
        logger.info("✅ All tests passed! The error handling fix is working correctly.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please review the error handling implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
