"""
MCP Host implementation for managing multiple tool servers and clients.
"""

from typing import Dict, Optional, Any, Union  # Add Union
import asyncio
import logging
from contextlib import AsyncExitStack

from mcp import (
    ClientSession,
    StdioServerParameters,
    stdio_client,
)
import mcp.types as types

# Foundation layer
from .foundation import SecurityManager, RootManager, MessageRouter
from .models import (
    HostConfig,
    ClientConfig,
)  # Renamed config.py to models.py


# Resource management layer
from .resources import PromptManager, ResourceManager, ToolManager

# Agent layer - Removed WorkflowManager import
# from .agent import WorkflowManager

logger = logging.getLogger(__name__)


class MCPHost:
    """
    The MCP Host orchestrates communication between agents and tool servers through MCP clients.
    This is the highest layer of abstraction in the MCP architecture.
    """

    def __init__(self, config: HostConfig, encryption_key: Optional[str] = None):
        # Layer 1: Foundation layer
        self._security_manager = SecurityManager(encryption_key=encryption_key)
        self._root_manager = RootManager()

        # Layer 2: Communication layer
        # self._transport_manager = TransportManager() # Removed unused manager
        self._message_router = MessageRouter()

        # Layer 3: Resource management layer
        self._prompt_manager = PromptManager()
        self._resource_manager = ResourceManager()
        # self._storage_manager = StorageManager() # Removed
        self._tool_manager = ToolManager(
            root_manager=self._root_manager, message_router=self._message_router
        )
        # Removed memory_config definition

        # Layer 4: Agent layer - Removed WorkflowManager instantiation
        # self._workflow_manager = WorkflowManager(host=self)

        # State management
        self._config = config
        self._clients: Dict[str, ClientSession] = {}

        # Track active requests
        self._active_requests: Dict[str, asyncio.Task] = {}
        self._exit_stack = AsyncExitStack()

        # Create property accessors for resource layer managers
        self.prompts = self._prompt_manager
        self.resources = self._resource_manager
        # self.storage = self._storage_manager # Removed
        self.tools = self._tool_manager
        # self.workflows = self._workflow_manager # Removed

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
        # await self._transport_manager.initialize() # Removed unused manager call
        await self._message_router.initialize()

        # Layer 3: Resource management layer
        logger.info("Initializing resource management layer...")
        await self._prompt_manager.initialize()
        await self._resource_manager.initialize()
        # await self._storage_manager.initialize() # Removed
        await self._tool_manager.initialize()

        # Removed conditional memory client initialization

        # Layer 4: Agent layer - Removed WorkflowManager initialization
        # logger.info("Initializing agent layer...")
        # await self._workflow_manager.initialize()

        # Initialize each configured client
        for client_config in self._config.clients:
            await self._initialize_client(client_config)

            # Register permissions based on capabilities
            # Removed storage-specific permission registration block
            # if "storage" in client_config.capabilities:
            #     await self._security_manager.register_server_permissions(...)
            #     await self._storage_manager.register_server_permissions(...)

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
                    clientInfo=types.Implementation(name="aurite-mcp", version="0.1.0"),
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

            # Store client and register with tool manager
            self._clients[config.client_id] = session

            if "tools" in config.capabilities:
                self._tool_manager.register_client(config.client_id, session)

                # Discover tools and register with the tool manager
                tools_response = await self._tool_manager.discover_client_tools(
                    client_id=config.client_id, client_session=session
                )

                # Update tool capabilities based on client capabilities
                for tool in tools_response.tools:
                    await self._tool_manager.register_tool(
                        tool_name=tool.name,
                        tool=tool,
                        client_id=config.client_id,
                        capabilities=config.capabilities,
                        exclude_list=config.exclude,
                    )

            # Initialize prompts if supported
            if "prompts" in config.capabilities:
                prompts_response = await session.list_prompts()
                await self._prompt_manager.register_client_prompts(
                    config.client_id, prompts_response.prompts, config.exclude
                )

            # Initialize resources if supported
            if "resources" in config.capabilities:
                resources_response = await session.list_resources()
                await self._resource_manager.register_client_resources(
                    config.client_id, resources_response.resources, config.exclude
                )

            logger.info(
                f"Client {config.client_id} initialized with tools: {[t.name for t in tools_response.tools]}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize client {config.client_id}: {e}")
            raise

    # prepare_prompt_with_tools method removed.
    # Logic moved to Agent.execute in src/agents/agent.py

    # execute_prompt_with_tools method removed.
    # Logic moved to Agent.execute in src/agents/agent.py

    async def get_prompt(
        self,
        prompt_name: str,
        arguments: Dict[str, Any],
        client_name: Optional[str] = None,
    ) -> Optional[Union[types.Prompt, types.GetPromptResult]]:
        """
        Gets a specific prompt template, discovering the client if necessary.

        Note: This currently only retrieves the prompt *template*.
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
                         providing the prompt.

        Returns:
            The Prompt template object, or None if not found.

        Raises:
            ValueError: If client_name is None and the prompt is not found or
                        is found on multiple clients (ambiguous).
        """
        if client_name:
            logger.info(
                f"Getting prompt template '{prompt_name}' from specified client '{client_name}'"
            )
            # Note: Passing arguments here, though manager currently ignores them for template retrieval
            return await self.prompts.get_prompt(
                name=prompt_name, client_id=client_name
            )
        else:
            logger.info(
                f"Discovering client for prompt '{prompt_name}' before retrieval..."
            )
            providing_clients = self.prompts.get_clients_for_prompt(prompt_name)

            if not providing_clients:
                # Return None if not found, consistent with manager's get_prompt
                logger.warning(
                    f"Prompt '{prompt_name}' not found on any registered client."
                )
                return None
                # Or raise ValueError("Prompt '{prompt_name}' not found...") if preferred
            elif len(providing_clients) > 1:
                raise ValueError(
                    f"Prompt '{prompt_name}' is ambiguous; found on multiple clients: "
                    f"{providing_clients}. Specify a client_name."
                )
            else:
                unique_client_id = providing_clients[0]
                logger.info(
                    f"Getting prompt template '{prompt_name}' from uniquely found client '{unique_client_id}'"
                )
                return await self.prompts.get_prompt(
                    name=prompt_name, client_id=unique_client_id
                )

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        client_name: Optional[str] = None,
    ) -> Any:
        """
        Executes a tool, either on a specific client or by discovering a unique client.

        Args:
            tool_name: The name of the tool to execute.
            arguments: The arguments to pass to the tool.
            client_name: Optional specific client ID to execute the tool on.
                         If None, the host will attempt to find a unique client
                         providing the tool.

        Returns:
            The result from the tool execution (typically List[TextContent]).

        Raises:
            ValueError: If client_name is None and the tool is not found or
                        is found on multiple clients (ambiguous).
            Exception: Any exception raised during the underlying tool execution.
        """
        if client_name:
            # Direct execution on specified client
            logger.info(
                f"Executing tool '{tool_name}' on specified client '{client_name}'"
            )
            return await self.tools.execute_tool(
                client_name=client_name, tool_name=tool_name, arguments=arguments
            )
        else:
            # Discover client providing the tool
            logger.info(
                f"Discovering client for tool '{tool_name}' before execution..."
            )
            providing_clients = self.tools.get_clients_for_tool(tool_name)

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
                unique_client_id = providing_clients[0]
                logger.info(
                    f"Executing tool '{tool_name}' on uniquely found client '{unique_client_id}'"
                )
                return await self.tools.execute_tool(
                    client_name=unique_client_id,
                    tool_name=tool_name,
                    arguments=arguments,
                )

    async def read_resource(
        self, uri: str, client_name: Optional[str] = None
    ) -> Optional[types.Resource]:
        """
        Reads a specific resource, discovering the client if necessary.

        Args:
            uri: The URI of the resource to read.
            client_name: Optional specific client ID to read the resource from.
                         If None, the host will attempt to find a unique client
                         providing the resource.

        Returns:
            The Resource object, or None if not found.

        Raises:
            ValueError: If client_name is None and the resource URI is not found or
                        is found on multiple clients (ambiguous).
            Exception: Any exception raised during the underlying resource reading.
                       (Note: The manager's get_resource currently doesn't read,
                        it just returns the registered Resource object. Reading
                        happens via session.read_resource, which isn't wrapped here yet).
        """
        uri_str = str(uri)  # Ensure string comparison
        if client_name:
            logger.info(
                f"Getting resource definition '{uri_str}' from specified client '{client_name}'"
            )
            # Note: This currently returns the *registered* resource definition,
            # not the *content* read from the server.
            return await self.resources.get_resource(uri=uri_str, client_id=client_name)
        else:
            logger.info(
                f"Discovering client for resource '{uri_str}' before retrieval..."
            )
            providing_clients = self.resources.get_clients_for_resource(uri_str)

            if not providing_clients:
                logger.warning(
                    f"Resource '{uri_str}' not found on any registered client."
                )
                return None
            elif len(providing_clients) > 1:
                raise ValueError(
                    f"Resource URI '{uri_str}' is ambiguous; found on multiple clients: "
                    f"{providing_clients}. Specify a client_name."
                )
            else:
                unique_client_id = providing_clients[0]
                logger.info(
                    f"Getting resource definition '{uri_str}' from uniquely found client '{unique_client_id}'"
                )
                return await self.resources.get_resource(
                    uri=uri_str, client_id=unique_client_id
                )

    # Removed register_workflow, execute_workflow, list_workflows, get_workflow methods
    # Removed add_memories and search_memories methods

    async def shutdown(self):
        """Shutdown the host and cleanup all resources"""
        logger.info("Shutting down MCP Host...")

        # Cancel any active requests
        for task in self._active_requests.values():
            task.cancel()

        # Close all resources using the exit stack
        await self._exit_stack.aclose()
        # logger.warning("Skipping AsyncExitStack.aclose() for debugging.") # Re-enabled after debugging

        # Shutdown managers in reverse layer order

        # Layer 4: Agent layer - Removed WorkflowManager shutdown
        # logger.info("Shutting down agent layer...")
        # await self._workflow_manager.shutdown()

        # Layer 3: Resource management layer
        logger.info("Shutting down resource management layer...")
        await self._prompt_manager.shutdown()
        await self._resource_manager.shutdown()
        # await self._storage_manager.shutdown() # Removed
        await self._tool_manager.shutdown()

        # Layer 2: Communication layer
        logger.info("Shutting down communication layer...")
        # await self._transport_manager.shutdown() # Removed unused manager call
        await self._message_router.shutdown()

        # Layer 1: Foundation layer
        logger.info("Shutting down foundation layer...")
        await self._security_manager.shutdown()
        await self._root_manager.shutdown()

        logger.info("MCP Host shutdown complete")
