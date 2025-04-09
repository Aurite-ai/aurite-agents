"""
MCP Host implementation for managing MCP client connections and interactions.
"""

import logging  # Removed importlib, inspect, Path
from contextlib import AsyncExitStack
from typing import (
    Any,
    Dict,
    List,
    Optional,
)  # Kept Any, Dict, List, Optional as they are used elsewhere

from mcp import (
    ClientSession,
    StdioServerParameters,
    stdio_client,
)
import mcp.types as types

# Foundation layer
from .foundation import SecurityManager, RootManager, MessageRouter
from .models import (  # Import WorkflowConfig
    AgentConfig,
    ClientConfig,
    # Removed CustomWorkflowConfig
    HostConfig,
    WorkflowConfig,
)


# Resource management layer
from .resources import PromptManager, ResourceManager, ToolManager

logger = logging.getLogger(__name__)


class MCPHost:
    """
    The MCP Host manages connections to configured MCP servers (clients) and provides
    a unified interface for interacting with their capabilities (tools, prompts, resources)
    via dedicated managers. It also stores configurations for named agents.
    It serves as the core infrastructure layer used by higher-level components.
    """

    def __init__(
        self,
        config: HostConfig,
        agent_configs: Optional[Dict[str, AgentConfig]] = None,
        workflow_configs: Optional[Dict[str, WorkflowConfig]] = None,
        # Removed custom_workflow_configs parameter
        encryption_key: Optional[str] = None,
    ):
        # Layer 1: Foundation layer
        self._security_manager = SecurityManager(encryption_key=encryption_key)
        self._root_manager = RootManager()

        # Layer 2: Communication layer
        self._message_router = MessageRouter()

        # Layer 3: Resource management layer
        self._prompt_manager = PromptManager()
        self._resource_manager = ResourceManager()
        self._tool_manager = ToolManager(
            root_manager=self._root_manager, message_router=self._message_router
        )

        # State management
        self._config = config
        self._agent_configs = agent_configs or {}
        self._workflow_configs = workflow_configs or {}
        # Removed self._custom_workflow_configs initialization
        self._clients: Dict[str, ClientSession] = {}
        self._exit_stack = AsyncExitStack()

        # Create property accessors for resource layer managers
        self.prompts = self._prompt_manager
        self.resources = self._resource_manager
        self.tools = self._tool_manager

    async def initialize(self):
        """Initialize the host and all configured clients"""
        logger.info("Initializing MCP Host...")

        # Initialize subsystems in layer order

        # Layer 1: Foundation layer
        logger.info("Initializing foundation layer...")
        await self._security_manager.initialize()
        await self._root_manager.initialize()

        # Layer 2: Communication layer
        logger.info("Initializing communication layer...")
        await self._message_router.initialize()

        # Layer 3: Resource management layer
        logger.info("Initializing resource management layer...")
        await self._prompt_manager.initialize()
        await self._resource_manager.initialize()
        await self._tool_manager.initialize()

        # Initialize each configured client
        for client_config in self._config.clients:
            await self._initialize_client(client_config)

        logger.info("MCP Host initialization complete")

    async def _initialize_client(self, config: ClientConfig):
        """Initialize a single client connection"""
        logger.info(f"Initializing client: {config.client_id}")

        try:
            # Setup transport
            server_params = StdioServerParameters(
                command="python", args=[str(config.server_path)], env=None
            )

            # Create transport using context manager
            transport = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            session = await self._exit_stack.enter_async_context(
                ClientSession(transport[0], transport[1])
            )

            # Initialize with capabilities using proper types
            init_request = types.InitializeRequest(
                method="initialize",
                params=types.InitializeRequestParams(
                    protocolVersion="2024-11-05",
                    clientInfo=types.Implementation(
                        name="aurite-agents", version="0.1.0"
                    ),  # Updated name
                    capabilities=types.ClientCapabilities(
                        roots=types.RootsCapability(listChanged=True)
                        if "roots" in config.capabilities
                        else None,
                        sampling={} if "sampling" in config.capabilities else None,
                        experimental={},
                        prompts={} if "prompts" in config.capabilities else None,
                        resources={} if "resources" in config.capabilities else None,
                    ),
                ),
            )
            await session.send_request(init_request, types.InitializeResult)

            # Send initialized notification
            init_notification = types.InitializedNotification(
                method="notifications/initialized", params={}
            )
            await session.send_notification(init_notification)

            # Register roots
            if "roots" in config.capabilities:
                await self._root_manager.register_roots(config.client_id, config.roots)

            # Register server capabilities with router
            await self._message_router.register_server(
                server_id=config.client_id,
                capabilities=set(config.capabilities),
                weight=config.routing_weight,
            )

            # Store client session
            self._clients[config.client_id] = session

            # Discover and register components based on capabilities, applying exclusions
            tool_names = []
            prompt_names = []
            resource_names = []

            if "tools" in config.capabilities:
                self._tool_manager.register_client(config.client_id, session)
                # discover_client_tools now returns List[types.Tool] directly
                discovered_tools = await self._tool_manager.discover_client_tools(
                    client_id=config.client_id, client_session=session
                )
                for tool in discovered_tools:  # Iterate directly over the list
                    # register_tool now handles the exclusion check internally
                    registered = await self._tool_manager.register_tool(
                        tool_name=tool.name,
                        tool=tool,
                        client_id=config.client_id,
                        exclude_list=config.exclude,
                    )
                    if registered:
                        tool_names.append(tool.name)

            if "prompts" in config.capabilities:
                prompts_response = await session.list_prompts()
                # register_client_prompts handles exclusion internally
                registered_prompts = await self._prompt_manager.register_client_prompts(
                    config.client_id, prompts_response.prompts, config.exclude
                )
                prompt_names = [p.name for p in registered_prompts]

            if "resources" in config.capabilities:
                resources_response = await session.list_resources()
                # register_client_resources handles exclusion internally
                registered_resources = (
                    await self._resource_manager.register_client_resources(
                        config.client_id, resources_response.resources, config.exclude
                    )
                )
                resource_names = [r.name for r in registered_resources]

            logger.info(
                f"Client '{config.client_id}' initialized. "
                f"Tools: {tool_names}, Prompts: {prompt_names}, Resources: {resource_names}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize client {config.client_id}: {e}")
            raise

    async def get_prompt(
        self,
        prompt_name: str,
        arguments: Dict[str, Any],  # Kept for potential future use by manager
        client_name: Optional[str] = None,
        filter_client_ids: Optional[List[str]] = None,  # Added filter parameter
    ) -> Optional[types.Prompt]:  # Manager returns Prompt object or None
        """
        Gets a specific prompt template definition, discovering the client if necessary,
        optionally filtering by a list of allowed client IDs.

        Note: This retrieves the prompt *template definition* (mcp.types.Prompt).
              Executing a prompt (which involves an LLM call) is handled
              within the Agent.execute method. This method primarily helps
              find the correct prompt definition from potentially multiple clients.
              It *could* be extended to also handle converting response data
              if needed, similar to the underlying manager method.

        Args:
            prompt_name: The name of the prompt to retrieve.
            arguments: Arguments for the prompt (currently unused by manager's get_prompt
                       when retrieving template, but kept for potential future use
                       and consistency).
            client_name: Optional specific client ID to get the prompt from.
                         If None, the host will attempt to find a unique client
                         providing the prompt within the filter.
            filter_client_ids: Optional list of client IDs to restrict the search/retrieval to.

        Returns:
            The Prompt definition object, or None if not found.

        Raises:
            ValueError: If client_name is None and the prompt is not found or
                        is found on multiple clients within the filter (ambiguous).
            ValueError: If client_name is specified but is not in filter_client_ids (if provided).
        """
        target_client_id: Optional[str] = None

        if client_name:
            # If specific client is requested, check filter first
            if filter_client_ids and client_name not in filter_client_ids:
                raise ValueError(
                    f"Specified client '{client_name}' is not in the allowed filter list."
                )
            # Check if the specified client actually provides the prompt (manager check)
            # Note: get_prompt itself will return None if client doesn't have it,
            # but we could add an explicit check using get_clients_for_prompt if needed for clarity.
            target_client_id = client_name
        else:
            # Discover clients
            logger.info(f"Discovering client for prompt '{prompt_name}'...")
            # Call the correct manager (MessageRouter) and await
            all_providing_clients = await self._message_router.get_clients_for_prompt(
                prompt_name
            )

            # Apply filter if provided
            if (
                filter_client_ids is not None
            ):  # Check for None explicitly, empty list is a valid filter
                providing_clients = [
                    cid for cid in all_providing_clients if cid in filter_client_ids
                ]
                logger.debug(
                    f"Filtered potential clients {all_providing_clients} to {providing_clients} using filter {filter_client_ids}"
                )
            else:
                providing_clients = all_providing_clients

            if not providing_clients:
                logger.warning(
                    f"Prompt '{prompt_name}' not found on any registered client"
                    f"{' matching the filter' if filter_client_ids is not None else ''}."
                )
                return None
            elif len(providing_clients) > 1:
                raise ValueError(
                    f"Prompt '{prompt_name}' is ambiguous within the filter; found on multiple clients: "
                    f"{providing_clients}. Specify a client_name."
                )
            else:
                # Exactly one client found (either overall or within the filter)
                target_client_id = providing_clients[0]
                logger.info(
                    f"Found unique client '{target_client_id}' for prompt '{prompt_name}'."
                )

        if target_client_id:
            logger.info(
                f"Getting prompt template '{prompt_name}' from client '{target_client_id}'"
            )
            # Note: Manager's get_prompt currently only needs name and client_id
            return await self.prompts.get_prompt(
                name=prompt_name, client_id=target_client_id
            )
        else:
            # This case should technically be unreachable due to checks above,
            # but returning None defensively.
            logger.error(f"Could not determine client for prompt '{prompt_name}'.")
            return None

    def get_agent_config(self, agent_name: str) -> AgentConfig:
        """
        Retrieves the configuration for a specific agent by name.

        Args:
            agent_name: The name of the agent whose configuration is needed.

        Returns:
            The AgentConfig object for the specified agent.

        Raises:
            KeyError: If no agent with the given name is found.
        """
        if agent_name not in self._agent_configs:
            logger.error(f"Agent configuration not found for name: {agent_name}")
            raise KeyError(f"Agent configuration not found for name: {agent_name}")
        return self._agent_configs[agent_name]

    def get_workflow_config(self, workflow_name: str) -> WorkflowConfig:
        """
        Retrieves the configuration for a specific workflow by name.

        Args:
            workflow_name: The name of the workflow whose configuration is needed.

        Returns:
            The WorkflowConfig object for the specified workflow.

        Raises:
            KeyError: If no workflow with the given name is found.
        """
        if workflow_name not in self._workflow_configs:
            logger.error(f"Workflow configuration not found for name: {workflow_name}")
            raise KeyError(
                f"Workflow configuration not found for name: {workflow_name}"
            )
        return self._workflow_configs[workflow_name]

    # Removed get_custom_workflow_config method
    # Removed execute_custom_workflow method

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        client_name: Optional[str] = None,
        filter_client_ids: Optional[List[str]] = None,  # Added filter parameter
    ) -> Any:
        """
        Executes a tool, either on a specific client or by discovering a unique client,
        optionally filtering by a list of allowed client IDs.

        Args:
            tool_name: The name of the tool to execute.
            arguments: The arguments to pass to the tool.
            client_name: Optional specific client ID to execute the tool on.
                         If None, the host will attempt to find a unique client
                         providing the tool within the filter.
            filter_client_ids: Optional list of client IDs to restrict the search/execution to.

        Returns:
            The result from the tool execution (typically List[TextContent]).

        Raises:
            ValueError: If client_name is None and the tool is not found or
                        is found on multiple clients within the filter (ambiguous).
            ValueError: If client_name is specified but is not in filter_client_ids (if provided).
            Exception: Any exception raised during the underlying tool execution.
        """
        target_client_id: Optional[str] = None

        if client_name:
            # If specific client is requested, check filter first
            if filter_client_ids and client_name not in filter_client_ids:
                raise ValueError(
                    f"Specified client '{client_name}' is not in the allowed filter list."
                )
            # We also need ToolManager to verify this client provides the tool
            target_client_id = client_name
            logger.info(
                f"Executing tool '{tool_name}' on specified client '{target_client_id}'"
            )
        else:
            # Discover clients
            logger.info(f"Discovering client for tool '{tool_name}'...")
            # Call the correct manager (MessageRouter) and await
            all_providing_clients = await self._message_router.get_clients_for_tool(
                tool_name
            )

            # Apply filter if provided
            if filter_client_ids is not None:
                providing_clients = [
                    cid for cid in all_providing_clients if cid in filter_client_ids
                ]
                logger.debug(
                    f"Filtered potential clients {all_providing_clients} to {providing_clients} using filter {filter_client_ids}"
                )
            else:
                providing_clients = all_providing_clients

            if not providing_clients:
                raise ValueError(
                    f"Tool '{tool_name}' not found on any registered client"
                    f"{' matching the filter' if filter_client_ids is not None else ''}."
                )
            elif len(providing_clients) > 1:
                raise ValueError(
                    f"Tool '{tool_name}' is ambiguous within the filter; found on multiple clients: "
                    f"{providing_clients}. Specify a client_name."
                )
            else:
                # Exactly one client found
                target_client_id = providing_clients[0]
                logger.info(
                    f"Executing tool '{tool_name}' on uniquely found client '{target_client_id}'"
                )

        # Ensure we have a target client ID before calling manager
        if not target_client_id:
            raise ValueError(
                f"Could not determine target client for tool '{tool_name}'."
            )  # Should be unreachable

        # Call the ToolManager's execute_tool, passing the determined client_name
        return await self.tools.execute_tool(
            client_name=target_client_id,  # Pass the determined client
            tool_name=tool_name,
            arguments=arguments,
        )

    async def read_resource(
        self,
        uri: str,
        client_name: Optional[str] = None,
        filter_client_ids: Optional[List[str]] = None,  # Added filter parameter
    ) -> Optional[types.Resource]:
        """
        Gets a specific resource definition, discovering the client if necessary,
        optionally filtering by a list of allowed client IDs.

        Note: This retrieves the resource *definition* (mcp.types.Resource),
              not the actual resource content. Reading content requires direct
              access to the client session's `read_resource` method.

        Args:
            uri: The URI of the resource to read.
            client_name: Optional specific client ID to read the resource from.
                         If None, the host will attempt to find a unique client
                         providing the resource within the filter.
            filter_client_ids: Optional list of client IDs to restrict the search/retrieval to.

        Returns:
            The Resource definition object, or None if not found.

        Raises:
            ValueError: If client_name is None and the resource URI is not found or
                        is found on multiple clients within the filter (ambiguous).
            ValueError: If client_name is specified but is not in filter_client_ids (if provided).
            Exception: Any exception raised during the underlying resource reading.
                       (Note: This method only gets the definition, not content).
        """
        uri_str = str(uri)  # Ensure string comparison
        target_client_id: Optional[str] = None

        if client_name:
            # If specific client is requested, check filter first
            if filter_client_ids and client_name not in filter_client_ids:
                raise ValueError(
                    f"Specified client '{client_name}' is not in the allowed filter list."
                )
            # We assume ResourceManager.get_resource will return None if client doesn't have it.
            target_client_id = client_name
        else:
            # Discover clients
            logger.info(f"Discovering client for resource '{uri_str}'...")
            # Call the correct manager (MessageRouter) and await
            all_providing_clients = await self._message_router.get_clients_for_resource(
                uri_str
            )

            # Apply filter if provided
            if filter_client_ids is not None:
                providing_clients = [
                    cid for cid in all_providing_clients if cid in filter_client_ids
                ]
                logger.debug(
                    f"Filtered potential clients {all_providing_clients} to {providing_clients} using filter {filter_client_ids}"
                )
            else:
                providing_clients = all_providing_clients

            if not providing_clients:
                logger.warning(
                    f"Resource definition '{uri_str}' not found on any registered client"
                    f"{' matching the filter' if filter_client_ids is not None else ''}."
                )
                return None  # Return None if not found
            elif len(providing_clients) > 1:
                raise ValueError(
                    f"Resource URI '{uri_str}' is ambiguous within the filter; found on multiple clients: "
                    f"{providing_clients}. Specify a client_name."
                )
            else:
                # Exactly one client found
                target_client_id = providing_clients[0]
                logger.info(
                    f"Found unique client '{target_client_id}' for resource '{uri_str}'."
                )

        # Ensure we have a target client ID before calling manager
        if not target_client_id:
            # Should be unreachable if logic above is correct and resource exists
            logger.error(f"Could not determine target client for resource '{uri_str}'.")
            return None

        # Call the ResourceManager's get_resource
        logger.info(
            f"Getting resource definition '{uri_str}' from client '{target_client_id}'"
        )
        return await self.resources.get_resource(
            uri=uri_str, client_id=target_client_id
        )

    async def register_client(self, config: ClientConfig):
        """
        Dynamically registers and initializes a new client after the host has started.

        Args:
            config: The configuration for the client to register.

        Raises:
            ValueError: If a client with the same ID is already registered.
            Exception: Propagates exceptions from the underlying client initialization process.
        """
        logger.info(f"Attempting to dynamically register client: {config.client_id}")
        if config.client_id in self._clients:
            logger.error(f"Client ID '{config.client_id}' already registered.")
            raise ValueError(f"Client ID '{config.client_id}' already registered.")

        try:
            # Reuse the existing internal initialization logic
            # This will add the client to self._clients and manage its lifecycle via self._exit_stack
            await self._initialize_client(config)
            logger.info(
                f"Client '{config.client_id}' dynamically registered and initialized successfully."
            )
        except Exception as e:
            logger.error(
                f"Failed to dynamically register client '{config.client_id}': {e}",
                exc_info=True,
            )
            # Re-raise the exception for the caller (HostManager) to handle
            raise

    async def shutdown(self):
        """Shutdown the host and cleanup all resources"""
        logger.info("Shutting down MCP Host...")

        # Shutdown managers first, in reverse layer order, before closing connections

        # Layer 3: Resource management layer
        logger.info("Shutting down resource management layer...")
        await self._prompt_manager.shutdown()
        await self._resource_manager.shutdown()
        await self._tool_manager.shutdown()

        # Layer 2: Communication layer
        logger.info("Shutting down communication layer...")
        await self._message_router.shutdown()

        # Layer 1: Foundation layer
        logger.info("Shutting down foundation layer...")
        await self._security_manager.shutdown()
        await self._root_manager.shutdown()

        # Now, close all client connections and resources using the exit stack
        logger.info("Closing client connections via AsyncExitStack...")
        await self._exit_stack.aclose()

        # Clear stored agent and workflow configs
        self._agent_configs.clear()
        self._workflow_configs.clear()
        # Removed clearing of self._custom_workflow_configs

        logger.info("MCP Host shutdown complete")
