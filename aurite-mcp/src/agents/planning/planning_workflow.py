"""
Simplified planning workflow for creating and saving plans.

This module implements a streamlined approach to plan creation with a single-step workflow
that uses the host's execute_prompt_with_tools method to create plans and save them
using the MCP server's tools.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..base_workflow import BaseWorkflow, WorkflowStep
from ..base_models import AgentContext
from ...host.resources.tools import ToolManager

# Import the constant from planning_server
from .planning_server import PLANS_DIR

logger = logging.getLogger(__name__)


@dataclass
class CreatePlanStep(WorkflowStep):
    """Single step that creates a plan and saves it using the MCP server's tools."""

    def __init__(self):
        super().__init__(
            name="create_and_save_plan",
            description="Create a plan using LLM and save it using MCP tools",
            required_inputs={"task", "plan_name"},
            provided_outputs={"plan_content", "save_result", "plan_path"},
            required_tools={"save_plan"},
            # Configure prompt-based execution
            prompt_name="create_plan_prompt",
            client_id="planning",
            user_message_template=(
                "Create a detailed plan for the following task: {task}. "
                "The plan should be well-structured, specific, and actionable. "
                "{timeframe_text}{resources_text}"
            ),
            # Allow the save_plan tool to be used by the LLM
            tool_names=["save_plan"],
            model="claude-3-opus-20240229",
        )

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute the plan creation and saving step"""
        # Extract inputs from context
        task = context.get("task")
        plan_name = context.get("plan_name")
        timeframe = context.get("timeframe")
        resources = context.get("resources")

        # Format the message parts
        timeframe_text = f" The timeframe is {timeframe}." if timeframe else ""
        resources_text = ""
        if resources:
            if isinstance(resources, list):
                resources_text = f" Available resources: {', '.join(resources)}."
            else:
                resources_text = f" Available resources: {resources}."

        # Add to context for template
        context.set("timeframe_text", timeframe_text)
        context.set("resources_text", resources_text)

        # Check for custom prompt template
        custom_template = context.get("custom_prompt_template")
        if custom_template:
            logger.info("Using custom prompt template")
            original_template = self.user_message_template
            self.user_message_template = custom_template

        try:
            # Execute the prompt with tools
            logger.info(f"Creating plan for task: {task}")
            result = await self.execute_with_prompt(context)

            # Check if the LLM used the save_plan tool
            tool_used = False
            save_result = None
            
            if "tool_uses" in result and result["tool_uses"]:
                for tool_use in result["tool_uses"]:
                    if "id" in tool_use and "save_plan" in str(tool_use):
                        tool_used = True
                        logger.info("LLM used save_plan tool")
                        
                        # Try to extract the save_result
                        if "content" in tool_use:
                            for content in tool_use["content"]:
                                if "text" in content and "success" in content["text"]:
                                    try:
                                        import json
                                        save_result = json.loads(content["text"])
                                        logger.info(f"Extracted save result: {save_result}")
                                    except:
                                        save_result = {"success": True, "message": "Plan saved"}

            # Extract plan content from the LLM response
            plan_content = self._extract_content(result)
            logger.info(f"Extracted plan content: {len(plan_content)} characters")

            # If the LLM didn't use the save_plan tool, we need to save it manually
            if not tool_used and context.tool_manager:
                logger.info(f"LLM didn't use save_plan tool, saving plan manually")
                
                # Process resources to get tags
                tags = []
                if resources:
                    if isinstance(resources, list):
                        tags = [r.strip() for r in resources if r]
                    else:
                        tags = [r.strip() for r in str(resources).split(",") if r.strip()]
                
                # Save the plan using the tool manager
                save_result = await context.tool_manager.execute_tool(
                    "save_plan",
                    {
                        "plan_name": plan_name,
                        "plan_content": plan_content,
                        "tags": tags
                    }
                )
                logger.info(f"Manual save result: {save_result}")

            # Determine the plan path
            plan_path = None
            if save_result and isinstance(save_result, dict) and "path" in save_result:
                plan_path = save_result["path"]
            else:
                # Fallback path
                plan_path = str(PLANS_DIR / f"{plan_name}.txt")

        finally:
            # Restore original template if we used a custom one
            if custom_template and "original_template" in locals():
                self.user_message_template = original_template

        # Store results in context
        context.set("plan_content", plan_content)
        context.set("save_result", save_result if save_result else {"success": True, "message": "Plan processed"})
        context.set("plan_path", plan_path)

        # Return the outputs
        return {
            "plan_content": plan_content,
            "save_result": save_result if save_result else {"success": True, "message": "Plan processed"},
            "plan_path": plan_path,
            "execution_details": result
        }

    def _extract_content(self, result: Dict[str, Any]) -> str:
        """Extract the plan content from the LLM response"""
        # Try to find the actual text content in the result
        if "final_response" in result:
            final_response = result.get("final_response")
            
            # If the response has content blocks (Claude API format)
            if hasattr(final_response, "content") and isinstance(final_response.content, list):
                text_content = ""
                for block in final_response.content:
                    if hasattr(block, "text") and block.type == "text":
                        text_content += block.text
                
                if text_content:
                    return text_content
        
        # If we couldn't extract content from the structured response, try other methods
        if "raw_response" in result and result["raw_response"]:
            return result["raw_response"]
            
        # Fallback to conversation history
        if "conversation" in result and result["conversation"]:
            for message in reversed(result["conversation"]):
                if message.get("role") == "assistant":
                    if isinstance(message.get("content"), list):
                        # Extract text from content blocks
                        text_content = ""
                        for block in message.get("content", []):
                            if isinstance(block, dict) and "text" in block:
                                text_content += block["text"]
                        if text_content:
                            return text_content
                    elif isinstance(message.get("content"), str):
                        return message["content"]
        
        # Last resort fallback - empty content
        logger.warning("Could not extract plan content from LLM response")
        return "No plan content could be extracted from the LLM response."


class PlanningWorkflow(BaseWorkflow):
    """
    Simplified workflow for creating and saving plans.
    
    This workflow uses a single step that combines plan creation and saving,
    leveraging the host's execute_prompt_with_tools method for both operations.
    """
    
    def __init__(self, tool_manager: ToolManager, name: str = "planning_workflow", host=None):
        """Initialize the planning workflow"""
        super().__init__(tool_manager, name=name, host=host)
        
        # Set description for documentation
        self.description = "Workflow for creating and saving plans"
        
        # Add the single step
        self.add_step(CreatePlanStep())
    
    async def create_plan(
        self,
        task: str,
        plan_name: str,
        timeframe: Optional[str] = None,
        resources: Optional[List[str]] = None,
        custom_prompt_template: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convenience method to execute the workflow with specific parameters.
        
        Args:
            task: The task to create a plan for
            plan_name: Name to save the plan as
            timeframe: Optional timeframe for the plan
            resources: Optional list of available resources
            custom_prompt_template: Optional custom prompt template
        
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
        if custom_prompt_template:
            input_data["custom_prompt_template"] = custom_prompt_template
        
        # Execute the workflow
        result_context = await self.execute(input_data)
        
        # Return the summarized results
        return result_context.summarize_results()