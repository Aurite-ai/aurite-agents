"""
Agent implementation for interacting with the Planning MCP Server.
"""

import os
import logging
import anthropic
from typing import Optional, List, Dict, Any
from anthropic.types import MessageParam, TextBlock

# Use relative imports for intra-package modules
from ..agent import Agent
from ...host.host import MCPHost
from ...host.models import AgentConfig

logger = logging.getLogger(__name__)


class PlanningAgent(Agent):
    """
    An agent specialized for interacting with the planning_server.py MCP server.

    Provides methods for saving and listing plans using the server's tools.
    """

    def __init__(self, config: AgentConfig):
        """
        Initializes the PlanningAgent.

        Args:
            config: The AgentConfig object containing agent settings and potentially
                    host configuration linkage.
        """
        super().__init__(config)
        logger.info(f"PlanningAgent '{config.name or 'Unnamed'}' initialized.")

    async def save_new_plan(
        self,
        host_instance: MCPHost,
        plan_name: str,
        plan_content: str,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Saves a new plan using the planning server's 'save_plan' tool.

        Args:
            host_instance: The initialized MCPHost instance providing access to tools.
            plan_name: The desired name for the plan (will be sanitized).
            plan_content: The textual content of the plan.
            tags: Optional list of tags for categorization.

        Returns:
            The result dictionary from the 'save_plan' tool execution.
        """
        logger.info(f"Attempting to save plan: {plan_name}")
        tool_args = {
            "plan_name": plan_name,
            "plan_content": plan_content,
        }
        if tags:
            tool_args["tags"] = tags

        try:
            # Assuming the planning server is configured with a known client_id
            # We might need a way to dynamically find the right client_id if not fixed
            # For now, let's assume a default or require it to be findable.
            # TODO: Determine how to reliably get the planning_server client_id
            # planning_client_id = self._find_planning_client_id(host_instance) # Removed

            # Use the new host-level execute_tool method
            result = await host_instance.execute_tool(
                # client_name=planning_client_id, # No longer needed if tool name is unique
                tool_name="save_plan",
                arguments=tool_args,
            )
            # The result from execute_tool is expected to be List[TextContent] or similar
            # We might need to parse this further depending on tool output format.
            # For now, returning the raw structure.
            logger.info(f"Save plan result for '{plan_name}': {result}")
            # Let's assume the tool returns a dict within the TextContent
            if result and isinstance(result, list) and hasattr(result[0], "text"):
                try:
                    import json

                    return json.loads(result[0].text)
                except Exception:
                    logger.warning("Could not parse save_plan result as JSON")
                    return {"raw_output": result[0].text}  # Return raw if not JSON
            return {"raw_output": result}  # Return raw list if not TextContent

        except Exception as e:
            logger.error(f"Error saving plan '{plan_name}': {e}")
            return {"success": False, "message": str(e)}

    async def list_existing_plans(
        self, host_instance: MCPHost, tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lists existing plans using the planning server's 'list_plans' tool.

        Args:
            host_instance: The initialized MCPHost instance.
            tag: Optional tag to filter the plans by.

        Returns:
            The result dictionary from the 'list_plans' tool execution.
        """
        logger.info(f"Attempting to list plans {f'with tag: {tag}' if tag else ''}")
        tool_args = {}
        if tag:
            tool_args["tag"] = tag

        try:
            # planning_client_id = self._find_planning_client_id(host_instance) # Removed

            # Use the new host-level execute_tool method
            result = await host_instance.execute_tool(
                # client_name=planning_client_id, # No longer needed if tool name is unique
                tool_name="list_plans",
                arguments=tool_args,
            )
            logger.info(f"List plans result: {result}")
            # Assuming the tool returns a dict within the TextContent
            if result and isinstance(result, list) and hasattr(result[0], "text"):
                try:
                    import json

                    return json.loads(result[0].text)
                except Exception:
                    logger.warning("Could not parse list_plans result as JSON")
                    return {"raw_output": result[0].text}
            return {"raw_output": result}

        except Exception as e:
            logger.error(f"Error listing plans: {e}")
            return {"success": False, "message": str(e)}

    async def execute_workflow(
        self,
        user_message: str,
        host_instance: MCPHost,
        anthropic_api_key: Optional[str] = None,
        plan_name: Optional[str] = "default_plan_name",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Executes the specific planning workflow:
        1. Generate plan content via LLM (no tools).
        2. Save the generated plan using the 'save_plan' tool.
        """
        logger.debug(f"PlanningAgent '{self.config.name}' starting workflow execution.")
        workflow_steps = []

        # --- Workflow Setup ---
        if not host_instance:
            logger.error("Workflow failed: Host instance is required.")
            # Return structure includes steps for traceability even on early failure
            return {
                "error": "Host instance required",
                "workflow_steps": workflow_steps,
                "final_output": None,
            }
        if not isinstance(host_instance, MCPHost):
            logger.error("Workflow failed: Invalid host instance type.")
            return {
                "error": "Invalid host instance type",
                "workflow_steps": workflow_steps,
                "final_output": None,
            }

        api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("Workflow failed: Anthropic API key not found.")
            return {
                "error": "API key not found",
                "workflow_steps": workflow_steps,
                "final_output": None,
            }

        try:
            client = anthropic.Anthropic(api_key=api_key)
            # Use agent's config for defaults, allow overrides if needed
            model = self.config.model or "claude-3-opus-20240229"
            temperature = (
                self.config.temperature or 0.5
            )  # Planning might benefit from lower temp
            max_tokens = self.config.max_tokens or 4096
            logger.debug(
                f"Workflow using LLM params: model={model}, temp={temperature}, max_tokens={max_tokens}"
            )
        except Exception as e:
            logger.error(f"Workflow failed during client initialization: {e}")
            # Add step info even for setup failure
            workflow_steps.append(
                {
                    "step": 0,
                    "action": "Setup",
                    "status": "Failed",
                    "error": f"Client initialization failed: {e}",
                }
            )
            return {
                "error": f"Client initialization failed: {e}",
                "workflow_steps": workflow_steps,
                "final_output": None,
            }

        # --- Step 1: Generate Plan (LLM Call, No Tools) ---
        plan_content = None
        try:
            logger.info("Workflow Step 1: Generating plan content via LLM.")
            # Define the specific prompt for this step
            planning_system_prompt = "You are an AI planning assistant. Create a detailed, step-by-step plan based on the user's request. Output only the plan text."
            # Prepare messages for the LLM call
            messages: List[MessageParam] = [{"role": "user", "content": user_message}]
            # Log the step initiation
            workflow_steps.append(
                {
                    "step": 1,
                    "action": "LLM Call (Generate Plan)",
                    "input": user_message,
                    "prompt": planning_system_prompt,
                }
            )

            # *** Use the internal helper method from the base Agent class ***
            llm_response = await self._make_llm_call(
                client=client,
                messages=messages,
                system_prompt=planning_system_prompt,
                tools=[],  # Explicitly no tools for generation step
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Extract text content from the response
            if llm_response.content and isinstance(llm_response.content[0], TextBlock):
                plan_content = llm_response.content[0].text
                logger.info("Plan content generated successfully.")
                workflow_steps.append(
                    {"step": 1, "status": "Success", "output_length": len(plan_content)}
                )
            else:
                # Handle cases where the response format isn't as expected
                logger.error("LLM response did not contain expected text block.")
                raise ValueError("LLM response did not contain expected text block.")

        except Exception as e:
            logger.error(f"Workflow Step 1 failed (LLM Call): {e}")
            workflow_steps.append({"step": 1, "status": "Failed", "error": str(e)})
            # Stop the workflow if plan generation fails
            return {
                "workflow_steps": workflow_steps,
                "final_output": None,
                "error": f"Plan generation failed: {e}",
            }

        # --- Step 2: Save Plan (Tool Call) ---
        save_result = None
        if plan_content:  # Only proceed if step 1 succeeded and produced content
            try:
                logger.info(f"Workflow Step 2: Saving plan '{plan_name}' via tool.")
                # Log the step initiation
                workflow_steps.append(
                    {
                        "step": 2,
                        "action": "Tool Call (save_plan)",
                        "plan_name": plan_name,
                        "tags": tags,
                    }
                )

                # Use the existing method which calls host_instance.execute_tool
                save_result = await self.save_new_plan(
                    host_instance=host_instance,
                    plan_name=plan_name,
                    plan_content=plan_content,
                    tags=tags,
                )
                # Assuming save_new_plan returns a dict with success/message or raw_output
                if (
                    isinstance(save_result, dict)
                    and save_result.get("success") is False
                ):
                    # Handle specific failure reported by save_new_plan
                    raise Exception(
                        save_result.get("message", "save_plan tool reported failure")
                    )
                else:
                    logger.info(f"Plan '{plan_name}' saved successfully via tool.")
                    workflow_steps.append(
                        {"step": 2, "status": "Success", "result": save_result}
                    )

            except Exception as e:
                logger.error(f"Workflow Step 2 failed (Tool Call): {e}")
                workflow_steps.append({"step": 2, "status": "Failed", "error": str(e)})
                # Decide if failure here halts everything or just logs - let's halt
                return {
                    "workflow_steps": workflow_steps,
                    "final_output": None,
                    "error": f"Plan saving failed: {e}",
                }
        else:
            # This case should technically be caught by the return in Step 1's except block,
            # but adding a log here for completeness if plan_content is None for other reasons.
            logger.warning(
                "Workflow Step 2 skipped: Plan content was not generated in Step 1."
            )
            workflow_steps.append(
                {
                    "step": 2,
                    "action": "Tool Call (save_plan)",
                    "status": "Skipped",
                    "reason": "No plan content from Step 1",
                }
            )

        # --- Workflow Completion ---
        logger.info(
            f"PlanningAgent workflow execution finished for plan '{plan_name}'."
        )
        return {
            "workflow_steps": workflow_steps,
            "final_output": save_result,  # Return the result from the save_plan tool call (or None if skipped/failed)
            "error": None,  # Indicate successful completion of the workflow itself
        }

    # Optional: Implement generate_plan method later if needed
    # async def generate_plan(self, host_instance: MCPHost, user_request: str):
    #     """Generates and potentially saves a plan using LLM and tools."""
    #     # 1. Get the planning prompt from the server
    #     # 2. Call self.execute() with the prompt and user_request
    #     # 3. Extract plan content from LLM response
    #     # 4. Call self.save_new_plan()
    #     pass
