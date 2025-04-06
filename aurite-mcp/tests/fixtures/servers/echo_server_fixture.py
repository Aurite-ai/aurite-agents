#!/usr/bin/env python
"""
Minimal MCP server fixture that provides an 'echo' tool.
Used for basic integration testing.
"""

import sys
import asyncio
import logging

# Add project root to path to allow importing mcp
# Assuming this script is run from aurite-mcp directory or project root is in PYTHONPATH
# If running directly, adjust path as needed
# sys.path.append(str(Path(__file__).parent.parent.parent.parent)) # Not needed if run via python -m

from mcp import Server, StdioServerTransport
import mcp.types as types

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EchoServer:
    def __init__(self):
        self.server = Server(
            types.Implementation(name="echo-test-server", version="0.1.0"),
            capabilities=types.ServerCapabilities(
                tools=types.ToolsCapabilities(dynamicRegistration=False)
            ),
        )
        self._setup_handlers()

    def _setup_handlers(self):
        @self.server.method(types.ListToolsRequest)
        async def list_tools(
            req: types.ListToolsRequest, session
        ) -> types.ListToolsResult:
            logger.info("Handling ListToolsRequest")
            return types.ListToolsResult(
                tools=[
                    types.Tool(
                        name="echo",
                        description="Echoes the input arguments back.",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "message": {
                                    "type": "string",
                                    "description": "The message to echo.",
                                }
                            },
                            "required": ["message"],
                        },
                    )
                ]
            )

        @self.server.method(types.CallToolRequest)
        async def call_tool(
            req: types.CallToolRequest, session
        ) -> types.CallToolResult:
            logger.info(f"Handling CallToolRequest for tool: {req.params.name}")
            if req.params.name == "echo":
                arguments = req.params.arguments or {}
                echo_message = arguments.get("message", "No message provided")
                logger.info(f"Echoing message: {echo_message}")
                return types.CallToolResult(
                    content=[
                        types.ToolResultContentBlock(
                            type="text", text=f"Echo: {echo_message}"
                        )
                    ]
                )
            else:
                logger.error(f"Unknown tool called: {req.params.name}")
                # Raise an error or return an error result
                return types.CallToolResult(
                    content=[
                        types.ToolResultContentBlock(
                            type="text", text=f"Error: Unknown tool '{req.params.name}'"
                        )
                    ],
                    isError=True,
                )

    async def run(self):
        logger.info("Starting EchoServer fixture...")
        transport = StdioServerTransport()
        await self.server.connect(transport)
        logger.info("EchoServer fixture connected via stdio.")
        await self.server.wait_closed()
        logger.info("EchoServer fixture finished.")


async def main():
    server = EchoServer()
    await server.run()


if __name__ == "__main__":
    # Ensure the script runs with asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("EchoServer fixture stopped by user.")
