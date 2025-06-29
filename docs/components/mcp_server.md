# Client Configurations (ClientConfig)

Client Configurations define how the Aurite framework connects to and interacts with Model Context Protocol (MCP) servers. These servers provide external capabilities to your agents, such as tools, prompts, or other resources. Each `ClientConfig` specifies how to reach an MCP server, what capabilities it offers, and other connection parameters.

This document first provides quickstart examples for common use cases and then details all available fields in a `ClientConfig` object, as defined in `src/aurite/config/config_models.py`.

## Quickstart Examples

For many common scenarios, you only need to define a few key fields.

### 1. Basic stdio Client

This is for running a local MCP server script (e.g., a Python file). The `transport_type` defaults to `"stdio"`, so you only need to specify `name`, `server_path`, and `capabilities`.

```json
{
  "name": "my_local_script_server",
  "server_path": "mcp_servers/my_script.py",
  "capabilities": ["tools"]
}
```

-   **`name`**: A unique name for your server.
-   **`server_path`**: Path to your server script, relative to your project root (where `aurite_config.json` is).
-   **`capabilities`**: What your server offers (e.g., `"tools"`, `"prompts"`).

### 2. Basic http_stream Client

This is for connecting to an MCP server that's running and accessible via an HTTP/HTTPS URL.

```json
{
  "name": "my_remote_http_server",
  "http_endpoint": "https://my-mcp-server.example.com/mcp",
  "capabilities": ["resources"]
}
```

-   **`name`**: A unique name for your server.
-   **`http_endpoint`**: The full URL where the MCP server is listening.
-   **`capabilities`**: What your server offers.

The `timeout`, `routing_weight`, and other fields have defaults or are optional for more advanced configurations.

## Detailed Configuration Fields

A Client configuration is a JSON object with the following fields:

| Field            | Type                                  | Default   | Description                                                                                                                                                                                                                            |
| ---------------- | ------------------------------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`           | string                                | Required  | A unique identifier for this MCP server configuration. Agents will use this name to specify which servers they can access. For backward compatibility, `client_id` is also supported.                                                    |
| `transport_type` | string (`"stdio"` or `"http_stream"`) | `"stdio"` | Specifies the communication transport to use with the MCP server.<br>- `"stdio"`: For servers that communicate via standard input/output (e.g., a local Python script).<br>- `"http_stream"`: For servers that expose an HTTP endpoint for streaming MCP messages (e.g., a FastAPI-based MCP server).<br>- `"local"`: For local servers that are imported from outside sources, like smithery.ai.|
| `server_path`    | string (Path)                         | `null`    | The file path to the MCP server script. Required if `transport_type` is `"stdio"`. The path is resolved relative to the project root directory (where `aurite_config.json` resides).                                                     |
| `http_endpoint`  | string (URL)                          | `null`    | The full URL of the MCP server's HTTP streaming endpoint. Required if `transport_type` is `"http_stream"`. Must be a valid HTTP or HTTPS URL (e.g., `http://localhost:8080/mcp_stream`).                                              |
| `roots`          | array of `RootConfig` objects       | `null`    | A list of specific MCP roots (entry points) provided by this server. If `null` or empty, the framework will discover roots from the server. See `RootConfig` details below.                                                              |
| `capabilities`   | array of string                       | Required  | A list of capability types this client provides (e.g., `"tools"`, `"prompts"`, `"resources"`). This helps agents understand what the client offers.                                                                                      |
| `timeout`        | number                                | `10.0`    | The timeout in seconds for waiting for a response from the MCP server.                                                                                                                                                                 |
| `routing_weight` | number                                | `1.0`     | A weight used by the agent's `"auto"` mode when selecting which clients to use. Higher weights might indicate a preference for this client for relevant tasks.                                                                           |
| `exclude`        | array of string                       | `null`    | A list of specific component names (tools, prompts, or resources) provided by this server that should be hidden from agents, even if the agent has access to this client.                                                              |
| `gcp_secrets`    | array of `GCPSecretConfig` objects  | `null`    | A list of Google Cloud Platform secrets to resolve and inject as environment variables into the MCP server's environment when it's started by the framework (primarily for `"stdio"` transport). See `GCPSecretConfig` details below. |
| `command`    | string  | `null`    | The command to be executed when accessing the MCP server. Required if `transport_type` is `local`. |
| `args`    | array of string  | `null`    | The arguments to be used when accessing the MCP server. Required if `transport_type` is `local`.|

### RootConfig Object

Each object in the `roots` array has the following structure:

| Field          | Type            | Description                                                                          |
| -------------- | --------------- | ------------------------------------------------------------------------------------ |
| `uri`          | string          | The URI of the MCP root (e.g., `"mcp://weather.com/tools"`).                           |
| `name`         | string          | A human-readable name for the root.                                                  |
| `capabilities` | array of string | Specific capabilities provided by this root (e.g., `["get_weather_forecast"]`).      |

### GCPSecretConfig Object

Each object in the `gcp_secrets` array has the following structure:

| Field          | Type   | Description                                                                                                |
| -------------- | ------ | ---------------------------------------------------------------------------------------------------------- |
| `secret_id`    | string | The full GCP Secret Manager secret ID (e.g., `"projects/my-proj/secrets/my-secret/versions/latest"`).      |
| `env_var_name` | string | The name of the environment variable that the resolved secret value will be mapped to for the server process. |

## Transport Types

### 1. stdio

-   Used for MCP servers that are typically local scripts (e.g., Python scripts).
-   The Aurite framework starts these servers as subprocesses and communicates with them over their standard input and standard output streams.
-   Requires the `server_path` field to be set.

**Example:**

```json
{
  "name": "local_weather_tool",
  "transport_type": "stdio",
  "server_path": "mcp_servers/weather_mcp_server.py",
  "capabilities": ["tools"],
  "timeout": 15.0
}
```

### 2. http_stream

-   Used for MCP servers that are accessible via an HTTP endpoint. These servers are expected to handle MCP communication over an HTTP stream (e.g., using Server-Sent Events or a similar streaming mechanism).
-   The Aurite framework connects to this endpoint as an HTTP client.
-   Requires the `http_endpoint` field to be set.
-   An example of an MCP server using this transport can be found in `src/aurite/packaged/example_mcp_servers/mcp_http_example_server.py`, which uses FastAPI.

**Example:**

```json
{
  "name": "remote_knowledge_base",
  "transport_type": "http_stream",
  "http_endpoint": "http://mcp-kb-service.example.com/mcp_stream",
  "capabilities": ["resources", "prompts"],
  "timeout": 20.0
}
```

### 3. local

-   Used for MCP servers that are will be imported from an outside source like [smithery.ai](https://smithery.ai/)
-   'Remote' servers can be imported with 'http_stream'
-   Requires the `command` and `args` fields to be set. If using Smithery, these can be found under Install, JSON on the right side of the page for a server.
-   It is best practice to replace any keys with references to environment variables, like in the below example. Ensure the corresponding variables (`SMITHERY_API_KEY` in this case) are defined in the `.env`.

**Example:**
```json
{
  "name": "memory_server",
  "transport_type": "local",
  "command": "npx",
  "args": [
      "-y",
      "@smithery/cli@latest",
      "run",
      "@jlia0/servers",
      "--key",
      "{SMITHERY_API_KEY}"
  ],
  "capabilities": ["tools", "prompts"],
  "timeout": 15.0
}
```

## Example MCP Server Config File

MCP Server configurations are usually stored in a JSON file (e.g., `config/mcp_servers/mcp_servers.json` or a custom file referenced in your project configuration). This file typically contains a list of MCP Server configuration objects.

```json
[
  {
    "name": "stdio_example_server",
    "transport_type": "stdio",
    "server_path": "mcp_servers/my_stdio_server.py",
    "capabilities": ["tools", "prompts"],
    "timeout": 10.0,
    "routing_weight": 1.0,
    "exclude": ["internal_debug_tool"],
    "gcp_secrets": [
      {
        "secret_id": "projects/my-gcp-project/secrets/my-server-api-key/versions/latest",
        "env_var_name": "MY_SERVER_API_KEY"
      }
    ]
  },
  {
    "name": "http_example_server",
    "transport_type": "http_stream",
    "http_endpoint": "http://localhost:8083/mcp_stream_example/",
    "capabilities": ["tools"],
    "timeout": 15.0,
    "routing_weight": 1.5
  }
]
```

## How Agents Use MCP Server Configs

An `AgentConfig` specifies which MCP servers it can use via its `mcp_servers` field. This list contains `name` strings that match the `name` in the MCP server configurations.

```json
// Example snippet from an AgentConfig
{
  "name": "MyWeatherAgent",
  "mcp_servers": ["weather_server", "planning_server"], // References MCP Server configs by name
  // ... other agent settings
}
```

If an agent's `auto` mode is enabled, the framework (or an LLM) might dynamically select a subset of these allowed clients based on the task and client `routing_weight`.
