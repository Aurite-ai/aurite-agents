"""
Example using the MCP host with the weather service.
"""

import asyncio
import logging
from pathlib import Path

from src.host.host import MCPHost, HostConfig, ClientConfig
from src.host.roots import RootConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def main():
    """Run the weather service example"""
    try:
        # Configure the weather client
        weather_config = ClientConfig(
            client_id="weather-client",
            server_path=Path("src/servers/server.py"),
            roots=[
                RootConfig(
                    uri="weather://api.weather.gov",
                    name="NWS Weather API",
                    capabilities=["get_alerts", "get_forecast"],
                )
            ],
            capabilities=["weather_info"],
        )

        # Create and initialize the host
        host = MCPHost(HostConfig(clients=[weather_config]))
        await host.initialize()

        # Example: Get weather alerts for California
        logger.info("Getting weather alerts for California...")
        alerts = await host.call_tool("get_alerts", {"state": "CA"})
        print("\nWeather Alerts:")
        for content in alerts:
            print(content.text)

        # Example: Get weather forecast for San Francisco
        logger.info("Getting weather forecast for San Francisco...")
        forecast = await host.call_tool(
            "get_forecast", {"latitude": 37.7749, "longitude": -122.4194}
        )
        print("\nWeather Forecast:")
        for content in forecast:
            print(content.text)

    except Exception as e:
        logger.error(f"Error in weather example: {e}")
        raise
    finally:
        # Cleanup
        await host.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
