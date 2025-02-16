"""
MCP Host implementation for managing multiple tool servers and clients.
"""

from dataclasses import dataclass
from typing import Dict, List, Any
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

logger = logging.getLogger(__name__)


@dataclass
class ClientConfig:
    """Configuration for an MCP client"""

    client_id: str
    server_path: Path
    roots: List[RootConfig]
    capabilities: List[str]
    timeout: float = 10.0  # Default timeout in seconds


@dataclass
class HostConfig:
    """Configuration for the MCP host"""

    clients: List[ClientConfig]


class MCPHost:
    """
    The MCP Host orchestrates communication between agents and tool servers through MCP clients.
    This is the highest layer of abstraction in the MCP architecture.
    """

    def __init__(self, config: HostConfig):
        # Core managers
        self._transport_manager = TransportManager()
        self._root_manager = RootManager()
        self._message_router = MessageRouter()

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
                    clientInfo=types.Implementation(name="aurite-mcp", version="0.1.0"),
                    capabilities=types.ClientCapabilities(
                        roots=types.RootsCapability(listChanged=True)
                        if "roots" in config.capabilities
                        else None,
                        sampling={} if "sampling" in config.capabilities else None,
                        experimental={},
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

            logger.info(
                f"Client {config.client_id} initialized with tools: {[t.name for t in tools_response.tools]}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize client {config.client_id}: {e}")
            raise

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

        # Get client for this tool
        client_id = await self._message_router.get_client_for_tool(tool_name)
        if not client_id:
            raise ValueError(f"No client found for tool: {tool_name}")

        client = self._clients[client_id]

        # Validate access through root manager
        await self._root_manager.validate_access(
            client_id=client_id, tool_name=tool_name
        )

        # Call the tool
        try:
            result = await client.call_tool(tool_name, arguments)
            return result.content
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

        logger.info("MCP Host shutdown complete")
