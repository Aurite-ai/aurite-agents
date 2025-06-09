# Example MCP Servers

This document provides a list of pre-configured MCP servers for example usage that are included with the `aurite` package. The servers listed below are defined in the `config/mcp_servers/example_mcp_servers.json` file.

## Available Servers

### `weather_server`

*   **Description**: Provides tools and prompts for fetching weather information. It is a simple example of a local `stdio` server that runs the `mcp_servers/weather_mcp_server.py` script.
*   **Configuration File**: `config/mcp_servers/example_mcp_servers.json`

**Tools:**
| Tool Name | Description |
| :-------- | :---------- |
| `get_weather` | Retrieves the current weather for a specified location. |
| `get_forecast` | Gets the weather forecast for a specified location for a number of days. |

**Example Usage:**
An agent with access to this server can answer questions like "What's the weather in London?".

### `planning_server`

*   **Description**: Provides a set of tools for creating, modifying, and saving plans. It runs the `mcp_servers/planning_server.py` script and is useful for agents that need to perform multi-step tasks.
*   **Configuration File**: `config/mcp_servers/example_mcp_servers.json`

**Tools:**
| Tool Name | Description |
| :-------- | :---------- |
| `create_plan` | Creates a new plan with a specified name and steps. |
| `add_step` | Adds a step to an existing plan. |
| `get_plan` | Retrieves the details of a specific plan. |

**Example Usage:**
An agent can use this server to create a step-by-step plan to accomplish a complex goal.
