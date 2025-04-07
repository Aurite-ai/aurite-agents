from mcp.server.fastmcp import FastMCP, Context
from sqlalchemy import create_engine, text, inspect
from typing import Dict, Optional, Any
import re
import uuid
import os
import json
from pathlib import Path
import pandas as pd

# Create the MCP server
mcp = FastMCP(
    "SQL Explorer", dependencies=["sqlalchemy", "pandas", "pymysql", "psycopg2-binary"]
)

# Dictionary to store connections for reuse
active_connections = {}

# Named connections from configuration
named_connections = {}

# Configuration file path
CONFIG_PATH = Path(__file__).parents[4] / "config" / "storage" / "connections.json"


# Load named connection configurations
def load_named_connections():
    """Load named connection configurations from the config file"""
    global named_connections, CONFIG_PATH

    print(f"Looking for config at: {CONFIG_PATH} (exists: {CONFIG_PATH.exists()})")

    if not CONFIG_PATH.exists():
        # Try alternate paths
        alt_paths = [
            Path(__file__).parents[4] / "config" / "storage" / "connections.json",
            Path(__file__).parents[3] / "config" / "storage" / "connections.json",
            Path(__file__).parent.parent.parent.parent
            / "config"
            / "storage"
            / "connections.json",
            Path(
                "/home/wilcoxr/workspace/aurite-agents/aurite-mcp/config/storage/connections.json"
            ),
        ]

        for path in alt_paths:
            print(f"Trying alternate path: {path} (exists: {path.exists()})")
            if path.exists():
                CONFIG_PATH = path
                break

    if not CONFIG_PATH.exists():
        print(
            f"No connection configuration found at {CONFIG_PATH} or alternative paths"
        )
        return

    try:
        print(f"Loading config from: {CONFIG_PATH}")
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)

        connections = config.get("connections", {})
        named_connections.update(connections)

        print(f"Loaded {len(named_connections)} named connection configurations")
        print(f"Available connections: {list(named_connections.keys())}")
    except Exception as e:
        print(f"Failed to load named connections: {e}")


# Load connections at startup
load_named_connections()


@mcp.tool()
def connect_database(
    host: str = None,
    database: str = None,
    username: str = None,
    password: str = None,
    port: Optional[int] = None,
    connection_string: str = None,
    connection_id: str = None,
    connection_name: str = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Connect to a SQL database using SQLAlchemy.

    Connection can be established in several ways:
    1. Using individual parameters (host, database, username, password)
    2. Using a full connection string
    3. Using a pre-established connection_id from the ConnectionManager
    4. Using a named connection from the configuration

    Args:
        host: Database host address
        database: Database name
        username: Database username
        password: Database password
        port: Database port
        connection_string: Full connection string (alternative to individual params)
        connection_id: Pre-established connection ID from ConnectionManager
        connection_name: Name of a pre-configured connection

    Returns:
        Dictionary with connection status, database type, and available tables
    """
    try:
        # If connection_id is provided, this means the connection was already established
        # by the ConnectionManager, and we should use the existing connection
        if connection_id and connection_id in active_connections:
            ctx.info(f"Using existing connection: {connection_id}")

            conn_info = active_connections[connection_id]
            return {
                "success": True,
                "connection_id": connection_id,
                "database_type": conn_info["type"],
                "tables": conn_info["tables"],
                "message": "Using existing connection",
            }

        # Handle named connection
        if connection_name:
            ctx.info(f"Looking up named connection: {connection_name}")

            # Check if the named connection exists in our config
            if connection_name not in named_connections:
                return {
                    "success": False,
                    "error": f"Named connection not found: {connection_name}",
                }

            # Get connection details from configuration
            config = named_connections[connection_name]

            # Get credentials from environment variable
            creds_env = config.get("credentialsEnv")
            if not creds_env or creds_env not in os.environ:
                return {
                    "success": False,
                    "error": f"Credentials not found for {connection_name}. Set {creds_env} environment variable.",
                }

            creds = os.environ[creds_env]

            # Parse credentials (username:password)
            if ":" not in creds and config["type"] != "sqlite":
                return {
                    "success": False,
                    "error": f"Invalid credential format in {creds_env}. Expected 'username:password'",
                }

            # For non-sqlite, extract username and password
            if config["type"] != "sqlite":
                username, password = creds.split(":", 1)

            # Update connection parameters from the named connection
            host = config.get("host")
            database = config.get("database")
            port = config.get("port")
            db_type = config.get("type", "postgresql")

            ctx.info(
                f"Using named connection {connection_name} for {db_type} database at {host}"
            )

            # For SQLite, we don't need username/password
            if db_type == "sqlite":
                # Construct SQLite connection string
                connection_string = f"sqlite:///{database}"
            else:
                # Construct connection string based on database type
                if db_type == "postgresql":
                    dialect = "postgresql+psycopg2"
                elif db_type == "mysql":
                    dialect = "mysql+pymysql"
                else:
                    return {
                        "success": False,
                        "error": f"Unsupported database type in named connection: {db_type}",
                    }

                # Build the connection string
                port_str = f":{port}" if port else ""
                connection_string = (
                    f"{dialect}://{username}:{password}@{host}{port_str}/{database}"
                )

        # Construct connection string if individual parameters are provided (not from named connection)
        elif not connection_string and (host and database):
            # For SQLite, we don't need username/password
            if database.endswith(".db") or database.endswith(".sqlite"):
                connection_string = f"sqlite:///{database}"
            else:
                # Ensure we have the required parameters
                if not (username and password):
                    return {
                        "success": False,
                        "error": "Username and password are required for non-SQLite databases",
                    }

                # Determine port or use default
                port_str = f":{port}" if port else ""
                # Default to PostgreSQL
                dialect = "postgresql+psycopg2"

                connection_string = (
                    f"{dialect}://{username}:{password}@{host}{port_str}/{database}"
                )

        # Ensure we have a connection string at this point
        if not connection_string:
            return {
                "success": False,
                "error": "Either connection string, individual parameters, or a named connection must be provided",
            }

        # Log connection attempt (masking password for security)
        masked_connection = mask_password(connection_string)
        ctx.info(f"Attempting to connect to database: {masked_connection}")

        # Auto-correct connection string format if needed
        if not (
            connection_string.startswith("mysql+")
            or connection_string.startswith("postgresql+")
            or connection_string.startswith("mysql://")
            or connection_string.startswith("postgresql://")
            or connection_string.startswith("sqlite:///")
        ):
            # Try to detect database type and correct format
            if "mysql" in connection_string.lower():
                connection_string = connection_string.replace(
                    "mysql://", "mysql+pymysql://"
                )
                if not connection_string.startswith("mysql+"):
                    connection_string = "mysql+pymysql://" + connection_string
            elif "postgre" in connection_string.lower():
                connection_string = connection_string.replace(
                    "postgresql://", "postgresql+psycopg2://"
                )
                if not connection_string.startswith("postgresql+"):
                    connection_string = "postgresql+psycopg2://" + connection_string
            elif "sqlite" in connection_string.lower():
                if not connection_string.startswith("sqlite:///"):
                    connection_string = "sqlite:///" + connection_string
            else:
                return {
                    "success": False,
                    "error": "Unsupported database type. Please use MySQL, PostgreSQL, or SQLite.",
                }

        # Create engine and connect
        engine = create_engine(connection_string)
        connection = engine.connect()

        # Determine database type
        if "mysql" in connection_string.lower():
            db_type = "MySQL"
        elif "postgresql" in connection_string.lower():
            db_type = "PostgreSQL"
        elif "sqlite" in connection_string.lower():
            db_type = "SQLite"
        else:
            db_type = "Unknown"

        # Get database inspector
        inspector = inspect(engine)

        # Get all tables
        tables = inspector.get_table_names()

        # Get schema information for each table
        schema_info = {}
        for table in tables:
            columns = inspector.get_columns(table)
            schema_info[table] = [
                {"name": col["name"], "type": str(col["type"])} for col in columns
            ]

        # Generate a unique connection ID
        conn_id = str(uuid.uuid4())

        # Store connection for future use
        active_connections[conn_id] = {
            "engine": engine,
            "connection": connection,
            "type": db_type,
            "tables": tables,
            "schema": schema_info,
        }

        # Add connection name to response if used
        result = {
            "success": True,
            "connection_id": conn_id,
            "database_type": db_type,
            "tables": tables,
            "schema": schema_info,
        }

        if connection_name:
            result["connection_name"] = connection_name

        return result
    except Exception as e:
        return {"success": False, "error": f"Failed to connect: {str(e)}"}


@mcp.tool()
def execute_query(
    connection_id: str,
    query: str,
    params: Optional[Dict[str, Any]] = None,
    limit: int = 100,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Execute a SQL query on a previously connected database.

    Args:
        connection_id: Connection identifier returned from connect_database
        query: SQL query to execute
        params: Optional parameters for the query
        limit: Maximum number of rows to return (for SELECT queries)

    Returns:
        Dictionary with query results or affected row count
    """
    if connection_id not in active_connections:
        return {
            "success": False,
            "error": "Invalid connection ID. Please connect to the database first.",
        }

    connection_info = active_connections[connection_id]
    connection = connection_info["connection"]

    try:
        ctx.info(f"Executing query: {query[:100]}...")

        # Check if it's a SELECT query
        is_select = query.strip().lower().startswith("select")

        if is_select:
            # For SELECT queries, use pandas to get results as a DataFrame
            if params:
                df = pd.read_sql(text(query), connection, params=params)
            else:
                df = pd.read_sql(text(query), connection)

            # Limit the number of rows
            if limit > 0:
                df = df.head(limit)

            # Convert to dictionary format
            result = {
                "success": True,
                "is_select": True,
                "rows": df.to_dict(orient="records"),
                "columns": df.columns.tolist(),
                "row_count": len(df),
            }
        else:
            # For non-SELECT queries, execute directly
            if params:
                result_proxy = connection.execute(text(query), params)
            else:
                result_proxy = connection.execute(text(query))

            result = {
                "success": True,
                "is_select": False,
                "affected_rows": result_proxy.rowcount,
            }

        return result
    except Exception as e:
        return {"success": False, "error": f"Query execution failed: {str(e)}"}


@mcp.tool()
def list_tables(connection_id: str, ctx: Context = None) -> Dict[str, Any]:
    """
    List all tables in the connected database.

    Args:
        connection_id: Connection identifier returned from connect_database

    Returns:
        Dictionary with list of tables and their schema information
    """
    if connection_id not in active_connections:
        return {
            "success": False,
            "error": "Invalid connection ID. Please connect to the database first.",
        }

    connection_info = active_connections[connection_id]

    return {
        "success": True,
        "database_type": connection_info["type"],
        "tables": connection_info["tables"],
        "schema": connection_info["schema"],
    }


@mcp.tool()
def describe_table(
    connection_id: str, table_name: str, ctx: Context = None
) -> Dict[str, Any]:
    """
    Get detailed schema information for a specific table.

    Args:
        connection_id: Connection identifier returned from connect_database
        table_name: Name of the table to describe

    Returns:
        Dictionary with table schema information
    """
    if connection_id not in active_connections:
        return {
            "success": False,
            "error": "Invalid connection ID. Please connect to the database first.",
        }

    connection_info = active_connections[connection_id]
    engine = connection_info["engine"]

    try:
        # Get database inspector
        inspector = inspect(engine)

        # Get column information
        columns = inspector.get_columns(table_name)

        # Get primary key information
        pk_columns = inspector.get_pk_constraint(table_name).get(
            "constrained_columns", []
        )

        # Get foreign key information
        foreign_keys = inspector.get_foreign_keys(table_name)

        # Get index information
        indexes = inspector.get_indexes(table_name)

        # Format column information
        column_info = []
        for col in columns:
            column_info.append(
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "default": str(col.get("default", "None")),
                    "is_primary_key": col["name"] in pk_columns,
                }
            )

        # Execute a sample query to get row count
        query = text(f"SELECT COUNT(*) as count FROM {table_name}")
        result = connection_info["connection"].execute(query).fetchone()
        row_count = result[0] if result else 0

        return {
            "success": True,
            "table_name": table_name,
            "columns": column_info,
            "primary_keys": pk_columns,
            "foreign_keys": foreign_keys,
            "indexes": indexes,
            "row_count": row_count,
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to describe table: {str(e)}"}


@mcp.tool()
def disconnect(connection_id: str, ctx: Context = None) -> Dict[str, Any]:
    """
    Close a database connection.

    Args:
        connection_id: Connection identifier returned from connect_database

    Returns:
        Dictionary with disconnection status
    """
    if connection_id not in active_connections:
        return {
            "success": False,
            "error": "Invalid connection ID. No active connection to close.",
        }

    try:
        connection_info = active_connections[connection_id]
        connection = connection_info["connection"]

        # Close the connection
        connection.close()

        # Remove from active connections
        del active_connections[connection_id]

        return {
            "success": True,
            "message": f"Successfully disconnected from {connection_info['type']} database.",
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to disconnect: {str(e)}"}


@mcp.resource("sql://schema/{connection_id}")
def schema_resource(connection_id: str) -> str:
    """
    Get the database schema as a formatted resource.

    Args:
        connection_id: Connection identifier returned from connect_database
    """
    if connection_id not in active_connections:
        return "# Error\n\nInvalid connection ID. Please connect to the database first."

    connection_info = active_connections[connection_id]

    # Format as markdown
    result = f"# {connection_info['type']} Database Schema\n\n"
    result += f"## Tables ({len(connection_info['tables'])})\n\n"

    for table_name in connection_info["tables"]:
        result += f"### {table_name}\n\n"
        result += "| Column | Type | Description |\n"
        result += "|--------|------|-------------|\n"

        for column in connection_info["schema"][table_name]:
            result += f"| {column['name']} | {column['type']} | |\n"

        result += "\n"

    return result


@mcp.resource("sql://query/{connection_id}/{query}")
def query_resource(connection_id: str, query: str) -> str:
    """
    Execute a SQL query and return the results as a formatted resource.

    Args:
        connection_id: Connection identifier returned from connect_database
        query: SQL query to execute (URL-encoded)
    """
    if connection_id not in active_connections:
        return "# Error\n\nInvalid connection ID. Please connect to the database first."

    # URL-decode the query
    query = query.replace("%20", " ").replace("%22", '"').replace("%27", "'")

    # Execute the query
    result = execute_query(connection_id, query, limit=20)

    if not result["success"]:
        return f"# Error Executing Query\n\n{result['error']}"

    # Format as markdown
    output = "# SQL Query Results\n\n"
    output += f"```sql\n{query}\n```\n\n"

    if result.get("is_select", False):
        # Format SELECT results as a table
        if result["row_count"] == 0:
            output += "No results returned.\n"
        else:
            # Create header row
            output += "| " + " | ".join(result["columns"]) + " |\n"
            output += "|" + "---|" * len(result["columns"]) + "\n"

            # Add data rows
            for row in result["rows"]:
                output += (
                    "| "
                    + " | ".join(str(row.get(col, "")) for col in result["columns"])
                    + " |\n"
                )

            if result["row_count"] >= 20:
                output += "\n*Query limited to 20 rows. Use the execute_query tool for more results.*\n"
    else:
        # Format non-SELECT results
        output += f"**Affected rows:** {result['affected_rows']}\n"

    return output


@mcp.prompt()
def connect_database_prompt(connection_string: str = "") -> str:
    """
    Create a prompt for connecting to a database.

    Args:
        connection_string: Optional database connection string
    """
    if connection_string:
        masked_connection = mask_password(connection_string)
        return f"""I'd like to connect to the database at {masked_connection}.

Please use the database connection tool to establish a connection and then show me what tables are available.
"""
    else:
        return """I'd like to connect to a SQL database.

Please provide the connection string in one of these formats:
- MySQL: "mysql+pymysql://user:password@host:port/database"
- PostgreSQL: "postgresql+psycopg2://user:password@host:port/database"

I'll help you explore the database schema and run queries.
"""


@mcp.prompt()
def explore_database_prompt(connection_id: str = "") -> str:
    """
    Create a prompt for exploring a connected database.

    Args:
        connection_id: Connection identifier returned from connect_database
    """
    return f"""I'm now connected to the database with connection ID: {connection_id}.

Let's explore this database. I can:
1. List all tables
2. Describe specific tables in detail
3. Run SQL queries
4. Analyze the data

What would you like to do first?
"""


# Helper function to mask password in connection strings for logging
def mask_password(connection_string: str) -> str:
    """Masks the password in a database connection string for security."""
    return re.sub(r"(://.+:).+(@.+)", r"\1*****\2", connection_string)


# Allow direct execution of the server
if __name__ == "__main__":
    mcp.run()
