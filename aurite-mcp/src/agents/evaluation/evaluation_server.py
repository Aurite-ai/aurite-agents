from mcp.server.fastmcp import FastMCP


mcp = FastMCP("eval-server")


@mcp.tool("evaluate_agent")
def hello_world(arguments):
    return [{"type": "text", "text": "The evaultion of the agent output is complete."}]


@mcp.prompt()
def evaluation_prompt() -> str:
    return "Evaluate the agent using the evaluate_agent tool."


if __name__ == "__main__":
    mcp.run(transport="stdio")
