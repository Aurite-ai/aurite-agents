"""
MCP Host implementation for managing multiple tool servers and clients.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
import asyncio
import logging
from pathlib import Path
from contextlib import AsyncExitStack

from mcp import (
    ClientSession,
    StdioServerParameters,
    stdio_client,
)
import mcp.types as types

from .transport import TransportManager
from .roots import RootManager, RootConfig
from .routing import MessageRouter
from .prompts import PromptManager
from .resources import ResourceManager
from .security import SecurityManager
from .connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


@dataclass
class ClientConfig:
    """Configuration for an MCP client"""

    client_id: str
    server_path: Path
    roots: List[RootConfig]
    capabilities: List[str]
    timeout: float = 10.0  # Default timeout in seconds
    routing_weight: float = 1.0  # New: Weight for server selection


@dataclass
class HostConfig:
    """Configuration for the MCP host"""

    clients: List[ClientConfig]


class MCPHost:
    """
    The MCP Host orchestrates communication between agents and tool servers through MCP clients.
    This is the highest layer of abstraction in the MCP architecture.
    """

    def __init__(self, config: HostConfig, encryption_key: Optional[str] = None):
        # Core managers
        self._transport_manager = TransportManager()
        self._root_manager = RootManager()
        self._message_router = MessageRouter()
        self._prompt_manager = PromptManager()
        self._resource_manager = ResourceManager()
        self._security_manager = SecurityManager(encryption_key=encryption_key)
        self._connection_manager = ConnectionManager()

        # State management
        self._config = config
        self._clients: Dict[str, ClientSession] = {}
        self._tools: Dict[str, types.Tool] = {}

        # Track active requests
        self._active_requests: Dict[str, asyncio.Task] = {}
        self._exit_stack = AsyncExitStack()

    async def initialize(self):
        """Initialize the host and all configured clients"""
        logger.info("Initializing MCP Host...")

        # Initialize subsystems
        await self._transport_manager.initialize()
        await self._root_manager.initialize()
        await self._message_router.initialize()
        await self._prompt_manager.initialize()
        await self._resource_manager.initialize()
        await self._security_manager.initialize()
        await self._connection_manager.initialize()

        # Initialize each configured client
        for client_config in self._config.clients:
            await self._initialize_client(client_config)

            # Register permissions based on capabilities
            if "storage" in client_config.capabilities:
                await self._security_manager.register_server_permissions(
                    client_config.client_id,
                    allowed_credential_types=["database_connection"],
                )

                # Register database connection permissions
                await self._connection_manager.register_server_permissions(
                    client_config.client_id,
                    allowed_connection_types=["postgresql", "mysql", "sqlite"],
                )

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
            await self._root_manager.register_roots(config.client_id, config.roots)

            # Register server capabilities with router
            await self._message_router.register_server(
                server_id=config.client_id,
                capabilities=set(config.capabilities),
                weight=config.routing_weight,
            )

            # Store client and discover tools
            self._clients[config.client_id] = session
            tools_response = await session.list_tools()

            # Register tools with router
            for tool in tools_response.tools:
                self._tools[tool.name] = tool
                await self._message_router.register_tool(
                    tool_name=tool.name,
                    client_id=config.client_id,
                    capabilities=config.capabilities,
                )

            # Initialize prompts if supported
            if "prompts" in config.capabilities:
                prompts_response = await session.list_prompts()
                await self._prompt_manager.register_client_prompts(
                    config.client_id, prompts_response.prompts
                )

            # Initialize resources if supported
            if "resources" in config.capabilities:
                resources_response = await session.list_resources()
                await self._resource_manager.register_client_resources(
                    config.client_id, resources_response.resources
                )

            logger.info(
                f"Client {config.client_id} initialized with tools: {[t.name for t in tools_response.tools]}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize client {config.client_id}: {e}")
            raise

    # Prompt-related methods
    async def list_prompts(self, client_id: Optional[str] = None) -> List[types.Prompt]:
        """List all available prompts, optionally filtered by client"""
        return await self._prompt_manager.list_prompts(client_id)

    async def execute_prompt(
        self, name: str, arguments: Dict[str, Any], client_id: str
    ) -> types.GetPromptResult:
        """Execute a prompt with given arguments"""
        prompt = await self._prompt_manager.get_prompt(name, client_id)
        if not prompt:
            raise ValueError(f"Prompt not found: {name}")

        # Validate arguments
        await self._prompt_manager.validate_prompt_arguments(prompt, arguments)

        # Execute prompt through client
        client = self._clients[client_id]
        return await client.get_prompt(name, arguments)

    # Resource-related methods
    async def list_resources(
        self, client_id: Optional[str] = None
    ) -> List[types.Resource]:
        """List all available resources, optionally filtered by client"""
        return await self._resource_manager.list_resources(client_id)

    async def read_resource(self, uri: str, client_id: str) -> types.ResourceContents:
        """Read a resource's content"""
        # Validate access
        await self._resource_manager.validate_resource_access(
            uri, client_id, self._root_manager
        )

        # Get resource through client
        client = self._clients[client_id]
        return await client.read_resource(uri)

    async def subscribe_to_resource(self, uri: str, client_id: str):
        """Subscribe to resource updates"""
        await self._resource_manager.subscribe(uri, client_id)

    async def unsubscribe_from_resource(self, uri: str, client_id: str):
        """Unsubscribe from resource updates"""
        await self._resource_manager.unsubscribe(uri, client_id)

    async def handle_resource_update(self, uri: str):
        """Handle resource content changes"""
        subscribers = await self._resource_manager.get_subscribers(uri)
        for client_id in subscribers:
            client = self._clients[client_id]
            await client.send_notification(
                "notifications/resources/updated", {"uri": uri}
            )

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> List[types.TextContent]:
        """
        Call a tool by name with the given arguments.
        Routes the request through the appropriate client.
        """
        # Validate tool exists
        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Get server for this tool (using enhanced routing)
        server_id = await self._message_router.select_server_for_tool(
            tool_name,
            required_capabilities=set(),  # Could be derived from arguments/context
        )
        if not server_id:
            raise ValueError(f"No server found for tool: {tool_name}")

        client = self._clients[server_id]

        # Validate access through root manager
        await self._root_manager.validate_access(
            client_id=server_id, tool_name=tool_name
        )

        # Call the tool
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
                raise ValueError(
                    result.content[0].text if result.content else "Unknown error"
                )
            if hasattr(result, "content"):
                return result.content
            return result
        except Exception as e:
            logger.error(f"Tool call failed - {tool_name}: {e}")
            raise

    async def shutdown(self):
        """Shutdown the host and cleanup all resources"""
        logger.info("Shutting down MCP Host...")

        # Cancel any active requests
        for task in self._active_requests.values():
            task.cancel()

        # Close all resources using the exit stack
        await self._exit_stack.aclose()

        # Shutdown managers
        await self._transport_manager.shutdown()
        await self._root_manager.shutdown()
        await self._message_router.shutdown()
        await self._prompt_manager.shutdown()
        await self._resource_manager.shutdown()
        await self._security_manager.shutdown()
        await self._connection_manager.shutdown()

        logger.info("MCP Host shutdown complete")

    async def create_database_connection(
        self, params: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Create a database connection from parameters and return a connection ID.

        Args:
            params: Connection parameters including type, host, database, username, password

        Returns:
            Tuple of (connection_id, connection_metadata)
        """
        return await self._connection_manager.create_db_connection(params)

    async def get_named_connection(
        self, connection_name: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Get a connection for a named database configuration.

        Args:
            connection_name: Name of the pre-configured connection

        Returns:
            Tuple of (connection_id, connection_metadata)
        """
        return await self._connection_manager.get_named_connection(connection_name)

    async def execute_query(
        self, conn_id: str, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a query on a database connection.

        Args:
            conn_id: Connection ID
            query: SQL query to execute
            params: Query parameters

        Returns:
            Query result dictionary
        """
        return await self._connection_manager.execute_query(conn_id, query, params)

    async def close_connection(self, conn_id: str) -> bool:
        """
        Close a database connection.

        Args:
            conn_id: Connection ID

        Returns:
            True if connection was closed, False if it wasn't found
        """
        return await self._connection_manager.close_connection(conn_id)

    async def list_active_connections(self) -> List[Dict[str, Any]]:
        """List all active connections with metadata"""
        return await self._connection_manager.list_active_connections()

    # Keep this for backward compatibility
    async def secure_database_connection(
        self, connection_string: str
    ) -> Tuple[str, str]:
        """
        Legacy method for compatibility. Creates a database connection from a connection string.

        Args:
            connection_string: Raw database connection string with credentials

        Returns:
            Tuple of (connection_id, masked_connection_string)
        """
        # Parse connection string to extract parameters
        try:
            # Determine type
            if "postgresql" in connection_string:
                db_type = "postgresql"
            elif "mysql" in connection_string:
                db_type = "mysql"
            elif "sqlite" in connection_string:
                db_type = "sqlite"
            else:
                raise ValueError(
                    f"Unsupported database type in connection string: {connection_string}"
                )

            # Parse standard format: dialect://username:password@host:port/database
            if db_type != "sqlite":
                # Extract username and password
                auth_part = connection_string.split("//")[1].split("@")[0]
                username, password = auth_part.split(":")

                # Extract host, port, and database
                host_db_part = connection_string.split("@")[1]
                host_port, database = host_db_part.split("/", 1)

                # Handle port
                if ":" in host_port:
                    host, port = host_port.split(":")
                    port = int(port)
                    params = {
                        "type": db_type,
                        "host": host,
                        "port": port,
                        "database": database,
                        "username": username,
                        "password": password,
                    }
                else:
                    params = {
                        "type": db_type,
                        "host": host_port,
                        "database": database,
                        "username": username,
                        "password": password,
                    }
            else:
                # SQLite connection string: sqlite:///path/to/database.db
                database = connection_string.split("///")[1]
                params = {"type": "sqlite", "database": database}

            # Create connection
            conn_id, metadata = await self.create_database_connection(params)

            # Return connection ID and masked connection string
            return conn_id, metadata.get("connection_string", "")
        except Exception as e:
            logger.error(f"Error creating database connection: {e}")
            raise
