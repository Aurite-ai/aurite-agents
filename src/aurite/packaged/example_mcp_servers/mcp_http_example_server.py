from fastapi import FastAPI
import uvicorn
from mcp.server.fastmcp import FastMCP
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-http-example-server")

# Create a FastMCP server instance
# stateless_http=True is often simpler for example servers.
# If state (like sessions across calls for the same client) were important,
# you might set it to False (which is the default).
mcp_app = FastMCP(name="HTTPExampleServer", stateless_http=True)


@mcp_app.tool(description="Convert text to uppercase.")
def uppercase_text(text: str) -> str:
    """
    A simple tool that converts input text to uppercase.
    """
    logger.info(f"Executing uppercase_text tool with input: {text}")
    result = text.upper()
    logger.info(f"Uppercase result: {result}")
    return result


@mcp_app.tool(description="Adds two numbers.")
def add_numbers(a: int, b: int) -> int:
    """
    A simple tool that adds two integers.
    """
    logger.info(f"Executing add_numbers tool with inputs: a={a}, b={b}")
    result = a + b
    logger.info(f"Addition result: {result}")
    return result


# Create a FastAPI application to mount the MCP server
import contextlib  # Add this import


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI lifespan: Starting session manager...")
    async with mcp_app.session_manager.run():  # Run the session manager for the mcp_app
        logger.info("FastAPI lifespan: Session manager running.")
        yield
    logger.info("FastAPI lifespan: Session manager stopped.")


app = FastAPI(lifespan=lifespan)  # Add lifespan to the FastAPI app

# Mount the FastMCP application.
# The streamable_http_app() method prepares the MCP app to be served via HTTP.
# It will be available at the path specified here, e.g., /mcp_stream_example
# Adding a trailing slash to the mount path.
app.mount("/mcp_stream_example/", mcp_app.streamable_http_app())

logger.info(f"MCP HTTP Example Server '{mcp_app.name}' is configured.")
# Attempting to access tools via a potentially internal attribute or a common name
# This line is for server-side logging only and might need adjustment based on FastMCP's actual API
try:
    # Common internal names for such registries
    tools_registry = getattr(mcp_app, "_tools", getattr(mcp_app, "tools_registry", {}))
    if not isinstance(tools_registry, dict):  # Fallback if it's not a dict
        tools_registry = {}
    logger.info(f"Tools available: {[tool.name for tool in tools_registry.values()]}")
except AttributeError:
    logger.warning(
        "Could not determine how to list tools directly from FastMCP instance for logging."
    )
logger.info(
    "Mounting MCP application at /mcp_stream_example/"
)  # Added trailing slash here too for logging consistency

if __name__ == "__main__":
    logger.info("Starting Uvicorn server for MCP HTTP Example Server...")
    # Run the FastAPI app with Uvicorn
    # Using a different port (e.g., 8083) to avoid conflict with sse_example_server (8082)
    uvicorn.run(app, host="0.0.0.0", port=8083, log_level="info")
