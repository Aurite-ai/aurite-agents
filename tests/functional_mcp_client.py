import asyncio
import json
import os
import sys
import re
from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from anthropic import Anthropic
from anthropic.types import MessageParam, ToolParam, ToolUseBlock, TextBlock
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()

    # methods will go here

    async def connect_to_server(self, server_config_str: str):
        """Connect to an MCP server

        Args:
            server_config_str: Path to a server script (.py or .js) or a JSON
                               string with "command" and "args".
        """
        transport_context = None
        try:
            config = json.loads(server_config_str)
            transport_type = config.get(
                "transport_type", "local"
            )  # Default to local for old format

            if transport_type == "http_stream":
                endpoint_url = config.get("http_endpoint")
                if not endpoint_url:
                    raise ValueError(
                        "http_endpoint is required for http_stream transport"
                    )

                # Resolve environment variable placeholders in the URL
                placeholders = re.findall(r"\{([^}]+)\}", endpoint_url)
                for placeholder in placeholders:
                    env_value = os.getenv(placeholder)
                    if env_value:
                        endpoint_url = endpoint_url.replace(
                            f"{{{placeholder}}}", env_value
                        )
                    else:
                        raise ValueError(
                            f"Could not resolve placeholder '{{{placeholder}}}' in http_endpoint."
                        )

                transport_context = streamablehttp_client(endpoint_url)

            else:  # Handles 'local' and legacy command/args format
                command = config["command"]
                args = config["args"]
                expanded_args = []
                for arg in args:
                    if arg.startswith("{") and arg.endswith("}"):
                        var_name = arg[1:-1]
                        value = os.getenv(var_name)
                        if value is None:
                            raise ValueError(
                                f"Environment variable {var_name} not set."
                            )
                        expanded_args.append(value)
                    else:
                        expanded_args.append(arg)
                args = expanded_args
                server_params = StdioServerParameters(
                    command=command, args=args, env=None
                )
                transport_context = stdio_client(server_params)

        except (json.JSONDecodeError, KeyError):
            # Fallback to legacy script path logic
            is_python = server_config_str.endswith(".py")
            is_js = server_config_str.endswith(".js")
            if not (is_python or is_js):
                raise ValueError(
                    "Argument must be a path to a .py or .js file, or a valid JSON config string."
                )
            command = "python" if is_python else "node"
            args = [server_config_str]
            server_params = StdioServerParameters(command=command, args=args, env=None)
            transport_context = stdio_client(server_params)

        transport_streams = await self.exit_stack.enter_async_context(transport_context)
        # Handle both 2-tuple (stdio) and 3-tuple (http) returns
        self.stdio, self.write = transport_streams[:2]
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()
        assert self.session is not None, "Session should be initialized"

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        assert self.session is not None, "Session must be active to process query"
        messages: List[MessageParam] = [{"role": "user", "content": query}]

        response = await self.session.list_tools()
        available_tools: List[ToolParam] = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]  # type: ignore

        # Start the conversation
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=messages,
            tools=available_tools,
        )

        final_text_parts = []

        while response.stop_reason == "tool_use":
            # Append any text content from the assistant's turn before the tool use
            for content_block in response.content:
                if content_block.type == "text":
                    final_text_parts.append(content_block.text)

            # Prepare for the next turn
            assistant_message_content: List[ToolUseBlock | TextBlock] = []
            tool_results_message_content: List[Dict[str, Any]] = []

            for content_block in response.content:
                if content_block.type == "tool_use":
                    tool_name = content_block.name
                    tool_args = content_block.input
                    tool_use_id = content_block.id

                    # Add the tool_use block to the assistant's message for history
                    assistant_message_content.append(content_block)

                    print(f"[Calling tool {tool_name} with args {tool_args}]")
                    # Execute tool call
                    assert self.session is not None
                    if not isinstance(tool_args, dict):
                        raise TypeError(
                            f"Tool arguments must be a dictionary, but got {type(tool_args)}"
                        )
                    result = await self.session.call_tool(tool_name, tool_args)

                    # Prepare the tool result for the next user message
                    tool_results_message_content.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": [{"type": "text", "text": str(result.content)}],
                        }
                    )
                elif content_block.type == "text":
                    # Also add text blocks to the assistant message history
                    assistant_message_content.append(content_block)

            # Append the full assistant message to history
            if assistant_message_content:
                messages.append(
                    {"role": "assistant", "content": assistant_message_content}
                )

            # Append the tool results to history for the next turn
            if tool_results_message_content:
                messages.append(
                    {"role": "user", "content": tool_results_message_content}  # type: ignore
                )

            # Make the next API call
            response = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=messages,
                tools=available_tools,
            )

        # After the loop, the final response should be text
        for content_block in response.content:
            if content_block.type == "text":
                final_text_parts.append(content_block.text)

        return "\n".join(final_text_parts)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print(
            'Usage: python functional_mcp_client.py <path_to_server_script | \'{"command": "...", "args": [...]}\'> [query]'
        )
        sys.exit(1)

    server_config_str = sys.argv[1]
    query = sys.argv[2] if len(sys.argv) > 2 else None

    client = MCPClient()
    try:
        await client.connect_to_server(server_config_str)
        if query:
            response = await client.process_query(query)
            print(response)
        else:
            await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
