"""
Math MCP server for HTTP testing using FastMCP HTTP transport
"""

import time
from fastmcp import FastMCP

mcp = FastMCP("math-http-server")


@mcp.tool()
def add_numbers(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b


@mcp.tool()
def subtract_numbers(a: float, b: float) -> float:
    """Subtract two numbers (always raises an error for testing)."""
    raise ValueError("This tool always fails for testing purposes")


if __name__ == "__main__":
    # Use streamable-http transport on port 8088 as expected by tests
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8088)
