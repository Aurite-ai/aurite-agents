"""
Defines the abstract base class for all custom tool providers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

import mcp.types as types


class BaseToolProvider(ABC):
    """
    An interface for a class that provides a set of custom, non-MCP tools.

    This abstract class defines the contract that any custom tool provider must
    adhere to in order to be integrated into the ToolHost. It ensures a
    consistent pattern for registering components, discovering tools, and
    executing tool calls.
    """

    @abstractmethod
    def provider_name(self) -> str:
        """
        Returns the unique name of this provider (e.g., 'storage', 'orchestration').
        This name is used to route component registrations in the ToolHost.
        """
        pass

    @abstractmethod
    async def register_component(self, config_dict: Dict[str, Any]):
        """
        Registers a component configuration dictionary (e.g., from a JSON file)
        and prepares its tools, including their schemas and handlers. The provider
        is responsible for parsing this dictionary into its specific Pydantic model.
        """
        pass

    @abstractmethod
    def get_tool_schemas(self) -> List[types.Tool]:
        """
        Returns the schemas of all tools currently managed by this provider.
        The ToolHost will aggregate these schemas with those from other providers
        and the MCPHost.
        """
        pass

    @abstractmethod
    def can_handle(self, tool_name: str) -> bool:
        """
        Returns True if this provider is responsible for executing the given tool name.
        This is typically checked by looking up the tool name in an internal registry.
        """
        pass

    @abstractmethod
    async def call_tool(self, name: str, args: Dict[str, Any]) -> types.CallToolResult:
        """
        Executes the specified tool by its unique name and returns the result.
        """
        pass
