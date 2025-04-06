import anyio
import sys
import logging

from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# Set up basic logging for demonstration if running standalone
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Minimal Server Creation ---


def create_minimal_server() -> Server:
    """Creates a minimal low-level MCP Server instance."""
    app = Server("minimal-lowlevel-server")

    # --- Tool Implementation ---

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        """Handles tool calls."""
        logger.debug(f"Received call_tool request for '{name}' with args: {arguments}")
        if name == "hello_world":
            # No arguments needed for this simple tool
            return [types.TextContent(type="text", text="Hey there buddy!")]
        else:
            logger.error(f"Unknown tool requested: {name}")
            raise ValueError(f"Unknown tool: {name}")

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        """Lists available tools."""
        logger.debug("Received list_tools request")
        return [
            types.Tool(
                name="hello_world",
                description="Says hello world",
                inputSchema={  # Minimal schema, accepts no input
                    "type": "object",
                    "properties": {},
                },
            )
        ]

    # --- Prompt Implementation ---

    @app.list_prompts()
    async def list_prompts() -> list[types.Prompt]:
        """Lists available prompts."""
        logger.debug("Received list_prompts request")
        return [
            types.Prompt(
                name="hello_world_prompt",
                description="Asks the assistant to say hello world",
                arguments=[],  # No arguments needed for this simple prompt
            )
        ]

    @app.get_prompt()
    async def get_prompt(name: str, arguments: dict) -> types.GetPromptResult:
        """Gets a specific prompt."""
        logger.debug(f"Received get_prompt request for '{name}' with args: {arguments}")
        if name == "hello_world_prompt":
            # No arguments to process for this simple prompt
            prompt_text = "Can you say hello world?"
            return types.GetPromptResult(
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(type="text", text=prompt_text),
                    )
                ]
            )
        else:
            logger.error(f"Unknown prompt requested: {name}")
            raise ValueError(f"Unknown prompt: {name}")

    return app


# --- Optional: Code to run the server standalone via stdio ---


def main() -> int:
    """Entry point to run the minimal MCP server."""
    logger.info("Starting Minimal Low-Level MCP Server...")

    app = create_minimal_server()

    async def arun():
        # Use stdio_server for simple command-line interaction
        async with stdio_server() as streams:
            # Get initialization options (can be customized if needed)
            init_options = app.create_initialization_options()
            # Run the server loop
            await app.run(streams[0], streams[1], init_options)

    try:
        anyio.run(arun)
        return 0
    except Exception as e:
        logger.exception(f"Server encountered an error: {e}")
        return 1
    finally:
        logger.info("Minimal Low-Level MCP Server stopped.")


if __name__ == "__main__":
    sys.exit(main())
