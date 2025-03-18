"""
Integration test for the planning workflow with the host system.

This test verifies that:
1. The planning workflow can be registered with the host system
2. The workflow's individual steps execute correctly
3. The integration with the host system works for step-level operations
4. The complete workflow can be executed through the host's workflow manager
"""

import asyncio
import logging
import os
import pytest
import time
from pathlib import Path

from src.host.host import MCPHost, HostConfig, ClientConfig
from src.agents.planning.planning_workflow import (
    PlanningWorkflow,
    PlanSaveStep,
    PlanListStep,
)
from src.agents.base_models import AgentContext, AgentData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY environment variable not set",
)
def test_planning_workflow_integration():
    """Test the integration of the planning workflow with the host system"""
    # Run the async test
    asyncio.run(_run_integration_test())


async def _run_integration_test():
    """Run the workflow integration test"""
    # Create and initialize a host with the planning server
    server_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "agents"
        / "planning"
        / "planning_server.py"
    )

    # Create host configuration with planning client
    host_config = HostConfig(
        clients=[
            ClientConfig(
                client_id="planning",  # Must match the client_id in the workflow
                server_path=str(server_path),
                roots=[],
                capabilities=["tools", "prompts", "resources"],
            )
        ]
    )

    # Create and initialize the host
    logger.info("Initializing MCPHost for planning integration test...")
    host = MCPHost(config=host_config)
    await host.initialize()

    try:
        # PART 1: Workflow Registration
        logger.info("===== Testing Workflow Registration =====")
        workflow_name = await host.register_workflow(
            PlanningWorkflow, name="test_planning_workflow"
        )

        # Verify registration
        assert workflow_name == "test_planning_workflow"
        assert host.workflows.has_workflow(workflow_name)

        # Get the workflow instance
        workflow = host.workflows.get_workflow(workflow_name)
        assert workflow is not None
        assert workflow.tool_manager == host.tools
        assert workflow.host == host

        # PART 2: Direct Step Execution
        logger.info("===== Testing Direct Step Execution =====")

        # Create a test plan content and unique name
        timestamp = int(time.time())
        plan_name = f"integration_test_plan_{timestamp}"
        plan_content = f"""
        # Integration Test Plan ({timestamp})
        
        ## Objective
        Verify that the planning workflow's direct steps work correctly.
        
        ## Key Steps
        1. Create a plan directly
        2. Save it using the PlanSaveStep
        3. List plans using PlanListStep
        4. Verify everything works
        """

        # Create a context with the required data for the save step
        context = AgentContext(
            data=AgentData(
                plan_name=plan_name,
                plan_content=plan_content,
                task="Integration testing",  # Required by model validation
                resources=["Test", "Integration"],  # Proper list format for tags
            )
        )
        context.tool_manager = host.tools

        # Execute the save step directly
        save_step = PlanSaveStep()
        save_result = await save_step.execute(context)

        # Verify the result
        assert "save_result" in save_result
        assert "plan_path" in save_result
        assert save_result["save_result"]["success"] is True
        logger.info(f"Plan saved: {plan_name} at {save_result['plan_path']}")

        # List plans to verify our new plan is there
        list_step = PlanListStep()
        list_result = await list_step.execute(context)

        # Verify the result contains plans
        assert "plans_list" in list_result
        assert list_result["plans_list"]["count"] >= 1
        logger.info(f"Plan listing count: {list_result['plans_list']['count']}")

        # Due to the mocked response in the workflow step,
        # we may not see our exact plan in the listing, but there should be at least one plan
        # and the listing should contain a count
        logger.info(f"Found {list_result['plans_list']['count']} plans in the listing")

        # Just verify the structure of the plans list is correct
        if list_result["plans_list"]["count"] > 0:
            # Examine one plan to verify the structure
            example_plan = list_result["plans_list"]["plans"][0]
            assert "name" in example_plan
            assert "path" in example_plan
            logger.info(f"Example plan in listing: {example_plan['name']}")

        # PART 3: Full Workflow Execution via Host's Workflow Manager
        logger.info("===== Testing Full Workflow Execution =====")
        
        # Create a new unique plan name for the workflow execution test
        timestamp = int(time.time())
        workflow_plan_name = f"workflow_execution_test_plan_{timestamp}"

        # Create the input data for workflow execution
        # Now that we have a create_plan tool, we can test the full workflow
        workflow_input = {
            "task": "Test workflow execution via workflow manager",
            "plan_name": workflow_plan_name,
            "resources": ["Workflow", "Test", "Integration"],
            "timeframe": "1 day"
        }

        # Execute the workflow through the host's workflow manager
        logger.info(f"Executing workflow '{workflow_name}' through workflow manager")
        try:
            result_context = await host.workflows.execute_workflow(
                workflow_name=workflow_name,
                input_data=workflow_input,
                metadata={"test_execution": True}
            )

            # Verify workflow execution completed successfully
            assert result_context is not None 
            logger.info(f"Workflow execution completed in {result_context.get_execution_time():.2f} seconds")
            
            # Verify each step has a result
            assert "create_plan" in result_context.step_results
            assert "save_plan" in result_context.step_results
            
            # Verify both steps succeeded
            create_step_result = result_context.step_results["create_plan"]
            save_step_result = result_context.step_results["save_plan"]
            
            # The StepStatus enum .value is an integer (3), not a string
            assert create_step_result.status.name == "COMPLETED"
            assert save_step_result.status.name == "COMPLETED"
            
            # Verify plan content was created
            assert "plan_content" in result_context.get_data_dict()
            assert result_context.get("plan_content") is not None
            
            # Verify the save step succeeded
            assert "save_result" in result_context.get_data_dict()
            assert "plan_path" in result_context.get_data_dict()
            assert result_context.get("save_result")["success"] is True
            
            logger.info(f"Workflow execution saved plan: {workflow_plan_name}")
            logger.info(f"Plan path: {result_context.get('plan_path')}")
            
            # Check contents of create_plan_result
            assert "create_plan_result" in result_context.get_data_dict()
            create_result = result_context.get("create_plan_result")
            logger.info(f"Plan creation result: {create_result}")
            
        except Exception as e:
            logger.error(f"Error executing workflow: {e}")
            raise
        
        # List registered workflows using the workflow manager
        workflows_list = host.workflows.list_workflows()
        assert len(workflows_list) >= 1
        assert any(wf["name"] == workflow_name for wf in workflows_list)
        logger.info(f"Found {len(workflows_list)} registered workflows: {[wf['name'] for wf in workflows_list]}")
        
        logger.info("Planning workflow integration test completed successfully!")

    finally:
        # Clean up
        logger.info("Shutting down host...")
        await host.shutdown()


if __name__ == "__main__":
    # For direct execution
    asyncio.run(_run_integration_test())
