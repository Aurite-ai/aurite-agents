import asyncio
from fastapi import FastAPI, Request
from sse_starlette.sse import EventSourceResponse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-server")

app = FastAPI()
clients = []

# Define a simple tool
TOOLS = [
    {
        "name": "uppercase_text",
        "description": "Convert text to uppercase",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    }
]


@app.get("/sse")
async def sse_endpoint():
    async def event_generator():
        session_id = "example-session-123"
        yield {"event": "endpoint", "data": f"/sse/messages?session_id={session_id}"}
        while True:
            await asyncio.sleep(5)
            yield {"event": "ping", "data": "Server is alive!"}

    return EventSourceResponse(event_generator())


@app.post("/sse/messages")
async def post_handler(request: Request):
    try:
        body = await request.json()
        logger.info(f"Received message: {body}")
        method = body.get("method")
        params = body.get("params", {})

        # Handle "initialize"
        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": body.get("id", 0),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listTools": True, "callTool": True},
                        "resources": {},
                    },
                    "serverInfo": {"name": "MyMCPserver", "version": "1.0.0"},
                },
            }
            return response

        # Handle "listTools"
        elif method == "listTools":
            return {
                "jsonrpc": "2.0",
                "id": body.get("id", 0),
                "result": {"tools": TOOLS},
            }

        # Handle "callTool"
        elif method == "callTool":
            tool_name = params.get("name")
            if tool_name == "uppercase_text":
                text = params.get("arguments", {}).get("text", "")
                result = text.upper()
                return {
                    "jsonrpc": "2.0",
                    "id": body.get("id", 0),
                    "result": {"output": result},
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": body.get("id", 0),
                    "error": {"code": -32602, "message": "Invalid tool name"},
                }

        # Unknown method
        else:
            return {
                "jsonrpc": "2.0",
                "id": body.get("id", 0),
                "error": {"code": -32601, "message": f"Method '{method}' not found"},
            }
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return {"error": "Invalid request"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8082)
