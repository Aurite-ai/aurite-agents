from mcp.server.fastmcp import FastMCP
from mcp import types, Tool

app = FastMCP("example-server")


@app.tool()
def list_tools() -> list[Tool]:
    return [
        Tool(
            name="calculate_sum",
            description="Add two numbers together",
            inputSchema={
                "type": "object",
                "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                "required": ["a", "b"],
            },
        )
    ]


@app.tool()
def call_tool(
    name: str, arguments: dict
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "calculate_sum":
        a = arguments["a"]
        b = arguments["b"]
        result = a + b
        return [types.TextContent(type="text", text=str(result))]
    raise ValueError(f"Tool not found: {name}")


@app.resource("example:/resource")
def example_resource() -> str:
    """
    An example resource.
    """
    return "This is an example resource."
