import time

from fastmcp import FastMCP

mcp = FastMCP("Error Server")


@mcp.tool
def timeout(a: float, b: float) -> float:
    # for testing timeout
    time.sleep(10)
    return a + b


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8088, path="/mcp")
