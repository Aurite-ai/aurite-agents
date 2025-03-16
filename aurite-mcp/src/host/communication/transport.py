"""
Transport management for MCP host.
"""

from enum import Enum
from typing import Dict, Optional, Any
import logging
from dataclasses import dataclass

from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters

logger = logging.getLogger(__name__)


class TransportType(Enum):
    """Supported transport types"""

    STDIO = "stdio"
    SSE = "sse"


@dataclass
class TransportConfig:
    """Configuration for a transport"""

    type: TransportType
    options: Dict[str, Any]


class TransportManager:
    """
    Manages different transport types and their lifecycles.
    Currently supports stdio and SSE transports.
    """

    def __init__(self):
        self._transports: Dict[str, Any] = {}  # client_id -> transport
        self._configs: Dict[str, TransportConfig] = {}  # client_id -> config
        self._active: Dict[str, bool] = {}  # client_id -> is_active

    async def initialize(self):
        """Initialize the transport manager"""
        logger.info("Initializing transport manager")

    async def create_transport(self, client_id: str, config: TransportConfig) -> Any:
        """
        Create a new transport for a client based on configuration.
        Returns the transport object.
        """
        if client_id in self._transports:
            raise ValueError(f"Transport already exists for client: {client_id}")

        try:
            transport = await self._create_transport_instance(config)

            self._transports[client_id] = transport
            self._configs[client_id] = config
            self._active[client_id] = True

            return transport

        except Exception as e:
            logger.error(f"Failed to create transport for {client_id}: {e}")
            raise

    async def _create_transport_instance(self, config: TransportConfig) -> Any:
        """Create the appropriate transport instance based on type"""
        if config.type == TransportType.STDIO:
            return await self._create_stdio_transport(config.options)
        elif config.type == TransportType.SSE:
            return await self._create_sse_transport(config.options)
        else:
            raise ValueError(f"Unsupported transport type: {config.type}")

    async def _create_stdio_transport(self, options: Dict[str, Any]) -> Any:
        """Create a stdio transport"""
        server_params = StdioServerParameters(
            command=options.get("command", "python"),
            args=options.get("args", []),
            env=options.get("env"),
        )
        return await stdio_client(server_params)

    async def _create_sse_transport(self, options: Dict[str, Any]) -> Any:
        """Create an SSE transport"""
        # TODO: Implement SSE transport
        raise NotImplementedError("SSE transport not yet implemented")

    async def get_transport(self, client_id: str) -> Optional[Any]:
        """Get the transport for a client if it exists"""
        return self._transports.get(client_id)

    async def close_transport(self, client_id: str):
        """Close a transport and cleanup resources"""
        if client_id not in self._transports:
            return

        try:
            transport = self._transports[client_id]
            # Close transport (implementation depends on transport type)
            if hasattr(transport, "aclose"):
                await transport.aclose()

            del self._transports[client_id]
            del self._configs[client_id]
            del self._active[client_id]

        except Exception as e:
            logger.error(f"Error closing transport for {client_id}: {e}")
            raise

    async def shutdown(self):
        """Shutdown all transports"""
        logger.info("Shutting down transport manager")

        # Close all active transports
        for client_id in list(self._transports.keys()):
            await self.close_transport(client_id)
