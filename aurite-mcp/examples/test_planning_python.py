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
    from src.host.foundation import RootConfig

    # Create host configuration with planning client and proper roots
    host_config = HostConfig(
        clients=[
            ClientConfig(
                client_id="planning",
                server_path=str(server_path),
                roots=[
                    # Register planning:// root URI for the planning server
                    RootConfig(
                        uri="planning://",
                        name="Planning Root",
                        capabilities=["read", "write"],
                    ),
                    # Register file:// root URI for plan storage
                    RootConfig(
                        uri="file://plans/",
                        name="Plan Storage",
                        capabilities=["read", "write"],
                    ),
                ],
                capabilities=["tools", "prompts", "resources", "roots"],
            )
        ]
    )

    # Create and initialize the host
    logger.info("Initializing MCPHost for planning workflow")
    host = MCPHost(config=host_config)
    await host.initialize()

    # For this example, explicitly tell the logging system to show debug messages
    logging.getLogger("src.agents.planning.planning_workflow").setLevel(logging.DEBUG)

    try:
        # Register the workflow
        workflow_name = await host.register_workflow(
            PlanningWorkflow, name="python_learning_workflow"
        )

        # Get the workflow instance to modify its configuration
        workflow = host.workflows.get_workflow("python_learning_workflow")

        # Custom user message template for Python learning
        python_message_template = (
            "I need a detailed plan for learning Python programming. "
            "For this specific Python learning plan, please include:\n"
            "1. Week-by-week curriculum breakdown\n"
            "2. Specific Python libraries/frameworks to learn and in what order\n"
            "3. Concrete coding projects with increasing complexity\n"
            "4. Recommended resources for each topic (books, courses, tutorials)\n"
            "5. How to measure progress and validate skills\n\n"
            "The plan should be named '{plan_name}' and should be completed in {timeframe}. "
            "Resources available: {resources_text}.\n\n"
            "VERY IMPORTANT: Your response MUST ONLY contain the plan itself as a structured markdown document. "
            "DO NOT include any introduction, explanation, summary, or conclusion about the plan. "
            "DO NOT talk about what you're going to do or what you've done. "
            "Start directly with the plan title/heading and end with the last content section. "
            "Format with clear headings, bullet points, and a logical progression."
        )

        # Create a unique plan name based on timestamp
        timestamp = int(time.time())
        plan_name = f"python_learning_plan_{timestamp}"
        
        # We no longer need to modify the workflow directly
        # Instead, we'll pass the custom prompt template in the input data
        
        # Prepare input data as a dictionary - including the required plan_name
        input_data = {
            "task": "Create a comprehensive learning plan for mastering Python programming, "
                   "suitable for a beginner with some basic programming knowledge.",
            "plan_name": plan_name,  # This is the REQUIRED field that was missing
            "timeframe": "3 months",
            "resources": ["Online courses", "Books", "Practice exercises", "Coding projects", "Community forums"],
            # Pass the custom prompt template directly in the input data
            "custom_prompt_template": python_message_template,
        }
        
        logger.info("Using custom Python learning plan prompt via input data")

        # Execute the workflow
        logger.info(f"Executing planning workflow for Python learning")
        result = await host.workflows.execute_workflow(
            workflow_name=workflow_name, input_data=input_data
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
