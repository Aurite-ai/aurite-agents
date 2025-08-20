import time

from fastmcp import FastMCP

mcp = FastMCP("Error STDIO Server")


@mcp.tool()
def timeout(a: float, b: float) -> float:
    # for testing timeout - sleeps for 10 seconds to trigger timeout
    time.sleep(10)
    return a + b


if __name__ == "__main__":
    mcp.run(transport="stdio")
