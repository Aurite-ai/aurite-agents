"""
Test file for demonstrating the host's security manager features with SQL connections.
"""

import asyncio
import os
from pathlib import Path

from src.host.host import MCPHost, HostConfig, ClientConfig, RootConfig

# Test configuration
SQL_SERVER_PATH = (
    Path(__file__).parent.parent.parent / "src" / "storage" / "sql" / "sql_server.py"
)
DATABASE_HOST = "localhost"
DATABASE_NAME = "testdb"
DATABASE_PORT = 5432
DATABASE_USER = "postgres"
DATABASE_PASSWORD = "password"


async def test_host_direct_connection():
    """Test connecting to database with direct parameters through host"""
    print("\n===== TESTING HOST WITH DIRECT CONNECTION =====")

    # Configure the host
    config = HostConfig(
        clients=[
            ClientConfig(
                client_id="sql_server",
                server_path=SQL_SERVER_PATH.absolute(),
                roots=[
                    RootConfig(
                        name="sql", uri="sql:///", capabilities=["read", "write"]
                    )
                ],
                capabilities=["tools", "storage"],
                routing_weight=1.0,
            )
        ]
    )

    # Create host instance
    host = MCPHost(config)

    try:
        # Initialize host (this starts the SQL server)
        await host.initialize()
        print("Host initialized with clients:", host._clients.keys())

        # Create connection parameters
        connection_params = {
            "type": "postgresql",
            "host": DATABASE_HOST,
            "database": DATABASE_NAME,
            "username": DATABASE_USER,
            "password": DATABASE_PASSWORD,
            "port": DATABASE_PORT,
        }

        # Create database connection through host
        print(
            "\nCreating database connection with parameters:",
            {
                k: v if k != "password" else "******"
                for k, v in connection_params.items()
            },
        )
        conn_id, metadata = await host.storage.create_database_connection(
            connection_params
        )
        print(f"Connection established with ID: {conn_id}")
        print(f"Connection metadata: {metadata}")

        # Execute a test query
        print("\nExecuting query...")
        result = await host.storage.execute_query(conn_id, "SELECT * FROM users")
        print(f"Query result: {result}")

        # Close the connection
        print("\nClosing connection...")
        closed = await host.storage.close_connection(conn_id)
        print(f"Connection closed: {closed}")

    finally:
        # Cleanup
        await host.shutdown()
        print("Host shut down")


async def test_host_named_connection():
    """Test connecting to database with named connection through host"""
    print("\n===== TESTING HOST WITH NAMED CONNECTION =====")

    # Make sure we have environment variable set
    os.environ["POSTGRES_CREDENTIALS"] = f"{DATABASE_USER}:{DATABASE_PASSWORD}"

    # Configure the host
    config = HostConfig(
        clients=[
            ClientConfig(
                client_id="sql_server",
                server_path=SQL_SERVER_PATH.absolute(),
                roots=[
                    RootConfig(
                        name="sql", uri="sql:///", capabilities=["read", "write"]
                    )
                ],
                capabilities=["tools", "storage"],
                routing_weight=1.0,
            )
        ]
    )

    # Create host instance
    host = MCPHost(config)

    try:
        # Initialize host (this starts the SQL server)
        await host.initialize()
        print("Host initialized with clients:", host._clients.keys())

        # Use named connection
        connection_name = "default_postgres"
        print(f"\nUsing named connection: {connection_name}")

        # Get connection from named configuration
        conn_id, metadata = await host.storage.get_named_connection(connection_name)
        print(f"Connection established with ID: {conn_id}")
        print(f"Connection metadata: {metadata}")

        # Execute a test query
        print("\nExecuting query...")
        result = await host.storage.execute_query(conn_id, "SELECT * FROM users")
        print(f"Query result: {result}")

        # Close the connection
        print("\nClosing connection...")
        closed = await host.storage.close_connection(conn_id)
        print(f"Connection closed: {closed}")

    finally:
        # Cleanup
        await host.shutdown()
        print("Host shut down")


async def test_client_call_through_host():
    """Test having a client make a connection through the host's security layer"""
    print("\n===== TESTING CLIENT CALL THROUGH HOST =====")

    # Configure the host
    config = HostConfig(
        clients=[
            ClientConfig(
                client_id="sql_server",
                server_path=SQL_SERVER_PATH.absolute(),
                roots=[
                    RootConfig(
                        name="sql", uri="sql:///", capabilities=["read", "write"]
                    )
                ],
                capabilities=["tools", "storage"],
                routing_weight=1.0,
            )
        ]
    )

    # Create host instance
    host = MCPHost(config)

    try:
        # Initialize host (this starts the SQL server)
        await host.initialize()
        print("Host initialized with clients:", host._clients.keys())

        # Client sends connection string (simulating an agent/client request)
        connection_string = f"postgresql+psycopg2://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

        # Host processes this through security manager
        conn_id, masked_connection = await host.storage.secure_database_connection(
            connection_string
        )
        print(f"Connection established with ID: {conn_id}")
        print(f"Masked connection string: {masked_connection}")

        # Using the connection ID for operations
        # In this model, future client requests would only use the connection ID
        print("\nExecuting query...")
        result = await host.storage.execute_query(conn_id, "SELECT * FROM users")
        print(f"Query result: {result}")

        # Client requests connection closure
        print("\nClosing connection...")
        closed = await host.storage.close_connection(conn_id)
        print(f"Connection closed: {closed}")

    finally:
        # Cleanup
        await host.shutdown()
        print("Host shut down")


async def main():
    """Run all tests"""
    # Test direct connection through host
    await test_host_direct_connection()

    # Test named connection through host
    await test_host_named_connection()

    # Test client call through host security layer
    await test_client_call_through_host()


if __name__ == "__main__":
    asyncio.run(main())
