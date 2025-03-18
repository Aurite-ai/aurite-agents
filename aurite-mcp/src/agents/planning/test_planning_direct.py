"""
Direct test script for the planning MCP server.

This script demonstrates:
1. Connecting to the planning server directly
2. Getting the planning prompt
3. Using the save_plan tool
4. Using the list_plans tool
5. Accessing plan resources
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from contextlib import AsyncExitStack

# Add parent directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PlanningClientTest:
    def __init__(self):
        # Initialize session and client objects
        self.session = None
        self.exit_stack = AsyncExitStack()
    
    async def connect_to_server(self, server_script_path: str):
        """Connect to the planning MCP server
        
        Args:
            server_script_path: Path to the server script
        """
        # Setup connection parameters
        server_params = StdioServerParameters(
            command="python",
            args=[str(server_script_path)],
            env=None
        )
        
        # Connect to the server
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )
        
        # Initialize the client
        await self.session.initialize()
        
        # List available tools
        tools_result = await self.session.list_tools()
        logger.info(f"Available tools: {[t.name for t in tools_result.tools]}")
        
        # List available prompts
        prompts_result = await self.session.list_prompts()
        logger.info(f"Available prompts: {[p.name for p in prompts_result.prompts]}")
    
    async def run_tests(self):
        """Run tests against the planning server"""
        logger.info("Testing planning_prompt...")
        prompt_result = await self.session.get_prompt(
            "planning_prompt",
            {
                "task": "Build a web application to manage tasks",
                "timeframe": "2 weeks",
                "resources": "Frontend developer, Backend developer, UI/UX designer"
            }
        )
        prompt_content = str(prompt_result)
        logger.info(f"Planning prompt received (first 100 chars): {prompt_content[:100]}...")
        
        logger.info("Testing save_plan...")
        save_result = await self.session.call_tool(
            "save_plan",
            {
                "plan_name": "test_direct_plan",
                "plan_content": "# Test Direct Plan\n\nThis is a test plan created directly via the MCP client.",
                "tags": ["test", "direct"]
            }
        )
        logger.info(f"Save plan result: {save_result}")
        
        logger.info("Testing list_plans...")
        list_result = await self.session.call_tool(
            "list_plans",
            {}
        )
        logger.info(f"List plans result: {list_result}")
        
        logger.info("Testing plan resource...")
        resource_result = await self.session.read_resource("planning://plan/test_direct_plan")
        resource_content = str(resource_result)
        logger.info(f"Plan resource content (first 100 chars): {resource_content[:100]}...")
        
        logger.info("All direct tests completed successfully!")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    """Main test function"""
    # Path to the server script
    server_path = Path(__file__).parent / "planning_server.py"
    
    logger.info(f"Testing planning server directly: {server_path}")
    
    client = PlanningClientTest()
    try:
        await client.connect_to_server(server_path)
        await client.run_tests()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())