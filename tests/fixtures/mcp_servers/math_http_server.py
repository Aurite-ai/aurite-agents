from fastmcp import FastMCP

mcp = FastMCP("Math HTTP")

@mcp.tool
def add_numbers(a: float, b: float) -> float:
    return a + b

@mcp.tool
def subtract_numbers(a: float, b: float) -> float:
    raise ValueError

if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8088, path="/mcp")
