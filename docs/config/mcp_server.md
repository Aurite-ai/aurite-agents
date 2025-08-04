# :material-server-network: MCP Server Configuration

MCP (Model-Context-Protocol) Servers are the backbone of an agent's capabilities. They are responsible for providing the tools, prompts, and resources that an agent can use to perform tasks. Each `mcp_server` configuration tells the framework how to connect to and interact with a specific server.

An MCP server configuration is a JSON or YAML object with a `type` field set to `"mcp_server"`.

!!! tip "Configuration Location"

    MCP Server configurations can be placed in any directory specified in your project's `.aurite` file (e.g., `config/mcp_servers/`). The framework will automatically discover them.

---

## Schema

<!-- prettier-ignore -->
!!! info "Transport Types"
    The `ClientConfig` model defines the structure for an MCP server configuration. There are three main transport types: `stdio`, `http_stream`, and `local`. Each transport type has its own required fields. The framework will infer the transport type based on the fields you provide.

=== ":material-format-list-bulleted-type: Core Fields"

    These fields define the fundamental properties of the server.

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `name` | `string` | Yes | A unique identifier for the MCP server. This name is used in an agent's `mcp_servers` list and as a prefix for its components (e.g., `my_server-tool_name`). |
    | `description` | `string` | No | A brief, human-readable description of the server's purpose. |
    | `capabilities` | `list[string]` | Yes | A list of the types of components this server provides. Accepted values are `"tools"`, `"prompts"`, and `"resources"`. |

=== ":material-transit-connection-variant: Transport Types"

    You must configure one of the following transport types. The framework will automatically infer the `transport_type` based on the fields you provide.

    ---
    **`stdio`**

    This is the most common transport for running local Python scripts as servers.

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `server_path` | `string` or `Path` | Yes | The path to the Python script that runs the MCP server. This path can be relative to the `.aurite` file of its context. |

    ---
    **`http_stream`**

    This transport is used for connecting to servers that are already running and accessible via an HTTP endpoint.

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `http_endpoint` | `string` | Yes | The full URL of the server's streaming endpoint. |
    | `headers` | `dict[str, str]` | No | A dictionary of HTTP headers to include in the request (e.g., for authentication). |

    ---
    **`local`**

    This transport is for running any executable command as a server.

    | Field | Type | Required | Description |
    | --- | --- | --- | --- |
    | `command` | `string` | Yes | The command or executable to run. |
    | `args` | `list[string]` | No | A list of arguments to pass to the command. |

=== ":material-cogs: Advanced Fields"

    These fields provide fine-grained control over the server's behavior.

    | Field | Type | Default | Description |
    | --- | --- | --- | --- |
    | `timeout` | `float` | `10.0` | The default timeout in seconds for operations (like tool calls) sent to this server. |
    | `registration_timeout` | `float` | `30.0` | The timeout in seconds for registering this server. |
    | `exclude` | `list[string]` | `None` | A list of component names (tools, prompts, or resources) to exclude from this server's offerings. |
    | `roots` | `list[object]` | `[]` | A list of root objects describing the server's capabilities. This is typically auto-discovered and rarely needs to be set manually. |

---

## :material-code-json: Configuration Examples

Here are some practical examples for each transport type.

=== "Stdio Transport"

    This example runs a local Python script as an MCP server.

    ```json
    {
      "type": "mcp_server",
      "name": "weather-server",
      "description": "Provides weather forecast tools.",
      "server_path": "mcp_servers/weather_server.py",
      "capabilities": ["tools"]
    }
    ```

=== "HTTP Stream Transport"

    This example connects to a custom running service. Note the use of an environment variable in the header for authentication.

    ```json
    {
      "type": "mcp_server",
      "name": "my-remote-service",
      "description": "Connects to a custom remote service.",
      "http_endpoint": "https://my-custom-service.com/mcp",
      "headers": {
        "X-API-Key": "{MY_SERVICE_API_KEY}"
      },
      "capabilities": ["tools", "resources"]
    }
    ```

=== "Local Command Transport"

    This example runs a pre-compiled binary as a server.

    ```json
    {
      "type": "mcp_server",
      "name": "my-custom-binary-server",
      "description": "A server running from a custom binary.",
      "command": "bin/my_server",
      "args": ["--port", "8080"],
      "capabilities": ["tools"]
    }
    ```
