#!/usr/bin/env python3
"""
This script tests the PlanningWorkflow with a real use case:
Creating a comprehensive learning plan for Python programming.

This demonstrates:
1. Using the host's execute_prompt_with_tools method for plan creation
2. Saving plans with the planning server's tools
3. Working with real-world task descriptions
"""

import asyncio
import logging
import os
import time
from pathlib import Path

from src.host.host import MCPHost, HostConfig, ClientConfig
from src.agents.planning.planning_workflow import PlanningWorkflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_planning_workflow():
    """Create a plan for learning Python using the PlanningWorkflow"""
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY environment variable not set!")
        return

    # Create and initialize a host with the planning server
    server_path = (
        Path(__file__).parent.parent
        / "src"
        / "agents"
        / "planning"
        / "planning_server.py"
    )

    # Create host configuration with planning client
    host_config = HostConfig(
        clients=[
            ClientConfig(
                client_id="planning",
                server_path=str(server_path),
                roots=[],
                capabilities=["tools", "prompts", "resources"],
            )
        ]
    )

    # Create and initialize the host
    logger.info("Initializing MCPHost for planning workflow")
    host = MCPHost(config=host_config)
    await host.initialize()

    try:
        # Create a unique plan name based on timestamp
        timestamp = int(time.time())
        plan_name = f"python_learning_plan_{timestamp}"

        # Register the workflow
        workflow_name = await host.register_workflow(
            PlanningWorkflow, name="python_learning_workflow"
        )

        # Create the input data for learning Python
        input_data = {
            "task": "Create a comprehensive learning plan for mastering Python programming, "
                   "suitable for a beginner with some basic programming knowledge.",
            "plan_name": plan_name,
            "resources": [
                "Online courses", 
                "Books", 
                "Practice exercises", 
                "Coding projects", 
                "Community forums"
            ],
            "timeframe": "3 months",
        }

        # Execute the workflow
        logger.info(f"Executing planning workflow for Python learning")
        result = await host.workflows.execute_workflow(
            workflow_name=workflow_name,
            input_data=input_data
        )

        # Check result
        if result:
            logger.info(f"Plan created successfully: {plan_name}")
            logger.info(f"Plan path: {result.get('plan_path')}")
            
            # Print the plan content
            logger.info("Python learning plan content:")
            logger.info(result.get("plan_content"))
            
            return result.get("plan_content")
        else:
            logger.error("Failed to create Python learning plan")
            return None

    finally:
        # Clean up
        logger.info("Shutting down host")
        await host.shutdown()


if __name__ == "__main__":
    # Run the async planning workflow
    asyncio.run(run_planning_workflow())