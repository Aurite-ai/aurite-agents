#!/usr/bin/env python3
"""
Test Weather MCP Server - Good Implementation
This server demonstrates best practices and proper implementation patterns.
It's designed to pass all framework-agnostic tests.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("test-weather-good")

# Simulated weather data for consistent testing
WEATHER_DATA = {
    "San Francisco": {"temperature": 72, "conditions": "Partly Cloudy", "humidity": 65, "wind_speed": 12},
    "New York": {"temperature": 68, "conditions": "Clear", "humidity": 55, "wind_speed": 8},
    "London": {"temperature": 59, "conditions": "Overcast", "humidity": 75, "wind_speed": 15},
    "Tokyo": {"temperature": 77, "conditions": "Sunny", "humidity": 60, "wind_speed": 5},
    "北京": {  # Beijing in Chinese
        "temperature": 70,
        "conditions": "Hazy",
        "humidity": 45,
        "wind_speed": 7,
    },
    "Москва": {  # Moscow in Russian
        "temperature": 50,
        "conditions": "Cloudy",
        "humidity": 80,
        "wind_speed": 20,
    },
    "القاهرة": {  # Cairo in Arabic
        "temperature": 95,
        "conditions": "Sunny",
        "humidity": 30,
        "wind_speed": 10,
    },
}

# Default weather for unknown cities
DEFAULT_WEATHER = {"temperature": 70, "conditions": "Clear", "humidity": 50, "wind_speed": 10}


class WeatherValidator:
    """Handles input validation for weather queries"""

    # Maximum city name length
    MAX_CITY_LENGTH = 100
    MIN_CITY_LENGTH = 1

    # Allowed characters: letters, numbers, spaces, hyphens, apostrophes, unicode
    # This regex allows Unicode letters, spaces, hyphens, and apostrophes
    VALID_CITY_PATTERN = re.compile(r"^[\w\s\-']+$", re.UNICODE)

    # Known injection patterns to reject
    INJECTION_PATTERNS = [
        r"<script",
        r"</script>",
        r"javascript:",
        r"DROP\s+TABLE",
        r"DELETE\s+FROM",
        r"INSERT\s+INTO",
        r"\.\./",
        r"\${",
        r"jndi:",
        r"ldap:",
    ]

    @classmethod
    def validate_city_name(cls, city: str) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Validates a city name for safety and format.

        Returns:
            tuple: (is_valid, sanitized_city, error_message)
        """
        # Check if city is provided
        if not city or not isinstance(city, str):
            return False, None, "City name is required and must be a string"

        # Trim whitespace
        city = city.strip()

        # Check length
        if len(city) < cls.MIN_CITY_LENGTH:
            return False, None, f"City name must be at least {cls.MIN_CITY_LENGTH} character"

        if len(city) > cls.MAX_CITY_LENGTH:
            return False, None, f"City name must not exceed {cls.MAX_CITY_LENGTH} characters"

        # Check for injection attempts
        city_lower = city.lower()
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, city_lower, re.IGNORECASE):
                logger.warning(f"Potential injection attempt detected: {city}")
                return False, None, "Invalid characters in city name"

        # Check character validity (allow unicode letters, spaces, hyphens, apostrophes)
        if not cls.VALID_CITY_PATTERN.match(city):
            return False, None, "City name contains invalid characters"

        return True, city, None


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="weather_lookup",
            description="Get current weather for a city",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name (1-100 characters, letters/numbers/spaces/hyphens/apostrophes)",
                    }
                },
                "required": ["location"],
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Handle tool calls"""

    # Add consistent 100ms delay to simulate API call
    await asyncio.sleep(0.1)

    if name != "weather_lookup":
        raise ValueError(f"Unknown tool: {name}")

    # Extract location parameter
    location = arguments.get("location")

    # Check location is provided
    if not location:
        error_response = {
            "error": True,
            "error_code": "MISSING_PARAMETER",
            "message": "Location parameter is required",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return [types.TextContent(type="text", text=json.dumps(error_response, indent=2))]

    # Validate input
    is_valid, sanitized_city, error_msg = WeatherValidator.validate_city_name(location)

    if not is_valid:
        # Return structured error response
        error_response = {
            "error": True,
            "error_code": "INVALID_INPUT",
            "message": error_msg,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return [types.TextContent(type="text", text=json.dumps(error_response, indent=2))]

    # Get weather data (use default if city not in our data)
    # sanitized_city is guaranteed to be a string here
    weather = WEATHER_DATA.get(sanitized_city or "", DEFAULT_WEATHER).copy()

    # Build consistent response format
    response = {
        "location": sanitized_city,
        "temperature": weather["temperature"],
        "conditions": weather["conditions"],
        "humidity": weather["humidity"],
        "wind_speed": weather["wind_speed"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return [types.TextContent(type="text", text=json.dumps(response, indent=2))]


async def main():
    """Run the server"""
    logger.info("Starting Test Weather Server (Good Implementation)")

    # Run the server using stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="test-weather-good",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(), experimental_capabilities={}
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
