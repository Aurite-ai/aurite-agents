"""
Error MCP server for HTTP testing using FastMCP HTTP transport
"""

import time
from fastmcp import FastMCP

mcp = FastMCP("error-http-server")


@mcp.tool()
def timeout(a: float, b: float) -> float:
    """A tool that sleeps for 10 seconds to trigger timeout."""
    # for testing timeout - sleeps for 10 seconds to trigger timeout
    time.sleep(10)
    return a + b


if __name__ == "__main__":
    # Use streamable-http transport on port 8088 as expected by tests
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8088)
