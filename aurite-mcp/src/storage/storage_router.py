"""
Storage Router MCP Server.
Routes database requests to appropriate backend storage servers.
"""

from mcp.server.fastmcp import FastMCP, Context
from typing import Dict, Optional, Any
import os
import json
import uuid
import logging
import re
import importlib.util
import asyncio

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
    storage_type: str, 
    host: str = None,
    database: str = None, 
    username: str = None,
    password: str = None,
    port: Optional[int] = None,
    connection_string: str = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Connect to a storage backend of the specified type.
    Automatically routes to the appropriate storage server.
    
    Args:
        storage_type: Type of storage (e.g., "postgresql", "mysql", "sqlite")
        host: Database host address
        database: Database name
        username: Database username
        password: Database password
        port: Database port
        connection_string: Optional full connection string (alternative to individual params)
        
    Returns:
        Connection information including a connection_id for future operations
    """
    try:
        # Validate storage type
        if storage_type not in STORAGE_SERVERS:
            return {
                "success": False,
                "error": f"Unsupported storage type: {storage_type}. Available types: {list(STORAGE_SERVERS.keys())}"
            }
            
        # In a full implementation, we would get access to the host's ConnectionManager
        # For now, we'll simulate the connection process
        
        # Construct connection params
        if connection_string:
            # Parse the connection string
            if storage_type == "sql" or storage_type == "postgresql":
                # This is a simplified version - a real implementation would parse properly
                masked_connection = mask_password(connection_string)
                conn_id = str(uuid.uuid4())
                
                # Track this connection
                active_connections[conn_id] = storage_type
                
                return {
                    "success": True,
                    "connection_id": conn_id,
                    "storage_type": storage_type,
                    "connection_string": masked_connection
                }
            else:
                return {
                    "success": False, 
                    "error": f"Connection string parsing not implemented for {storage_type}"
                }
        else:
            # Use individual parameters
            if not database:
                return {"success": False, "error": "Database name is required"}
                
            if storage_type != "sqlite" and storage_type != "sql":
                if not (host and username and password):
                    return {"success": False, "error": "Host, username, and password are required"}
                    
            # Create connection ID
            conn_id = str(uuid.uuid4())
            
            # Track this connection
            active_connections[conn_id] = storage_type
            
            # In real implementation: conn_id, metadata = await host.create_database_connection(params)
            return {
                "success": True,
                "connection_id": conn_id,
                "storage_type": storage_type,
                "database": database,
                "host": host,
            }
            
    except Exception as e:
        return {"success": False, "error": f"Failed to connect to {storage_type}: {str(e)}"}


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


@mcp.tool()
async def connect_named_storage(
    connection_name: str, ctx: Context = None
) -> Dict[str, Any]:
    """
    Connect to a pre-configured named storage backend.
    
    Args:
        connection_name: Name of the pre-configured connection
        
    Returns:
        Connection information including a connection_id for future operations
    """
    try:
        # In a full implementation, this would load the configuration
        # named connections from connections.json
        # For now, we'll simulate with hardcoded examples
        
        # Mock named connections
        named_connections = {
            "default_postgres": {
                "type": "postgresql",
                "host": "localhost",
                "database": "defaultdb",
                "credentialsEnv": "DB_CREDENTIALS"
            },
            "analytics": {
                "type": "mysql",
                "host": "analytics.example.com",
                "database": "analytics",
                "credentialsEnv": "ANALYTICS_DB_CREDENTIALS"
            }
        }
        
        if connection_name not in named_connections:
            return {
                "success": False,
                "error": f"Named connection not found: {connection_name}"
            }
            
        # In real implementation: conn_id, metadata = await host.get_named_connection(connection_name)
        
        # For demo, simulate success
        conn_id = str(uuid.uuid4())
        config = named_connections[connection_name]
        
        # Track this connection
        active_connections[conn_id] = config["type"]
        
        return {
            "success": True,
            "connection_id": conn_id,
            "connection_name": connection_name,
            "storage_type": config["type"],
            "database": config["database"],
            "host": config["host"]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to connect to named storage {connection_name}: {str(e)}"
        }


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
