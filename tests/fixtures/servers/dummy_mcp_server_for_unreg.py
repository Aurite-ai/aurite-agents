"""
A simple, self-contained MCP server for testing purposes.
This server provides a basic weather lookup tool and is used to verify
server registration and unregistration functionality without external dependencies.
"""

import logging
from typing import Dict, Any, Optional

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("Test Weather Server")


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
    # Mock weather data for consistent testing
    weather_data = {"Test City": {"temp": 25, "condition": "Sunny", "humidity": 50}}
    data = weather_data.get(
        location, {"temp": 10, "condition": "Cloudy", "humidity": 70}
    )

    temp = data["temp"]
    unit_label = "°C"
    if units == "imperial":
        temp = round(temp * 9 / 5 + 32)
        unit_label = "°F"

    response = {
        "location": location,
        "temperature": f"{temp}{unit_label}",
        "condition": data["condition"],
    }
    logger.info(f"Test server weather lookup for {location}: {response}")
    return response


if __name__ == "__main__":
    mcp.run()
