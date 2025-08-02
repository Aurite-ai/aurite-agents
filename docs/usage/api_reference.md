# Aurite Framework API Reference

## Overview

The Aurite Framework API is organized around four core managers, each with its own base path and specific responsibilities. This document provides a comprehensive reference for all available endpoints.

**Note:** For detailed request/response schemas, refer to the OpenAPI specification available at:

- `/openapi.json` - OpenAPI JSON schema
- `/api-docs` - Swagger UI interface
- `/redoc` - ReDoc documentation interface

## Authentication

All API endpoints require authentication via API key. Include the API key in the request headers:

```
X-API-Key: your-api-key-here
```

## Base URL

```
http://localhost:8000
```

## API Organization

The API is structured around four main paths, each corresponding to a core manager:

1. **`/config`** - Configuration Manager endpoints
2. **`/tools`** - MCP Host Manager endpoints
3. **`/execution`** - Execution Facade endpoints
4. **`/system`** - System management endpoints

---

## 1. Configuration Management APIs (`/config`)

Handles all configuration file operations, component CRUD operations, and project/workspace management.

### Component CRUD Operations (Wildcard Approach)

| Method | Endpoint                                                      | Description               |
| ------ | ------------------------------------------------------------- | ------------------------- |
| GET    | `/config/components`                                          | List all component types  |
| GET    | `/config/components/{component_type}`                         | List components by type   |
| POST   | `/config/components/{component_type}`                         | Create new component      |
| GET    | `/config/components/{component_type}/{component_id}`          | Get component details     |
| PUT    | `/config/components/{component_type}/{component_id}`          | Update component          |
| DELETE | `/config/components/{component_type}/{component_id}`          | Delete component          |
| POST   | `/config/components/{component_type}/{component_id}/validate` | Validate component config |

**Component Types:** `agent`, `llm`, `mcp_server`, `linear_workflow`, `custom_workflow`

### Project & Workspace Management

| Method | Endpoint                    | Description                    |
| ------ | --------------------------- | ------------------------------ |
| GET    | `/config/projects`          | List all projects in workspace |
| POST   | `/config/projects`          | Create new project             |
| GET    | `/config/projects/{name}`   | Get project details            |
| PUT    | `/config/projects/{name}`   | Update project                 |
| DELETE | `/config/projects/{name}`   | Delete project                 |
| GET    | `/config/projects/active`   | Get currently active project   |
| GET    | `/config/workspaces`        | List workspaces                |
| GET    | `/config/workspaces/active` | Get the active workspace       |

### Configuration File Operations

| Method | Endpoint                                  | Description                                       |
| ------ | ----------------------------------------- | ------------------------------------------------- |
| GET    | `/config/sources`                         | List all config sources (project, user, packaged) |
| POST   | `/config/files`                           | Create new config file                            |
| GET    | `/config/files/{source_name}`             | List config files by source                       |
| GET    | `/config/files/{source_name}/{file_path}` | Get config file content                           |
| PUT    | `/config/files/{source_name}/{file_path}` | Update config file                                |
| DELETE | `/config/files/{source_name}/{file_path}` | Delete config file                                |
| POST   | `/config/refresh`                         | Force refresh config cache                        |
| POST   | `/config/validate`                        | Validate all configurations                       |

---

## 2. Tool Management APIs (`/tools`)

Manages runtime operations for MCP servers, tool discovery, and execution. These endpoints work with servers that are actively registered with the MCPHost instance.

**Note:** For MCP server configuration management (create, update, delete configs), use `/config/components/mcp_servers/*` endpoints.

### Tool Discovery & Execution

| Method | Endpoint                  | Description                                      |
| ------ | ------------------------- | ------------------------------------------------ |
| GET    | `/tools`                  | List all available tools from registered servers |
| GET    | `/tools/{tool_name}`      | Get tool details                                 |
| POST   | `/tools/{tool_name}/call` | Execute specific tool                            |

### Runtime Server Management

| Method | Endpoint                               | Description                                 |
| ------ | -------------------------------------- | ------------------------------------------- |
| GET    | `/tools/servers`                       | List currently registered servers (runtime) |
| GET    | `/tools/servers/{server_name}`         | Get runtime status of registered server     |
| POST   | `/tools/servers/{server_name}/restart` | Restart a registered server                 |
| GET    | `/tools/servers/{server_name}/tools`   | List tools from specific server             |
| POST   | `/tools/servers/{server_name}/test`    | Test server connection                      |

### Server Registration

| Method | Endpoint                        | Description                         |
| ------ | ------------------------------- | ----------------------------------- |
| POST   | `/tools/register/config`        | Register server by config object    |
| POST   | `/tools/register/{server_name}` | Register server by name from config |
| DELETE | `/tools/servers/{server_name}`  | Unregister server from host         |

### Host Status

| Method | Endpoint        | Description        |
| ------ | --------------- | ------------------ |
| GET    | `/tools/status` | Get MCPHost status |

---

## 3. Execution Management APIs (`/execution`)

Handles agent and workflow execution, execution history, and monitoring.

### Agent Execution

| Method | Endpoint                                 | Description                 |
| ------ | ---------------------------------------- | --------------------------- |
| POST   | `/execution/agents/{agent_name}/run`     | Execute agent (sync)        |
| POST   | `/execution/agents/{agent_name}/stream`  | Execute agent (streaming)   |
| POST   | `/execution/agents/{agent_name}/test`    | Test agent configuration    |
| GET    | `/execution/agents/{agent_name}/history` | Get agent execution history |

### Workflow Execution

| Method | Endpoint                                               | Description                          |
| ------ | ------------------------------------------------------ | ------------------------------------ |
| POST   | `/execution/workflows/linear/{workflow_name}/run`      | Execute linear workflow              |
| POST   | `/execution/workflows/custom/{workflow_name}/run`      | Execute custom workflow              |
| POST   | `/execution/workflows/linear/{workflow_name}/test`     | Test linear workflow                 |
| POST   | `/execution/workflows/custom/{workflow_name}/test`     | Test custom workflow                 |
| POST   | `/execution/workflows/custom/{workflow_name}/validate` | Validate custom workflow Python code |
| GET    | `/execution/workflows/{workflow_name}/history`         | Get workflow execution history       |

### Execution History & Monitoring

| Method | Endpoint                                 | Description                                 |
| ------ | ---------------------------------------- | ------------------------------------------- |
| GET    | `/execution/history`                     | List all sessions (paginated)               |
| GET    | `/execution/history/{session_id}`        | Get session conversation history            |
| DELETE | `/execution/history/{session_id}`        | Delete session                              |
| POST   | `/execution/history/cleanup`             | Clean up old sessions (30 days/50 sessions) |
| GET    | `/execution/agents/{agent_name}/history` | Get agent-specific sessions                 |

### Facade Status

| Method | Endpoint            | Description                |
| ------ | ------------------- | -------------------------- |
| GET    | `/execution/status` | Get ExecutionFacade status |

---

## 4. System Management APIs (`/system`)

Provides system information, environment management, and monitoring capabilities.

### System Information

| Method | Endpoint               | Description                |
| ------ | ---------------------- | -------------------------- |
| GET    | `/system/info`         | Get system information     |
| GET    | `/system/health`       | Comprehensive health check |
| GET    | `/system/version`      | Get framework version info |
| GET    | `/system/capabilities` | List system capabilities   |

### Environment Management

| Method | Endpoint                     | Description                  |
| ------ | ---------------------------- | ---------------------------- |
| GET    | `/system/environment`        | Get environment variables    |
| PUT    | `/system/environment`        | Update environment variables |
| GET    | `/system/dependencies`       | List installed dependencies  |
| POST   | `/system/dependencies/check` | Check dependency health      |

### Real-time Monitoring

| Method | Endpoint                     | Description                  |
| ------ | ---------------------------- | ---------------------------- |
| GET    | `/system/monitoring/metrics` | Get system metrics           |
| GET    | `/system/monitoring/logs`    | Get recent logs (SSE stream) |
| GET    | `/system/monitoring/active`  | List active system processes |

---

## Error Responses

All endpoints follow a consistent error response format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes

- `200 OK` - Request succeeded
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Missing or invalid API key
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

---

## Rate Limiting

Currently, the API does not implement rate limiting. This may be added in future versions.

---

## Versioning

The API is currently at version 1.0.0. Future versions will maintain backward compatibility where possible, with deprecation notices for breaking changes.
