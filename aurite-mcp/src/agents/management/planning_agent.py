"""
Agent implementation for interacting with the Planning MCP Server.
"""

import logging
from typing import Optional, List, Dict, Any

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

    # def _find_planning_client_id(self, host_instance: MCPHost) -> str: # Removed helper method
    #     """
    #     Helper method to find the client ID associated with the planning server.
    #
    #     Currently assumes the planning server offers the 'save_plan' tool.
    #     Raises ValueError if no suitable client is found.
    #
    #     TODO: Make this more robust, perhaps by checking server metadata or config.
    #     """
    #     planning_clients = host_instance.tools.get_clients_for_tool("save_plan")
    #     if not planning_clients:
    #         raise ValueError(
    #             "Could not find a client providing the 'save_plan' tool. "
    #             "Ensure the planning server is configured correctly in the host."
    #         )
    #     # Return the first client found that offers the tool
    #     return planning_clients[0]

    # Optional: Implement generate_plan method later if needed
    # async def generate_plan(self, host_instance: MCPHost, user_request: str):
    #     """Generates and potentially saves a plan using LLM and tools."""
    #     # 1. Get the planning prompt from the server
    #     # 2. Call self.execute() with the prompt and user_request
    #     # 3. Extract plan content from LLM response
    #     # 4. Call self.save_new_plan()
    #     pass
