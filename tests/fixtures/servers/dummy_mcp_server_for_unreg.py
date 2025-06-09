"""
MCP Server for weather and time functionality.
This server is a refactored version that uses the FastMCP convenience layer
for more intuitive tool and prompt definition.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

import pytz
from mcp.server.fastmcp import FastMCP

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server instance
mcp = FastMCP("Weather and Time Server")


@mcp.tool()
async def weather_lookup(
    location: str, units: Optional[str] = "metric"
) -> Dict[str, Any]:
    """
    Look up weather information for a specific location.

    Args:
        location: The city name to look up the weather for.
        units: The temperature units to use ('metric' for Celsius, 'imperial' for Fahrenheit).
    """
    # Mock weather data for demonstration
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

    response = {
        "location": location,
        "temperature": f"{temp}{unit_label}",
        "condition": data["condition"],
        "humidity": f"{data['humidity']}%",
    }
    logger.info(f"Looked up weather for {location}: {response}")
    return response


@mcp.tool()
async def current_time(timezone: str) -> str:
    """
    Get the current time in a specific timezone.

    Args:
        timezone: The timezone name (e.g., 'America/New_York', 'Europe/London').
    """
    try:
        tz = pytz.timezone(timezone)
        current_time_val = datetime.now(tz)
        formatted_time = current_time_val.strftime("%Y-%m-%d %H:%M:%S %Z")
        return f"Current time in {timezone}: {formatted_time}"
    except pytz.exceptions.UnknownTimeZoneError:
        logger.warning(f"Unknown timezone provided: {timezone}")
        return f"Error: Unknown timezone: {timezone}. Please provide a valid timezone name."


@mcp.prompt("weather_assistant")
def weather_assistant_prompt(
    user_name: Optional[str] = None, preferred_units: Optional[str] = None
) -> str:
    """
    A helpful assistant for weather and time information.

    Args:
        user_name: Name of the user for personalization.
        preferred_units: Preferred temperature units (metric/imperial).
    """
    prompt = (
        "You are a helpful weather assistant with access to weather and time tools.\n"
        "Use these tools to provide accurate weather and time information.\n\n"
        "Guidelines:\n"
        "1. Use weather_lookup to get current weather conditions.\n"
        "2. Use current_time to get timezone-specific times.\n"
        "3. Provide clear, concise responses.\n"
        "4. Always specify temperature units clearly."
    )

    # Add personalization if user_name provided
    if user_name:
        prompt = f"Hello {user_name}! " + prompt

    # Add unit preference if specified
    if preferred_units:
        prompt += f"\nPreferred units: {preferred_units.upper()}"

    return prompt


# Allow direct execution of the server
if __name__ == "__main__":
    mcp.run()
