"""MCP server implementation for the weather service."""

import anyio
import sys
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from src.tools.weather import get_alerts, get_forecast


def create_server() -> Server:
    """Create and configure the MCP server with all available tools."""
    app = Server("weather-service")

    @app.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle tool calls by routing to appropriate implementation."""
        try:
            if name == "get_alerts":
                result = await get_alerts(arguments)
            elif name == "get_forecast":
                result = await get_forecast(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
            return result
        except Exception as e:
            print(f"Error: Tool call failed - {e}", file=sys.stderr)
            raise

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        """List all available tools."""
        return [
            types.Tool(
                name="get_alerts",
                description="Get weather alerts for a US state",
                inputSchema={
                    "type": "object",
                    "required": ["state"],
                    "properties": {
                        "state": {
                            "type": "string",
                            "description": "Two-letter US state code (e.g. CA, NY)",
                        }
                    },
                },
            ),
            types.Tool(
                name="get_forecast",
                description="Get weather forecast for a location",
                inputSchema={
                    "type": "object",
                    "required": ["latitude", "longitude"],
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "description": "Latitude of the location (-90 to 90)",
                        },
                        "longitude": {
                            "type": "number",
                            "description": "Longitude of the location (-180 to 180)",
                        },
                    },
                },
            ),
        ]

    return app


def main() -> int:
    """Entry point for the MCP server."""
    print("Starting Weather Service MCP Server...", file=sys.stderr)

    app = create_server()

    async def arun():
        async with stdio_server() as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())

    anyio.run(arun)
    return 0


if __name__ == "__main__":
    sys.exit(main())
