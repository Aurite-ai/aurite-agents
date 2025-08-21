# :material-api: API Reference

The Aurite Framework API is organized around four core managers, each with its own base path and specific responsibilities. This document provides a comprehensive reference for all available endpoints.

<!-- prettier-ignore -->
!!! info "Interactive API Docs"
    For detailed request/response schemas and to try out the API live, please use the interactive documentation interfaces available when the server is running:

    -   `/api-docs` - Swagger UI interface
    -   `/redoc` - ReDoc documentation interface
    -   `/openapi.json` - Raw OpenAPI schema

---

## Authentication & Base URL

All API endpoints require authentication via an API key.

- **Header:** `X-API-Key: your-api-key-here`
- **Base URL:** `http://localhost:8000`

---

## API Endpoints

The API is structured around four main routers.

=== ":material-cogs: Configuration (`/config`)"

    Handles all configuration file operations, component CRUD, and project/workspace management.

    **Component CRUD**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `GET` | `/config/components` | List all component types. |
    | `GET` | `/config/components/{type}` | List all components of a specific type. |
    | `POST` | `/config/components/{type}` | Create a new component. |
    | `GET` | `/config/components/{type}/{id}` | Get a specific component's details. |
    | `PUT` | `/config/components/{type}/{id}` | Update an existing component. |
    | `DELETE` | `/config/components/{type}/{id}` | Delete a component. |
    | `POST` | `/config/components/{type}/{id}/validate` | Validate a component's configuration. |

    **Project & Workspace Management**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `GET` | `/config/projects` | List all projects in the current workspace. |
    | `POST` | `/config/projects` | Create a new project. |
    | `GET` | `/config/projects/active` | Get the currently active project. |
    | `GET` | `/config/projects/{name}` | Get details for a specific project. |
    | `PUT` | `/config/projects/{name}` | Update a project. |
    | `DELETE` | `/config/projects/{name}` | Delete a project. |
    | `GET` | `/config/workspaces/active` | Get the active workspace details. |

    **Configuration File Operations**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `GET` | `/config/sources` | List all configuration source directories. |
    | `GET` | `/config/files/{source}` | List config files within a specific source. |
    | `POST` | `/config/files` | Create a new configuration file. |
    | `GET` | `/config/files/{source}/{path}` | Get a config file's content. |
    | `PUT` | `/config/files/{source}/{path}` | Update a config file's content. |
    | `DELETE` | `/config/files/{source}/{path}` | Delete a configuration file. |
    | `POST` | `/config/refresh` | Force a refresh of the configuration index. |
    | `POST` | `/config/validate` | Validate all loaded configurations. |

=== ":material-tools: MCP Host (`/tools`)"

    Manages runtime operations for MCP servers, tool discovery, and execution.

    **Tool Discovery & Execution**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `GET` | `/tools` | List all available tools from registered servers. |
    | `GET` | `/tools/{tool_name}` | Get detailed information for a specific tool. |
    | `POST` | `/tools/{tool_name}/call` | Execute a specific tool with arguments. |

    **Runtime Server Management**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `GET` | `/tools/servers` | List all currently registered MCP servers. |
    | `GET` | `/tools/servers/{server_name}` | Get detailed runtime status of a server. |
    | `POST` | `/tools/servers/{server_name}/restart` | Restart a registered server. |
    | `GET` | `/tools/servers/{server_name}/tools` | List all tools provided by a specific server. |
    | `POST` | `/tools/servers/{server_name}/test` | Test a server configuration. |
    | `DELETE` | `/tools/servers/{server_name}` | Unregister a server from the host. |

    **Server Registration**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `POST` | `/tools/register/config` | Register a server using a config object. |
    | `POST` | `/tools/register/{server_name}` | Register a server by its configured name. |

=== ":material-robot-happy: Execution (`/execution`)"

    Handles agent and workflow execution, history management, and testing.

    **Agent & Workflow Execution**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `POST` | `/execution/agents/{agent_name}/run` | Execute an agent and wait for the result. |
    | `POST` | `/execution/agents/{agent_name}/stream` | Execute an agent and stream the response. |
    | `POST` | `/execution/workflows/linear/{workflow_name}/run` | Execute a linear workflow. |
    | `POST` | `/execution/workflows/graph/{workflow_name}/run` | Execute a graph workflow. |
    | `POST` | `/execution/workflows/custom/{workflow_name}/run` | Execute a custom workflow. |

    **Testing & Validation**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `POST` | `/execution/agents/{agent_name}/test` | Test an agent's configuration. |
    | `POST` | `/execution/llms/{llm_config_id}/test` | Test an LLM configuration. |
    | `POST` | `/execution/workflows/linear/{workflow_name}/test` | Test a linear workflow. |
    | `POST` | `/execution/workflows/custom/{workflow_name}/test` | Test a custom workflow. |
    | `POST` | `/execution/evaluate` | Run evaluation on a component. |
    | `POST` | `/execution/evaluate/{evaluation_config_id}` | Run evaluation on a component, using an evaluation config. |

    **Execution History**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `GET` | `/execution/history` | List all sessions (paginated). Filter with `agent_name` or `workflow_name` query params. |
    | `GET` | `/execution/history/{session_id}` | Get the full history for a specific session. |
    | `DELETE` | `/execution/history/{session_id}` | Delete a session's history. |
    | `POST` | `/execution/history/cleanup` | Clean up old sessions based on retention policy. |

=== ":material-server: System (`/system`)"

    Provides system information, environment management, and monitoring.

    **System Information**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `GET` | `/system/info` | Get detailed system information. |
    | `GET` | `/system/health` | Perform a comprehensive health check. |
    | `GET` | `/system/version` | Get framework version information. |
    | `GET` | `/system/capabilities` | List system capabilities and features. |

    **Environment & Dependencies**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `GET` | `/system/environment` | Get environment variables (sensitive values masked). |
    | `PUT` | `/system/environment` | Update non-sensitive environment variables. |
    | `GET` | `/system/dependencies` | List all installed Python dependencies. |
    | `POST` | `/system/dependencies/check` | Check the health of critical dependencies. |

    **Monitoring**

    | Method | Endpoint | Description |
    | --- | --- | --- |
    | `GET` | `/system/monitoring/metrics` | Get current system metrics (CPU, memory, etc.). |
    | `GET` | `/system/monitoring/active` | List active Aurite-related processes. |

---
