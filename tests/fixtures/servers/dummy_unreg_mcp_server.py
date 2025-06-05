import mcp.server
import mcp.types as types
import anyio
import sys
from mcp.server.stdio import stdio_server as mcp_stdio_server

TOOL_NAME = "unreg_tool_test"


# Define handlers as separate functions
async def _dummy_list_tools_handler() -> list[types.Tool]:  # Return list[types.Tool]
    tool_instance = types.Tool(
        name=TOOL_NAME, description="A test tool for unregistration.", inputSchema={}
    )
    return [tool_instance]


async def _dummy_call_tool_handler(name: str, arguments: dict) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="dummy result from " + name)]
    )


class DummyServer(mcp.server.Server):
    def __init__(self, server_name: str = "dummy_unreg_server"):
        super().__init__(server_name)
        # Register handlers in __init__
        self.list_tools()(_dummy_list_tools_handler)
        self.call_tool()(_dummy_call_tool_handler)


def main():
    app = DummyServer()  # Instantiate the server

    async def arun():
        async with mcp_stdio_server() as streams:
            # Pass the app instance itself to run
            await app.run(streams[0], streams[1], app.create_initialization_options())

    anyio.run(arun)
    return 0


if __name__ == "__main__":
    sys.exit(main())
