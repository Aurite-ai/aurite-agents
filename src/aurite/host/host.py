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
from mcp.client.session_group import (
    ClientSessionGroup,
    ServerParameters,
    StreamableHttpParameters,
)
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.stdio import StdioServerParameters

from ..config.config_models import (
    AgentConfig,
    ClientConfig,
)
from .filtering import FilteringManager
from .foundation import MessageRouter, RootManager, SecurityManager
from .resources import PromptManager, ResourceManager, ToolManager

logger = logging.getLogger(__name__)


class MCPHost:
    """
    The MCP Host manages connections to configured MCP servers (clients) and provides
    a unified interface for interacting with their capabilities (tools, prompts, resources).
    It serves as the core infrastructure layer used by higher-level components.
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

        # Session management
        self._session_group = ClientSessionGroup()
        self._exit_stack = AsyncExitStack()
        self._sessions_by_name: Dict[str, ClientSession] = {}

        # Resource management (These might be simplified or removed if SessionGroup handles all)
        self._prompt_manager = PromptManager(
            message_router=self._message_router, session_group=self._session_group
        )
        self._resource_manager = ResourceManager(
            message_router=self._message_router, session_group=self._session_group
        )
        self._tool_manager = ToolManager(
            root_manager=self._root_manager,
            message_router=self._message_router,
            session_group=self._session_group,
        )

        # State
        self._config: Dict[str, ClientConfig] = {}

    @property
    def prompts(self) -> dict[str, types.Prompt]:
        """Returns the prompts as a dictionary of names to prompts."""
        return self._session_group.prompts

    @property
    def resources(self) -> dict[str, types.Resource]:
        """Returns the resources as a dictionary of names to resources."""
        return self._session_group.resources

    @property
    def tools(self) -> dict[str, types.Tool]:
        """Returns the tools as a dictionary of names to tools."""
        return self._session_group.tools

    @property
    def registered_server_names(self) -> List[str]:
        """Returns a list of the names of all registered servers."""
        return list(self._sessions_by_name.keys())

    async def __aenter__(self):
        await self._exit_stack.__aenter__()
        await self._exit_stack.enter_async_context(self._session_group)

        logger.debug("Initializing MCP Host...")
        # Initialize managers
        await self._security_manager.initialize()
        await self._root_manager.initialize()
        await self._message_router.initialize()
        await self._prompt_manager.initialize()
        await self._resource_manager.initialize()
        await self._tool_manager.initialize()

        logger.info("MCP Host initialization finished.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        logger.debug("Shutting down MCP Host...")
        await self._exit_stack.aclose()
        logger.debug("MCP Host shutdown complete.")

    async def _get_server_params(self, config: ClientConfig) -> ServerParameters:
        client_env = os.environ.copy()

        # 2. Helper to replace placeholders in strings (for URLs and args)
        def _resolve_placeholders(value: str) -> str:
            placeholders = re.findall(r"\{([^}]+)\}", value)
            for placeholder in placeholders:
                env_value = client_env.get(placeholder)
                if env_value:
                    value = value.replace(f"{{{placeholder}}}", env_value)
                else:
                    # Keep unresolved placeholders for clarity, but log a warning
                    logger.warning(
                        f"Could not resolve placeholder '{{{placeholder}}}' for client '{config.name}'. "
                        f"Ensure the environment variable '{placeholder}' is set."
                    )
            return value

        # 3. Determine parameters based on transport type
        if config.transport_type == "stdio":
            if not config.server_path:
                raise ValueError("'server_path' is required for stdio transport")

            return StdioServerParameters(
                command="python",
                args=[str(config.server_path)],
                env=client_env,
            )

        elif config.transport_type == "http_stream":
            if not config.http_endpoint:
                raise ValueError("URL is required for http_stream transport")

            endpoint_url = _resolve_placeholders(config.http_endpoint)

            # Handle Docker environment
            if os.environ.get("DOCKER_ENV", "false").lower() == "true":
                if "localhost" in endpoint_url:
                    endpoint_url = endpoint_url.replace(
                        "localhost", "host.docker.internal"
                    )
                    logger.info(
                        f"DOCKER_ENV is true, updated http_endpoint to: {endpoint_url}"
                    )

            return StreamableHttpParameters(
                url=endpoint_url,
                headers=config.headers,
                timeout=timedelta(seconds=config.timeout or 30.0),
            )

        elif config.transport_type == "local":
            if not config.command:
                raise ValueError("'command' is required for local transport")

            resolved_args = [_resolve_placeholders(arg) for arg in (config.args or [])]

            return StdioServerParameters(
                command=config.command,
                args=resolved_args,
                env=client_env,
            )

        else:
            raise ValueError(f"Unsupported transport type: {config.transport_type}")

    async def call_tool(self, name: str, args: dict[str, Any]) -> types.CallToolResult:
        """Executes a tool given its name and arguments."""
        return await self._session_group.call_tool(name, args)

    async def _establish_session_silently(
        self, server_params: ServerParameters
    ) -> tuple[types.Implementation, mcp.ClientSession]:
        """Establish a client session to an MCP server, silencing stderr for stdio."""
        import contextlib

        session_stack = contextlib.AsyncExitStack()
        try:
            # Create read and write streams that facilitate io with the server.
            if isinstance(server_params, StdioServerParameters):
                # This is the key change: pass errlog=open(os.devnull, 'w')
                client = stdio_client(server_params, errlog=open(os.devnull, "w"))
                read, write = await session_stack.enter_async_context(client)
            elif isinstance(server_params, StreamableHttpParameters):
                client = streamablehttp_client(
                    url=server_params.url,
                    headers=server_params.headers,
                    timeout=server_params.timeout,
                    sse_read_timeout=timedelta(seconds=60 * 5),
                    terminate_on_close=True,
                )
                read, write, _ = await session_stack.enter_async_context(client)
            else:
                # Fallback for SseServerParameters or other types if added in the future
                # This part is adapted from the original session_group logic
                # Note: sse_client is not directly imported, so this path is less likely
                # to be used but included for robustness.
                raise TypeError(
                    f"Unsupported server_params type: {type(server_params)}"
                )

            session = await session_stack.enter_async_context(
                mcp.ClientSession(read, write)
            )
            result = await session.initialize()

            # This is a deviation from the library, we need to manage the stack
            # The session_group would normally do this. We'll store it on the host.
            # This part of the logic is complex, so for now, we will rely on the host's main exit stack.
            # A more robust solution might involve a custom session group.
            # For now, we will just return the session and server_info
            # and let the caller manage it.
            # The session_group will manage the lifecycle of the session after connection.
            await self._session_group._exit_stack.enter_async_context(session_stack)

            return result.serverInfo, session
        except Exception:
            await session_stack.aclose()
            raise

    async def register_client(self, config: ClientConfig):
        """Dynamically registers and initializes a new client."""
        logger.info(f"Attempting to dynamically register client: {config.name}")
        try:
            params = await self._get_server_params(config)

            # Instead of connect_to_server, we use our custom method
            server_info, session = await self._establish_session_silently(params)

            # Now, register the established session with the group
            await self._session_group.connect_with_session(server_info, session)

            self._sessions_by_name[config.name] = session

            logger.info(f"Client '{config.name}' dynamically registered successfully.")
        except Exception as e:
            logger.error(
                f"Failed to dynamically register client '{config.name}': {e}",
                exc_info=True,
            )

    async def unregister_client(self, server_name: str):
        """Dynamically unregisters a client."""
        logger.info(f"Attempting to dynamically unregister client: {server_name}")
        session_to_remove = self._sessions_by_name.pop(server_name, None)

        if session_to_remove:
            try:
                await self._session_group.disconnect_from_server(session_to_remove)
                await self._message_router.unregister_server(server_name)
                logger.info(
                    f"Client '{server_name}' dynamically unregistered successfully."
                )
            except Exception as e:
                logger.error(
                    f"Failed to dynamically unregister client '{server_name}': {e}",
                    exc_info=True,
                )
                raise
        else:
            logger.warning(f"Client '{server_name}' not found for unregistration.")

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
