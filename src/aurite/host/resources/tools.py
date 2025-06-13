"""
Tool management for MCP Host.

This module provides a ToolManager class that handles:
1. Tool registration and discovery
2. Tool execution and validation
3. Tool capability mapping
4. Integration with agent frameworks
"""

from typing import Dict, List, Any, Optional, Set
import logging
# import asyncio # No longer needed after removing _active_requests

import mcp.types as types

# Import from lower layers for dependencies
from ..foundation import RootManager, MessageRouter
from ..filtering import FilteringManager  # Added import
from aurite.config.config_models import ClientConfig, AgentConfig  # Added imports

logger = logging.getLogger(__name__)


class ToolManager:
    """
    Manages tool registration, discovery, and execution.
    Part of the resource management layer of the Host system.

    This manager allows the agent framework to interact with tools
    without requiring the entire host system.
    """

    def __init__(
        self,
        root_manager: RootManager,
        message_router: MessageRouter,
        # filtering_manager: FilteringManager # Added filtering_manager - Decided against adding here, pass to methods instead
    ):
        """
        Initialize the tool manager.

        Args:
            root_manager: The root manager for access control.
            message_router: The message router for routing decisions.
            # filtering_manager: The filtering manager for applying rules. # Removed from init
        """
        self._root_manager = root_manager
        self._message_router = message_router
        # self._filtering_manager = filtering_manager # Removed from init

        # Tool registry
        self._tools: Dict[str, types.Tool] = {}
        # Tool metadata (simplified, capabilities removed)
        self._tool_metadata: Dict[str, Dict[str, Any]] = {}

        # Client registry - Client ID to client session
        self._clients: Dict[str, Any] = {}

        # _active_requests removed as unused

    async def initialize(self):
        """Initialize the tool manager"""
        logger.debug("Initializing tool manager")  # INFO -> DEBUG
        # No initialization needed beyond the constructor at this point

    def register_client(self, client_id: str, client_session):
        """Register a client session with the tool manager"""
        self._clients[client_id] = client_session

    async def register_tool(
        self,
        tool_name: str,
        tool: types.Tool,
        client_id: str,
        client_config: ClientConfig,  # Added client_config
        filtering_manager: FilteringManager,  # Added filtering_manager
    ) -> bool:  # Return bool indicating if registered
        """
        Register a tool with its providing client, applying client-level exclusions.

        Args:
            tool_name: The name of the tool.
            tool: The tool definition (mcp.types.Tool).
            client_id: The ID of the client providing the tool.
            client_config: The configuration object for the client.
            filtering_manager: The filtering manager instance.

        Returns:
            True if the tool was registered, False if excluded by client config.
        """
        # Check registration allowance using FilteringManager
        if not filtering_manager.is_registration_allowed(tool_name, client_config):
            # Logging is handled within is_registration_allowed
            return False  # Indicate not registered

        # Store the tool definition (overwrites if same tool name registered again by another client,
        # but MessageRouter handles the multiple client mapping)
        self._tools[tool_name] = tool

        # Store simplified metadata (consider if this is still needed or if _tools is enough)
        # Keeping description/parameters might be useful for list_tools
        self._tool_metadata[tool_name] = {
            "client_id": client_id,  # Redundant? Router knows this.
            "description": tool.description if hasattr(tool, "description") else "",
            # Use inputSchema, which is the correct attribute for tool parameters.
            "parameters": getattr(tool, "inputSchema", {}),
        }

        # Register with the message router (only name and client_id needed now)
        await self._message_router.register_tool(tool_name, client_id)

        logger.debug(f"Registered tool '{tool_name}' for client '{client_id}'")
        return True  # Indicate registered

    async def discover_client_tools(self, client_id: str, client_session):
        """
        Discover tools provided by a client.

        Args:
            client_id: The client ID
            client_session: The client session

        Returns:
            List of discovered tool definitions (mcp.types.Tool).
        """
        try:
            # Get tools from the client
            tools_response = (
                await client_session.list_tools()
            )  # Returns ListToolsResult

            # Extract the list of tools
            # Assuming tools_response has a 'tools' attribute based on mcp.types
            if hasattr(tools_response, "tools"):
                discovered_tools: List[types.Tool] = tools_response.tools
                logger.debug(
                    f"Discovered {len(discovered_tools)} tools for client {client_id}"
                )
                return discovered_tools
            else:
                logger.warning(
                    f"Unexpected response format from list_tools for client {client_id}: {tools_response}"
                )
                return []  # Return empty list if format is unexpected

        except Exception as e:
            logger.error(f"Failed to discover tools for client {client_id}: {e}")
            raise

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        client_name: Optional[str] = None,  # Added client_name parameter
    ) -> Any:
        """
        Execute a tool with the given arguments, potentially on a specific client.

        Args:
            tool_name: The name of the tool to execute.
            arguments: The arguments to pass to the tool.
            client_name: Optional specific client ID to execute the tool on.
                         If None, the manager will attempt to find a unique client.

        Returns:
            The result content from the tool execution (List[TextContent]).

        Raises:
            ValueError: If the tool is unknown, ambiguous (and client_name not specified),
                        or the specified client_name is invalid or doesn't provide the tool.
            Exception: Any exception raised during the underlying tool execution by the client.
        """
        target_client_id: Optional[str] = None

        # Determine the target client ID
        if client_name:
            # If a specific client is requested, validate it
            if client_name not in self._clients:
                raise ValueError(f"Specified client '{client_name}' is not registered.")
            # Check if this specific client actually provides the tool (using router)
            providing_clients = await self._message_router.get_clients_for_tool(
                tool_name
            )
            if client_name not in providing_clients:
                raise ValueError(
                    f"Specified client '{client_name}' does not provide tool '{tool_name}'."
                )
            target_client_id = client_name
            logger.debug(
                f"Executing tool '{tool_name}' on specified client '{target_client_id}'"
            )
        else:
            # Discover clients providing the tool
            logger.debug(f"Discovering client for tool '{tool_name}'...")
            providing_clients = await self._message_router.get_clients_for_tool(
                tool_name
            )

            if not providing_clients:
                raise ValueError(
                    f"Tool '{tool_name}' not found on any registered client."
                )
            elif len(providing_clients) > 1:
                raise ValueError(
                    f"Tool '{tool_name}' is ambiguous; found on multiple clients: "
                    f"{providing_clients}. Specify a client_name."
                )
            else:
                target_client_id = providing_clients[0]
                logger.debug(
                    f"Executing tool '{tool_name}' on uniquely found client '{target_client_id}'"
                )

        # Ensure we have a target client ID
        if not target_client_id:
            # Should be unreachable due to logic above, but raise defensively
            raise ValueError(
                f"Could not determine target client for tool '{tool_name}'."
            )

        # Get client session
        client = self._clients.get(target_client_id)
        if not client:
            # Should also be unreachable if target_client_id was validated
            raise ValueError(
                f"Client session not found for determined client ID: {target_client_id}"
            )

        # Validate access through root manager (using simplified method)
        await self._root_manager.validate_access(client_id=target_client_id)

        # Execute the tool
        try:
            result = await client.call_tool(tool_name, arguments)

            # Convert result to proper types if it's been serialized to tuples
            if isinstance(result, tuple):
                result_dict = dict(result)
                return [
                    types.TextContent(type="text", text=c.text)
                    if hasattr(c, "text")
                    else types.TextContent(type="text", text=str(c))
                    for c in result_dict.get("content", [])
                ]

            # Handle the result directly as a CallToolResult
            if hasattr(result, "isError") and result.isError:
                error_message = (
                    result.content[0].text
                    if result.content and hasattr(result.content[0], "text")
                    else "Unknown tool execution error"
                )
                logger.error(
                    f"Tool '{tool_name}' execution on client '{target_client_id}' returned an error: {error_message}"
                )
                # Re-raise as a ValueError or a custom exception? Using ValueError for now.
                raise ValueError(f"Tool execution failed: {error_message}")

            if hasattr(result, "content"):
                # Ensure content is List[TextContent] or similar
                if isinstance(result.content, list) and all(
                    isinstance(item, types.TextContent) for item in result.content
                ):
                    return result.content
                else:
                    # Attempt conversion if possible, or raise error
                    logger.warning(
                        f"Unexpected content format in tool result for '{tool_name}': {result.content}"
                    )
                    # Basic conversion attempt:
                    try:
                        return [
                            types.TextContent(type="text", text=str(item))
                            for item in result.content
                        ]
                    except Exception:
                        raise TypeError(
                            f"Could not convert tool result content for '{tool_name}' to List[TextContent]"
                        )

            # If result has no 'content', maybe it's an older format or error?
            logger.warning(
                f"Tool '{tool_name}' result from client '{target_client_id}' has no 'content' attribute: {result}"
            )
            # Return empty list or raise error? Returning empty for now.
            return []
        except Exception as e:
            logger.error(
                f"Tool execution failed - Tool: '{tool_name}', Client: '{target_client_id}', Error: {e}"
            )
            raise  # Re-raise the original exception

    def list_tools(
        self, allowed_clients: list[str] | None = None
    ) -> List[Dict[str, Any]]:
        """
        List all available tools with basic metadata (name, description, parameters).

        Args:
            allowed_clients: Optional list of clients to list tools from (if None, all tools are listed)

        Returns:
            List of tools with metadata.
        """
        tool_list = []
        for name, tool_def in self._tools.items():
            # Use metadata if available, otherwise fallback to tool_def attributes
            metadata = self._tool_metadata.get(name, {})

            # skip if not an allowed client
            if (
                allowed_clients is not None
                and metadata.get("client_id") not in allowed_clients
            ):
                continue

            description = metadata.get(
                "description", getattr(tool_def, "description", "")
            )
            parameters = metadata.get(
                "parameters", getattr(tool_def, "inputSchema", {})
            )
            client_id = metadata.get(
                "client_id", "UNKNOWN"
            )  # Get client_id from metadata
            tool_list.append(
                {
                    "name": name,
                    "description": description,
                    "client_id": client_id,  # Add client_id here
                    # "capabilities" removed
                    "parameters": parameters,
                }
            )
        return tool_list

    def get_tool(self, tool_name: str) -> Optional[types.Tool]:
        """
        Get a tool by name.

        Args:
            tool_name: The name of the tool

        Returns:
            The tool if found, None otherwise
        """
        return self._tools.get(tool_name)

    def has_tool(self, tool_name: str) -> bool:
        """
        Check if a tool exists.

        Args:
            tool_name: The name of the tool

        Returns:
            True if the tool exists, False otherwise
        """
        return tool_name in self._tools

    # find_tools_by_capability method removed.

    def format_tools_for_llm(
        self,
        filtering_manager: FilteringManager,  # Added filtering_manager
        agent_config: Optional[AgentConfig] = None,  # Added agent_config
        tool_names: Optional[List[str]] = None,
        # allowed_clients parameter is now handled by filtering_manager based on agent_config
    ) -> List[Dict[str, Any]]:
        """
        Format tools for use with LLM APIs like Anthropic's Claude, applying agent-specific filters.

        Args:
            filtering_manager: The filtering manager instance.
            agent_config: Optional configuration of the agent requesting the tools.
                          Used for filtering by client_ids and exclude_components.
            tool_names: Optional list of specific tool names to *potentially* include
                        (if None, considers all registered tools subject to filtering).

        Returns:
            List of formatted tool definitions ready for API calls, filtered for the agent.
        """
        # 1. Get all registered tools initially
        all_tools_metadata = self.list_tools()  # Gets metadata for all tools

        # 2. Determine allowed clients for the agent (if agent_config provided)
        allowed_clients = None
        if agent_config:
            # Get all client IDs that have registered *any* tool
            # Ensure clients_with_tools_str_set is Set[str]
            clients_with_tools_str_set: Set[str] = set()
            for meta_item in all_tools_metadata:
                client_id_val = meta_item.get("client_id")
                if client_id_val is not None:
                    # We expect client_id_val to be a string or stringifiable to a non-empty string
                    s_client_id = str(client_id_val)
                    if s_client_id:  # Ensure it's a non-empty string after conversion
                        clients_with_tools_str_set.add(s_client_id)

            allowed_clients = filtering_manager.filter_clients_for_request(
                list(clients_with_tools_str_set), agent_config
            )

        # 3. Filter tools based on allowed clients
        if allowed_clients is not None:
            client_filtered_tools = [
                tool_meta
                for tool_meta in all_tools_metadata
                if tool_meta.get("client_id") in allowed_clients
            ]
        else:
            # If no agent_config or agent_config allows all clients
            client_filtered_tools = all_tools_metadata

        # 4. Filter by specific tool_names if provided
        if tool_names is not None:
            specific_tool_filtered = [
                tool_meta
                for tool_meta in client_filtered_tools
                if tool_meta.get("name") in tool_names
            ]
        else:
            specific_tool_filtered = client_filtered_tools

        # 5. Filter by agent's exclude_components list (if agent_config provided)
        agent_excluded_filtered = specific_tool_filtered
        if agent_config:
            agent_excluded_filtered = filtering_manager.filter_component_list(
                specific_tool_filtered, agent_config
            )

        # 6. Format the final list for the LLM
        tools_data = []
        for tool_meta in agent_excluded_filtered:
            tool_name = tool_meta.get("name")
            if not tool_name:
                continue  # Skip if name is missing

            tool = self.get_tool(tool_name)
            if tool:
                # Get correct input schema format
                input_schema = getattr(tool, "inputSchema", {})

                # Ensure schema has a 'type' field for LLM APIs
                if isinstance(input_schema, dict) and "type" not in input_schema:
                    input_schema["type"] = "object"

                tools_data.append(
                    {
                        "name": tool.name,
                        "description": tool.description
                        if hasattr(tool, "description")
                        else "",
                        "input_schema": input_schema,
                    }
                )

        return tools_data

    def format_tool_result(self, tool_result) -> str:
        """
        Format a tool result as text.

        Args:
            tool_result: The result from executing a tool

        Returns:
            Formatted text representation of the tool result
        """
        if isinstance(tool_result, list):
            return "\n".join([getattr(item, "text", str(item)) for item in tool_result])
        else:
            return str(tool_result)

    def create_tool_result_blocks(
        self, tool_use_id: str, tool_result: Any, is_error: bool = False
    ) -> Dict[str, Any]:
        """
        Create a properly formatted tool result block for LLM APIs.

        Args:
            tool_use_id: ID of the tool use to associate with the result
            tool_result: The result from executing the tool

        Returns:
            Formatted tool result block suitable for Anthropic API.
        """
        # Ensure content is formatted as a list of text blocks
        if isinstance(tool_result, list) and all(
            hasattr(item, "text") for item in tool_result
        ):
            content_list = [{"type": "text", "text": item.text} for item in tool_result]
        elif isinstance(tool_result, str):
            content_list = [{"type": "text", "text": tool_result}]
        else:
            # Fallback for unexpected formats
            logger.warning(
                f"Formatting unexpected tool result type: {type(tool_result)}"
            )
            content_list = [{"type": "text", "text": str(tool_result)}]

        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": content_list,
            "is_error": is_error,
        }

    async def unregister_client_tools(self, client_id: str):
        """
        Removes tool registrations associated with a specific client ID.
        If a tool definition is only registered to this client, it's removed entirely.

        Args:
            client_id: The ID of the client whose tools should be unregistered.
        """
        if client_id not in self._clients:
            logger.debug(
                f"Client '{client_id}' not found in ToolManager, cannot unregister tools."
            )
            return

        # Get the set of tools registered specifically for this client from the router
        tools_registered_by_client = await self._message_router.get_tools_for_client(
            client_id
        )
        removed_tool_definitions = []

        for tool_name in tools_registered_by_client:
            # Check how many clients provide this tool
            providers = await self._message_router.get_clients_for_tool(tool_name)
            # If this client is the *only* provider left after it's removed conceptually
            # (or if it was the only one to begin with)
            if len(providers) <= 1 and client_id in providers:
                # Remove the tool definition itself
                self._tools.pop(tool_name, None)
                self._tool_metadata.pop(tool_name, None)
                removed_tool_definitions.append(tool_name)
                logger.debug(
                    f"Removed tool definition '{tool_name}' as client '{client_id}' was the last provider."
                )

        # Remove the client session itself
        self._clients.pop(client_id, None)

        logger.debug(
            f"Unregistered client '{client_id}' from ToolManager. "
            f"Removed definitions for tools: {removed_tool_definitions}"
        )
        # Note: The MessageRouter's unregister_server method handles removing the client
        # from the router's perspective (called separately in MCPHost).

    async def shutdown(self):
        """Shutdown the tool manager"""
        logger.debug("Shutting down tool manager")  # Changed to DEBUG

        # _active_requests removed

        # Clear registries
        self._tools.clear()
        self._tool_metadata.clear()
        self._clients.clear()
