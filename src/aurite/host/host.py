"""
MCP Host implementation for managing MCP client connections and interactions.
"""

import logging
import os
import re
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional
from datetime import timedelta

import mcp.types as types
from mcp.client.session_group import (
    ClientSessionGroup,
    ServerParameters,
    StreamableHttpParameters,
)
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
                command=config.command, args=resolved_args, env=client_env
            )

        else:
            raise ValueError(f"Unsupported transport type: {config.transport_type}")

    async def call_tool(self, name: str, args: dict[str, Any]) -> types.CallToolResult:
        """Executes a tool given its name and arguments."""
        return await self._session_group.call_tool(name, args)

    async def register_client(self, config: ClientConfig):
        """Dynamically registers and initializes a new client."""
        logger.info(f"Attempting to dynamically register client: {config.name}")
        # The ClientSessionGroup will raise an error if a component name conflicts,
        # which serves as our duplicate check.
        try:
            params = await self._get_server_params(config)
            await self._session_group.connect_to_server(params)
            logger.info(f"Client '{config.name}' dynamically registered successfully.")
        except Exception as e:
            logger.error(
                f"Failed to dynamically register client '{config.name}': {e}",
                exc_info=True,
            )
            raise

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
