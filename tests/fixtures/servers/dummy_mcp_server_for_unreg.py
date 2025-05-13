
import mcp.server
import mcp.types as types

class DummyServer(mcp.server.Server):
    async def list_tools(self) -> types.ListToolsResult:
        return types.ListToolsResult(tools=[
            types.Tool(name="unreg_tool_test", description="A test tool for unregistration.", inputSchema={})
        ])
    async def call_tool(self, name: str, arguments: dict) -> types.CallToolResult:
        return types.CallToolResult(content=[types.TextContent(type="text", text="dummy result")])

if __name__ == "__main__":
    mcp.server.run_server(DummyServer())
