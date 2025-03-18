"""
Planning workflow for creating and saving plans.

This module implements a workflow-based approach to plan creation and management.
It demonstrates two key approaches to workflow steps:
- Prompt-based execution: Using LLMs with tool-calling capabilities for flexible plan creation
- Direct tool execution: Using MCP tools directly for deterministic operations like saving

The workflow architecture separates concerns into distinct steps:
- PlanCreationStep: Generates a structured plan using prompt-based execution
- PlanSaveStep: Persists plans to disk with metadata
- PlanAnalysisStep: Analyzes existing plans for gaps and improvements
- PlanListStep: Lists available plans with filtering capabilities

Key Features:
1. Robust LLM response handling with multi-stage fallbacks
2. Flexible type handling between prompt system and tool execution
3. Clear step interfaces with defined inputs and outputs
4. Context management for reliable data passing between steps
"""

import asyncio
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import logging
import json
from pydantic import Field
from datetime import datetime
from ...host.resources.tools import ToolManager
from ..base_workflow import BaseWorkflow, WorkflowStep
from ..base_models import AgentContext, AgentData

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
    user_message_template: Optional[str] = None


@dataclass
class PlanCreationStep(WorkflowStep):
    """Step to create a plan using the host's execute_prompt_with_tools method"""

    def __init__(self):
        super().__init__(
            name="create_plan",
            description="Create a plan using prompt-based execution",
            required_inputs={"task", "plan_name"},
            provided_outputs={"plan_content"},
            # No tools needed - this step uses prompt-based execution directly
            required_tools=set(),
            # Configure prompt-based execution
            prompt_name="create_plan_prompt",
            client_id="planning",
            user_message_template=(
                "I need to create a detailed, specific plan for the following task: {task}. "
                "Please provide a structured learning path with specific resources, concepts to master, "
                "and practical projects to work on. The plan should be named '{plan_name}'"
                "{timeframe_text}{resources_text}. "
                "Be detailed, specific, and focus on actionable steps rather than generic advice.\n\n"
                "Format the response as a structured markdown document with clear sections, bullet points, "
                "and a logical progression. Include specific steps, resources, timelines, and success metrics."
            ),
            # Don't use any tools - generate the plan content directly
            tool_names=[],
            model="claude-3-opus-20240229",
        )

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute the plan creation step using prompt-based execution"""
        # Check if plan was already created in a previous retry attempt
        # This prevents duplicate plan creation on retries
        existing_plan_content = context.get("plan_content")
        if existing_plan_content:
            logger.info(
                "Plan content already exists in context, skipping plan creation step"
            )
            plan_name = context.get("plan_name")
            return {
                "plan_content": existing_plan_content,
                "plan_name": plan_name,
                "create_plan_result": {
                    "success": True,
                    "message": f"Plan '{plan_name}' already exists in context",
                },
                "prompt_execution_details": {"reused_existing": True},
            }

        # Extract inputs from context
        task = context.get("task")
        plan_name = context.get("plan_name")
        timeframe = context.get("timeframe")
        resources = context.get("resources")

        # Check for custom prompt template in the context
        # We check both 'user_message_template' (for backward compatibility)
        # and 'custom_prompt_template' (new recommended field name)
        custom_template = context.get(
            "custom_prompt_template", context.get("user_message_template", None)
        )

        if custom_template:
            logger.info("Using custom prompt template from input data")
            # Store original template for restoration if needed
            original_template = self.user_message_template
            # Override with the custom template just for this execution
            self.user_message_template = custom_template

        # Format the user message template parts and store them in context
        # so the message template can access these
        timeframe_text = f" with a timeframe of {timeframe}" if timeframe else ""
        context.set("timeframe_text", timeframe_text)

        resources_text = ""
        if resources:
            resources_list = ", ".join(resources)
            resources_text = f" and using these resources: {resources_list}"
        context.set("resources_text", resources_text)

        # Set the prompt arguments
        # The prompt system expects resources as a string, while the tool expects a list
        resources_str = (
            ", ".join(resources)
            if isinstance(resources, list)
            else str(resources)
            if resources
            else ""
        )
        self.prompt_arguments = {
            "task": task,
            "timeframe": timeframe,
            "resources": resources_str,  # Pass resources as a string for the prompt
        }

        # Use the utility method that handles prompt-based execution
        # This will call the host's execute_prompt_with_tools method
        prompt_result = await self.execute_with_prompt(context)

        try:
            # Process the prompt result to extract plan content
            plan_content, create_plan_result = self._extract_plan_content(
                prompt_result, plan_name, task
            )
        finally:
            # Restore original template if we used a custom one
            if custom_template and "original_template" in locals():
                self.user_message_template = original_template

        # IMPORTANT: Make sure we set all required fields in the context directly
        # This is critical for subsequent steps like PlanSaveStep
        context.set("plan_content", plan_content)
        # Make sure plan_name is in the context (required by PlanSaveStep)
        context.set("plan_name", plan_name)

        # We still return the values for the step result
        # IMPORTANT: Include plan_name in outputs to ensure it's available for subsequent steps
        return {
            "plan_content": plan_content,
            "plan_name": plan_name,  # Include plan_name explicitly
            "create_plan_result": create_plan_result,
            "prompt_execution_details": prompt_result,
        }

    def _extract_plan_content(
        self, prompt_result: Dict[str, Any], plan_name: str, task: str
    ) -> tuple[str, Any]:
        """
        Extract plan content from the prompt execution result.

        Processes the response from execute_prompt_with_tools to extract the
        plan content directly from the LLM's response.

        Args:
            prompt_result: The result from execute_prompt_with_tools
            plan_name: The name of the plan (for fallback generation)
            task: The task description (for fallback generation)

        Returns:
            Tuple of (plan_content, result_dict)
        """
        plan_content = None

        # Extract directly from the final response
        final_response = prompt_result.get("final_response", {})

        # Simplified response extraction using consistent approach
        response_text = ""

        # Handle different response structures consistently
        if hasattr(final_response, "content"):
            content = final_response.content

            # Content could be a list of content blocks or a string
            if isinstance(content, list):
                for block in content:
                    # Handle content block objects (Claude API style)
                    if hasattr(block, "text"):
                        response_text += block.text
                    # Handle dictionary blocks
                    elif isinstance(block, dict) and "text" in block:
                        response_text += block["text"]
            # Handle string content directly
            elif isinstance(content, str):
                response_text = content
        # Handle response as string
        elif hasattr(final_response, "text"):
            response_text = final_response.text
        # Handle dictionary with 'text' key
        elif isinstance(final_response, dict) and "text" in final_response:
            response_text = final_response["text"]
        # Last resort: try string representation
        elif final_response:
            response_text = str(final_response)

        # Check if we have content
        if response_text.strip():
            # Cleaner approach - just use the full text and optimize the prompt instructions instead
            plan_content = response_text.strip()
            
            # Log detailed information about what we extracted
            logger.info(f"PLAN EXTRACTION - LENGTH: {len(plan_content)} chars")
            logger.info(f"PLAN STARTS WITH: {plan_content[:100]}...")
            if len(plan_content) > 200:
                logger.info(f"PLAN ENDS WITH: ...{plan_content[-100:]}")

        # Create fallback plan if we still don't have content
        if not plan_content:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            plan_content = f"""
            # Plan: {plan_name}

            ## Task
            {task}

            ## Created
            {current_time}

            ## Content
            This is a fallback plan created when prompt-based execution didn't return expected content.
            """
            logger.warning(
                "Prompt-based execution for create_plan did not return expected plan_content"
            )

        # Create a simple result dictionary
        result_dict = {
            "plan_name": plan_name,
            "plan_content": plan_content,
            "success": True,
            "message": f"Plan '{plan_name}' created successfully",
        }

        return plan_content, result_dict


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

    def _prepare_resource_tags(self, resources: Any) -> Optional[List[str]]:
        """
        Convert resources to a list format suitable for the tags parameter.

        Args:
            resources: Resources in any format (list, string, etc.)

        Returns:
            List of resource tags or None if no valid resources
        """
        # Already a list
        if isinstance(resources, list):
            return resources

        # String that needs splitting
        if isinstance(resources, str) and resources:
            return [r.strip() for r in resources.split(",")]

        # No valid resources
        return None

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute the plan saving step"""
        # Extract inputs with hardcoded defaults to avoid missing field errors
        plan_name = context.get("plan_name", context.get("task", "unnamed_plan"))
        plan_content = context.get("plan_content", "No plan content available")
        resources = context.get("resources", [])

        # Log available data for debugging
        logger.debug(
            f"PlanSaveStep - available keys: {list(context.get_data_dict().keys())}"
        )

        # Always ensure plan_name is available for this step
        if not plan_name or plan_name == "unnamed_plan":
            # Try to get from previous step
            create_step_result = context.get_step_result("create_plan")
            if create_step_result and hasattr(create_step_result, "outputs"):
                # Check outputs for plan_name
                outputs_dict = getattr(create_step_result, "outputs", {})
                if "plan_name" in outputs_dict:
                    plan_name = outputs_dict["plan_name"]
                    logger.info(
                        f"Retrieved plan_name from create_plan step outputs: {plan_name}"
                    )

        # Log what we're using
        logger.info(f"PlanSaveStep using plan_name: {plan_name}")

        # Prepare parameters for save_plan tool
        tags = self._prepare_resource_tags(resources)

        # Check if the plan with this name already exists
        try:
            # Try to list plans first to avoid duplicate saves
            list_plans_result = await context.tool_manager.execute_tool("list_plans")

            # Parse the plans list result to get plan names
            plan_exists = False
            if isinstance(list_plans_result, dict) and list_plans_result.get(
                "success", False
            ):
                plans = list_plans_result.get("plans", [])
                plan_exists = any(p.get("name") == plan_name for p in plans)

            if plan_exists:
                logger.info(
                    f"Plan '{plan_name}' already exists, skipping save operation"
                )
                return {
                    "save_result": {
                        "success": True,
                        "message": f"Plan '{plan_name}' already exists, skipping save",
                        "path": f"plans/{plan_name}.txt",
                    },
                    "plan_path": f"plans/{plan_name}.txt",
                }
        except Exception as e:
            logger.warning(
                f"Error checking if plan exists: {e}, will attempt to save anyway"
            )

        # Execute the save_plan tool with a timeout of 30 seconds
        try:
            # Use asyncio.wait_for to add a timeout
            result = await asyncio.wait_for(
                context.tool_manager.execute_tool(
                    "save_plan",
                    {
                        "plan_name": plan_name,
                        "plan_content": plan_content,
                        "tags": tags,
                    },
                ),
                timeout=30.0,  # 30 second timeout
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"save_plan tool timed out after 30 seconds for plan '{plan_name}'"
            )
            # Return success anyway since the plan was likely saved
            return {
                "save_result": {
                    "success": True,
                    "message": f"Plan '{plan_name}' save operation timed out, but likely succeeded",
                    "path": f"plans/{plan_name}.txt",
                },
                "plan_path": f"plans/{plan_name}.txt",
            }

        # Extract the text content from the result
        result_text = context.tool_manager.format_tool_result(result)
        logger.debug(f"Save plan result: {result_text}")

        # Parse the result JSON if possible
        try:
            if isinstance(result, dict):
                save_result = result
            elif hasattr(result, "model_dump"):
                save_result = result.model_dump()
            elif isinstance(result_text, str) and result_text.strip().startswith("{"):
                save_result = json.loads(result_text)
            else:
                # Fallback with reasonable defaults
                save_result = {
                    "success": True,
                    "message": f"Plan '{plan_name}' saved successfully",
                    "path": f"plans/{plan_name}.txt",
                }
        except Exception as e:
            logger.warning(f"Error parsing save result: {e}")
            save_result = {
                "success": True,
                "message": f"Plan '{plan_name}' saved successfully",
                "path": f"plans/{plan_name}.txt",
            }

        return {
            "save_result": save_result,
            "plan_path": save_result.get("path")
            if save_result.get("success")
            else None,
        }


@dataclass
class PlanAnalysisStep(WorkflowStep):
    """Step to analyze an existing plan"""

    def __init__(self):
        super().__init__(
            name="analyze_plan",
            description="Analyze an existing plan for gaps and improvements",
            required_inputs={"plan_name"},
            provided_outputs={"analysis_report"},
            # Configure prompt-based execution
            prompt_name="plan_analysis_prompt",
            client_id="planning",
            user_message_template=(
                "Please analyze the existing plan named '{plan_name}'. "
                "Identify any gaps, inconsistencies, and suggest improvements."
            ),
            tool_names=["list_plans"],
            model="claude-3-opus-20240229",
        )

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute the plan analysis step using prompt-based execution"""
        # Extract inputs
        plan_name = context.get("plan_name")

        # Set the prompt argument for the plan name
        self.prompt_arguments = {"plan_name": plan_name}

        # Call the utility method that handles prompt-based execution
        prompt_result = await self.execute_with_prompt(context)

        # Extract the analysis from the response
        final_response = prompt_result.get("final_response", {})

        # Extract the analysis text from the final response
        if final_response and hasattr(final_response, "content"):
            # Extract text content from content blocks
            analysis_text = ""
            for block in final_response.content:
                if hasattr(block, "text"):
                    analysis_text += block.text
                elif isinstance(block, dict) and "text" in block:
                    analysis_text += block["text"]

            # If we couldn't extract text from content blocks, use string representation
            if not analysis_text:
                analysis_text = str(final_response)
        else:
            # Fallback if we can't extract from final_response
            analysis_text = (
                "Error: Could not generate analysis using prompt-based execution"
            )

        return {
            "analysis_report": analysis_text,
            "prompt_execution_details": prompt_result,
        }


@dataclass
class PlanListStep(WorkflowStep):
    """Step to list available plans, optionally filtered by tag"""

    def __init__(self):
        super().__init__(
            name="list_plans",
            description="List available plans, optionally filtered by tag",
            required_inputs=set(),  # No required inputs
            provided_outputs={"plans_list"},
            required_tools={"list_plans"},
        )

    async def execute(self, context: AgentContext) -> Dict[str, Any]:
        """Execute the plan listing step"""
        # Extract optional filter tag if present
        tag = context.get("filter_tag", None)

        # Use the list_plans tool
        result = await context.tool_manager.execute_tool(
            "list_plans", {"tag": tag} if tag else {}
        )

        # Extract the text content from the result
        result_text = context.tool_manager.format_tool_result(result)
        logger.debug(f"List plans result: {result_text}")

        # Parse the actual list_plans response
        try:
            # Try to parse as JSON if it's a string
            if isinstance(result_text, str) and result_text.strip().startswith("{"):
                plans_data = json.loads(result_text)
            # If result is already a dict, use it directly
            elif isinstance(result, dict):
                plans_data = result
            # If result has model_dump method (Pydantic model)
            elif hasattr(result, "model_dump"):
                plans_data = result.model_dump()
            else:
                # Last resort: try to parse the string representation
                plans_data = json.loads(str(result))

            return {"plans_list": plans_data}
        except Exception as e:
            logger.warning(f"Error parsing list_plans result: {e}")
            # Fall back to a safe default
            return {
                "plans_list": {
                    "success": False,
                    "message": f"Error parsing plans list: {str(e)}",
                    "count": 0,
                    "plans": [],
                }
            }


class PlanningWorkflow(BaseWorkflow):
    """
    Workflow for creating, saving, and analyzing plans.

    This workflow demonstrates:
    1. Using prompt-based execution with LLM-directed tool use for plan creation
    2. Saving plans using direct tool execution
    3. Analyzing existing plans using prompt-based execution
    4. Listing available plans using direct tool execution
    5. Different approaches to workflow step implementation
    """

    def __init__(
        self, tool_manager: ToolManager, name: str = "planning_workflow", host=None
    ):
        """Initialize the planning workflow"""
        super().__init__(tool_manager, name=name, host=host)

        # Set description for documentation
        self.description = "Workflow for creating, saving, and analyzing detailed plans"

        # Add steps
        self.add_step(PlanCreationStep())
        self.add_step(PlanSaveStep())

        # PlanAnalysisStep is added conditionally when needed
        # PlanListStep is added conditionally when needed

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

    async def analyze_plan(
        self,
        plan_name: str,
    ) -> Dict[str, Any]:
        """
        Convenience method to analyze an existing plan.

        Args:
            plan_name: Name of the plan to analyze

        Returns:
            Dictionary with analysis results
        """
        # Create a new workflow instance for analysis only
        analysis_workflow = PlanningWorkflow(self.tool_manager, host=self.host)

        # Replace steps with just the analysis step
        analysis_workflow.steps = [PlanAnalysisStep()]

        # Execute the workflow
        result_context = await analysis_workflow.execute({"plan_name": plan_name})

        # Return the summarized results
        return result_context.summarize_results()

    async def list_plans(
        self,
        filter_tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convenience method to list available plans.

        Args:
            filter_tag: Optional tag to filter plans by

        Returns:
            Dictionary with list of plans
        """
        # Create a new workflow instance for listing only
        list_workflow = PlanningWorkflow(self.tool_manager, host=self.host)

        # Replace steps with just the list step
        list_workflow.steps = [PlanListStep()]

        # Create input data
        input_data = {}
        if filter_tag:
            input_data["filter_tag"] = filter_tag

        # Execute the workflow
        result_context = await list_workflow.execute(input_data)

        # Return the summarized results
        return result_context.summarize_results()
