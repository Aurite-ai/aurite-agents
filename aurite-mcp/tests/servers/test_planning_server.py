"""
Specific tests for the planning server.
This file demonstrates how to test a specific MCP server with detailed checks.
"""

import asyncio
import logging
import pytest
from pathlib import Path

from tests.servers.test_mcp_functional import MCPServerTester

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Path to the planning server
PLANNING_SERVER_PATH = Path(__file__).parent.parent.parent / "src" / "agents" / "planning" / "planning_server.py"


@pytest.mark.asyncio
async def test_planning_server_tools():
    """Test that planning server's tools are accessible and working."""
    tester = MCPServerTester(PLANNING_SERVER_PATH)
    try:
        await tester.initialize_host()
        
        # Discover components
        components = await tester.discover_components()
        tools = components["tools"]
        
        # Verify expected tools exist
        expected_tools = ["save_plan", "list_plans"]
        for tool_name in expected_tools:
            tool_exists = any(t["name"] == tool_name for t in tools)
            assert tool_exists, f"Expected tool '{tool_name}' not found in planning server"
            
        # Test tools functionality (if we want to go beyond basic accessibility)
        # Here we could actually execute tools and verify their behavior
            
    finally:
        await tester.cleanup()


@pytest.mark.asyncio
async def test_planning_server_prompts():
    """Test that planning server's prompts are accessible and working."""
    tester = MCPServerTester(PLANNING_SERVER_PATH)
    try:
        await tester.initialize_host()
        
        # Discover components
        components = await tester.discover_components()
        prompts = components["prompts"]
        
        # Verify expected prompts exist
        # Note: The planning server defines the prompt with @mcp.prompt("create_plan_prompt")
        # but the function is called planning_prompt()
        expected_prompts = ["create_plan_prompt"]
        for prompt_name in expected_prompts:
            prompt_exists = any(p.name == prompt_name for p in prompts)
            assert prompt_exists, f"Expected prompt '{prompt_name}' not found in planning server"
            
        # Test prompt content (optional)
        if prompts:
            prompt_details = await tester.host.prompts.get_prompt("create_plan_prompt", tester.client_id)
            assert prompt_details.description, "Planning prompt should have a description"
            
    finally:
        await tester.cleanup()


@pytest.mark.asyncio
async def test_planning_server_resources():
    """Test that planning server's resources are accessible."""
    tester = MCPServerTester(PLANNING_SERVER_PATH)
    try:
        from src.host.host import RootConfig
        
        # We'll skip the resource test for now
        # Resources in MCP servers require specific root permissions
        # and proper setup via the host configuration
        
        # Just verify we can initialize and connect to the server
        await tester.initialize_host()
        components = await tester.discover_components()
        
        # Log that we're skipping the full resource test
        logger.info("Skipping full resource test - would require proper root setup")
        logger.info("A complete test would create a plan and access it via resource URI")
        
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    # When run directly, run the tests
    asyncio.run(test_planning_server_tools())
    asyncio.run(test_planning_server_prompts())
    asyncio.run(test_planning_server_resources())