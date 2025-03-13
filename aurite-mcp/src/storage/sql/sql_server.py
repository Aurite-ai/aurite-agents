from mcp.server.fastmcp import FastMCP, Context
from sqlalchemy import create_engine, text, inspect
from typing import Dict, Optional, Any
import re
import pandas as pd

# Create the MCP server
mcp = FastMCP(
    "SQL Explorer", dependencies=["sqlalchemy", "pandas", "pymysql", "psycopg2-binary"]
)

# Dictionary to store connections for reuse
active_connections = {}


@mcp.tool()
def connect_database(connection_string: str, ctx: Context = None) -> Dict[str, Any]:
    """
    Connect to a SQL database using SQLAlchemy.
    Automatically detects MySQL or PostgreSQL databases.

    Args:
        connection_string: Database connection string
            - MySQL format: "mysql+pymysql://user:password@host:port/database"
            - PostgreSQL format: "postgresql+psycopg2://user:password@host:port/database"

    Returns:
        Dictionary with connection status, database type, and available tables
    """
    try:
        # Log connection attempt (masking password for security)
        masked_connection = mask_password(connection_string)
        ctx.info(f"Attempting to connect to database: {masked_connection}")

        # Check if connection string has the right format
        if not (
            connection_string.startswith("mysql+")
            or connection_string.startswith("postgresql+")
            or connection_string.startswith("mysql://")
            or connection_string.startswith("postgresql://")
        ):
            # Try to auto-correct the connection string if possible
            if "mysql" in connection_string.lower():
                if not connection_string.startswith("mysql+pymysql://"):
                    connection_string = connection_string.replace(
                        "mysql://", "mysql+pymysql://"
                    )
                    if not connection_string.startswith("mysql+"):
                        connection_string = "mysql+pymysql://" + connection_string
            elif "postgre" in connection_string.lower():
                if not connection_string.startswith("postgresql+psycopg2://"):
                    connection_string = connection_string.replace(
                        "postgresql://", "postgresql+psycopg2://"
                    )
                    if not connection_string.startswith("postgresql+"):
                        connection_string = "postgresql+psycopg2://" + connection_string
            else:
                return {
                    "success": False,
                    "error": "Unsupported database type. Please use MySQL or PostgreSQL connection strings.",
                }

        # Create engine and connect
        engine = create_engine(connection_string)
        connection = engine.connect()

        # Determine database type
        db_type = "MySQL" if "mysql" in connection_string.lower() else "PostgreSQL"

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

        # Store connection for future use
        conn_id = masked_connection
        active_connections[conn_id] = {
            "engine": engine,
            "connection": connection,
            "type": db_type,
            "tables": tables,
            "schema": schema_info,
        }

        return {
            "success": True,
            "connection_id": conn_id,
            "database_type": db_type,
            "tables": tables,
            "schema": schema_info,
        }
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
