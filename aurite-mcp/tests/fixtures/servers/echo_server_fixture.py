#!/usr/bin/env python
"""
Minimal MCP server fixture that provides an 'echo' tool.
Used for basic integration testing.
"""

import sys
import logging
import anyio  # Import anyio

# Add project root to path to allow importing mcp
# Assuming this script is run from aurite-mcp directory or project root is in PYTHONPATH
# If running directly, adjust path as needed
# sys.path.append(str(Path(__file__).parent.parent.parent.parent)) # Not needed if run via python -m

# Use low-level Server and stdio_server context manager
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
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

    # Removed the manual run method


def main() -> int:
    """Entry point for the MCP server using anyio."""
    logger.info("Starting EchoServer fixture...")
    server_instance = EchoServer()  # Create instance
    app = server_instance.server  # Get the low-level server app

    async def arun():
        # Use the stdio_server context manager
        async with stdio_server() as streams:
            logger.info("EchoServer fixture connected via stdio.")
            # Run the server app with the streams
            await app.run(streams[0], streams[1], app.create_initialization_options())
        logger.info("EchoServer fixture finished.")

    try:
        anyio.run(arun)
        return 0
    except KeyboardInterrupt:
        logger.info("EchoServer fixture stopped by user.")
        return 0
    except Exception as e:
        logger.exception(f"EchoServer fixture encountered an error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
