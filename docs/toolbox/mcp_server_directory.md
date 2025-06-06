# Packaged MCP Servers

The `aurite` package comes with a selection of pre-configured MCP servers that you can use in your projects. These servers are organized by category and can be easily integrated into your `aurite_config.json`.

## How to Use

When you initialize a new project with `aurite init`, example server configuration files (e.g., `web_search.json`) are copied into the `config/mcp_servers/` directory.

The framework automatically loads all servers defined in these files. You can then enable a specific server for your project by referencing its `name` in the `mcp_servers` array of your main `aurite_config.json` file.

**Example `aurite_config.json`:**

```json
{
  "mcp_servers": [
    "example_weather_server",
    "brave_search_server"
  ],
  "...": "..."
}
```

In this example, `example_weather_server` might be defined in `example_mcp_servers.json` and `brave_search_server` in `web_search.json`. You can also define servers inline directly in this array.

## Server Categories

Below is a list of the available MCP server categories. Each document provides details on the specific servers included, what they do, and how to use them.

*   **[Example Servers](servers/example_mcp_servers.md):** A collection of general-purpose servers to get you started.
*   More categories will be added here as new server configurations are created.
