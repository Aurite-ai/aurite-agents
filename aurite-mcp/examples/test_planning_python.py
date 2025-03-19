#!/usr/bin/env python3
"""
This script tests the simplified PlanningWorkflow with a Python learning plan.

This demonstrates:
1. Using the host's execute_prompt_with_tools method for both plan creation and saving
2. Working with a real-world task (Python learning plan)
"""

import asyncio
import logging
import os
import time
from pathlib import Path

from src.host.host import MCPHost, HostConfig, ClientConfig
from src.agents.planning.planning_workflow import PlanningWorkflow
from src.host.foundation import RootConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_planning_workflow():
    """Create a plan for learning Python using the simplified PlanningWorkflow"""
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY environment variable not set!")
        return

    # Path to the planning server
    server_path = (
        Path(__file__).parent.parent
        / "src"
        / "agents"
        / "planning"
        / "planning_server.py"
    )

    # Create host configuration
    host_config = HostConfig(
        clients=[
            ClientConfig(
                client_id="planning",
                server_path=str(server_path),
                roots=[
                    # Register planning:// root URI
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
    logger.info("Initializing host for planning workflow")
    host = MCPHost(config=host_config)
    await host.initialize()

    try:
        # Register the workflow
        workflow_name = await host.register_workflow(
            PlanningWorkflow, name="python_learning_workflow"
        )

        # Create a custom prompt template focused on Python learning
        python_prompt_template = (
            "You are creating a Python learning plan. IMPORTANT INSTRUCTIONS:\n\n"
            "1. Output ONLY the plain markdown learning plan\n"
            "2. DO NOT include any meta-commentary\n"
            "3. Start directly with '# Python Learning Plan'\n\n"
            "Create a 3-month Python learning plan with these sections:\n"
            "1. Week-by-week curriculum\n"
            "2. Python libraries to learn\n"
            "3. Coding projects\n"
            "4. Learning resources\n"
            "5. Progress metrics\n\n"
            "The task is: {task}"
            "{timeframe_text}{resources_text}"
        )

        # Create a unique plan name based on timestamp
        timestamp = int(time.time())
        plan_name = f"python_learning_plan_{timestamp}"

        # Input data for the workflow
        input_data = {
            "task": "Create a comprehensive Python learning plan for a beginner with some programming knowledge",
            "plan_name": plan_name,
            "timeframe": "3 months",
            "resources": [
                "Books",
                "Online courses",
                "Practice exercises",
                "Coding projects",
            ],
            "custom_prompt_template": python_prompt_template,
        }

        # Execute the workflow
        logger.info(f"Creating Python learning plan: {plan_name}")
        result_context = await host.execute_workflow(
            workflow_name=workflow_name, input_data=input_data
        )

        # Use get_data_dict() instead of summarize_results() to avoid serialization issues
        result_data = result_context.get_data_dict()

        # Check the result
        if "plan_content" in result_data:
            logger.info("Python learning plan created successfully")

            # Get plan path from the result
            plan_path = result_data.get("plan_path", "Unknown")
            logger.info(f"Plan path: {plan_path}")

            # Get the content
            content = result_data.get("plan_content", "")

            # Print the first 200 characters as a preview
            preview = content[:200] + "..." if len(content) > 200 else content
            logger.info(f"Plan preview: {preview}")

            # Try to read the file to verify it was saved
            try:
                with open(plan_path, "r") as f:
                    file_content = f.read()
                    logger.info(f"File size: {len(file_content)} characters")
            except Exception as e:
                logger.warning(f"Could not read plan file: {e}")

            return {
                "success": True,
                "plan_name": plan_name,
                "plan_path": plan_path,
                "content_length": len(content),
            }
        else:
            logger.error("Failed to create Python learning plan")
            logger.error(f"Available keys in result: {list(result_data.keys())}")
            return {"success": False}

    finally:
        # Clean up
        logger.info("Shutting down host")
        await host.shutdown()


if __name__ == "__main__":
    # Run the workflow
    asyncio.run(run_planning_workflow())
