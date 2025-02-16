"""
Weather service MCP server implementation.
"""

import asyncio
import logging
from typing import Dict, List, Any
import sys
import json
from urllib.parse import urlparse

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

logger = logging.getLogger(__name__)

# Example weather prompts
WEATHER_PROMPTS = [
    types.Prompt(
        name="analyze-weather",
        description="Analyze current weather conditions",
        arguments=[
            types.PromptArgument(
                name="location", description="Location to analyze", required=True
            ),
            types.PromptArgument(
                name="conditions",
                description="Weather conditions to analyze",
                required=True,
            ),
        ],
    ),
    types.Prompt(
        name="analyze-forecast",
        description="Analyze weather forecast with historical context",
        arguments=[
            types.PromptArgument(
                name="forecast", description="Current forecast data", required=True
            ),
            types.PromptArgument(
                name="historical_data",
                description="Historical weather data",
                required=True,
            ),
        ],
    ),
]

# Example weather resources
WEATHER_RESOURCES = [
    types.Resource(
        uri="weather://cache/san_francisco.json",
        name="San Francisco Weather Cache",
        mimeType="application/json",
        description="Current weather data for San Francisco",
    ),
    types.Resource(
        uri="weather://cache/historical/san_francisco.json",
        name="San Francisco Historical Weather",
        mimeType="application/json",
        description="Historical weather data for San Francisco",
    ),
    types.Resource(
        uri="weather://api.weather.gov/alerts/CA",
        name="California Weather Alerts",
        mimeType="application/json",
        description="Active weather alerts for California",
    ),
]


def create_server() -> Server:
    """Create and configure the MCP server with all available capabilities."""
    app = Server("weather-server")

    @app.list_tools()
    async def list_tools() -> List[types.Tool]:
        """List available weather tools"""
        return [
            types.Tool(
                name="get_alerts",
                description="Get weather alerts for a state",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "state": {
                            "type": "string",
                            "description": "Two-letter state code (e.g., CA)",
                        }
                    },
                    "required": ["state"],
                },
            ),
            types.Tool(
                name="get_forecast",
                description="Get weather forecast for a location",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "description": "Latitude of the location",
                        },
                        "longitude": {
                            "type": "number",
                            "description": "Longitude of the location",
                        },
                    },
                    "required": ["latitude", "longitude"],
                },
            ),
        ]

    @app.list_prompts()
    async def list_prompts() -> List[types.Prompt]:
        """List available weather prompts"""
        return WEATHER_PROMPTS

    @app.get_prompt()
    async def get_prompt(name: str, arguments: Dict[str, Any]) -> types.GetPromptResult:
        """Get a specific prompt with arguments"""
        if name == "analyze-weather":
            return types.GetPromptResult(
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text=f"Analyzing weather for {arguments['location']}: {arguments['conditions']}\n"
                            "Current conditions are sunny with light winds.\n"
                            "Forecast shows continued fair weather.",
                        ),
                    )
                ]
            )
        elif name == "analyze-forecast":
            return types.GetPromptResult(
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text="Analyzing forecast with historical context:\n"
                            "Temperature trends are within normal range.\n"
                            "Precipitation patterns match seasonal averages.",
                        ),
                    )
                ]
            )
        raise ValueError(f"Unknown prompt: {name}")

    @app.list_resources()
    async def list_resources() -> List[types.Resource]:
        """List available weather resources"""
        return WEATHER_RESOURCES

    @app.read_resource()
    async def read_resource(uri: str) -> str:
        """Read a weather resource"""
        logger.info(f"Reading resource: {uri}")

        # Convert string URI to normalized form for comparison
        uri_str = str(uri)  # Handle both string and AnyUrl objects
        parsed = urlparse(uri_str)
        normalized_uri = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

        # Find the matching resource
        matching_resource = None
        for resource in WEATHER_RESOURCES:
            if (
                str(resource.uri) == normalized_uri
            ):  # Convert AnyUrl to string for comparison
                matching_resource = resource
                break

        if not matching_resource:
            logger.error(f"Resource not found: {uri_str}")
            raise ValueError(f"Resource not found: {uri_str}")

        # Return JSON content directly as a string
        if normalized_uri == "weather://cache/san_francisco.json":
            return json.dumps(
                {
                    "current": {
                        "temp": 72,
                        "conditions": "Sunny",
                        "wind": "Light breeze",
                    },
                    "forecast": {
                        "today": "Sunny, high 72°F",
                        "tonight": "Clear, low 55°F",
                    },
                },
                indent=2,
            )
        elif normalized_uri == "weather://cache/historical/san_francisco.json":
            return json.dumps(
                {
                    "last_week": {
                        "high": 70,
                        "low": 54,
                        "conditions": "Partly cloudy",
                    }
                },
                indent=2,
            )
        elif normalized_uri == "weather://api.weather.gov/alerts/CA":
            return json.dumps({"alerts": []}, indent=2)
        else:
            logger.error(f"Resource content not implemented: {uri_str}")
            raise ValueError(f"Resource content not implemented: {uri_str}")

    @app.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a weather tool"""
        from src.tools.weather import get_alerts, get_forecast

        try:
            if name == "get_alerts":
                content = await get_alerts(arguments)
                # Return a dictionary that matches the exact structure needed
                return dict(
                    __root__={
                        "content": [
                            {
                                "type": "text",
                                "text": c.text if hasattr(c, "text") else str(c),
                            }
                            for c in content
                        ],
                        "isError": False,
                        "meta": None,
                    }
                )
            elif name == "get_forecast":
                content = await get_forecast(arguments)
                # Return a dictionary that matches the exact structure needed
                return dict(
                    __root__={
                        "content": [
                            {
                                "type": "text",
                                "text": c.text if hasattr(c, "text") else str(c),
                            }
                            for c in content
                        ],
                        "isError": False,
                        "meta": None,
                    }
                )
            raise ValueError(f"Unknown tool: {name}")
        except Exception as e:
            return dict(
                __root__={
                    "content": [{"type": "text", "text": str(e)}],
                    "isError": True,
                    "meta": None,
                }
            )

    return app


def main() -> int:
    """Entry point for the MCP server."""
    print("Starting Weather Service MCP Server...", file=sys.stderr)

    app = create_server()

    async def run():
        # Create initialization options with capabilities
        init_options = app.create_initialization_options()
        init_options.capabilities = types.ServerCapabilities(
            roots=types.RootsCapability(listChanged=True, enabled=True),
            tools=types.ToolsCapability(listChanged=True, enabled=True),
            prompts=types.PromptsCapability(listChanged=True, enabled=True),
            resources=types.ResourcesCapability(
                subscribe=True, listChanged=True, enabled=True
            ),
        )

        # Start the server with stdio transport
        async with stdio_server() as (read_stream, write_stream):
            print("Server ready for client connection...", file=sys.stderr)
            try:
                await app.run(read_stream, write_stream, init_options)
            except Exception as e:
                print(f"Server error: {e}", file=sys.stderr)
                raise

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("Server shutting down...", file=sys.stderr)
    except Exception as e:
        print(f"Server failed: {e}", file=sys.stderr)
        sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
