"""
Test MCP server for host integration testing
"""

import anyio
import sys
import logging
from typing import Dict, Any
from datetime import datetime
import pytz

from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# Set up logging
logging.basicConfig(
    level=logging.DEBUG, format="%(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_server() -> Server:
    """Create and configure the MCP server with all available tools."""
    app = Server("test-weather-server")

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        """Handle tool calls by routing to appropriate implementation."""
        try:
            if name == "weather_lookup":
                result = await weather_lookup(arguments)
            elif name == "current_time":
                result = await current_time(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
            return result
        except Exception as e:
            logger.error(f"Error: Tool call failed - {e}")
            raise

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        """List all available tools."""
        return [
            types.Tool(
                name="weather_lookup",
                description="Look up weather information for a location",
                inputSchema={
                    "type": "object",
                    "required": ["location"],
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name or location",
                        },
                        "units": {
                            "type": "string",
                            "description": "Temperature units (metric or imperial)",
                            "default": "metric",
                            "enum": ["metric", "imperial"],
                        },
                    },
                },
            ),
            types.Tool(
                name="current_time",
                description="Get the current time in a specific timezone",
                inputSchema={
                    "type": "object",
                    "required": ["timezone"],
                    "properties": {
                        "timezone": {
                            "type": "string",
                            "description": "Timezone name (e.g., 'America/New_York', 'Europe/London')",
                        },
                    },
                },
            ),
        ]

    return app


async def weather_lookup(args: Dict[str, Any]) -> list[types.TextContent]:
    """Look up weather information for a location."""
    location = args["location"]
    units = args.get("units", "metric")

    # Mock weather data
    weather_data = {
        "San Francisco": {"temp": 18, "condition": "Foggy", "humidity": 85},
        "New York": {"temp": 22, "condition": "Partly Cloudy", "humidity": 60},
        "London": {"temp": 15, "condition": "Rainy", "humidity": 90},
        "Tokyo": {"temp": 25, "condition": "Sunny", "humidity": 50},
    }

    data = weather_data.get(
        location, {"temp": 20, "condition": "Clear", "humidity": 65}
    )

    # Convert temperature if needed
    temp = data["temp"]
    if units == "imperial":
        temp = round(temp * 9 / 5 + 32)
        unit_label = "°F"
    else:
        unit_label = "°C"

    response_text = (
        f"Weather for {location}:\n"
        f"Temperature: {temp}{unit_label}\n"
        f"Condition: {data['condition']}\n"
        f"Humidity: {data['humidity']}%"
    )

    return [types.TextContent(type="text", text=response_text)]


async def current_time(args: Dict[str, Any]) -> list[types.TextContent]:
    """Get the current time in a specific timezone."""
    timezone = args["timezone"]

    try:
        tz = pytz.timezone(timezone)
        current_time = datetime.now(tz)
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S %Z")

        return [
            types.TextContent(
                type="text", text=f"Current time in {timezone}: {formatted_time}"
            )
        ]
    except pytz.exceptions.UnknownTimeZoneError:
        return [
            types.TextContent(
                type="text",
                text=f"Error: Unknown timezone: {timezone}. Please provide a valid timezone name.",
            )
        ]


def main() -> int:
    """Entry point for the MCP server."""
    logger.info("Starting Test Weather MCP Server...")

    app = create_server()

    async def arun():
        async with stdio_server() as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())

    anyio.run(arun)
    return 0


if __name__ == "__main__":
    sys.exit(main())
