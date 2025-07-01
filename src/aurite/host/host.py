"""
MCP Host implementation for managing MCP client connections and interactions.
"""

import logging  # Removed importlib, inspect, Path
from contextlib import AsyncExitStack
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
)  # Kept Any, Dict, List, Optional as they are used elsewhere

import anyio  # Import anyio
from anyio import abc
import mcp.types as types

# Foundation layer
from .foundation import (
    SecurityManager,
    RootManager,
    MessageRouter,
    ClientManager,
)  # Added ClientManager
from .filtering import FilteringManager
from ..config.config_models import (  # Changed to relative import
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
        encryption_key: Optional[str] = None,
    ):
        # Layer 1: Foundation layer
        self._security_manager = SecurityManager(encryption_key=encryption_key)
        self._root_manager = RootManager()

        # Layer 2: Communication layer
        self._message_router = MessageRouter()
        self._filtering_manager = FilteringManager()  # Removed message_router argument

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
        # self._agent_configs = agent_configs or {} # Removed
        # Removed self._workflow_configs initialization
        # Removed self._custom_workflow_configs initialization
        # self._clients: Dict[str, ClientSession] = {} # Removed

        # MCPHost's main exit stack for managing its own resources, including the client runners task group
        self._main_exit_stack = AsyncExitStack()
        self._client_runners_task_group: Optional[abc.TaskGroup] = None
        self._client_cancel_scopes: Dict[str, anyio.CancelScope] = {}

        self.client_manager = ClientManager()  # Updated instantiation

        # Create property accessors for resource layer managers
        self.prompts = self._prompt_manager
        self.resources = self._resource_manager
        self.tools = self._tool_manager

    async def initialize(self):
        """Initialize the host and all configured clients"""
        logger.debug("Initializing MCP Host...")  # Changed to DEBUG

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

        # Create and enter the main task group for client runners
        if (
            self._client_runners_task_group is None
        ):  # Should always be None here unless initialize is called multiple times
            self._client_runners_task_group = (
                await self._main_exit_stack.enter_async_context(
                    anyio.create_task_group()
                )
            )
            logger.debug("Main client runners task group created and entered.")
        else:
            logger.warning(
                "Initialize called but _client_runners_task_group already exists."
            )

        # Initialize each configured client
        successful_initializations = 0
        num_configured_clients = len(self._config.mcp_servers)

        for client_config in self._config.mcp_servers:
            try:
                await self._initialize_client(client_config)
                successful_initializations += 1
            except Exception as e:
                logger.error(
                    f"Failed to initialize client '{client_config.name}'. "
                    f"This client will be unavailable. Error: {e}",
                    exc_info=True,
                )
                # Continue to the next client

        num_active_clients = len(
            self.client_manager.active_clients
        )  # Should reflect successfully started ones

        logger.info(
            f"MCP Host initialization attempt finished. "
            f"Successfully initialized {num_active_clients}/{num_configured_clients} configured clients. "
        )

        if num_active_clients < num_configured_clients:
            logger.warning(
                f"{num_configured_clients - num_active_clients} client(s) failed to initialize. "
                "Check error logs for details. Host will continue with available clients."
            )
            logger.debug("MCP Host initialization partially complete.")
        else:
            logger.debug("MCP Host initialization fully complete for all clients.")

    async def _initialize_client(self, config: ClientConfig):
        """Initialize a single client connection"""
        logger.debug(f"Initializing client: {config.name}")

        try:
            if self._client_runners_task_group is None:
                # This should not happen if initialize was called correctly
                logger.error(
                    "_initialize_client called before _client_runners_task_group was created."
                )
                raise RuntimeError("Client runners task group not initialized.")

            client_id = config.name
            client_scope = anyio.CancelScope()
            self._client_cancel_scopes[client_id] = client_scope

            logger.debug(
                f"Starting client lifecycle task for {client_id} in task group."
            )
            session = await self._client_runners_task_group.start(
                self.client_manager.manage_client_lifecycle,
                config,
                self._security_manager,
                client_scope,
                # task_status is implicitly handled by tg.start()
            )
            logger.debug(
                f"Client session for {client_id} obtained from lifecycle task."
            )

            # --- Communication and Registration (using the session returned by the lifecycle task) ---
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
                await self._root_manager.register_roots(config.name, config.roots)

            # Register server capabilities with router
            await self._message_router.register_server(
                server_id=config.name,
                capabilities=set(config.capabilities),
                weight=config.routing_weight,
            )

            # Client session is stored in self.client_manager.active_clients
            # self._clients[config.name] = session # Removed

            # Discover and register components based on capabilities, applying exclusions
            tool_names = []
            prompt_names = []
            resource_names = []

            if "tools" in config.capabilities:
                self._tool_manager.register_client(config.name, session)
                # discover_client_tools now returns List[types.Tool] directly
                discovered_tools = await self._tool_manager.discover_client_tools(
                    client_id=config.name, client_session=session
                )
                # --- Removed detailed logging ---
                for tool in discovered_tools:  # Iterate directly over the list
                    # Pass FilteringManager and ClientConfig to allow manager to check exclusion
                    registered = await self._tool_manager.register_tool(
                        tool_name=tool.name,
                        tool=tool,
                        client_id=config.name,
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
                    client_id=config.name,
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
                        client_id=config.name,
                        resources=resources_response.resources,
                        client_config=config,  # Pass the whole config
                        filtering_manager=self._filtering_manager,  # Pass the manager
                    )
                )
                resource_names = [r.name for r in registered_resources]

            logger.debug(  # Changed to DEBUG
                f"Client '{config.name}' initialized. "
                f"Tools: {tool_names}, Prompts: {prompt_names}, Resources: {resource_names}"
            )
            # --- End of restored section ---

        except Exception as e:
            logger.error(
                f"Failed to initialize client {config.name}: {e}"
            )  # Keep error as ERROR
            raise

    def is_client_registered(self, client_id: str) -> bool:
        """Checks if a client with the given ID is registered."""
        # Check in ClientManager's active clients
        return client_id in self.client_manager.active_clients

    async def get_prompt(
        self,
        prompt_name: str,
        arguments: Dict[str, Any],
        client_name: Optional[str] = None,
        agent_config: Optional[AgentConfig] = None,
    ) -> Optional[types.Prompt]:
        """
        Gets a specific prompt template definition by resolving the target client
        and delegating to the PromptManager.
        """
        target_client_id = await self._resolve_target_client_for_component(
            component_name=prompt_name,
            component_type="prompt",
            client_name=client_name,
            agent_config=agent_config,
        )
        return await self.prompts.get_prompt(
            name=prompt_name, client_id=target_client_id
        )

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        client_name: Optional[str] = None,
        agent_config: Optional[AgentConfig] = None,
    ) -> Any:
        """
        Executes a tool by resolving the target client and delegating to the ToolManager.
        """
        target_client_id = await self._resolve_target_client_for_component(
            component_name=tool_name,
            component_type="tool",
            client_name=client_name,
            agent_config=agent_config,
        )
        return await self.tools.execute_tool(
            client_name=target_client_id,
            tool_name=tool_name,
            arguments=arguments,
        )

    async def read_resource(
        self,
        uri: str,
        client_name: Optional[str] = None,
        agent_config: Optional[AgentConfig] = None,
    ) -> Optional[types.Resource]:
        """
        Gets a specific resource definition by resolving the target client and
        delegating to the ResourceManager.
        """
        target_client_id = await self._resolve_target_client_for_component(
            component_name=uri,
            component_type="resource",
            client_name=client_name,
            agent_config=agent_config,
        )
        return await self.resources.get_resource(uri=uri, client_id=target_client_id)

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

    async def _resolve_target_client_for_component(
        self,
        component_name: str,
        component_type: Literal["tool", "prompt", "resource"],
        client_name: Optional[str] = None,
        agent_config: Optional[AgentConfig] = None,
    ) -> str:
        """
        Resolves which client should be used for a given component request.

        This method centralizes the logic for:
        1. Discovering clients that provide the component.
        2. Filtering clients based on the agent's allowed list (`mcp_servers`).
        3. Resolving ambiguity to find a single target client.
        4. Validating against the agent's exclusion list (`exclude_components`).

        Args:
            component_name: The name of the tool, prompt, or resource URI.
            component_type: The type of the component ('tool', 'prompt', or 'resource').
            client_name: An optional, specific client to use.
            agent_config: The configuration of the agent making the request.

        Returns:
            The resolved client ID as a string.

        Raises:
            ValueError: If no suitable client can be found, if the request is
                        ambiguous, or if the component is disallowed for the agent.
        """
        agent_name = agent_config.name if agent_config else "UnknownAgent"

        # 1. Discover potential clients based on component type
        if client_name:
            if not self.is_client_registered(client_name):
                raise ValueError(f"Specified client '{client_name}' is not registered.")
            potential_clients = [client_name]
        else:
            if component_type == "tool":
                potential_clients = await self._message_router.get_clients_for_tool(
                    component_name
                )
            elif component_type == "prompt":
                potential_clients = await self._message_router.get_clients_for_prompt(
                    component_name
                )
            elif component_type == "resource":
                potential_clients = await self._message_router.get_clients_for_resource(
                    component_name
                )
            else:
                raise ValueError(f"Invalid component_type: {component_type}")

            if not potential_clients:
                raise ValueError(
                    f"{component_type.capitalize()} '{component_name}' not found on any registered client."
                )

        # 2. Filter clients based on AgentConfig
        allowed_clients = potential_clients
        if agent_config:
            allowed_clients = self._filtering_manager.filter_clients_for_request(
                potential_clients, agent_config
            )
            if not allowed_clients:
                raise ValueError(
                    f"{component_type.capitalize()} '{component_name}' is provided by clients {potential_clients}, "
                    f"but none are allowed for agent '{agent_name}' by its mcp_servers list."
                )

        # 3. Resolve to a single target client
        target_client_id: str
        if client_name:
            if client_name not in allowed_clients:
                raise ValueError(
                    f"Specified client '{client_name}' is not allowed for agent '{agent_name}'."
                )
            target_client_id = client_name
        else:
            if len(allowed_clients) > 1:
                raise ValueError(
                    f"{component_type.capitalize()} '{component_name}' is ambiguous for agent '{agent_name}'; "
                    f"found on multiple allowed clients: {allowed_clients}. Specify a client_name."
                )
            target_client_id = allowed_clients[0]

        # 4. Validate against agent's explicit exclusion list
        if agent_config and not self._filtering_manager.is_component_allowed_for_agent(
            component_name, agent_config
        ):
            raise ValueError(
                f"{component_type.capitalize()} '{component_name}' is explicitly excluded for agent '{agent_name}'."
            )

        logger.debug(
            f"Resolved client '{target_client_id}' for {component_type} '{component_name}' for agent '{agent_name}'."
        )
        return target_client_id

    async def register_client(self, config: ClientConfig):
        """
        Dynamically registers and initializes a new client after the host has started.

        Args:
            config: The configuration for the client to register.

        Raises:
            ValueError: If a client with the same ID is already registered.
            Exception: Propagates exceptions from the underlying client initialization process.
        """
        logger.info(f"Attempting to dynamically register client: {config.name}")
        # Check using the new method
        if self.is_client_registered(config.name):
            logger.error(f"Client ID '{config.name}' already registered.")
            raise ValueError(f"Client ID '{config.name}' already registered.")

        try:
            # Reuse the existing internal initialization logic, which now uses ClientManager
            await self._initialize_client(config)
            logger.info(
                f"Client '{config.name}' dynamically registered and initialized successfully."
            )
        except Exception as e:
            logger.error(
                f"Failed to dynamically register client '{config.name}': {e}",
                exc_info=True,
            )
            # Re-raise the exception for the caller (Aurite) to handle
            raise

    async def shutdown(self):
        """Shutdown the host and cleanup all resources"""
        logger.debug("Shutting down MCP Host...")

        # Shutdown managers first, in reverse layer order, before closing connections

        # Layer 3: Resource management layer
        logger.debug("Shutting down resource management layer...")  # Changed to DEBUG
        await self._prompt_manager.shutdown()
        await self._resource_manager.shutdown()
        await self._tool_manager.shutdown()

        # Layer 2: Communication layer
        logger.debug("Shutting down communication layer...")  # Changed to DEBUG
        await self._message_router.shutdown()

        # Layer 1: Foundation layer
        logger.debug("Shutting down foundation layer...")  # Changed to DEBUG
        await self._security_manager.shutdown()
        await self._root_manager.shutdown()

        # Call shutdown_all_clients to unregister components and cancel individual client scopes
        logger.debug(
            "Calling shutdown_all_clients to unregister components and cancel individual client scopes..."
        )
        await self.shutdown_all_clients()

        # Cancel the main client runners task group itself.
        # This will wait for all tasks within it (the client lifecycle tasks) to finish their cancellation.
        if self._client_runners_task_group:
            logger.debug("Cancelling main client runners task group...")
            self._client_runners_task_group.cancel_scope.cancel()
            # The waiting for this task group to actually finish happens when _main_exit_stack is closed,
            # as the task group was entered into it.
        else:
            logger.debug("No main client runners task group to cancel.")

        # Now, close the main exit stack. This will await the _client_runners_task_group
        # if it was entered, and any other resources MCPHost might manage in it.
        logger.debug("Closing main AsyncExitStack for MCPHost...")
        await self._main_exit_stack.aclose()

        # Clear any remaining state related to client scopes, just in case
        self._client_cancel_scopes.clear()
        self._client_runners_task_group = None  # Ensure it's reset

        # self._agent_configs.clear() # Removed, as _agent_configs is removed
        # Removed clearing of self._workflow_configs
        # Removed clearing of self._custom_workflow_configs

        logger.debug("MCP Host shutdown complete")

    # --- New Client Lifecycle Methods ---

    async def client_shutdown(self, client_id: str):
        """
        Shuts down a specific client by ID.

        Args:
            client_id: The ID of the client to shut down.
        """
        logger.debug(  # Changed to DEBUG
            f"MCPHost requesting ClientManager to shut down client: {client_id}"
        )
        # Unregister components from managers *before* shutting down the client session
        logger.debug(f"Unregistering components for client '{client_id}'...")
        await self._tool_manager.unregister_client_tools(client_id)
        await self._prompt_manager.unregister_client_prompts(client_id)
        await self._resource_manager.unregister_client_resources(client_id)
        await self._message_router.unregister_server(client_id)
        logger.debug(f"Component unregistration complete for client '{client_id}'.")

        # Now request ClientManager to shut down the client session and process
        # await self.client_manager.shutdown_client(client_id) # Removed, ClientManager no longer has this

        # Cancel the specific client's task scope
        client_scope = self._client_cancel_scopes.pop(client_id, None)
        if client_scope:
            client_scope.cancel()
            logger.debug(f"Cancelled client task scope for {client_id}.")
        else:
            logger.warning(
                f"No cancel scope found for client {client_id} during shutdown."
            )

        # Remove the client from the ClientManager's active list
        if client_id in self.client_manager.active_clients:
            del self.client_manager.active_clients[client_id]
            logger.debug(f"Removed client {client_id} from ClientManager active list.")
        else:
            # This might happen if shutdown is called multiple times or after an error
            logger.warning(
                f"Client {client_id} not found in ClientManager active list during shutdown."
            )

        logger.debug(
            f"MCPHost completed shutdown request for client: {client_id}"
        )  # Changed to DEBUG

    async def shutdown_all_clients(self):
        """
        Shuts down all currently active clients managed by the ClientManager.
        """
        logger.debug(
            "MCPHost requesting ClientManager to shut down all clients..."
        )  # Changed to DEBUG

        # Get a list of client IDs for which we have cancel scopes
        # Iterate over a copy of keys if modifying the dict during iteration (pop)
        client_ids_to_shutdown = list(self._client_cancel_scopes.keys())
        logger.debug(
            f"Shutting down and unregistering components for clients: {client_ids_to_shutdown}"
        )

        for client_id in client_ids_to_shutdown:
            logger.debug(
                f"Unregistering components for client '{client_id}' during shutdown_all_clients..."
            )
            await self._tool_manager.unregister_client_tools(client_id)
            await self._prompt_manager.unregister_client_prompts(client_id)
            await self._resource_manager.unregister_client_resources(client_id)
            await self._message_router.unregister_server(client_id)
            logger.debug(f"Component unregistration complete for client '{client_id}'.")

            # Cancel the specific client's task scope
            client_scope = self._client_cancel_scopes.pop(client_id, None)
            if client_scope:
                client_scope.cancel()
                logger.debug(
                    f"Cancelled client task scope for {client_id} during shutdown_all_clients."
                )
            else:
                # This case should ideally not happen if _client_cancel_scopes is managed correctly
                logger.warning(
                    f"No cancel scope found for client {client_id} during shutdown_all_clients."
                )

        # ClientManager no longer has shutdown_all_clients.
        # The cancellation of individual scopes above, followed by the cancellation
        # of _client_runners_task_group in MCPHost.shutdown(), handles this.

        # TODO: Add logic here to unregister all components from managers # This TODO is now addressed above
        # Example (needs implementation in managers):
        # await self._tool_manager.unregister_all_client_tools() # Addressed above
        # ... etc for prompts, resources, router
        logger.debug(
            "MCPHost completed shutdown request for all clients."
        )  # Changed to DEBUG
