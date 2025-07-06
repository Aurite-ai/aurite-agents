# MCP Server Configuration

MCP (Model-Context-Protocol) Servers are the backbone of an agent's capabilities. They are responsible for providing the tools, prompts, and resources that an agent can use to perform tasks. Each `mcp_server` configuration tells the framework how to connect to and interact with a specific server.

An MCP server configuration is a JSON or YAML object with a `type` field set to `"mcp_server"`.

## Core Fields

### `name`
**Type:** `string` (Required)
**Description:** A unique identifier for the MCP server. This name is used in an agent's `mcp_servers` list to grant it access to this server.

```json
{
  "name": "file-system-server"
}
```

### `capabilities`
**Type:** `list[string]` (Required)
**Description:** A list of the types of components this server provides. Accepted values are `"tools"`, `"prompts"`, and `"resources"`.

```json
{
  "capabilities": ["tools", "resources"]
}
```

### `description`
**Type:** `string` (Optional)
**Description:** A brief, human-readable description of the server's purpose.

```json
{
  "description": "A server that provides tools for reading and writing to the local file system."
}
```

### Stdio Transport

This is the most common transport for running local Python scripts as servers.

**`server_path`**
**Type:** `string` (Required for stdio)
**Description:** The path to the Python script that runs the MCP server. This path can be relative to the `.aurite` file of its context.

```json
{
  "name": "weather-server",
  "server_path": "mcp_servers/weather_server.py",
  "capabilities": ["tools"]
}
```

### HTTP Stream Transport

This transport is used for connecting to servers that are already running and accessible via an HTTP endpoint.

**`http_endpoint`**
**Type:** `string` (Required for http_stream)
**Description:** The full URL of the server's streaming endpoint.

**`headers`**
**Type:** `object` (Optional)
**Description:** A dictionary of HTTP headers to include in the request (e.g., for authentication).

```json
{
  "name": "notion-api-server",
  "http_endpoint": "https://api.notion.com/v1/mcp",
  "headers": {
    "Authorization": "Bearer {NOTION_API_KEY}"
  },
  "capabilities": ["tools"]
}
```

### Local Command Transport

This transport is for running any executable command as a server.

**`command`**
**Type:** `string` (Required for local)
**Description:** The command or executable to run.

**`args`**
**Type:** `list[string]` (Optional)
**Description:** A list of arguments to pass to the command.

```json
{
  "name": "my-custom-binary-server",
  "command": "bin/my_server",
  "args": ["--port", "8080"],
  "capabilities": ["tools"]
}
```

## Advanced Fields

### `timeout`
**Type:** `float` (Optional)
**Default:** `10.0`
**Description:** The default timeout in seconds for operations (like tool calls) sent to this server.

### `exclude`
**Type:** `list[string]` (Optional)
**Description:** A list of component names (tools, prompts, or resources) to exclude from this server's offerings. This is useful if a server script provides many tools, but you only want to expose a subset of them in this particular configuration.

### `roots`
**Type:** `list[object]` (Optional)
**Description:** A list of root objects that describe the server's capabilities in more detail. This is typically auto-discovered from the server and rarely needs to be set manually. Each root object contains a `uri`, `name`, and `capabilities`.
