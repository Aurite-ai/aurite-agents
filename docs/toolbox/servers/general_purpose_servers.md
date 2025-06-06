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
