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

        # Custom prompt with explicit formatting requirements
        python_message_template = (
            "You are creating a Python learning plan. EXTREMELY IMPORTANT:\n\n"
            "1. Output ONLY the plain markdown learning plan\n"
            "2. Do NOT include ANY text about 'I've created a plan' or 'Plan saved successfully'\n"
            "3. Do NOT explain what you did or will do\n"
            "4. Start your response with '# Python Learning Plan'\n\n"
            "Create a 3-month Python learning plan named '{plan_name}' with these elements:\n"
            "1. Week-by-week curriculum breakdown\n"
            "2. Python libraries to learn (in order)\n"
            "3. Coding projects\n"
            "4. Resources for each topic\n"
            "5. Progress metrics\n\n"
            "Format as markdown with headings. Start with '# Python Learning Plan' and end with metrics. "
            "DO NOT include any comments about saving the plan or what you've created."
        )

        # Create a unique plan name based on timestamp
        timestamp = int(time.time())
        plan_name = f"python_learning_plan_{timestamp}"
        
        # We no longer need to modify the workflow directly
        # Instead, we'll pass the custom prompt template in the input data
        
        # There are two approaches we can take:
        # 1. Use the server's named prompt with basic parameters
        # 2. Continue using our custom prompt template for more control
        
        # Let's support both methods via a flag
        use_server_prompt = False  # Set to True to use the server's prompt, False to use custom
        
        # Configure step timeout to prevent hanging
        if hasattr(workflow, "steps") and len(workflow.steps) > 0:
            # Add higher timeouts to prevent retry issues
            for step in workflow.steps:
                # Increase timeout for save step, which seems to have issues
                if step.name == "save_plan":
                    step.timeout = 5.0  # Short timeout for save plan to fail fast
                    step.max_retries = 0  # No retries for save plan - if it fails, just continue
                else:
                    # Normal settings for other steps
                    step.timeout = 120.0  # 2 minutes timeout
                    step.max_retries = 1  # Only retry once
                
                # Log config
                logger.info(f"Configured step {step.name} with timeout={step.timeout}s, max_retries={step.max_retries}")
        
        # Prepare input data as a dictionary
        input_data = {
            "task": "Create a comprehensive learning plan for mastering Python programming, "
                   "suitable for a beginner with some basic programming knowledge.",
            "plan_name": plan_name, 
            "timeframe": "3 months",
            "resources": ["Online courses", "Books", "Practice exercises", "Coding projects", "Community forums"],
        }
        
        # Add the custom template only if we're not using the server prompt
        if not use_server_prompt:
            input_data["custom_prompt_template"] = python_message_template
            logger.info("Using custom Python learning plan prompt via input data")
        else:
            logger.info("Using server's create_plan_prompt")

        # Execute the workflow
        logger.info(f"Executing planning workflow for Python learning")
        result = await host.workflows.execute_workflow(
            workflow_name=workflow_name, input_data=input_data
        )

        # Check result
        if result:
            logger.info(f"Plan created successfully: {plan_name}")
            
            # First try to get the plan path
            plan_path = result.get('plan_path')
            if not plan_path:
                # Try a direct path
                plan_path = f"src/agents/planning/plans/{plan_name}.txt"
            logger.info(f"Plan path: {plan_path}")
            
            # Try to get plan content first from the result
            plan_content = result.get('plan_content')
            
            # If we don't have content but have a path, try to read the file
            if not plan_content and plan_path:
                try:
                    with open(plan_path, 'r') as f:
                        plan_content = f.read()
                        logger.info(f"Read plan from file: {len(plan_content)} characters")
                except Exception as e:
                    logger.error(f"Error reading plan file: {e}")
            
            # Print the plan content
            if plan_content:
                logger.info("Python learning plan content:")
                logger.info(plan_content)
                return plan_content
            else:
                logger.warning("Plan was created but content couldn't be retrieved")
                return None
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
