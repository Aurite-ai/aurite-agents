# General Purpose MCP Servers

This document provides a list of pre-configured MCP servers for General Purpose tasks that are included with the `aurite` package. The servers listed below are defined in the `config/mcp_servers/general_purpose_servers.json` file.

## Available Servers

### `desktop_commander`

*   **Description**: A server that provides a wide range of tools for interacting with the local desktop environment, including file system operations, process management, and command execution.
*   **Configuration File**: `config/mcp_servers/general_purpose_servers.json`

**Tools:**
| Tool Name | Description |
| :-------- | :---------- |
| `get_config` | Get complete server configuration |
| `set_config_value` | Set specific configuration values |
| `read_file` | Read contents of a file or URL |
| `read_multiple_files` | Read multiple files simultaneously |
| `write_file` | Write or append to files |
| `create_directory` | Create new directories |
| `list_directory` | List contents of a directory |
| `move_file` | Move or rename files/directories |
| `edit_block` | Make precise text replacements in files |
| `search_files` | Find files by name (case-insensitive) |
| `search_code` | Search within file contents using ripgrep |
| `get_file_info` | Get detailed file/directory metadata |
| `execute_command` | Run terminal commands |
| `read_output` | Read output from running terminal sessions |
| `force_terminate` | Terminate a terminal session |
| `list_sessions` | List active terminal sessions |
| `list_processes` | List all running processes |
| `kill_process` | Terminate a process by PID |

**Example Usage:**
```
python tests/functional_mcp_client.py '{"name": "desktop_commander"}' "list tools"
```

**Relevant Agents:**
*   **`desktop_commander_agent`**: An agent that can interact with the local desktop environment using the desktop_commander server.
    *   **Configuration File**: `config/agents/general_purpose_agents.json`

### `memory_bank`

*   **Description**: A server for creating and managing a persistent "memory bank" for an agent, allowing it to store and retrieve information across sessions.
*   **Configuration File**: `config/mcp_servers/general_purpose_servers.json`

**Tools:**
| Tool Name | Description |
| :-------- | :---------- |
| `initialize_memory_bank` | Initialize a Memory Bank in a specified directory |
| `set_memory_bank_path` | Set a custom path for the Memory Bank |
| `debug_mcp_config` | Debug the current MCP configuration |
| `read_memory_bank_file` | Read a file from the Memory Bank |
| `write_memory_bank_file` | Write to a Memory Bank file |
| `list_memory_bank_files` | List Memory Bank files |
| `get_memory_bank_status` | Check Memory Bank status |
| `migrate_file_naming` | Migrate files from camelCase to kebab-case naming |
| `track_progress` | Track progress and update Memory Bank files |
| `update_active_context` | Update the active context file |
| `log_decision` | Log a decision in the decision log |
| `switch_mode` | Switch to a specific mode (architect, ask, code, debug, test) |
| `get_current_mode` | Get information about the current mode |
| `process_umb_command` | Process UMB commands |
| `complete_umb` | Complete the UMB process |

**Example Usage:**
```
python tests/functional_mcp_client.py '{"name": "memory_bank"}' "Use the 'initialize_memory_bank' tool to create a memory bank in a directory called 'test_memory_bank'"
```

**Relevant Agents:**
*   **`memory_bank_agent`**: An agent that can create and manage a persistent "memory bank" for an agent, allowing it to store and retrieve information across sessions.
    *   **Configuration File**: `config/agents/general_purpose_agents.json`

### `planning_server`

*   **Description**: A server that provides tools for creating, saving, and listing structured plans.
*   **Configuration File**: `config/mcp_servers/general_purpose_servers.json`

**Tools:**
| Tool Name | Description |
| :-------- | :---------- |
| `save_plan` | Save a plan to disk with optional tags. |
| `list_plans` | List all available plans, optionally filtered by tag. |

**Prompts:**
| Prompt Name | Description |
| :-------- | :---------- |
| `create_plan_prompt` | Generate a structured planning prompt. |

**Resources:**
| Resource URI | Description |
| :-------- | :---------- |
| `planning://plan/{plan_name}` | Get a saved plan as a formatted resource. |

**Example Usage:**
```
python tests/functional_mcp_client.py '{"name": "planning_server"}' "Use the 'create_plan_prompt' to create a plan for a new feature."
```

**Relevant Agents:**
*   **`planning_agent`**: An agent that can create, save, and list structured plans using the planning_server.
    *   **Configuration File**: `config/agents/general_purpose_agents.json`
