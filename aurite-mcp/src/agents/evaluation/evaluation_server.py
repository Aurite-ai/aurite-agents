from mcp.server.fastmcp import FastMCP


mcp = FastMCP("eval-server")


@mcp.tool("evaluate_agent")
def hello_world(arguments):
    return [{"type": "text", "text": "The evaultion of the agent output is complete."}]


@mcp.prompt()
def evaluation_prompt(
    state : str
) -> str:
    return f"Evaluate the agent using the evaluate_agent tool. From the agent state: {state}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
