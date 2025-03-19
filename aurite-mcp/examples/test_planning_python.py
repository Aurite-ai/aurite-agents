#!/usr/bin/env python3
"""
This script tests the simplified PlanningWorkflow with a Python learning plan.

This demonstrates:
1. Using the host's execute_prompt_with_tools method for both plan creation and saving
2. Working with a real-world task (Python learning plan)
3. Using workflow configuration from aurite_workflows.json
"""

import asyncio
import logging
import os
import time
import json
from pathlib import Path

from src.host.host import MCPHost
from src.host.config import HostConfig, ClientConfig, RootConfig
from src.agents.planning.planning_workflow import PlanningWorkflow

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

    # Load workflow configuration
    config_path = Path(__file__).parents[1] / "config/workflows/aurite_workflows.json"
    try:
        with open(config_path) as f:
            workflow_configs = json.load(f)

        # Get planning workflow config
        planning_config = next(
            (
                w["config"]
                for w in workflow_configs["workflows"]
                if w["name"] == "planning"
            ),
            None,
        )
        if not planning_config:
            logger.error("Planning workflow configuration not found")
            return
    except Exception as e:
        logger.error(f"Error loading workflow configuration: {e}")
        return

    # Create and initialize the host with minimal config
    logger.info("Initializing host for planning workflow")
    host = MCPHost(config=HostConfig(clients=[]))
    await host.initialize()

    try:
        # Register the workflow with its configuration
        workflow_name = await host.register_workflow(
            PlanningWorkflow,
            name="python_learning_workflow",
            workflow_config=planning_config,
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
