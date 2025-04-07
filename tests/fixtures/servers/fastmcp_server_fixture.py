import sys
import logging
from mcp.server.fastmcp import FastMCP

# Set up basic logging (FastMCP might configure its own, but this is good practice)
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# --- FastMCP Server Definition ---

# Initialize the FastMCP server instance
mcp = FastMCP("test-fastmcp-server")


# Define the 'hello_world' tool using the decorator
@mcp.tool("hello_world")
def hello_world(arguments):
    """A simple tool that returns a greeting."""
    logger.debug(f"Executing hello_world tool with args: {arguments}")
    # Note: FastMCP expects a list of content blocks, matching mcp.types
    return [{"type": "text", "text": "Hey there buddy!"}]


# Define the 'hello_world_prompt' using the decorator
@mcp.prompt("hello_world_prompt")  # Providing the name explicitly is good practice
def hello_world_prompt_impl(arguments) -> str:
    """Provides the text for the hello_world_prompt."""
    logger.debug(f"Generating hello_world_prompt with args: {arguments}")
    # FastMCP prompt functions typically return the prompt string directly
    return "Can you say hello world?"


# --- Main Execution Block ---


def main() -> int:
    """Entry point to run the FastMCP server."""
    logger.info(f"Starting FastMCP Server: {mcp.server_name}...")
    try:
        # FastMCP's run method handles the server loop and transport setup.
        # 'stdio' means it will communicate over standard input/output.
        mcp.run(transport="stdio")
        logger.info(f"FastMCP Server: {mcp.server_name} stopped cleanly.")
        return 0
    except Exception as e:
        logger.exception(f"FastMCP Server {mcp.server_name} encountered an error: {e}")
        return 1  # Indicate failure with a non-zero exit code


# Standard Python entry point check
if __name__ == "__main__":
    # Call main and exit with the return code
    sys.exit(main())
