"""
Storage Router MCP Server.
Routes database requests to appropriate backend storage servers.
"""

from mcp.server.fastmcp import FastMCP, Context
from typing import Dict, Optional, Any
import os
import json

import logging
import re

# Create the router MCP server
mcp = FastMCP("Storage Router", dependencies=["httpx"])

# Directory to backend storage servers
STORAGE_SERVERS = {}

# Configuration file path
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config",
    "storage",
    "storage_config.json",
)

# Active connections to backend servers (connection_id -> server_type)
active_connections = {}

# Logger
logger = logging.getLogger(__name__)


async def load_configuration():
    """Load storage server configuration"""
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Storage configuration file not found: {CONFIG_FILE}")

    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

    for server_type, server_config in config.get("mcpServers", {}).items():
        STORAGE_SERVERS[server_type] = server_config

    logger.info(f"Loaded storage configurations: {list(STORAGE_SERVERS.keys())}")


@mcp.tool()
async def connect_storage(
    storage_type: str, connection_string: str, ctx: Context = None
) -> Dict[str, Any]:
    """
    Connect to a storage backend of the specified type.
    Automatically routes to the appropriate storage server.

    Args:
        storage_type: Type of storage (e.g., "sql", "vector", "redis")
        connection_string: Connection string for the storage backend

    Returns:
        Connection information including a connection_id for future operations
    """
    try:
        # Validate storage type
        if storage_type not in STORAGE_SERVERS:
            return {
                "success": False,
                "error": f"Unsupported storage type: {storage_type}. Available types: {list(STORAGE_SERVERS.keys())}",
            }

        # For security, we should use the host's security manager to create a secure token
        # This is a placeholder for direct integration with the MCPHost's security manager
        # token, masked_connection = await host.secure_database_connection(connection_string)

        # For now, we'll just mask the password ourselves
        masked_connection = mask_password(connection_string)

        # Route to appropriate backend server
        # In a real implementation, this would use MCPHost's client session to call the backend
        # For now, we'll simply propagate the connection string

        if storage_type == "sql":
            # In a full implementation, this would use:
            # result = await sql_client.call_tool(
            #    "connect_database",
            #    {"connection_string": connection_string, "use_token": False}
            # )

            # For now we'll simulate the response
            result = {
                "success": True,
                "connection_id": masked_connection,
                "storage_type": "sql",
                # Other details would be here
            }

            # Track this connection
            active_connections[masked_connection] = "sql"

            return result
        else:
            # Implement routing for other storage types
            return {
                "success": False,
                "error": f"Storage type '{storage_type}' is configured but not yet implemented",
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to connect to {storage_type}: {str(e)}",
        }


@mcp.tool()
async def execute_query(
    connection_id: str,
    query: str,
    params: Optional[Dict[str, Any]] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Execute a query on a storage backend.
    Automatically routes to the appropriate storage server.

    Args:
        connection_id: Connection identifier from connect_storage
        query: Query to execute (SQL or other query language)
        params: Optional parameters for the query

    Returns:
        Query results
    """
    try:
        # Determine storage type from connection_id
        storage_type = active_connections.get(connection_id)
        if not storage_type:
            return {
                "success": False,
                "error": "Invalid connection ID. Please connect to a storage backend first.",
            }

        # Route to appropriate backend server
        # In a real implementation, this would use MCPHost's client sessions
        if storage_type == "sql":
            # result = await sql_client.call_tool(
            #    "execute_query",
            #    {"connection_id": connection_id, "query": query, "params": params}
            # )

            # For now we'll simulate the response
            result = {
                "success": True,
                "is_select": query.strip().lower().startswith("select"),
                # Other details would be here
            }

            return result
        else:
            return {
                "success": False,
                "error": f"Query execution not implemented for storage type: {storage_type}",
            }

    except Exception as e:
        return {"success": False, "error": f"Query execution failed: {str(e)}"}


@mcp.tool()
async def disconnect(connection_id: str, ctx: Context = None) -> Dict[str, Any]:
    """
    Disconnect from a storage backend.

    Args:
        connection_id: Connection identifier from connect_storage

    Returns:
        Disconnection status
    """
    try:
        # Determine storage type from connection_id
        storage_type = active_connections.get(connection_id)
        if not storage_type:
            return {
                "success": False,
                "error": "Invalid connection ID. No active connection to close.",
            }

        # Route to appropriate backend server
        if storage_type == "sql":
            # result = await sql_client.call_tool(
            #    "disconnect",
            #    {"connection_id": connection_id}
            # )

            # For now we'll simulate the response
            result = {
                "success": True,
                "message": f"Successfully disconnected from {storage_type} storage.",
            }

            # Remove from active connections
            if connection_id in active_connections:
                del active_connections[connection_id]

            return result
        else:
            return {
                "success": False,
                "error": f"Disconnect not implemented for storage type: {storage_type}",
            }

    except Exception as e:
        return {"success": False, "error": f"Failed to disconnect: {str(e)}"}


@mcp.resource("storage://schema/{connection_id}")
def schema_resource(connection_id: str) -> str:
    """
    Get the storage schema as a formatted resource.

    Args:
        connection_id: Connection identifier from connect_storage
    """
    if connection_id not in active_connections:
        return "# Error\n\nInvalid connection ID. Please connect to a storage backend first."

    storage_type = active_connections[connection_id]

    # Route to appropriate backend server
    # In a full implementation, this would proxy to the corresponding schema resource
    return f"# {storage_type.upper()} Storage Schema\n\nThis is a placeholder schema for {storage_type} storage."


# Helper function to mask passwords in connection strings
def mask_password(connection_string: str) -> str:
    """Masks the password in a database connection string for security."""
    return re.sub(r"(://.+:).+(@.+)", r"\1*****\2", connection_string)


async def initialize():
    """Initialize the storage router"""
    await load_configuration()


# Run initialization at startup
@mcp.on_startup
async def startup():
    await initialize()


# Allow direct execution of the server
if __name__ == "__main__":
    mcp.run()
