#!/usr/bin/env python3
"""
Test Weather MCP Server - Bad Implementation
This server has intentional flaws to test our detection capabilities.
It's designed to FAIL specific framework-agnostic tests.

INTENTIONAL FLAWS:
1. Security Issues:
   - No input sanitization (allows injection attempts)
   - Exposes internal errors in responses
   - Logs sensitive data without sanitization

2. Quality Issues:
   - Crashes on city names > 100 characters
   - Returns inconsistent response formats
   - Has race conditions with concurrent requests
   - Memory leak simulation (growing internal buffer)

3. Performance Issues:
   - Random delays (100ms - 5000ms)
   - Occasional timeouts
   - Performance degradation over time
"""

import asyncio
import json
import logging
import random
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Configure logging (BAD: logs everything including sensitive data)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("test-weather-bad")

# Simulated weather data
WEATHER_DATA = {
    "San Francisco": {"temperature": 72, "conditions": "Partly Cloudy", "humidity": 65, "wind_speed": 12},
    "New York": {"temperature": 68, "conditions": "Clear", "humidity": 55, "wind_speed": 8},
    "London": {"temperature": 59, "conditions": "Overcast", "humidity": 75, "wind_speed": 15},
}

# BAD: Memory leak simulation - this list grows without bounds
MEMORY_LEAK_BUFFER = []

# BAD: Global state that causes race conditions
REQUEST_COUNTER = 0
LAST_REQUEST_TIME = None


class BadWeatherValidator:
    """Intentionally flawed input validation"""

    @classmethod
    def validate_city_name(cls, city: str) -> tuple[bool, Optional[str], Optional[str]]:
        """
        BAD VALIDATION: Has multiple security and quality issues
        """
        # BAD: No type checking
        # BAD: No trimming of whitespace

        # BAD: Will crash on long inputs (buffer overflow simulation)
        if len(city) > 100:
            # BAD: Unhandled exception will crash the server
            raise MemoryError(f"Buffer overflow! Input too long: {len(city)} characters")

        # BAD: No injection protection - just logs the input
        logger.debug(f"Processing city name: {city}")  # BAD: Logs unsanitized input

        # BAD: Weak validation that misses many edge cases
        if not city:
            return False, None, "City required"

        # BAD: Accepts any input that isn't empty
        return True, city, None


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools"""
    # BAD: Sometimes returns incomplete schema
    if random.random() < 0.1:  # 10% chance of bad schema
        return [
            types.Tool(
                name="weather_lookup",
                description="Get weather",  # BAD: Vague description
                inputSchema={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string"
                            # BAD: Missing description and constraints
                        }
                    },
                    # BAD: Missing "required" field
                },
            )
        ]

    return [
        types.Tool(
            name="weather_lookup",
            description="Get current weather for a city",
            inputSchema={
                "type": "object",
                "properties": {"location": {"type": "string", "description": "City name"}},
                "required": ["location"],
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Handle tool calls with intentional flaws"""

    global REQUEST_COUNTER, LAST_REQUEST_TIME, MEMORY_LEAK_BUFFER

    # BAD: Race condition with global state
    REQUEST_COUNTER += 1
    current_time = time.time()

    # BAD: Memory leak - keeps growing
    MEMORY_LEAK_BUFFER.append(
        {
            "request_id": REQUEST_COUNTER,
            "timestamp": current_time,
            "arguments": str(arguments),  # BAD: Stores potentially sensitive data
        }
    )

    # BAD: Random delays to simulate performance issues
    delay = random.uniform(0.1, 5.0)  # Up to 5 seconds!
    if random.random() < 0.05:  # 5% chance of timeout
        delay = 30.0  # Simulate timeout

    # BAD: Performance degradation over time
    if len(MEMORY_LEAK_BUFFER) > 100:
        delay += len(MEMORY_LEAK_BUFFER) * 0.01  # Gets slower as memory leak grows

    await asyncio.sleep(delay)

    if name != "weather_lookup":
        # BAD: Exposes internal error details
        return [
            types.TextContent(
                type="text", text=f"ERROR: Unknown tool '{name}'. Available tools: {list(WEATHER_DATA.keys())}"
            )
        ]

    # Extract location parameter
    location = arguments.get("location")

    # BAD: Sometimes doesn't check if location is provided
    if random.random() < 0.1:  # 10% chance to skip validation
        pass
    elif not location:
        # BAD: Inconsistent error format
        return [
            types.TextContent(
                type="text",
                text="ERROR: No location",  # BAD: Different format than other errors
            )
        ]

    try:
        # Validate input (badly)
        is_valid, sanitized_city, error_msg = BadWeatherValidator.validate_city_name(location or "")

        if not is_valid:
            # BAD: Exposes validation logic in error
            return [
                types.TextContent(type="text", text=f"Validation failed: {error_msg} (validator: BadWeatherValidator)")
            ]

        # BAD: SQL injection vulnerability simulation
        if location and ("DROP TABLE" in location.upper() or "'; " in location):
            # BAD: Actually logs this as if it were executed
            logger.warning(f"EXECUTING SQL: SELECT * FROM weather WHERE city = '{location}'")

        # BAD: Path traversal vulnerability simulation
        if location and "../" in location:
            # BAD: Exposes file system structure
            return [types.TextContent(type="text", text=f"File not found: /var/data/weather/{location}.json")]

        # Get weather data
        weather = WEATHER_DATA.get(
            sanitized_city or "",
            {
                "temperature": random.randint(0, 100),  # BAD: Random data for unknown cities
                "conditions": random.choice(["Sunny", "Rainy", None]),  # BAD: Can be None!
                "humidity": random.randint(0, 200),  # BAD: Invalid range (>100%)
            },
        )

        # BAD: Inconsistent response format
        if random.random() < 0.2:  # 20% chance of missing fields
            response = {
                "location": sanitized_city,
                "temp": weather.get("temperature"),  # BAD: Different field name
                # Missing other fields
            }
        elif random.random() < 0.1:  # 10% chance of wrong structure
            response = {
                "data": {
                    "location": sanitized_city,
                    "weather": weather,  # BAD: Nested differently
                }
            }
        else:
            response = {
                "location": sanitized_city,
                "temperature": weather.get("temperature"),
                "conditions": weather.get("conditions"),
                "humidity": weather.get("humidity"),
                "wind_speed": weather.get("wind_speed"),
                # BAD: Sometimes includes debug info
                "debug": {"request_count": REQUEST_COUNTER, "memory_usage": len(MEMORY_LEAK_BUFFER)}
                if random.random() < 0.3
                else None,
            }

            # BAD: Remove None values inconsistently
            if random.random() < 0.5:
                response = {k: v for k, v in response.items() if v is not None}

        # BAD: Sometimes forgets timestamp
        if random.random() > 0.3 and isinstance(response, dict):
            response["timestamp"] = datetime.now(timezone.utc).isoformat()  # type: ignore

        return [types.TextContent(type="text", text=json.dumps(response, indent=2))]

    except Exception as e:
        # BAD: Exposes full stack trace
        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": True,
                        "message": str(e),
                        "traceback": traceback.format_exc(),  # BAD: Exposes internals
                        "type": type(e).__name__,
                        "server": "test-weather-bad",
                        "version": "1.0.0",
                    },
                    indent=2,
                ),
            )
        ]


async def main():
    """Run the server"""
    logger.info("Starting Test Weather Server (Bad Implementation)")
    logger.warning("This server has intentional flaws for testing purposes!")

    # Run the server using stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="test-weather-bad",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(), experimental_capabilities={}
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
