import asyncio
import logging
import os
import json

# Add the project root to the Python path to allow imports from 'src/aurite'
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.aurite.host.host import MCPHost
from src.aurite.config.config_models import ClientConfig

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def load_server_config(file_path: str, server_name: str) -> dict:
    """Load a specific server's configuration from a JSON file."""
    with open(file_path, "r") as f:
        all_configs = json.load(f)

    for config in all_configs:
        if config.get("name") == server_name:
            return config

    raise ValueError(
        f"Server configuration for '{server_name}' not found in {file_path}"
    )


async def main():
    """
    Initializes the MCPHost, registers the weather server, calls a tool,
    and shuts down, to test the host in isolation.
    """
    logging.info("--- Starting Host Isolation Test ---")
    host = MCPHost()

    try:
        async with host:
            logging.info("Host entered context.")

            # 1. Load server configuration
            config_path = (
                "src/aurite/init_templates/config/mcp_servers/example_mcp_servers.json"
            )
            server_name = "weather_server"
            server_config_dict = load_server_config(config_path, server_name)

            # Adjust path for local execution
            original_path = server_config_dict["server_path"]
            server_config_dict["server_path"] = os.path.join(
                "src/aurite/init_templates", original_path
            )

            client_config = ClientConfig(**server_config_dict)

            # 2. Register the client
            logging.info(f"Registering client: {client_config.name}")
            await host.register_client(client_config)
            logging.info("Client registered.")

            # 3. Verify tool is available
            if "weather_lookup" in host.tools:
                logging.info("Tool 'weather_lookup' is available.")
            else:
                logging.error("Tool 'weather_lookup' was not registered.")
                return

            # 4. Call the tool
            logging.info("Calling tool 'weather_lookup' for London...")
            args = {"location": "London"}
            result = await host.call_tool("weather_lookup", args)
            logging.info(f"Tool call result: {result}")

    except Exception as e:
        logging.error(f"An error occurred during the host test: {e}", exc_info=True)
    finally:
        logging.info("--- Host Isolation Test Finished ---")


if __name__ == "__main__":
    asyncio.run(main())
