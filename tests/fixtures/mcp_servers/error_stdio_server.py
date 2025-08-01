import time

from fastmcp import FastMCP

mcp = FastMCP("Error Server")


@mcp.tool
def timeout(a: float, b: float) -> float:
    # for testing timeout
    time.sleep(10)
    return a + b


if __name__ == "__main__":
    mcp.run()
