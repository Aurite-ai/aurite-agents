# Secure Database Connection Design

## Overview

This document outlines the design for securely handling database connections in the Aurite MCP framework. The design focuses on minimizing credential exposure while maintaining a clean and flexible API for clients.

## Architecture Components

```
┌─────────┐     ┌─────────┐     ┌───────────────┐     ┌────────────┐
│  Client │────▶│   Host  │────▶│ Storage Router│────▶│ SQL Server │
└─────────┘     └─────────┘     └───────────────┘     └────────────┘
                     │                  │                   │
                     │                  │                   │
                     ▼                  ▼                   ▼
               ┌─────────────┐    ┌──────────┐      ┌─────────────┐
               │ Connection  │    │Connection│      │Query Executor│
               │ Management  │    │  Routing │      │              │
               └─────────────┘    └──────────┘      └─────────────┘
```

### Components and Responsibilities

1. **Client**
   - Provides initial connection parameters
   - Uses connection ID for subsequent operations
   - Never receives raw credentials after initial request

2. **Host**
   - Accepts connection parameters from client
   - Creates and manages database connections
   - Issues connection IDs to clients
   - Enforces security policies

3. **Storage Router**
   - Routes queries to appropriate database backends
   - Maps connection IDs to connection types
   - Abstracts database-specific details

4. **SQL Server**
   - Executes SQL queries
   - Works with established connections, never raw credentials
   - Returns query results to clients

## Security Flow

### 1. Initial Connection (One-Time Credential Transmission)

```
Client                          Host
  │                              │
  │ Connect to DB with params    │
  │ (host, db, username, pwd)    │
  │ ─────────────────────────────▶
  │                              │
  │                              │ Create connection object
  │                              │ Generate connection ID
  │                              │ Store connection (not credentials)
  │                              │
  │ Connection ID                │
  │ ◀─────────────────────────────
  │                              │
```

### 2. Query Execution (No Credential Transmission)

```
Client                          Host                          SQL Server
  │                              │                              │
  │ Execute query with conn_id   │                              │
  │ ─────────────────────────────▶                              │
  │                              │                              │
  │                              │ Look up connection object    │
  │                              │ by conn_id                   │
  │                              │                              │
  │                              │ Execute query with connection│
  │                              │ ─────────────────────────────▶
  │                              │                              │ Execute query using
  │                              │                              │ connection object
  │                              │ Query results                │
  │                              │ ◀─────────────────────────────
  │ Results                      │                              │
  │ ◀─────────────────────────────                              │
```

## Implementation Design

### 1. Connection Object Management

```python
# In host.py or storage_router.py
connection_pool = {}

def create_connection(connection_params):
    # Construct connection string (only in memory)
    conn_string = f"{connection_params['type']}://{connection_params['username']}:{connection_params['password']}@{connection_params['host']}/{connection_params['database']}"

    # Create connection
    engine = create_engine(conn_string)

    # Generate unique ID
    conn_id = str(uuid.uuid4())

    # Store only the connection object, not credentials
    connection_pool[conn_id] = {
        "engine": engine,
        "type": connection_params['type'],
        "metadata": {
            "host": connection_params['host'],
            "database": connection_params['database'],
            "username": connection_params['username'],
            # Password is NOT stored
        }
    }

    return conn_id
```

### 2. Connection API

Two main connection patterns will be supported:

#### A. Client-Provided Connection (Dynamic)

```python
@mcp.tool()
async def connect_storage(
    storage_type: str,
    host: str,
    database: str,
    username: str,
    password: str,
    port: Optional[int] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """Connect to a database with provided credentials"""
    # Create connection and get ID
    conn_id = create_connection({
        "type": storage_type,
        "host": host,
        "database": database,
        "username": username,
        "password": password,
        "port": port or default_ports[storage_type]
    })

    return {
        "success": True,
        "connection_id": conn_id,
        "database": database,
        "host": host
    }
```

#### B. Pre-Configured Connection (Managed)

```python
@mcp.tool()
async def connect_named_storage(
    connection_name: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """Connect to a pre-configured database by name"""
    # Load config
    config = load_connection_config(connection_name)
    if not config:
        return {"success": False, "error": f"Connection {connection_name} not found"}

    # Get credentials from environment or secure store
    credentials = get_credentials(config["credentialsEnv"])

    # Create connection with same pattern as dynamic connection
    conn_id = create_connection({
        "type": config["type"],
        "host": config["host"],
        "database": config["database"],
        "username": credentials["username"],
        "password": credentials["password"],
        "port": config.get("port", default_ports[config["type"]])
    })

    return {
        "success": True,
        "connection_id": conn_id,
        "connection_name": connection_name
    }
```

### 3. Query Execution

```python
@mcp.tool()
async def execute_query(
    connection_id: str,
    query: str,
    params: Optional[Dict[str, Any]] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """Execute a query using an established connection"""
    # Validate connection ID
    if connection_id not in connection_pool:
        return {"success": False, "error": "Invalid connection ID"}

    connection = connection_pool[connection_id]
    engine = connection["engine"]

    try:
        # Execute query
        with engine.connect() as conn:
            if params:
                result = conn.execute(text(query), params)
            else:
                result = conn.execute(text(query))

            # Process results
            if query.strip().lower().startswith("select"):
                rows = [dict(row) for row in result]
                return {
                    "success": True,
                    "rows": rows,
                    "row_count": len(rows)
                }
            else:
                return {
                    "success": True,
                    "affected_rows": result.rowcount
                }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

## Security Considerations

### 1. Transport Security

- All API communication must use HTTPS/TLS
- Internal process communication should use secure channels

### 2. Credential Handling

- Credentials exist only during connection establishment
- No logging of credentials or connection strings
- Parameterized queries to prevent SQL injection

### 3. Connection Lifecycle

- Implement proper connection timeout and cleanup
- Support explicit disconnection from client
- Monitor connection health and usage

### 4. Configuration Security

- Store pre-configured credentials in environment variables
- Use secure parameter stores in production
- Implement least-privilege database users

## Implementation Plan

1. Update `host.py` to implement connection pool management
2. Modify `storage_router.py` to use connection pool
3. Adapt `sql_server.py` to work with connection objects
4. Add configuration support for named connections
5. Implement secure logging throughout

## Managed Connection Configuration Format

```json
{
  "connections": {
    "main_db": {
      "type": "postgresql",
      "host": "localhost",
      "database": "mydb",
      "port": 5432,
      "credentialsEnv": "MAIN_DB_CREDENTIALS"
    },
    "analytics_db": {
      "type": "mysql",
      "host": "analytics.example.com",
      "database": "analytics",
      "credentialsEnv": "ANALYTICS_DB_CREDENTIALS"
    }
  }
}
```

Environment variables format:
```
MAIN_DB_CREDENTIALS=username:password
```