"""
Example using the MCP host with the weather service.
"""

import asyncio
import logging
from pathlib import Path
import json

from src.host.host import MCPHost, HostConfig, ClientConfig
from src.host.roots import RootConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def test_resources(host: MCPHost, client_id: str):
    """Test resource capabilities"""
    logger.info("Testing resource capabilities...")

    # List available resources
    resources = await host.list_resources(client_id)
    logger.info(f"Available resources: {[r.uri for r in resources]}")

    # Read San Francisco weather cache
    sf_uri = "weather://cache/san_francisco.json"
    logger.info(f"Reading resource: {sf_uri}")
    sf_data = await host.read_resource(sf_uri, client_id)
    for content in sf_data.contents:
        print("\nSan Francisco Weather Cache:")
        print(json.dumps(json.loads(content.text), indent=2))

    # Subscribe to resource updates
    logger.info(f"Subscribing to resource: {sf_uri}")
    await host.subscribe_to_resource(sf_uri, client_id)

    # Read historical data
    historical_uri = "weather://cache/historical/san_francisco.json"
    logger.info(f"Reading resource: {historical_uri}")
    historical_data = await host.read_resource(historical_uri, client_id)
    for content in historical_data.contents:
        print("\nHistorical Weather Data:")
        print(json.dumps(json.loads(content.text), indent=2))


async def test_prompts(host: MCPHost, client_id: str):
    """Test prompt capabilities"""
    logger.info("Testing prompt capabilities...")

    # List available prompts
    prompts = await host.list_prompts(client_id)
    logger.info(f"Available prompts: {[p.name for p in prompts]}")

    # Execute analyze-weather prompt
    logger.info("Executing analyze-weather prompt...")
    weather_result = await host.execute_prompt(
        "analyze-weather",
        {"location": "San Francisco", "conditions": "Sunny with light winds"},
        client_id,
    )
    print("\nWeather Analysis:")
    for message in weather_result.messages:
        print(message.content.text)

    # Execute analyze-forecast prompt
    logger.info("Executing analyze-forecast prompt...")
    forecast_result = await host.execute_prompt(
        "analyze-forecast",
        {
            "forecast": "Sunny, high 72°F, low 55°F",
            "historical_data": "Last week: high 70°F, low 54°F",
        },
        client_id,
    )
    print("\nForecast Analysis:")
    for message in forecast_result.messages:
        print(message.content.text)


async def test_tools(host: MCPHost):
    """Test tool capabilities"""
    logger.info("Testing tool capabilities...")

    # Get weather alerts for California
    logger.info("Getting weather alerts for California...")
    alerts = await host.call_tool("get_alerts", {"state": "CA"})
    print("\nWeather Alerts:")
    for content in alerts:
        print(content.text)

    # Get weather forecast for San Francisco
    logger.info("Getting weather forecast for San Francisco...")
    forecast = await host.call_tool(
        "get_forecast", {"latitude": 37.7749, "longitude": -122.4194}
    )
    print("\nWeather Forecast:")
    for content in forecast:
        print(content.text)


async def main():
    """Run the weather service example"""
    try:
        # Configure the weather client with routing weight
        weather_config = ClientConfig(
            client_id="weather-client",
            server_path=Path("examples/weather_server.py"),
            roots=[
                RootConfig(
                    uri="weather://api.weather.gov",
                    name="NWS Weather API",
                    capabilities=["read", "execute"],
                ),
                RootConfig(
                    uri="weather://cache",
                    name="Weather Cache",
                    capabilities=["read", "subscribe"],
                ),
            ],
            capabilities=["prompts", "resources", "tools"],
            routing_weight=1.0,  # Default weight for this server
        )

        # Could add additional weather servers with different weights
        backup_weather = ClientConfig(
            client_id="weather-backup",
            server_path=Path("examples/weather_server_backup.py"),
            roots=[...],
            capabilities=["tools"],
            routing_weight=0.5,  # Lower priority backup server
        )

        # Create and initialize the host with multiple servers
        host = MCPHost(HostConfig(clients=[weather_config, backup_weather]))
        await host.initialize()

        # Tools will now automatically route to the best available server
        await test_tools(host)  # No changes needed to test code

    except Exception as e:
        logger.error(f"Error in weather example: {e}")
        raise
    finally:
        # Cleanup
        await host.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
