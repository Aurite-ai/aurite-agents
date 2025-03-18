"""
Planning workflow for creating and saving plans.

This module demonstrates:
1. Using the host's execute_prompt_with_tools method for plan creation
2. Saving plans with the planning server's tools
3. A workflow step that uses prompt-based execution
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import logging
from pydantic import Field

from ...host.resources.tools import ToolManager
from ..base_workflow import BaseWorkflow, WorkflowStep
from ..base_models import AgentContext, AgentData, StepStatus, StepResult

logger = logging.getLogger(__name__)


# Define a Pydantic model for our workflow data
class PlanningContext(AgentData):
    """Data model for planning workflow context"""

    task: str = Field(..., description="Task to create a plan for")
    timeframe: Optional[str] = Field(None, description="Timeframe for the plan")
    resources: Optional[List[str]] = Field(None, description="Available resources")
    plan_name: str = Field(..., description="Name for the plan (used for saving)")
    
    # Fields that will be populated during workflow execution
    plan_content: Optional[str] = None
    plan_path: Optional[str] = None
    save_result: Optional[Dict[str, Any]] = None


@dataclass
class PlanCreationStep(WorkflowStep):
    """Step to create a plan using prompt-based execution"""

    def __init__(self):
        super().__init__(
            name="create_plan",
            description="Create a plan using AI prompt",
            required_inputs={"task", "plan_name"},
            provided_outputs={"plan_content"},
            
            # Configure prompt-based execution
            prompt_name="planning_prompt",
            client_id="planning",  # This should match the client_id in your host config
            user_message_template=(
                "Please create a detailed plan for the following task: {task}. "
                "I need a comprehensive, well-structured plan that I can execute."
            ),
            # The planning server's save_plan tool will be available here
            tool_names=["save_plan"],
        )

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute using prompt-based execution"""
        # Extract inputs from context
        task = context.get("task")
        plan_name = context.get("plan_name")
        timeframe = context.get("timeframe")
        resources = context.get("resources")
        
        # Prepare custom prompt arguments if needed
        prompt_args = {
            "task": task,
        }
        
        # Add optional arguments if provided
        if timeframe:
            prompt_args["timeframe"] = timeframe
        if resources:
            prompt_args["resources"] = resources
            
        # Override the default prompt arguments
        self.prompt_arguments = prompt_args
        
        # Call the utility method that handles prompt-based execution
        prompt_result = await self.execute_with_prompt(context)
        
        # Extract the plan content from the response
        final_response = prompt_result.get("final_response", {})
        
        # Extract the plan text from the final response
        if final_response and hasattr(final_response, "content"):
            # Extract text content from content blocks
            plan_text = ""
            for block in final_response.content:
                if hasattr(block, "text"):
                    plan_text += block.text
                elif isinstance(block, dict) and "text" in block:
                    plan_text += block["text"]
            
            # If we couldn't extract text from content blocks, use string representation
            if not plan_text:
                plan_text = str(final_response)
        else:
            # Fallback if we can't extract from final_response
            plan_text = "Error: Could not generate plan using prompt-based execution"
        
        return {
            "plan_content": plan_text,
            "prompt_execution_details": prompt_result
        }


@dataclass
class PlanSaveStep(WorkflowStep):
    """Step to save a plan to disk"""

    def __init__(self):
        super().__init__(
            name="save_plan",
            description="Save the generated plan to disk",
            required_inputs={"plan_name", "plan_content"},
            provided_outputs={"save_result", "plan_path"},
            required_tools={"save_plan"},
        )

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute the plan saving step"""
        # Extract inputs
        plan_name = context.get("plan_name")
        plan_content = context.get("plan_content")
        resources = context.get("resources", [])
        
        # Use the save_plan tool to save the plan
        save_result = await context.tool_manager.execute_tool(
            "save_plan",
            {
                "plan_name": plan_name,
                "plan_content": plan_content,
                "tags": resources if resources else None
            },
        )
        
        # Return the results
        return {
            "save_result": save_result,
            "plan_path": save_result.get("path") if save_result.get("success") else None
        }


class PlanningWorkflow(BaseWorkflow):
    """
    Workflow for creating and saving plans.
    
    This workflow demonstrates:
    1. Using prompt-based execution for plan creation
    2. Saving plans using direct tool execution
    """
    
    def __init__(self, tool_manager: ToolManager, name: str = "planning_workflow", host=None):
        """Initialize the planning workflow"""
        super().__init__(tool_manager, name=name, host=host)
        
        # Set description for documentation
        self.description = "Workflow for creating and saving detailed plans"
        
        # Add steps
        self.add_step(PlanCreationStep())
        self.add_step(PlanSaveStep())
        
    async def create_plan(
        self,
        task: str,
        plan_name: str,
        timeframe: Optional[str] = None,
        resources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Convenience method to execute the workflow with specific parameters.
        
        Args:
            task: The task to create a plan for
            plan_name: Name to save the plan as
            timeframe: Optional timeframe for the plan
            resources: Optional list of available resources
            
        Returns:
            Dictionary with workflow results
        """
        # Create input data
        input_data = {
            "task": task,
            "plan_name": plan_name,
        }
        
        # Add optional parameters if provided
        if timeframe:
            input_data["timeframe"] = timeframe
        if resources:
            input_data["resources"] = resources
            
        # Execute the workflow
        result_context = await self.execute(input_data)
        
        # Return the summarized results
        return result_context.summarize_results()