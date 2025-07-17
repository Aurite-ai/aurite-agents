# Simple HTTP server example using FastMCP v2 (https://github.com/jlowin/fastmcp)
# Note that you will need to run this file directly to start the server before it can be used by agents

from fastmcp import FastMCP

mcp = FastMCP("Math HTTP")

@mcp.tool
def add_numbers(a: float, b: float) -> float:
    """Adds two numbers together. Returns a + b"""
    return a + b

@mcp.tool
def subtract_numbers(a: float, b: float) -> float:
    """Subtracts two numbers. Returns a - b"""
    raise a - b

if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8088, path="/mcp")
