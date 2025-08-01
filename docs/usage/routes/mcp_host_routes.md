# MCP Host Routes Documentation

## Overview

The MCP Host routes (`/tools/*`) provide runtime management for Model Context Protocol (MCP) servers within the Aurite Framework. These endpoints focus on:

- **Runtime Server Management**: Monitor and control actively registered servers
- **Tool Discovery & Execution**: List and execute tools from registered servers
- **Host Status**: Monitor the MCPHost instance state

**Important:** These routes manage the runtime state of servers. For server configuration management (create, update, delete configs), use the Configuration Manager endpoints at `/config/components/mcp_servers/*`.

### Key Concepts

- **Registered Server**: An MCP server that has an active connection to the MCPHost
- **Runtime State**: The current operational status of servers and their tools
- **Tool**: A callable function exposed by a registered MCP server
- **Session**: An active connection between MCPHost and an MCP server

## Architecture & Design

### Separation of Concerns

```
Configuration Management          Runtime Management
(/config/components/mcp_servers) (/tools/*)
        |                              |
        v                              v
   ConfigManager                   MCPHost
   (stores configs)            (manages sessions)
                                       |
                                       v
                                 MCP Servers
                               (provide tools)
```

### Server Lifecycle

1. **Configuration**: Server configs are created/managed via `/config/components/mcp_servers/*`
2. **Registration**: Servers are registered with MCPHost via `/tools/register/*`
3. **Runtime**: Active servers can be monitored and used via `/tools/*`
4. **Unregistration**: Servers are disconnected via `DELETE /tools/servers/{name}`

## API Endpoints

### Tool Discovery & Execution

#### List All Available Tools

```http
GET /tools
```

Lists all tools available from currently registered servers.

**Response:**

```json
[
  {
    "name": "get_weather",
    "description": "Get current weather for a location",
    "inputSchema": {
      "type": "object",
      "properties": {
        "location": {
          "type": "string",
          "description": "City name or coordinates"
        }
      },
      "required": ["location"]
    }
  }
]
```

#### Get Tool Details

```http
GET /tools/{tool_name}
```

Gets detailed information about a specific tool, including which server provides it.

**Response:**

```json
{
  "name": "get_weather",
  "description": "Get current weather for a location",
  "server_name": "weather_server",
  "inputSchema": {
    "type": "object",
    "properties": {
      "location": {
        "type": "string",
        "description": "City name or coordinates"
      },
      "units": {
        "type": "string",
        "enum": ["celsius", "fahrenheit"],
        "default": "celsius"
      }
    },
    "required": ["location"]
  }
}
```

#### Execute Tool

```http
POST /tools/{tool_name}/call
```

Executes a specific tool with provided arguments.

**Request Body:**

```json
{
  "args": {
    "location": "San Francisco",
    "units": "fahrenheit"
  }
}
```

**Response:**

```json
{
  "content": [
    {
      "type": "text",
      "text": "Current weather in San Francisco: 68°F, partly cloudy"
    }
  ],
  "isError": false
}
```

### Runtime Server Management

#### List Registered Servers

```http
GET /tools/servers
```

Lists all servers currently registered with the MCPHost (runtime state only).

**Response:**

```json
[
  {
    "name": "weather_server",
    "status": "active",
    "transport_type": "stdio",
    "tools_count": 2,
    "registration_time": "2025-01-09T16:30:00Z"
  },
  {
    "name": "planning_server",
    "status": "active",
    "transport_type": "local",
    "tools_count": 3,
    "registration_time": "2025-01-09T16:31:00Z"
  }
]
```

#### Get Server Runtime Status

```http
GET /tools/servers/{server_name}
```

Gets detailed runtime status of a specific registered server.

**Response:**

```json
{
  "name": "weather_server",
  "registered": true,
  "status": "active",
  "transport_type": "stdio",
  "tools": ["weather_lookup", "current_time"],
  "registration_time": "2025-01-09T16:30:00Z",
  "session_active": true
}
```

**404 Response (not registered):**

```json
{
  "detail": "Server 'weather_server' is not currently registered"
}
```

#### List Server Tools

```http
GET /tools/servers/{server_name}/tools
```

Lists all tools provided by a specific registered server.

**Response:**

```json
[
  {
    "name": "weather_lookup",
    "description": "Look up weather information for a location",
    "inputSchema": {...}
  },
  {
    "name": "current_time",
    "description": "Get the current time in a specific timezone",
    "inputSchema": {...}
  }
]
```

#### Test Server Connection

```http
POST /tools/servers/{server_name}/test
```

Tests a server configuration without permanently registering it. Useful for validating configurations.

**Response (Success):**

```json
{
  "status": "success",
  "server_name": "weather_server",
  "connection_time": 0.234,
  "tools_discovered": ["weather_lookup", "current_time"],
  "test_tool_result": {
    "tool": "current_time",
    "success": true,
    "result": "2025-01-09T16:30:00Z"
  }
}
```

**Response (Failure):**

```json
{
  "status": "failed",
  "server_name": "weather_server",
  "error": "Connection timeout after 10.0 seconds"
}
```

### Server Registration

#### Register Server by Config

```http
POST /tools/register/config
```

Registers a server using a provided configuration object.

**Request Body:**

```json
{
  "name": "custom_server",
  "transport_type": "stdio",
  "server_path": "path/to/server.py",
  "timeout": 30.0,
  "capabilities": ["tools", "prompts", "resources"]
}
```

**Response:**

```json
{
  "status": "success",
  "name": "custom_server"
}
```

#### Register Server by Name

```http
POST /tools/register/{server_name}
```

Registers a server using its configured name from ConfigManager.

**Response:**

```json
{
  "status": "success",
  "name": "weather_server"
}
```

#### Unregister Server

```http
DELETE /tools/servers/{server_name}
```

Unregisters a server from the MCPHost, closing the connection.

**Response:**

```json
{
  "status": "success",
  "name": "weather_server"
}
```

### Host Status

#### Get MCPHost Status

```http
GET /tools/status
```

Gets the overall status of the MCPHost.

**Response:**

```json
{
  "status": "active",
  "tool_count": 5
}
```

## Error Handling

### Common Error Responses

#### 404 Not Found

- Server not registered: `"Server 'name' is not currently registered"`
- Tool not found: `"Tool 'name' not found"`
- Config not found: `"Server 'name' not found in configuration"`

#### 409 Conflict

- Already registered: `"Server 'name' is already registered"`

#### 500 Internal Server Error

- Connection failures: `"Failed to connect to server: [details]"`
- Registration timeout: `"Registration timeout after X seconds"`

## Implementation Notes

### Runtime vs Configuration

**Runtime Operations** (these endpoints):

- List registered servers
- Get server status
- Monitor active connections
- Execute tools
- Test connections

**Configuration Operations** (use `/config/components/mcp_servers/*`):

- Create server configs
- Update server settings
- Delete server configs
- List all configured servers

### Transport Types

The MCPHost supports three transport types for connecting to servers:

#### stdio

- Launches server as subprocess
- Communication via stdin/stdout
- Requires `server_path` parameter

```json
{
  "transport_type": "stdio",
  "server_path": "path/to/server.py"
}
```

#### local

- Launches server with custom command
- Flexible argument passing
- Requires `command` and optional `args`

```json
{
  "transport_type": "local",
  "command": "python",
  "args": ["-m", "my_server", "--mode", "production"]
}
```

#### http_stream

- Connects to HTTP SSE endpoint
- Supports authentication headers
- Requires `http_endpoint`

```json
{
  "transport_type": "http_stream",
  "http_endpoint": "https://api.example.com/mcp",
  "headers": { "Authorization": "Bearer token" }
}
```

### Environment Variable Resolution

Server configurations support environment variable placeholders:

```json
{
  "env": {
    "API_KEY": "{WEATHER_API_KEY}",
    "BASE_URL": "{WEATHER_BASE_URL}"
  }
}
```

These are resolved from the system environment at registration time.

## Testing & Debugging

### Example Test Script

```python
import httpx
import asyncio

API_KEY = "your-api-key"
BASE_URL = "http://localhost:8000"

async def test_mcp_host_routes():
    async with httpx.AsyncClient() as client:
        headers = {"X-API-Key": API_KEY}

        # 1. Check current status
        response = await client.get(f"{BASE_URL}/tools/status", headers=headers)
        print(f"Host status: {response.json()}")

        # 2. List registered servers
        response = await client.get(f"{BASE_URL}/tools/servers", headers=headers)
        print(f"Registered servers: {response.json()}")

        # 3. Register a server by name
        response = await client.post(
            f"{BASE_URL}/tools/register/weather_server",
            headers=headers
        )
        print(f"Registration result: {response.json()}")

        # 4. List available tools
        response = await client.get(f"{BASE_URL}/tools", headers=headers)
        tools = response.json()
        print(f"Available tools: {len(tools)}")

        # 5. Execute a tool
        if tools:
            tool_name = tools[0]["name"]
            response = await client.post(
                f"{BASE_URL}/tools/{tool_name}/call",
                headers=headers,
                json={"args": {"location": "New York"}}
            )
            print(f"Tool result: {response.json()}")

        # 6. Unregister server
        response = await client.delete(
            f"{BASE_URL}/tools/servers/weather_server",
            headers=headers
        )
        print(f"Unregistration result: {response.json()}")

asyncio.run(test_mcp_host_routes())
```

### Common Issues and Solutions

#### Server Registration Timeout

**Issue**: Server takes too long to initialize
**Solution**: Increase `registration_timeout` in server config

```json
{
  "registration_timeout": 30.0
}
```

#### Tool Not Found

**Issue**: Tool execution fails with "not found"
**Solution**: Ensure server is registered and check tool name spelling

#### Connection Refused

**Issue**: HTTP stream server connection fails
**Solution**: Verify endpoint URL and authentication headers

### Debugging Tips

1. **Enable Debug Logging**:

   ```python
   import logging
   logging.getLogger("aurite.host").setLevel(logging.DEBUG)
   ```

2. **Check Server Logs**: MCP servers output logs to stderr
3. **Verify Registration**: Use `GET /tools/servers` to check what's registered
4. **Test Connection First**: Use `/tools/servers/{name}/test` before registration

## Best Practices

### Server Management

1. **Check Registration**: Use `GET /tools/servers` to see what's currently registered
2. **Test First**: Use the test endpoint before permanent registration
3. **Clean Shutdown**: Always unregister servers when done
4. **Monitor Status**: Use status endpoints to track server health

### Tool Design

1. **Single Responsibility**: Each tool should do one thing well
2. **Clear Naming**: Use verb_noun format (e.g., `get_weather`, `create_plan`)
3. **Validate Inputs**: Use JSON Schema for robust input validation
4. **Return Structured Data**: Consistent response format across tools

### Performance Optimization

1. **Lazy Registration**: Register servers only when needed
2. **Connection Pooling**: Reuse server connections
3. **Timeout Configuration**: Set appropriate timeouts for different operations
4. **Resource Cleanup**: Properly unregister unused servers

### When to Use Each Registration Method

#### Configuration-based (`/tools/register/{server_name}`)

- Production deployments with predefined servers
- Servers that multiple agents will use
- Standard tool sets

#### Direct Registration (`/tools/register/config`)

- Dynamic server discovery
- Testing and development
- Temporary or one-off servers
- External API integrations

#### JIT Registration (Automatic)

- Agent-driven tool discovery
- Optimal resource usage
- Simplified agent configuration

## Integration Examples

### With ExecutionFacade

```python
# ExecutionFacade automatically handles tool registration
facade = ExecutionFacade(config_manager, aurite)
result = await facade.execute_agent("weather-assistant", {
    "message": "What's the weather in Paris?"
})
# Tools are registered JIT when agent needs them
```

### Direct Tool Execution

```python
# For testing or direct tool usage
async with httpx.AsyncClient() as client:
    # Register server
    await client.post(
        "http://localhost:8000/tools/register/weather_server",
        headers={"X-API-Key": api_key}
    )

    # Execute tool
    result = await client.post(
        "http://localhost:8000/tools/weather_lookup/call",
        headers={"X-API-Key": api_key},
        json={"args": {"location": "London"}}
    )
```

### Batch Operations

```python
# Register multiple servers
servers = ["weather_server", "planning_server", "file_server"]
for server in servers:
    await client.post(
        f"http://localhost:8000/tools/register/{server}",
        headers={"X-API-Key": api_key}
    )

# Get all tools
tools = await client.get(
    "http://localhost:8000/tools",
    headers={"X-API-Key": api_key}
)
```

## Related Documentation

- [Configuration Manager Routes](./config_manager_routes.md) - For server configuration management
- [API Reference](../api_reference.md) - Complete API overview
- [MCP Server Configuration](../../config/mcp_server.md) - Server configuration guide
- [ExecutionFacade Routes](./facade_routes.md) - Agent execution endpoints
