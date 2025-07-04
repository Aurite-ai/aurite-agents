"""
MCP Host implementation for managing MCP client connections and interactions.
"""

import logging
import os
import re
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional
from datetime import timedelta

import mcp
import mcp.types as types
from mcp.client.session import ClientSession
from mcp.client.session_group import StreamableHttpParameters
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.stdio import StdioServerParameters, stdio_client

from ..config.config_models import (
    AgentConfig,
    ClientConfig,
)
from .filtering import FilteringManager
from .foundation import MessageRouter, RootManager, SecurityManager


logger = logging.getLogger(__name__)


class MCPHost:
    """
    The MCP Host manages connections to configured MCP servers (clients) and provides
    a unified interface for interacting with their capabilities (tools, prompts, resources).
    It now manages session lifecycles directly to avoid asyncio/anyio conflicts.
    """

    def __init__(
        self,
        encryption_key: Optional[str] = None,
    ):
        # Foundation
        self._security_manager = SecurityManager(encryption_key=encryption_key)
        self._root_manager = RootManager()
        self._message_router = MessageRouter()
        self._filtering_manager = FilteringManager()

        # Direct session and component management
        self._sessions: Dict[str, ClientSession] = {}
        self._session_exit_stacks: Dict[str, AsyncExitStack] = {}
        self._tools: Dict[str, types.Tool] = {}
        self._prompts: Dict[str, types.Prompt] = {}
        self._resources: Dict[str, types.Resource] = {}
        self._tool_to_session: Dict[str, ClientSession] = {}

    @property
    def prompts(self) -> dict[str, types.Prompt]:
        """Returns the prompts as a dictionary of names to prompts."""
        return self._prompts

    @property
    def resources(self) -> dict[str, types.Resource]:
        """Returns the resources as a dictionary of names to resources."""
        return self._resources

    @property
    def tools(self) -> dict[str, types.Tool]:
        """Returns the tools as a dictionary of names to tools."""
        return self._tools

    @property
    def registered_server_names(self) -> List[str]:
        """Returns a list of the names of all registered servers."""
        return list(self._sessions.keys())

    async def __aenter__(self):
        logger.debug("Initializing MCP Host...")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        logger.debug("Shutting down MCP Host...")
        server_names = list(self._sessions.keys())
        for server_name in server_names:
            await self.unregister_client(server_name)
        logger.debug("MCP Host shutdown complete.")

    async def call_tool(self, name: str, args: dict[str, Any]) -> types.CallToolResult:
        """Executes a tool given its name and arguments."""
        if name not in self._tool_to_session:
            raise KeyError(f"Tool '{name}' not found or its server is not registered.")
        session = self._tool_to_session[name]
        return await session.call_tool(name, args)

    async def register_client(self, config: ClientConfig):
        """
        Dynamically registers and initializes a new client, managing its lifecycle
        with a dedicated AsyncExitStack to ensure proper cleanup.
        """
        logger.info(f"Attempting to dynamically register client: {config.name}")
        if config.name in self._sessions:
            logger.warning(f"Client '{config.name}' is already registered.")
            return

        session_stack = AsyncExitStack()
        try:
            client_env = os.environ.copy()

            def _resolve_placeholders(value: str) -> str:
                placeholders = re.findall(r"\{([^}]+)\}", value)
                for placeholder in placeholders:
                    env_value = client_env.get(placeholder)
                    if env_value:
                        value = value.replace(f"{{{placeholder}}}", env_value)
                return value

            if config.transport_type in ["stdio", "local"]:
                if config.transport_type == "stdio":
                    if not config.server_path:
                        raise ValueError(
                            "'server_path' is required for stdio transport"
                        )
                    params = StdioServerParameters(
                        command="python", args=[str(config.server_path)], env=client_env
                    )
                else:  # local
                    if not config.command:
                        raise ValueError("'command' is required for local transport")
                    resolved_args = [
                        _resolve_placeholders(arg) for arg in (config.args or [])
                    ]
                    params = StdioServerParameters(
                        command=config.command, args=resolved_args, env=client_env
                    )
                client = stdio_client(params, errlog=open(os.devnull, "w"))
                read, write = await session_stack.enter_async_context(client)

            elif config.transport_type == "http_stream":
                if not config.http_endpoint:
                    raise ValueError("URL is required for http_stream transport")
                endpoint_url = _resolve_placeholders(config.http_endpoint)
                params = StreamableHttpParameters(
                    url=endpoint_url,
                    headers=config.headers,
                    timeout=timedelta(seconds=config.timeout or 30.0),
                )
                client = streamablehttp_client(
                    url=params.url,
                    headers=params.headers,
                    timeout=params.timeout,
                    sse_read_timeout=params.sse_read_timeout,
                    terminate_on_close=True,
                )
                read, write, _ = await session_stack.enter_async_context(client)
            else:
                raise ValueError(f"Unsupported transport type: {config.transport_type}")

            session = await session_stack.enter_async_context(
                mcp.ClientSession(read, write)
            )
            await session.initialize()

            # Aggregate components
            try:
                tools_response = await session.list_tools()
                for tool in tools_response.tools:
                    self._tools[tool.name] = tool
                    self._tool_to_session[tool.name] = session
            except Exception as e:
                logger.warning(f"Could not fetch tools from '{config.name}': {e}")

            self._sessions[config.name] = session
            self._session_exit_stacks[config.name] = session_stack

            logger.info(f"Client '{config.name}' dynamically registered successfully.")

        except Exception as e:
            logger.error(
                f"Failed to dynamically register client '{config.name}': {e}",
                exc_info=True,
            )
            await session_stack.aclose()
            raise

    async def unregister_client(self, server_name: str):
        """Dynamically unregisters a client and cleans up its resources."""
        logger.info(f"Attempting to dynamically unregister client: {server_name}")
        session_to_remove = self._sessions.pop(server_name, None)
        session_stack = self._session_exit_stacks.pop(server_name, None)

        if session_to_remove:
            tools_to_remove = [
                name
                for name, session in self._tool_to_session.items()
                if session == session_to_remove
            ]
            for tool_name in tools_to_remove:
                del self._tools[tool_name]
                del self._tool_to_session[tool_name]

        if session_stack:
            await session_stack.aclose()

        logger.info(f"Client '{server_name}' dynamically unregistered successfully.")

    def get_formatted_tools(
        self,
        agent_config: Optional[AgentConfig] = None,
        tool_names: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Gets the list of tools formatted for LLM use, applying agent-specific filtering.
        """
        all_tools = list(self.tools.values())

        if tool_names:
            all_tools = [tool for tool in all_tools if tool.name in tool_names]

        formatted_tools = [tool.model_dump() for tool in all_tools]

        if agent_config:
            return self._filtering_manager.filter_component_list(
                formatted_tools, agent_config
            )

        return formatted_tools
