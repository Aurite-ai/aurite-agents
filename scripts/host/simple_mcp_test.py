import asyncio
import json
import logging
import os
import shutil
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class Server:
    """Manages MCP server connections and tool execution."""

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name: str = name
        self.config: dict[str, Any] = config
        self.session: ClientSession | None = None
        self.exit_stack: AsyncExitStack = AsyncExitStack()

    async def initialize(self) -> None:
        """Initialize the server connection."""
        command = self.config.get("command")
        if not command:
            raise ValueError("A 'command' must be specified in the server config.")

        # Resolve command path
        if command == "npx":
            command = shutil.which("npx")

        if not command:
            raise ValueError(f"Command '{self.config.get('command')}' not found in PATH.")

        server_params = StdioServerParameters(
            command=command,
            args=self.config.get("args", []),
            env={**os.environ, **self.config.get("env", {})},
        )
        try:
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params, errlog=open(os.devnull, "w"))
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self.session = session
            logging.info(f"Successfully initialized server: {self.name}")
        except Exception as e:
            logging.error(f"Error initializing server {self.name}: {e}")
            await self.cleanup()
            raise

    async def list_tools(self) -> list[Any]:
        """List available tools from the server."""
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")

        logging.info(f"Listing tools for server: {self.name}")
        tools_response = await self.session.list_tools()
        logging.info(f"Tools response: {tools_response}")
        return tools_response.tools

    async def cleanup(self) -> None:
        """Clean up server resources."""
        logging.info(f"Cleaning up server: {self.name}")
        await self.exit_stack.aclose()
        self.session = None
        logging.info(f"Cleanup complete for server: {self.name}")


def load_server_config(file_path: str, server_name: str) -> dict[str, Any]:
    """Load a specific server's configuration from a JSON file."""
    with open(file_path, "r") as f:
        all_configs = json.load(f)

    for config in all_configs:
        if config.get("name") == server_name:
            return config

    raise ValueError(f"Server configuration for '{server_name}' not found in {file_path}")


async def main() -> None:
    """Initialize, test, and clean up the weather server."""
    server_config = None
    server = None
    try:
        # Path to the packaged config used by the agent runner
        config_path = "src/aurite/lib/init_templates/config/mcp_servers/example_mcp_servers.json"
        server_name = "weather_server"

        logging.info(f"Loading config for '{server_name}' from '{config_path}'")
        server_config = load_server_config(config_path, server_name)

        # The server_path in the config is relative to the project root created by `aurite init`
        # We need to adjust it to be relative to our current working directory.
        original_path = server_config["server_path"]
        server_config["server_path"] = os.path.join("src/aurite/lib/init_templates", original_path)

        # The command for a python script is 'python'
        server_config["command"] = "python"
        server_config["args"] = [server_config.pop("server_path")]

        server = Server(name=server_name, config=server_config)

        await server.initialize()
        await server.list_tools()

    except Exception as e:
        logging.error(f"An error occurred during the test: {e}", exc_info=True)
    finally:
        if server:
            await server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
