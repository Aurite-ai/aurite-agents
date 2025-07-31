"""
A concrete implementation of BaseToolProvider that handles the 'storage' component type.
"""

import logging
from typing import Any, Callable, Dict, List

import mcp.types as types
from mcp.types import TextContent
from pydantic import TypeAdapter

from ..config.config_models import StorageConfig
from .base_provider import BaseToolProvider

logger = logging.getLogger(__name__)


class StorageToolProvider(BaseToolProvider):
    """
    Manages storage components, providing native, in-process tools for
    storage types like 'memory'.
    """

    def __init__(self):
        self._tools: Dict[str, types.Tool] = {}
        self._handlers: Dict[str, Callable] = {}
        self._datastores: Dict[str, Dict[str, Any]] = {}  # e.g., {"my_mem_db": {"key1": "value1"}}
        logger.debug("StorageToolProvider initialized.")

    def provider_name(self) -> str:
        return "storage"

    async def register_component(self, config_dict: Dict[str, Any]):
        """
        Registers a storage component from its configuration dictionary.
        If it's a native type like 'memory', it creates the necessary tools and handlers.
        """
        # Use TypeAdapter to correctly parse the discriminated union
        adapter = TypeAdapter(StorageConfig)
        config = adapter.validate_python(config_dict)

        if config.storage_type == "memory":
            # Only register the component and its tools if it hasn't been seen before
            if config.name in self._datastores:
                logger.debug(f"In-memory storage component '{config.name}' already registered. Skipping.")
                return

            logger.info(f"Registering native in-memory storage component: '{config.name}'")
            self._datastores[config.name] = {}

            # --- Create 'write' tool ---
            write_tool_name = f"{config.name}-write"
            write_schema = types.Tool(
                name=write_tool_name,
                description=f"Writes a value to a key in the '{config.name}' in-memory store.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "The key to write to."},
                        "value": {"type": "string", "description": "The value to store."},
                    },
                    "required": ["key", "value"],
                },
            )
            self._tools[write_tool_name] = write_schema
            self._handlers[write_tool_name] = self._create_write_handler(config.name)

            # --- Create 'read' tool ---
            read_tool_name = f"{config.name}-read"
            read_schema = types.Tool(
                name=read_tool_name,
                description=f"Reads a value from a key in the '{config.name}' in-memory store.",
                inputSchema={
                    "type": "object",
                    "properties": {"key": {"type": "string", "description": "The key to read from."}},
                    "required": ["key"],
                },
            )
            self._tools[read_tool_name] = read_schema
            self._handlers[read_tool_name] = self._create_read_handler(config.name)

        # Other storage types like 'postgresql' would be handled by MCP servers,
        # so this provider does nothing for them.

    def get_tool_schemas(self) -> List[types.Tool]:
        return list(self._tools.values())

    def can_handle(self, tool_name: str) -> bool:
        return tool_name in self._handlers

    async def call_tool(self, name: str, args: Dict[str, Any]) -> types.CallToolResult:
        if not self.can_handle(name):
            raise KeyError(f"StorageToolProvider cannot handle tool '{name}'.")
        handler = self._handlers[name]
        return await handler(args)

    # --- Handler Factory Methods ---

    def _create_write_handler(self, datastore_name: str) -> Callable:
        async def _write_handler(args: Dict[str, Any]) -> types.CallToolResult:
            key = args.get("key")
            value = args.get("value")
            if not key:
                return types.CallToolResult(
                    content=[TextContent(type="text", text="Error: 'key' is a required argument.")]
                )
            self._datastores[datastore_name][key] = value
            logger.debug(f"Wrote to in-memory store '{datastore_name}': key='{key}'")
            return types.CallToolResult(
                content=[TextContent(type="text", text=f"Successfully wrote value to key '{key}'.")]
            )

        return _write_handler

    def _create_read_handler(self, datastore_name: str) -> Callable:
        async def _read_handler(args: Dict[str, Any]) -> types.CallToolResult:
            key = args.get("key")
            if not key:
                return types.CallToolResult(
                    content=[TextContent(type="text", text="Error: 'key' is a required argument.")]
                )
            value = self._datastores[datastore_name].get(key)
            logger.debug(f"Read from in-memory store '{datastore_name}': key='{key}'")
            if value is None:
                return types.CallToolResult(content=[TextContent(type="text", text=f"Error: Key '{key}' not found.")])
            return types.CallToolResult(content=[TextContent(type="text", text=str(value))])

        return _read_handler
