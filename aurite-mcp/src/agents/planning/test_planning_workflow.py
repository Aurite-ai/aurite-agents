"""
Test script for the planning workflow using the host's execute_prompt_with_tools.

This script demonstrates:
1. Setting up an MCPHost with a planning client
2. Initializing the planning workflow
3. Creating a plan using the workflow
4. Analyzing an existing plan
5. Listing available plans
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add parent directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.host.host import MCPHost, HostConfig, ClientConfig, RootConfig
from src.agents.planning.planning_workflow import PlanningWorkflow
from src.agents.base_workflow import BaseWorkflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class BasicPlanningWorkflow(BaseWorkflow):
    """A simplified version of the planning workflow for testing"""
    
    def __init__(self, tool_manager, host=None):
        super().__init__(tool_manager, name="basic_planning_workflow", host=host)
        self.description = "Basic planning workflow for testing"
        
    async def create_simple_plan(self, task, plan_name):
        """Create a simple plan without using complex models"""
        logger.info(f"Creating simple plan: {plan_name}")
        
        # Use tool_manager directly to save a plan
        result = await self.tool_manager.execute_tool(
            "save_plan",
            {
                "plan_name": plan_name,
                "plan_content": f"# Simple Plan for: {task}\n\nThis is a basic test plan.",
                "tags": ["test", "simple"]
            }
        )
        
        # Return the result
        return {
            "success": True,
            "plan_name": plan_name,
            "result": result
        }
        
    async def list_all_plans(self):
        """List all plans using the tool directly"""
        logger.info("Listing all plans")
        
        # Use tool_manager directly to list plans
        result = await self.tool_manager.execute_tool("list_plans", {})
        
        # Return the result
        return {
            "success": True,
            "result": result
        }


async def main():
    """Test the planning workflow with host execute_prompt_with_tools"""
    
    # Set environment variable for Anthropic API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.warning("ANTHROPIC_API_KEY environment variable not set!")
        logger.warning("Set it before running this test, or the prompt execution will fail.")
        return
    
    # Path to the server script
    server_path = Path(__file__).parent / "planning_server.py"
    
    # Create host configuration with planning client
    host_config = HostConfig(
        clients=[
            ClientConfig(
                client_id="planning",  # This must match the client_id in the workflow
                server_path=str(server_path),
                roots=[],
                capabilities=["tools", "prompts", "resources"],
            )
        ]
    )
    
    # Create and initialize the host
    logger.info("Initializing MCPHost...")
    host = MCPHost(config=host_config)
    await host.initialize()
    
    try:
        # Create and initialize a simple planning workflow
        logger.info("Creating basic planning workflow...")
        workflow = BasicPlanningWorkflow(
            tool_manager=host.tools, 
            host=host
        )
        
        # Create a simple plan
        logger.info("Creating a simple plan...")
        result = await workflow.create_simple_plan(
            task="Test the planning workflow", 
            plan_name="simple_test_plan"
        )
        
        # Print result
        logger.info(f"Plan creation result: {result['success']}")
        
        # List all plans
        logger.info("Listing all plans...")
        list_result = await workflow.list_all_plans()
        
        # Print formatted output
        result_text = host.tools.format_tool_result(list_result["result"])
        logger.info(f"Found plans: {result_text}")
        
        logger.info("Test completed successfully!")
        
    finally:
        # Shutdown the host
        logger.info("Shutting down host...")
        await host.shutdown()
        
    logger.info("All tests complete!")


if __name__ == "__main__":
    asyncio.run(main())