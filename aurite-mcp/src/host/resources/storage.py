"""
Database connection management for MCP host.
Handles secure database connection pooling.
"""

import os
import re
import logging
import uuid
import time
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass, field

from ..config import ConfigurableManager, ConnectionConfig, ConfigurationManager

# Type hint for SQLAlchemy objects
try:
    from sqlalchemy.engine import Engine, Connection
    from sqlalchemy import create_engine, text
except ImportError:
    # Mock types for systems without SQLAlchemy
    class Engine:
        pass

    class Connection:
        pass


logger = logging.getLogger(__name__)

# Default ports for database types
DEFAULT_DB_PORTS = {
    "postgresql": 5432,
    "mysql": 3306,
    "sqlite": None,
    "oracle": 1521,
    "mssql": 1433,
}

# Database type to SQLAlchemy dialect mapping
DB_TYPE_TO_DIALECT = {
    "postgresql": "postgresql+psycopg2",
    "mysql": "mysql+pymysql",
    "sqlite": "sqlite",
    "oracle": "oracle",
    "mssql": "mssql+pyodbc",
}


@dataclass
class ConnectionInfo:
    """Information about a database connection"""

    id: str
    engine: Engine
    connection: Optional[Connection] = None
    storage_type: str = "sql"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    is_active: bool = True


class StorageManager(ConfigurableManager[ConnectionConfig]):
    """
    Manages database connections for the MCP host.
    Handles secure creation and retrieval of database connections.
    """

    def __init__(self):
        super().__init__("storage")
        # Connection pool: ID -> ConnectionInfo
        self._connections: Dict[str, ConnectionInfo] = {}
        # Server permissions: server_id -> allowed_connection_types
        self._server_permissions: Dict[str, List[str]] = {}

    def _config_model_class(self):
        return ConnectionConfig

    def _validate_config_structure(self, config: Dict[str, Any]) -> bool:
        return ConfigurationManager.validate_config_structure(
            config, ["connections"], "storage"
        )

    async def register_server_permissions(
        self, server_id: str, allowed_connection_types: List[str]
    ):
        """Register which connection types a server is allowed to access"""
        self._server_permissions[server_id] = allowed_connection_types
        logger.info(
            f"Registered permissions for server {server_id}: {allowed_connection_types}"
        )

    async def create_db_connection(
        self, params: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Create a database connection from parameters and return a connection ID.

        Args:
            params: Connection parameters including type, host, database, username, password

        Returns:
            Tuple of (connection_id, connection_metadata)
        """
        try:
            # Validate required parameters
            required_params = ["type", "host", "database", "username", "password"]
            if not ConfigurationManager.validate_config_structure(
                params,
                [
                    p
                    for p in required_params
                    if params.get("type") != "sqlite" or p in ["type", "database"]
                ],
                "connection parameters",
            ):
                raise ValueError("Invalid connection parameters")

            # Construct connection string (only in memory)
            db_type = params["type"].lower()
            dialect = DB_TYPE_TO_DIALECT.get(db_type, db_type)

            # Handle SQLite special case
            if db_type == "sqlite":
                conn_string = f"{dialect}:///{params['database']}"
            else:
                port = params.get("port", DEFAULT_DB_PORTS.get(db_type))
                port_str = f":{port}" if port else ""
                conn_string = f"{dialect}://{params['username']}:{params['password']}@{params['host']}{port_str}/{params['database']}"

            # Create connection
            engine = create_engine(conn_string)

            # Verify connection by attempting to connect
            with engine.connect():
                # Just test the connection
                pass

            # Generate unique ID
            conn_id = str(uuid.uuid4())

            # Store connection info (without raw password)
            metadata = {
                "host": params.get("host", "local" if db_type == "sqlite" else None),
                "database": params["database"],
                "username": params.get("username", ""),
                "db_type": db_type,
            }
            if "port" in params:
                metadata["port"] = params["port"]

            connection_info = ConnectionInfo(
                id=conn_id, engine=engine, storage_type=db_type, metadata=metadata
            )

            self._connections[conn_id] = connection_info

            # Create a masked connection string for logs/display
            masked_conn_string = re.sub(
                r"://([^:]+):([^@]+)@", r"://\1:******@", conn_string
            )
            metadata["connection_string"] = masked_conn_string

            logger.info(
                f"Created database connection {conn_id} to {metadata.get('host', 'local')}/{metadata['database']}"
            )

            return conn_id, metadata

        except Exception as e:
            logger.error(f"Failed to create database connection: {str(e)}")
            raise

    async def get_named_connection(
        self, connection_name: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Get a connection for a named database configuration.

        Args:
            connection_name: Name of the pre-configured connection

        Returns:
            Tuple of (connection_id, connection_metadata)
        """
        if not self._config or connection_name not in self._config.connections:
            raise ValueError(f"Named connection not found: {connection_name}")

        config = self._config.connections[connection_name]

        # Get credentials from environment
        creds_env = config.get("credentialsEnv")
        if not creds_env or creds_env not in os.environ:
            raise ValueError(
                f"Credentials not found for {connection_name}. Set {creds_env} environment variable."
            )

        creds_value = os.environ[creds_env]

        # Parse credentials (format: username:password)
        if ":" not in creds_value:
            raise ValueError(
                f"Invalid credential format in {creds_env}. Expected 'username:password'"
            )

        username, password = creds_value.split(":", 1)

        # Create connection params
        params = {
            "type": config["type"],
            "host": config["host"],
            "database": config["database"],
            "username": username,
            "password": password,
        }

        if "port" in config:
            params["port"] = config["port"]

        # Create the connection
        conn_id, metadata = await self.create_db_connection(params)

        # Add the named connection to metadata
        metadata["connection_name"] = connection_name

        return conn_id, metadata

    async def get_connection(self, conn_id: str) -> Optional[ConnectionInfo]:
        """
        Get a database connection by ID.

        Args:
            conn_id: Connection ID

        Returns:
            ConnectionInfo if found, None otherwise
        """
        if conn_id not in self._connections:
            return None

        connection_info = self._connections[conn_id]

        # Update last used time
        connection_info.last_used = time.time()

        return connection_info

    async def validate_server_access(self, server_id: str, conn_id: str) -> bool:
        """
        Validate if a server is allowed to access a specific connection.

        Args:
            server_id: Server ID
            conn_id: Connection ID

        Returns:
            True if access is allowed, False otherwise
        """
        if server_id not in self._server_permissions:
            return False

        if conn_id not in self._connections:
            return False

        # Check if server has permission for this connection type
        allowed_types = self._server_permissions[server_id]
        conn_type = self._connections[conn_id].storage_type

        return conn_type in allowed_types

    async def close_connection(self, conn_id: str) -> bool:
        """
        Close a database connection.

        Args:
            conn_id: Connection ID

        Returns:
            True if connection was closed, False if it wasn't found
        """
        if conn_id not in self._connections:
            return False

        connection_info = self._connections[conn_id]

        try:
            # Close active connection if it exists
            if connection_info.connection is not None:
                connection_info.connection.close()

            # Mark as inactive
            connection_info.is_active = False

            # Remove from connection pool
            del self._connections[conn_id]

            logger.info(f"Closed database connection {conn_id}")
            return True

        except Exception as e:
            logger.error(f"Error closing connection {conn_id}: {e}")
            return False

    async def execute_query(
        self, conn_id: str, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a query on a database connection.

        Args:
            conn_id: Connection ID
            query: SQL query to execute
            params: Query parameters

        Returns:
            Query result dictionary
        """
        connection_info = await self.get_connection(conn_id)
        if not connection_info:
            return {"success": False, "error": "Invalid connection ID"}

        if not connection_info.is_active:
            return {"success": False, "error": "Connection is no longer active"}

        try:
            engine = connection_info.engine

            with engine.connect() as conn:
                # Check if it's a SELECT query
                is_select = query.strip().lower().startswith("select")

                if params:
                    result = conn.execute(text(query), params)
                else:
                    result = conn.execute(text(query))

                if is_select:
                    # For SELECT queries, return rows
                    # Use SQLAlchemy's result mapping functions
                    results = result.fetchall()
                    if results:
                        columns = result.keys()
                        rows = []
                        for row in results:
                            # Convert row to dict safely
                            row_dict = {}
                            for i, col in enumerate(columns):
                                row_dict[col] = row[i]
                            rows.append(row_dict)

                        return {
                            "success": True,
                            "is_select": True,
                            "rows": rows,
                            "columns": list(columns),
                            "row_count": len(rows),
                        }
                    else:
                        # Empty result set
                        return {
                            "success": True,
                            "is_select": True,
                            "rows": [],
                            "columns": [],
                            "row_count": 0,
                        }
                else:
                    # For non-SELECT queries, return affected rows
                    return {
                        "success": True,
                        "is_select": False,
                        "affected_rows": result.rowcount,
                    }

        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            return {"success": False, "error": f"Query execution failed: {str(e)}"}

    async def list_active_connections(self) -> List[Dict[str, Any]]:
        """List all active connections with metadata"""
        connections = []
        for conn_id, info in self._connections.items():
            if info.is_active:
                connections.append(
                    {
                        "connection_id": conn_id,
                        "storage_type": info.storage_type,
                        "metadata": info.metadata,
                        "created_at": info.created_at,
                        "last_used": info.last_used,
                    }
                )

        return connections

    async def cleanup_stale_connections(self, max_idle_seconds: int = 3600) -> int:
        """
        Close connections that haven't been used for a while.

        Args:
            max_idle_seconds: Maximum idle time in seconds

        Returns:
            Number of connections closed
        """
        now = time.time()
        closed_count = 0

        for conn_id, info in list(self._connections.items()):
            if info.is_active and (now - info.last_used) > max_idle_seconds:
                if await self.close_connection(conn_id):
                    closed_count += 1

        return closed_count

    async def shutdown(self):
        """Shutdown the connection manager and close all connections"""
        logger.info("Shutting down connection manager")

        # Close all active connections
        for conn_id, info in list(self._connections.items()):
            if info.is_active:
                await self.close_connection(conn_id)

        # Clear all collections
        self._connections.clear()
        self._server_permissions.clear()
