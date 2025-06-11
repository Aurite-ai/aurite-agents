# filepath: /home/wilcoxr/workspace/aurite/aurite-agents/src/aurite/packaged/example_mcp_servers/weather_mcp_server.py

from mcp.server.fastmcp import FastMCP
from mcp import types, Tool
from datetime import datetime
import pytz

WEATHER_ASSISTANT_PROMPT = """You are a helpful weather assistant with access to weather and time tools.
Use these tools to provide accurate weather and time information.

Guidelines:
1. Use weather_lookup to get current weather conditions
2. Use current_time to get timezone-specific times
3. Provide clear, concise responses
4. Always specify temperature units clearly
"""

app = FastMCP("weather-mcp-server")


@app.tool()
def list_tools() -> list[Tool]:
    return [
        Tool(
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
        Tool(
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


@app.tool()
def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "weather_lookup":
        location = arguments["location"]
        units = arguments.get("units", "metric")
        weather_data = {
            "San Francisco": {"temp": 18, "condition": "Foggy", "humidity": 85},
            "New York": {"temp": 22, "condition": "Partly Cloudy", "humidity": 60},
            "London": {"temp": 15, "condition": "Rainy", "humidity": 90},
            "Tokyo": {"temp": 25, "condition": "Sunny", "humidity": 50},
        }
        data = weather_data.get(
            location, {"temp": 20, "condition": "Clear", "humidity": 65}
        )
        temp = data["temp"]
        if units == "imperial":
            temp = round(temp * 9 / 5 + 32)
            unit_label = "°F"
        else:
            unit_label = "°C"
        response = f"Weather for {location}: Temp {temp}{unit_label}, {data['condition']}, Humidity {data['humidity']}%"
        return [types.TextContent(type="text", text=response)]
    elif name == "current_time":
        timezone = arguments["timezone"]
        try:
            tz = pytz.timezone(timezone)
            current_time = datetime.now(tz)
            formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S %Z")
            response = f"Current time in {timezone}: {formatted_time}"
        except pytz.exceptions.UnknownTimeZoneError:
            response = f"Error: Unknown timezone: {timezone}. Please provide a valid timezone name."
        return [types.TextContent(type="text", text=response)]
    raise ValueError(f"Tool not found: {name}")


@app.resource("weather:/assistant_prompt")
def weather_assistant_resource() -> str:
    """
    Weather assistant system prompt.
    """
    return WEATHER_ASSISTANT_PROMPT


if __name__ == "__main__":
    app.run()
