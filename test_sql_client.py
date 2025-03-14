import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv
import sys

load_dotenv()  # load environment variables from .env


class TestSQLClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command, args=[server_script_path], env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def run_sql_test(self):
        """Run a predefined SQL test query"""
        # First connect to the database
        query = "Connect to the PostgreSQL database on localhost with the following connection string: postgresql+psycopg2://postgres:password@localhost:5432/testdb"

        result = await self.process_query(query)
        print("\nConnection Result:")
        print(result)

        # Extract connection_id from the first response
        import re

        # Search for connection_id in the result
        match = re.search(r'"connection_id": "([^"]+)"', result)
        if match:
            connection_id = match.group(1)
            print(f"\nExtracted connection_id: {connection_id}")

            # Query the users table
            query = f"Using connection_id {connection_id}, execute a SELECT query to show all records in the users table"

            result = await self.process_query(query)
            print("\nQuery Result:")
            print(result)

            # Disconnect
            query = f"Disconnect from the database with connection_id {connection_id}"

            result = await self.process_query(query)
            print("\nDisconnect Result:")
            print(result)
        else:
            print(
                "\nFailed to extract connection_id from response, cannot continue with queries."
            )

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [{"role": "user", "content": query}]

        response = await self.session.list_tools()
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]

        # Initial Claude API call
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=messages,
            tools=available_tools,
        )

        # Process response and handle tool calls
        tool_results = []
        final_text = []

        for content in response.content:
            if content.type == "text":
                final_text.append(content.text)
            elif content.type == "tool_use":
                tool_name = content.name
                tool_args = content.input

                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                tool_results.append({"call": tool_name, "result": result})
                final_text.append(f"\n[Calling tool {tool_name} with args {tool_args}]")
                final_text.append(f"\n[Tool result: {result.content}]")

                # Add the assistant's tool use message
                messages.append(
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": content.id,
                                "name": tool_name,
                                "input": tool_args,
                            }
                        ],
                    }
                )

                # Add the tool result message
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": result.content,
                            }
                        ],
                    }
                )

                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=messages,
                    tools=available_tools,  # Important: Include tools in subsequent calls
                )

                final_text.append("\n" + response.content[0].text)

        return "\n".join(final_text)

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python test_sql_client.py <path_to_server_script>")
        sys.exit(1)

    client = TestSQLClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.run_sql_test()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
