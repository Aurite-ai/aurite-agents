"""
Test MCP server for host integration testing
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import pytz

from mcp.server.fastmcp import FastMCP, Context

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Define a system prompt that will be returned by our server
SYSTEM_PROMPT = """You are a helpful AI assistant with specialized tools.
Use these tools to answer questions about weather and time data.

Guidelines:
1. Use the weather_lookup tool to get weather information for a location
2. Use the current_time tool to get the current time in different timezones
3. Analyze the data and provide helpful insights
4. Explain your reasoning clearly
"""

# Create the MCP server
mcp = FastMCP(name="Test Weather Server")

# Tool definitions
@mcp.tool()
def weather_lookup(location: str, units: str = "metric", ctx: Context = None) -> Dict[str, Any]:
    """
    Look up weather information for a location
    
    Args:
        location: City name or location
        units: Temperature units (metric or imperial)
        
    Returns:
        Dictionary with weather information
    """
    ctx.info(f"Looking up weather for {location} in {units} units")
    
    # Mock weather data for testing
    weather_data = {
        "San Francisco": {"temp": 18, "condition": "Foggy", "humidity": 85},
        "New York": {"temp": 22, "condition": "Partly Cloudy", "humidity": 60},
        "London": {"temp": 15, "condition": "Rainy", "humidity": 90},
        "Tokyo": {"temp": 25, "condition": "Sunny", "humidity": 50},
    }
    
    # Get data for the requested location or provide a default response
    data = weather_data.get(
        location, 
        {"temp": 20, "condition": "Clear", "humidity": 65}
    )
    
    # Convert temperature if needed
    temp = data["temp"]
    if units == "imperial":
        temp = round(temp * 9/5 + 32)
        unit_label = "°F"
    else:
        unit_label = "°C"
        
    response_text = (
        f"Weather for {location}:\n"
        f"Temperature: {temp}{unit_label}\n"
        f"Condition: {data['condition']}\n"
        f"Humidity: {data['humidity']}%"
    )
    
    return {"text": response_text}

@mcp.tool()
def current_time(timezone: str = "UTC", ctx: Context = None) -> Dict[str, Any]:
    """
    Get the current time in a specific timezone
    
    Args:
        timezone: Timezone name (e.g., 'America/New_York', 'Europe/London')
        
    Returns:
        Dictionary with current time information
    """
    ctx.info(f"Getting current time for timezone: {timezone}")
    
    try:
        # Try to get the current time in the requested timezone
        tz = pytz.timezone(timezone)
        current_time = datetime.now(tz)
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S %Z")
        
        return {"text": f"Current time in {timezone}: {formatted_time}"}
    except pytz.exceptions.UnknownTimeZoneError:
        return {"text": f"Error: Unknown timezone: {timezone}. Please provide a valid timezone name."}

# Prompt definitions
@mcp.prompt()
def assistant(user_name: Optional[str] = None, temperature_units: Optional[str] = None) -> str:
    """
    System prompt for weather assistant
    
    Args:
        user_name: Name of the user for personalization
        temperature_units: Default units for temperature
    
    Returns:
        Formatted system prompt
    """
    formatted_prompt = SYSTEM_PROMPT
    
    # Add personalization if user_name is provided
    if user_name:
        formatted_prompt = f"Hello {user_name}! " + formatted_prompt
        
    # Add default units preference if specified
    if temperature_units:
        formatted_prompt += f"\n\nDefault temperature units: {temperature_units.upper()}"
        
    return formatted_prompt

# Allow direct execution of the server
if __name__ == "__main__":
    mcp.run()