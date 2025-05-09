"""
MCP Host implementation for managing MCP client connections and interactions.
"""

import os  # Added os import
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
from .foundation import (
    SecurityManager,
    RootManager,
    MessageRouter,
    ClientManager,
)  # Added ClientManager
from .filtering import FilteringManager
from src.config.config_models import (
    AgentConfig,
    ClientConfig,
    HostConfig,
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
        # Removed workflow_configs parameter
        # Removed custom_workflow_configs parameter
        encryption_key: Optional[str] = None,
    ):
        # Layer 1: Foundation layer
        self._security_manager = SecurityManager(encryption_key=encryption_key)
        self._root_manager = RootManager()

        # Layer 2: Communication layer
        self._message_router = MessageRouter()
        self._filtering_manager = FilteringManager(
            message_router=self._message_router
        )  # Added instantiation

        # Layer 3: Resource management layer
        self._prompt_manager = PromptManager(
            message_router=self._message_router
        )  # Pass router
        self._resource_manager = ResourceManager(
            message_router=self._message_router
        )  # Pass router
        self._tool_manager = ToolManager(
            root_manager=self._root_manager, message_router=self._message_router
        )

        # State management
        self._config = config
        self._agent_configs = agent_configs or {}
        # Removed self._workflow_configs initialization
        # Removed self._custom_workflow_configs initialization
        # self._clients: Dict[str, ClientSession] = {} # Removed, managed by ClientManager
        self._exit_stack = AsyncExitStack()  # MCPHost still owns the main exit stack
        self.client_manager = ClientManager(
            exit_stack=self._exit_stack
        )  # Instantiate ClientManager

        # Create property accessors for resource layer managers
        self.prompts = self._prompt_manager
        self.resources = self._resource_manager
        self.tools = self._tool_manager

    async def initialize(self):
        """Initialize the host and all configured clients"""
        logger.info("Initializing MCP Host...")  # Keep high-level start as INFO

        # Initialize subsystems in layer order

        # Layer 1: Foundation layer
        logger.debug("Initializing foundation layer...")  # INFO -> DEBUG
        await self._security_manager.initialize()
        await self._root_manager.initialize()

        # Layer 2: Communication layer
        logger.debug("Initializing communication layer...")  # INFO -> DEBUG
        await self._message_router.initialize()

        # Layer 3: Resource management layer
        logger.debug("Initializing resource management layer...")  # INFO -> DEBUG
        await self._prompt_manager.initialize()
        await self._resource_manager.initialize()
        await self._tool_manager.initialize()

        # Initialize each configured client
        for client_config in self._config.clients:
            await self._initialize_client(client_config)

        logger.info("MCP Host initialization complete")  # Keep high-level end as INFO

    async def _initialize_client(self, config: ClientConfig):
        """Initialize a single client connection"""
        logger.debug(f"Initializing client: {config.client_id}")

        try:
            # Delegate client starting to ClientManager
            # ClientManager handles secrets, process start, session creation, and exit stack management
            session = await self.client_manager.start_client(
                config, self._security_manager
            )
            # ClientManager now stores the session and process handle

            # --- Communication and Registration (using the session returned by ClientManager) ---
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
                        sampling=types.SamplingCapability()  # Instantiate capability object
                        if "sampling" in config.capabilities
                        else None,
                        experimental={},
                        # Removed prompts and resources as they are not ClientCapabilities
                    ),
                ),
            )
            await session.send_request(init_request, types.InitializeResult)  # type: ignore[arg-type]

            # Send initialized notification
            init_notification = types.InitializedNotification(
                method="notifications/initialized",
                params=None,  # Pass None instead of {}
            )
            await session.send_notification(init_notification)  # type: ignore[arg-type]

            # Register roots
            if "roots" in config.capabilities:
                await self._root_manager.register_roots(config.client_id, config.roots)

            # Register server capabilities with router
            await self._message_router.register_server(
                server_id=config.client_id,
                capabilities=set(config.capabilities),
                weight=config.routing_weight,
            )

            # Client session is stored in self.client_manager.active_clients
            # self._clients[config.client_id] = session # Removed

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
                # --- Removed detailed logging ---
                for tool in discovered_tools:  # Iterate directly over the list
                    # Pass FilteringManager and ClientConfig to allow manager to check exclusion
                    registered = await self._tool_manager.register_tool(
                        tool_name=tool.name,
                        tool=tool,
                        client_id=config.client_id,
                        client_config=config,  # Pass the whole config
                        filtering_manager=self._filtering_manager,  # Pass the manager
                    )
                    # --- Removed detailed logging ---
                    if registered:
                        tool_names.append(tool.name)

            if "prompts" in config.capabilities:
                prompts_response = await session.list_prompts()
                # Pass FilteringManager and ClientConfig to allow manager to check exclusion
                registered_prompts = await self._prompt_manager.register_client_prompts(
                    client_id=config.client_id,
                    prompts=prompts_response.prompts,
                    client_config=config,  # Pass the whole config
                    filtering_manager=self._filtering_manager,  # Pass the manager
                )
                prompt_names = [p.name for p in registered_prompts]

            if "resources" in config.capabilities:
                resources_response = await session.list_resources()
                # Pass FilteringManager and ClientConfig to allow manager to check exclusion
                registered_resources = (
                    await self._resource_manager.register_client_resources(
                        client_id=config.client_id,
                        resources=resources_response.resources,
                        client_config=config,  # Pass the whole config
                        filtering_manager=self._filtering_manager,  # Pass the manager
                    )
                )
                resource_names = [r.name for r in registered_resources]

            logger.info(
                f"Client '{config.client_id}' initialized. "
                f"Tools: {tool_names}, Prompts: {prompt_names}, Resources: {resource_names}"
            )  # Keep client summary as INFO
            # --- End of restored section ---

        except Exception as e:
            logger.error(
                f"Failed to initialize client {config.client_id}: {e}"
            )  # Keep error as ERROR
            raise

    def is_client_registered(self, client_id: str) -> bool:
        """Checks if a client with the given ID is registered."""
        # Check in ClientManager's active clients
        return client_id in self.client_manager.active_clients

    async def get_prompt(
        self,
        prompt_name: str,
        arguments: Dict[str, Any],  # Kept for potential future use by manager
        client_name: Optional[str] = None,
        agent_config: Optional[AgentConfig] = None,  # Replaced filter_client_ids
    ) -> Optional[types.Prompt]:  # Manager returns Prompt object or None
        """
        Gets a specific prompt template definition, discovering the client if necessary,
        applying agent-specific filtering if agent_config is provided.

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
                         providing the prompt, applying agent filters if provided.
            agent_config: Optional configuration of the agent making the request, used
                          for applying client_ids and exclude_components filters.

        Returns:
            The Prompt definition object, or None if not found or excluded for the agent.

        Raises:
            ValueError: If client_name is None and the prompt is not found or
                        is found on multiple allowed clients (ambiguous).
            ValueError: If client_name is specified but is not allowed for the agent
                        or does not provide the prompt.
            ValueError: If the prompt is explicitly excluded by the agent's config.
        """
        target_client_id: Optional[str] = None
        agent_name = agent_config.name if agent_config else "UnknownAgent"

        # 1. Determine potential clients
        if client_name:
            # Validate specified client exists (using new method)
            if not self.is_client_registered(client_name):
                raise ValueError(f"Specified client '{client_name}' is not registered.")
            # Check if this client provides the prompt
            providing_clients = await self._message_router.get_clients_for_prompt(
                prompt_name
            )
            if client_name not in providing_clients:
                raise ValueError(
                    f"Specified client '{client_name}' does not provide prompt '{prompt_name}'."
                )
            potential_clients = [client_name]
        else:
            # Discover all clients providing the prompt
            logger.debug(f"Discovering clients for prompt '{prompt_name}'...")
            potential_clients = await self._message_router.get_clients_for_prompt(
                prompt_name
            )
            if not potential_clients:
                logger.warning(
                    f"Prompt '{prompt_name}' not found on any registered client."
                )
                return None

        # 2. Filter clients based on AgentConfig.client_ids (if provided)
        allowed_clients = potential_clients
        if agent_config:
            allowed_clients = self._filtering_manager.filter_clients_for_request(
                potential_clients, agent_config
            )
            if not allowed_clients:
                logger.warning(
                    f"Prompt '{prompt_name}' is provided by clients {potential_clients}, "
                    f"but none are allowed for agent '{agent_name}' by client_ids."
                )
                return None  # Or raise error? Returning None seems safer.

        # 3. Determine target client (handle ambiguity)
        if client_name:
            if client_name not in allowed_clients:
                # This case means the specified client was filtered out by agent_config.client_ids
                raise ValueError(
                    f"Specified client '{client_name}' is not allowed for agent '{agent_name}'."
                )
            target_client_id = client_name
        else:
            # If client_name wasn't specified, check for ambiguity among allowed clients
            if len(allowed_clients) > 1:
                raise ValueError(
                    f"Prompt '{prompt_name}' is ambiguous for agent '{agent_name}'; "
                    f"found on multiple allowed clients: {allowed_clients}. Specify a client_name."
                )
            elif not allowed_clients:
                # Should have been caught earlier, but defensive check
                logger.error(
                    f"No allowed client found for prompt '{prompt_name}' for agent '{agent_name}'."
                )
                return None
            else:
                target_client_id = allowed_clients[0]
                logger.info(
                    f"Found unique allowed client '{target_client_id}' for prompt '{prompt_name}' for agent '{agent_name}'."
                )

        # 4. Check agent-specific component exclusion (if agent_config provided)
        if agent_config:
            if not self._filtering_manager.is_component_allowed_for_agent(
                prompt_name, agent_config
            ):
                # Log and raise an error if explicitly excluded
                logger.warning(
                    f"Access denied: Prompt '{prompt_name}' is excluded for agent '{agent_name}' by exclude_components."
                )
                raise ValueError(
                    f"Prompt '{prompt_name}' is excluded for agent '{agent_name}'."
                )

        # 5. Get the prompt from the target client
        if target_client_id:
            logger.info(
                f"Getting prompt template '{prompt_name}' from client '{target_client_id}' for agent '{agent_name}'"
            )
            # Note: Manager's get_prompt currently only needs name and client_id
            return await self.prompts.get_prompt(
                name=prompt_name, client_id=target_client_id
            )
        else:
            # Should be unreachable
            logger.error(
                f"Could not determine target client for prompt '{prompt_name}' for agent '{agent_name}'."
            )
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

    # Removed get_workflow_config method
    # Removed get_custom_workflow_config method
    # Removed execute_custom_workflow method

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        client_name: Optional[str] = None,
        agent_config: Optional[AgentConfig] = None,  # Replaced filter_client_ids
    ) -> Any:
        """
        Executes a tool, either on a specific client or by discovering a unique client,
        applying agent-specific filtering if agent_config is provided.

        Args:
            tool_name: The name of the tool to execute.
            arguments: The arguments to pass to the tool.
            client_name: Optional specific client ID to execute the tool on.
                         If None, the host will attempt to find a unique client
                         providing the tool, applying agent filters if provided.
            agent_config: Optional configuration of the agent making the request, used
                          for applying client_ids and exclude_components filters.

        Returns:
            The result from the tool execution.

        Raises:
            ValueError: If client_name is None and the tool is not found or
                        is found on multiple allowed clients (ambiguous).
            ValueError: If client_name is specified but is not allowed for the agent
                        or does not provide the tool.
            ValueError: If the tool is explicitly excluded by the agent's config.
            Exception: Any exception raised during the underlying tool execution.
        """
        target_client_id: Optional[str] = None
        agent_name = agent_config.name if agent_config else "UnknownAgent"

        # 1. Determine potential clients
        if client_name:
            # Validate specified client exists (using new method)
            if not self.is_client_registered(client_name):
                raise ValueError(f"Specified client '{client_name}' is not registered.")
            # Check if this client provides the tool
            providing_clients = await self._message_router.get_clients_for_tool(
                tool_name
            )
            if client_name not in providing_clients:
                raise ValueError(
                    f"Specified client '{client_name}' does not provide tool '{tool_name}'."
                )
            potential_clients = [client_name]
        else:
            # Discover all clients providing the tool
            logger.debug(f"Discovering clients for tool '{tool_name}'...")
            potential_clients = await self._message_router.get_clients_for_tool(
                tool_name
            )
            if not potential_clients:
                raise ValueError(
                    f"Tool '{tool_name}' not found on any registered client."
                )

        # 2. Filter clients based on AgentConfig.client_ids (if provided)
        allowed_clients = potential_clients
        if agent_config:
            allowed_clients = self._filtering_manager.filter_clients_for_request(
                potential_clients, agent_config
            )
            if not allowed_clients:
                raise ValueError(
                    f"Tool '{tool_name}' is provided by clients {potential_clients}, "
                    f"but none are allowed for agent '{agent_name}' by client_ids."
                )

        # 3. Determine target client (handle ambiguity)
        if client_name:
            if client_name not in allowed_clients:
                raise ValueError(
                    f"Specified client '{client_name}' is not allowed for agent '{agent_name}'."
                )
            target_client_id = client_name
        else:
            if len(allowed_clients) > 1:
                raise ValueError(
                    f"Tool '{tool_name}' is ambiguous for agent '{agent_name}'; "
                    f"found on multiple allowed clients: {allowed_clients}. Specify a client_name."
                )
            elif not allowed_clients:
                # Should have been caught earlier
                raise ValueError(
                    f"No allowed client found for tool '{tool_name}' for agent '{agent_name}'."
                )
            else:
                target_client_id = allowed_clients[0]
                logger.info(
                    f"Determined unique allowed client '{target_client_id}' for tool '{tool_name}' for agent '{agent_name}'."
                )

        # 4. Check agent-specific component exclusion (if agent_config provided)
        if agent_config:
            if not self._filtering_manager.is_component_allowed_for_agent(
                tool_name, agent_config
            ):
                logger.warning(
                    f"Execution denied: Tool '{tool_name}' is excluded for agent '{agent_name}' by exclude_components."
                )
                raise ValueError(
                    f"Tool '{tool_name}' is excluded for agent '{agent_name}'."
                )

        # 5. Execute the tool via ToolManager
        if target_client_id:
            logger.info(
                f"Executing tool '{tool_name}' on client '{target_client_id}' for agent '{agent_name}'"
            )
            # Call the ToolManager's execute_tool, passing the determined client_name
            return await self.tools.execute_tool(
                client_name=target_client_id,  # Pass the determined client
                tool_name=tool_name,
                arguments=arguments,
            )
        else:
            # Should be unreachable
            raise ValueError(
                f"Could not determine target client for tool '{tool_name}' for agent '{agent_name}'."
            )

    async def read_resource(
        self,
        uri: str,
        client_name: Optional[str] = None,
        agent_config: Optional[AgentConfig] = None,  # Replaced filter_client_ids
    ) -> Optional[types.Resource]:
        """
        Gets a specific resource definition, discovering the client if necessary,
        applying agent-specific filtering if agent_config is provided.

        Note: This retrieves the resource *definition* (mcp.types.Resource),
              not the actual resource content. Reading content requires direct
              access to the client session's `read_resource` method.

        Args:
            uri: The URI of the resource to read.
            client_name: Optional specific client ID to read the resource from.
                         If None, the host will attempt to find a unique client
                         providing the resource, applying agent filters if provided.
            agent_config: Optional configuration of the agent making the request, used
                          for applying client_ids and exclude_components filters.

        Returns:
            The Resource definition object, or None if not found or excluded for the agent.

        Raises:
            ValueError: If client_name is None and the resource URI is not found or
                        is found on multiple allowed clients (ambiguous).
            ValueError: If client_name is specified but is not allowed for the agent
                        or does not provide the resource.
            ValueError: If the resource is explicitly excluded by the agent's config.
            Exception: Any exception raised during the underlying resource reading.
                       (Note: This method only gets the definition, not content).
        """
        uri_str = str(uri)  # Ensure string comparison
        target_client_id: Optional[str] = None
        agent_name = agent_config.name if agent_config else "UnknownAgent"
        resource_name = uri_str  # Use URI as the "name" for exclusion checks

        # 1. Determine potential clients
        if client_name:
            # Validate specified client exists (using new method)
            if not self.is_client_registered(client_name):
                raise ValueError(f"Specified client '{client_name}' is not registered.")
            # Check if this client provides the resource
            providing_clients = await self._message_router.get_clients_for_resource(
                uri_str
            )
            if client_name not in providing_clients:
                raise ValueError(
                    f"Specified client '{client_name}' does not provide resource '{uri_str}'."
                )
            potential_clients = [client_name]
        else:
            # Discover all clients providing the resource
            logger.debug(f"Discovering clients for resource '{uri_str}'...")
            potential_clients = await self._message_router.get_clients_for_resource(
                uri_str
            )
            if not potential_clients:
                logger.warning(
                    f"Resource '{uri_str}' not found on any registered client."
                )
                return None

        # 2. Filter clients based on AgentConfig.client_ids (if provided)
        allowed_clients = potential_clients
        if agent_config:
            allowed_clients = self._filtering_manager.filter_clients_for_request(
                potential_clients, agent_config
            )
            if not allowed_clients:
                logger.warning(
                    f"Resource '{uri_str}' is provided by clients {potential_clients}, "
                    f"but none are allowed for agent '{agent_name}' by client_ids."
                )
                return None

        # 3. Determine target client (handle ambiguity)
        if client_name:
            if client_name not in allowed_clients:
                raise ValueError(
                    f"Specified client '{client_name}' is not allowed for agent '{agent_name}'."
                )
            target_client_id = client_name
        else:
            if len(allowed_clients) > 1:
                raise ValueError(
                    f"Resource '{uri_str}' is ambiguous for agent '{agent_name}'; "
                    f"found on multiple allowed clients: {allowed_clients}. Specify a client_name."
                )
            elif not allowed_clients:
                logger.error(
                    f"No allowed client found for resource '{uri_str}' for agent '{agent_name}'."
                )
                return None
            else:
                target_client_id = allowed_clients[0]
                logger.info(
                    f"Found unique allowed client '{target_client_id}' for resource '{uri_str}' for agent '{agent_name}'."
                )

        # 4. Check agent-specific component exclusion (if agent_config provided)
        # We use the URI string as the component name for exclusion purposes
        if agent_config:
            if not self._filtering_manager.is_component_allowed_for_agent(
                resource_name, agent_config
            ):
                logger.warning(
                    f"Access denied: Resource '{resource_name}' is excluded for agent '{agent_name}' by exclude_components."
                )
                raise ValueError(
                    f"Resource '{resource_name}' is excluded for agent '{agent_name}'."
                )

        # 5. Get the resource definition from the target client via ResourceManager
        if target_client_id:
            logger.info(
                f"Getting resource definition '{uri_str}' from client '{target_client_id}' for agent '{agent_name}'"
            )
            return await self.resources.get_resource(
                uri=uri_str, client_id=target_client_id
            )
        else:
            # Should be unreachable
            logger.error(
                f"Could not determine target client for resource '{uri_str}' for agent '{agent_name}'."
            )
            return None

    def get_formatted_tools(
        self,
        agent_config: Optional[AgentConfig] = None,
        tool_names: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Gets the list of tools formatted for LLM use, applying agent-specific filtering.

        Args:
            agent_config: Optional configuration of the agent requesting the tools.
                          Used for filtering by client_ids and exclude_components.
            tool_names: Optional list of specific tool names to potentially include
                        (if None, considers all registered tools subject to filtering).

        Returns:
            List of formatted tool definitions ready for API calls, filtered for the agent.
        """
        # Delegate directly to ToolManager's formatting method, passing the FilteringManager
        return self.tools.format_tools_for_llm(
            filtering_manager=self._filtering_manager,
            agent_config=agent_config,
            tool_names=tool_names,
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
        # Check using the new method
        if self.is_client_registered(config.client_id):
            logger.error(f"Client ID '{config.client_id}' already registered.")
            raise ValueError(f"Client ID '{config.client_id}' already registered.")

        try:
            # Reuse the existing internal initialization logic, which now uses ClientManager
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

        # Shutdown clients via ClientManager *before* closing the main exit stack
        logger.info("Shutting down all clients via ClientManager...")
        await self.shutdown_all_clients()  # Call the new method

        # Now, close the main exit stack (which ClientManager used)
        logger.info("Closing main AsyncExitStack...")
        await self._exit_stack.aclose()

        # Clear stored agent configs
        self._agent_configs.clear()
        # Removed clearing of self._workflow_configs
        # Removed clearing of self._custom_workflow_configs

        logger.info("MCP Host shutdown complete")

    # --- New Client Lifecycle Methods ---

    async def client_shutdown(self, client_id: str):
        """
        Shuts down a specific client by ID.

        Args:
            client_id: The ID of the client to shut down.
        """
        logger.info(
            f"MCPHost requesting ClientManager to shut down client: {client_id}"
        )
        # TODO: Consider unregistering components from managers if needed before shutdown
        await self.client_manager.shutdown_client(client_id)
        # TODO: Add logic here to unregister tools/prompts/resources from managers
        # Example (needs implementation in managers):
        # await self._tool_manager.unregister_client_tools(client_id)
        # await self._prompt_manager.unregister_client_prompts(client_id)
        # await self._resource_manager.unregister_client_resources(client_id)
        # await self._message_router.unregister_server(client_id)
        logger.info(f"MCPHost completed shutdown request for client: {client_id}")

    async def shutdown_all_clients(self):
        """
        Shuts down all currently active clients managed by the ClientManager.
        """
        logger.info("MCPHost requesting ClientManager to shut down all clients...")
        # TODO: Consider unregistering components from managers if needed before shutdown
        await self.client_manager.shutdown_all_clients()
        # TODO: Add logic here to unregister all components from managers
        # Example (needs implementation in managers):
        # await self._tool_manager.unregister_all_client_tools()
        # ... etc for prompts, resources, router
        logger.info("MCPHost completed shutdown request for all clients.")
