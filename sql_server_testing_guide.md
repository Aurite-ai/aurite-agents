# SQL MCP Server Testing Guide

This guide explains how to test the SQL MCP server implementation in the Aurite Agents codebase.

## Prerequisites

1. Python 3.12+ (recommended)
2. PostgreSQL installed locally
3. A test database created in PostgreSQL

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install the required dependencies:
   ```bash
   pip install sqlalchemy pandas pymysql psycopg2-binary mcp anthropic
   ```

3. Install the aurite-mcp package in development mode:
   ```bash
   cd aurite-mcp
   pip install -e .
   cd ..
   ```

4. Create a test database in PostgreSQL:
   ```bash
   sudo -u postgres psql -c "CREATE DATABASE testdb;"
   sudo -u postgres psql -d testdb -c "CREATE TABLE users (id SERIAL PRIMARY KEY, name VARCHAR(100), email VARCHAR(100));"
   sudo -u postgres psql -d testdb -c "INSERT INTO users (name, email) VALUES ('John Doe', 'john@example.com'), ('Jane Smith', 'jane@example.com');"
   ```

5. Ensure your PostgreSQL user has the correct password:
   ```bash
   sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'password';"
   ```

6. Create a .env file with your Anthropic API key:
   ```bash
   echo "ANTHROPIC_API_KEY=your_api_key_here" > .env
   ```

## Testing with the MCP Client

You can test the SQL MCP server using either the interactive client or the automated test script:

### Automated Testing

Run the provided test script to automatically connect to the database, run a query, and disconnect:

```bash
python test_sql_client.py aurite-mcp/src/storage/sql/sql_server.py
```

### Interactive Testing

You can also use the interactive client for manual testing:

```bash
python client.py aurite-mcp/src/storage/sql/sql_server.py
```

When using the interactive client, follow these steps:

1. Connect to the database:
   ```
   Connect to the PostgreSQL database on localhost with the following connection string: postgresql+psycopg2://postgres:password@localhost:5432/testdb
   ```

2. Get the connection_id from the response, then query the database:
   ```
   Using connection_id <connection_id>, execute a SELECT query to show all records in the users table
   ```

3. Disconnect when finished:
   ```
   Disconnect from the database with connection_id <connection_id>
   ```

## Available Tools

The SQL MCP server provides the following tools:

1. `connect_database` - Connect to a SQL database using a connection string
2. `execute_query` - Execute a SQL query on a connected database
3. `list_tables` - List all tables in a connected database
4. `describe_table` - Get detailed schema for a specific table
5. `disconnect` - Close a database connection

## SQL Server Features

- Supports both MySQL and PostgreSQL databases
- Automatic connection string correction
- Schema introspection capabilities
- Support for both SELECT and non-SELECT queries
- Secure handling of database credentials (password masking)
- Connection pooling for multiple database sessions
