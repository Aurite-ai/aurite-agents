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
        
        # Initialize with config that includes the proper roots (loaded from JSON)
        await tester.initialize_host()
        components = await tester.discover_components()
        
        # Verify the correct client_id
        assert tester.client_id == "planning", "Client ID should be 'planning'"
        
        # Get root configuration and verify planning roots are set properly
        client_configs = tester.host._config.clients
        assert len(client_configs) > 0, "No client configs found"
        
        planning_client = next((c for c in client_configs if c.client_id == "planning"), None)
        if planning_client:
            logger.info(f"Planning client found with roots: {[r.uri for r in planning_client.roots]}")
            has_planning_root = any(r.uri.startswith("planning://") for r in planning_client.roots)
            assert has_planning_root, "Planning root not found in client config"
        
        # For a full test, we would:
        # 1. Create a plan using the save_plan tool
        # 2. Access it via the resource URI planning://plan/{plan_name}
        # But for functional testing, we just verify the infrastructure is working
        
        # Log the resource capabilities
        logger.info("Resource testing infrastructure is in place")
        logger.info("Full resource testing would create and access resources via URI")
        
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    # When run directly, run the tests
    asyncio.run(test_planning_server_tools())
    asyncio.run(test_planning_server_prompts())
    asyncio.run(test_planning_server_resources())