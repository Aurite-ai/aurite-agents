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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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
                capabilities=["tools", "prompts", "resources"],  # Added resources capability
            )
        ]
    )
    
    # Create and initialize the host
    logger.info("Initializing MCPHost...")
    host = MCPHost(config=host_config)
    await host.initialize()
    
    try:
        # Create and initialize the planning workflow
        logger.info("Creating planning workflow...")
        workflow = PlanningWorkflow(
            tool_manager=host.tools, 
            host=host  # Pass the host for prompt-based execution
        )
        await workflow.initialize()
        
        # Register the workflow with the host
        workflow_name = await host.register_workflow(PlanningWorkflow)
        logger.info(f"Registered workflow: {workflow_name}")
        
        # Execute the workflow to create a plan
        logger.info("Creating a new plan...")
        result = await host.execute_workflow(
            workflow_name=workflow_name,
            input_data={
                "task": "Design and implement a note-taking application",
                "plan_name": "note_app_project",
                "timeframe": "1 month",
                "resources": ["Frontend developer", "Backend developer", "UI/UX designer", "QA engineer"],
            }
        )
        
        # Print results
        logger.info("Plan creation complete!")
        summary = result.summarize_results()
        
        logger.info(f"Success: {summary['success']}")
        logger.info(f"Steps completed: {summary['steps_completed']}")
        
        # Get the plan content
        plan_content = result.get("plan_content")
        plan_path = result.get("plan_path")
        
        logger.info(f"Plan saved to: {plan_path}")
        
        # Print a portion of the plan content
        if plan_content:
            logger.info("Plan content (first 300 characters):")
            print(plan_content[:300] + "...\n")
            
        # Test plan analysis
        logger.info("Analyzing the created plan...")
        analysis_result = await workflow.analyze_plan("note_app_project")
        
        logger.info(f"Analysis success: {analysis_result['success']}")
        
        # Print a portion of the analysis
        if "analysis_report" in analysis_result["data"]:
            analysis_report = analysis_result["data"]["analysis_report"]
            logger.info("Analysis report (first 300 characters):")
            print(analysis_report[:300] + "...\n")
        
        # Test listing plans
        logger.info("Listing all plans...")
        list_result = await workflow.list_plans()
        
        logger.info(f"Listing success: {list_result['success']}")
        
        # Print the list of plans
        if "plans_list" in list_result["data"]:
            plans_list = list_result["data"]["plans_list"]
            logger.info(f"Found {plans_list.get('count', 0)} plans:")
            for plan in plans_list.get("plans", []):
                logger.info(f"- {plan.get('name')} (tags: {', '.join(plan.get('tags', []))})")
        
        # Test filtered listing
        if "resources" in result.get_data_dict():
            resources = result.get("resources")
            if resources and len(resources) > 0:
                # Use the first resource as a filter tag
                filter_tag = resources[0]
                logger.info(f"Listing plans filtered by tag '{filter_tag}'...")
                filtered_result = await workflow.list_plans(filter_tag=filter_tag)
                
                if "plans_list" in filtered_result["data"]:
                    filtered_plans = filtered_result["data"]["plans_list"]
                    logger.info(f"Found {filtered_plans.get('count', 0)} plans with tag '{filter_tag}'")
        
    finally:
        # Shutdown the host
        logger.info("Shutting down host...")
        await host.shutdown()
        
    logger.info("All tests complete!")


if __name__ == "__main__":
    asyncio.run(main())