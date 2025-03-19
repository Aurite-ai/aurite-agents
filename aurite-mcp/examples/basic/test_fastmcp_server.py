from mcp.server.fastmcp import FastMCP


mcp = FastMCP("test-server")


@mcp.tool("hello_world")
def hello_world(arguments):
    return [{"type": "text", "text": "Hey there buddy!"}]


if __name__ == "__main__":
    mcp.run(transport="stdio")


@mcp.prompt()
def hello_world_prompt(arguments) -> str:
    return "Can you say hello world?"
