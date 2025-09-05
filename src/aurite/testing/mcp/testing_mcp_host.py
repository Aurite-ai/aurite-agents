"""
TestingMCPHost - Framework-agnostic MCP host for testing MCP servers.

This host provides direct MCP protocol interaction without framework-specific
features like server name prefixing, agent-based security, or filtering.
"""

import asyncio
import logging
import os
import re
from contextlib import AsyncExitStack
from datetime import timedelta
from typing import Dict, List

import mcp
import mcp.types as types
from mcp.client.session import ClientSession
from mcp.client.session_group import StreamableHttpParameters
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamablehttp_client

logger = logging.getLogger(__name__)


class TestingMCPHost:
    """
    Framework-agnostic MCP host for testing MCP servers.

    Key differences from MCPHost:
    - No server name prefixing (tools keep original names)
    - No agent-based security or filtering
    - Simple dict configuration instead of models
    - Direct protocol interaction
    """

    def __init__(self):
        """Initialize the testing host with minimal state."""
        # Core session management
        self._sessions: Dict[str, ClientSession] = {}
        self._session_exit_stacks: Dict[str, AsyncExitStack] = {}

        # Tool tracking (no prefixing)
        self._tools: Dict[str, types.Tool] = {}
        self._tool_to_session: Dict[str, ClientSession] = {}
        self._server_tools: Dict[str, List[types.Tool]] = {}  # Track tools per server

        logger.info("TestingMCPHost initialized")

    async def __aenter__(self):
        """Context manager entry."""
        logger.debug("TestingMCPHost context entered")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup all servers."""
        logger.debug("TestingMCPHost context exiting, shutting down all servers")
        await self.shutdown_all()
        logger.debug("TestingMCPHost context exit complete")

    async def register_server(self, config: dict) -> bool:
        """
        Register an MCP server with minimal configuration.

        Args:
            config: Dictionary with server configuration:
                - name: Server identifier
                - transport_type: "stdio", "local", or "http_stream"
                - server_path: Path to server script (for stdio)
                - command: Command to run (for local)
                - args: Arguments for command (for local)
                - http_endpoint: URL for http_stream
                - timeout: Operation timeout in seconds
                - registration_timeout: Registration timeout in seconds

        Returns:
            bool: True if registration successful, False otherwise
        """
        server_name = config.get("name")
        if not server_name:
            logger.error("Server configuration missing 'name' field")
            return False

        if server_name in self._sessions:
            logger.warning(f"Server '{server_name}' is already registered")
            return False

        logger.info(f"Registering server: {server_name}")

        session_stack = AsyncExitStack()

        async def _registration_process():
            try:
                # Setup environment
                client_env = os.environ.copy()

                def _resolve_placeholders(value: str) -> str:
                    """Resolve environment variable placeholders."""
                    placeholders = re.findall(r"\{([^}]+)\}", value)
                    for placeholder in placeholders:
                        env_value = client_env.get(placeholder)
                        if env_value:
                            value = value.replace(f"{{{placeholder}}}", env_value)
                    return value

                # Setup transport based on type
                transport_type = config.get("transport_type", "stdio")

                if transport_type in ["stdio", "local"]:
                    if transport_type == "stdio":
                        server_path = config.get("server_path")
                        if not server_path:
                            raise ValueError("'server_path' is required for stdio transport")
                        params = StdioServerParameters(command="python", args=[str(server_path)], env=client_env)
                    else:  # local
                        command = config.get("command")
                        if not command:
                            raise ValueError("'command' is required for local transport")
                        args = config.get("args", [])
                        resolved_args = [_resolve_placeholders(arg) for arg in args]
                        params = StdioServerParameters(command=command, args=resolved_args, env=client_env)

                    client = stdio_client(params, errlog=open(os.devnull, "w"))
                    read, write = await session_stack.enter_async_context(client)

                elif transport_type == "http_stream":
                    http_endpoint = config.get("http_endpoint")
                    if not http_endpoint:
                        raise ValueError("'http_endpoint' is required for http_stream transport")

                    endpoint_url = _resolve_placeholders(http_endpoint)
                    timeout_seconds = config.get("timeout", 30.0)

                    params = StreamableHttpParameters(
                        url=endpoint_url, headers=config.get("headers"), timeout=timedelta(seconds=timeout_seconds)
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
                    raise ValueError(f"Unsupported transport type: {transport_type}")

                # Create and initialize session
                session = await session_stack.enter_async_context(mcp.ClientSession(read, write))

                await session.initialize()

                # Fetch and store tools (NO PREFIXING)
                server_tools = []
                try:
                    tools_response = await session.list_tools()
                    for tool in tools_response.tools:
                        # Keep original tool name - no prefixing!
                        self._tools[tool.name] = tool
                        self._tool_to_session[tool.name] = session
                        server_tools.append(tool)
                        logger.debug(f"Registered tool '{tool.name}' from server '{server_name}'")
                except Exception as e:
                    logger.warning(f"Could not fetch tools from '{server_name}': {e}")

                # Store session and tools
                self._sessions[server_name] = session
                self._session_exit_stacks[server_name] = session_stack
                self._server_tools[server_name] = server_tools

                logger.info(f"Server '{server_name}' registered successfully with {len(server_tools)} tools")
                return True

            except Exception as e:
                logger.error(f"Failed to register server '{server_name}': {e}", exc_info=True)
                await session_stack.aclose()
                return False

        # Handle registration with timeout
        registration_timeout = config.get("registration_timeout", 30.0)
        registration_task = asyncio.create_task(_registration_process())

        try:
            result = await asyncio.wait_for(registration_task, timeout=registration_timeout)
            return result
        except asyncio.TimeoutError:
            logger.error(f"Registration of server '{server_name}' timed out after {registration_timeout} seconds")
            registration_task.cancel()
            try:
                await registration_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"Exception during task cancellation: {e}")

            # Cleanup
            try:
                await session_stack.aclose()
            except Exception as e:
                logger.debug(f"Exception during cleanup: {e}")

            return False

    async def unregister_server(self, server_name: str) -> bool:
        """
        Unregister a single server and cleanup resources.

        Args:
            server_name: Name of the server to unregister

        Returns:
            bool: True if unregistered successfully, False if not found
        """
        logger.info(f"Unregistering server: {server_name}")

        session = self._sessions.pop(server_name, None)
        session_stack = self._session_exit_stacks.pop(server_name, None)
        self._server_tools.pop(server_name, [])

        if session:
            # Remove tools associated with this session
            tools_to_remove = [name for name, sess in self._tool_to_session.items() if sess == session]
            for tool_name in tools_to_remove:
                self._tools.pop(tool_name, None)
                self._tool_to_session.pop(tool_name, None)

            logger.debug(f"Removed {len(tools_to_remove)} tools from server '{server_name}'")

        if session_stack:
            try:
                await session_stack.aclose()
                logger.debug(f"Closed session stack for server '{server_name}'")
            except Exception as e:
                logger.error(f"Error during cleanup for server '{server_name}': {e}")

        success = session is not None
        logger.info(f"Server '{server_name}' unregistered: {success}")
        return success

    async def shutdown_all(self):
        """Shutdown all registered servers."""
        logger.info(f"Shutting down all servers ({len(self._sessions)} registered)")

        server_names = list(self._sessions.keys())
        for server_name in server_names:
            await self.unregister_server(server_name)

        logger.info("All servers shut down")

    async def is_server_registered(self, server_name: str) -> bool:
        """
        Check if a server is registered and active.

        Args:
            server_name: Name of the server to check

        Returns:
            bool: True if server is registered and has an active session
        """
        return server_name in self._sessions

    async def get_server_tools(self, server_name: str) -> List[types.Tool]:
        """
        Get tools from a specific server (no filtering).

        Args:
            server_name: Name of the server

        Returns:
            List of tools from the server, empty list if server not found
        """
        return self._server_tools.get(server_name, [])

    async def call_tool(self, tool_name: str, args: dict) -> types.CallToolResult:
        """
        Call a tool directly without any filtering or security checks.

        Args:
            tool_name: Original tool name (not prefixed)
            args: Tool arguments

        Returns:
            Tool execution result

        Raises:
            KeyError: If tool not found
        """
        if tool_name not in self._tool_to_session:
            raise KeyError(f"Tool '{tool_name}' not found")

        session = self._tool_to_session[tool_name]
        logger.debug(f"Calling tool '{tool_name}' with args: {args}")

        try:
            result = await session.call_tool(tool_name, args)
            logger.debug(f"Tool '{tool_name}' executed successfully")
            return result
        except Exception as e:
            logger.error(f"Error calling tool '{tool_name}': {e}")
            raise

    def get_all_tools(self) -> Dict[str, types.Tool]:
        """
        Get all registered tools across all servers.

        Returns:
            Dictionary mapping tool names to Tool objects
        """
        return self._tools.copy()

    def get_registered_servers(self) -> List[str]:
        """
        Get list of all registered server names.

        Returns:
            List of server names
        """
        return list(self._sessions.keys())
