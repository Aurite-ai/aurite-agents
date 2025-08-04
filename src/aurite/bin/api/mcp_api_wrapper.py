import json
import os

import httpx
from fastmcp import FastMCP

API_KEY = os.getenv("API_KEY", "test-api-key")  # Replace with your actual secret!

with open("openapi.json") as f:
    openapi_spec = json.load(f)

# Create an HTTP client with the X-API-KEY header
api_client = httpx.AsyncClient(
    base_url="http://localhost:8000",
    headers={"X-API-KEY": API_KEY},
)

# Instantiate the MCP server
mcp = FastMCP.from_openapi(
    openapi_spec=openapi_spec,
    client=api_client,
    name="Aurite MCP Server",
    timeout=15.0,
    # route_maps=[...],  # Optional: advanced customization
)

if __name__ == "__main__":
    mcp.run(transport="http", port=8123)
