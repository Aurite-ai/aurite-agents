# Configuration Manager API Routes

This document provides detailed information about the Configuration Manager API endpoints, including decision trees, error handling, and examples.

## Overview

The Configuration Manager API provides comprehensive CRUD operations for managing framework components (agents, LLMs, MCP servers, workflows) and their configuration files.

## Base Path
All configuration endpoints are prefixed with `/config/`.

## Component Operations

### Component Creation Decision Tree

```
POST /config/components/{component_type}
│
├─ Input Parameters:
│  ├─ name (required): Component name
│  ├─ config (required): Component configuration
│  ├─ project (optional): Project name
│  ├─ workspace (optional): Boolean flag
│  └─ file_path (optional): File name or relative path
│
└─ STEP 1: Determine Configuration Context
   │
   ├─ [workspace=true provided?]
   │  └─ YES → Use workspace root as context
   │
   ├─ [project name provided?]
   │  └─ YES → Use specified project root as context
   │
   └─ [Neither provided?]
      ├─ [Single project exists?]
      │  └─ YES → Use project root as context
      └─ [Multiple projects exist?]
         └─ NO → ERROR: "Multiple projects found. Specify 'project' or 'workspace'"

STEP 2: Determine Target File
│
├─ [file_path provided?]
│  │
│  ├─ [Is it just a filename? (no '/' in path)]
│  │  │
│  │  ├─ Search index for files with this name in context
│  │  │
│  │  ├─ [Exactly 1 match found?]
│  │  │  └─ YES → Use this existing file
│  │  │
│  │  ├─ [Multiple matches found?]
│  │  │  └─ NO → ERROR: "Multiple files named '{filename}' found. Specify relative path"
│  │  │
│  │  └─ [No matches found?]
│  │     └─ YES → Create new file at: config/{component_type}s/{filename}
│  │
│  └─ [Is it a relative path? (contains '/')]
│     │
│     ├─ [File exists at this path in context?]
│     │  └─ YES → Use this existing file
│     │
│     └─ [File doesn't exist?]
│        └─ NO → Create new file at specified path
│
└─ [No file_path provided?]
   └─ Use/Create default: config/{component_type}s/{component_type}s.json

STEP 3: Add Component to File
│
├─ [Component name already exists in file?]
│  └─ YES → ERROR: "Component '{name}' already exists in {file_path}"
│
└─ [Component name unique?]
   ├─ Add component to file
   └─ Return success with details:
      {
        "message": "Component created successfully",
        "component": {
          "name": "...",
          "type": "...",
          "file_path": "relative/path/to/file.json",
          "context": "project|workspace",
          "project_name": "..." (if applicable),
          "workspace_name": "..."
        }
      }
```

### Endpoints

#### List Component Types
`GET /config/components`

Returns a list of all available component types in the system.

**Response:**
```json
["agent", "llm", "mcp_server", "simple_workflow", "custom_workflow"]
```

#### List Components by Type
`GET /config/components/{component_type}`

Returns all components of a specific type. Accepts both singular and plural forms (e.g., 'agent' or 'agents').

**Parameters:**
- `component_type` (path): The type of component to list

**Response:**
```json
[
  {
    "name": "Weather Agent",
    "type": "agent",
    "description": "An agent that provides weather information",
    ...
  }
]
```

#### Get Component by ID
`GET /config/components/{component_type}/{component_id}`

Retrieves a specific component by its type and ID.

**Parameters:**
- `component_type` (path): The type of component
- `component_id` (path): The unique identifier (name) of the component

**Response:**
```json
{
  "name": "Weather Agent",
  "type": "agent",
  "description": "An agent that provides weather information",
  "system_prompt": "You are a helpful weather assistant...",
  "llm_config_id": "anthropic_claude",
  "mcp_servers": ["weather_server"]
}
```

#### Create Component
`POST /config/components/{component_type}`

Creates a new component following the decision tree logic above.

**Parameters:**
- `component_type` (path): The type of component to create

**Request Body:**
```json
{
  "name": "My Agent",
  "config": {
    "description": "A custom agent",
    "system_prompt": "You are a helpful assistant",
    "llm_config_id": "anthropic_claude"
  },
  "file_path": "custom_agents.json",  // Optional
  "project": "my_project",            // Optional
  "workspace": false                  // Optional
}
```

**Response:**
```json
{
  "message": "Component 'My Agent' created successfully",
  "component": {
    "name": "My Agent",
    "type": "agent",
    "file_path": "config/agents/custom_agents.json",
    "context": "project",
    "project_name": "my_project",
    "workspace_name": "my_workspace"
  }
}
```

#### Update Component
`PUT /config/components/{component_type}/{component_id}`

Updates an existing component's configuration.

**Parameters:**
- `component_type` (path): The type of component
- `component_id` (path): The unique identifier (name) of the component

**Request Body:**
```json
{
  "config": {
    "description": "Updated description",
    "system_prompt": "Updated prompt",
    "llm_config_id": "openai_gpt4"
  }
}
```

#### Delete Component
`DELETE /config/components/{component_type}/{component_id}`

Deletes a component from its configuration file.

**Parameters:**
- `component_type` (path): The type of component
- `component_id` (path): The unique identifier (name) of the component

#### Validate Component
`POST /config/components/{component_type}/{component_id}/validate`

Validates a component's configuration against its schema.

**Parameters:**
- `component_type` (path): The type of component
- `component_id` (path): The unique identifier (name) of the component

## File Operations

### List Configuration Sources
`GET /config/sources`

Returns all configuration source directories being monitored by the system.

**Response:**
```json
[
  {
    "path": "/home/user/workspace/project/config",
    "context": "project",
    "project_name": "my_project"
  },
  {
    "path": "/home/user/workspace/config",
    "context": "workspace",
    "workspace_name": "my_workspace"
  }
]
```

### List Configuration Files
`GET /config/files`

Lists all configuration files across all sources.

**Response:**
```json
[
  {
    "path": "config/agents/agents.json",
    "context": "project",
    "project_name": "my_project",
    "components": [
      {"type": "agent", "name": "Weather Agent"},
      {"type": "agent", "name": "Code Assistant"}
    ]
  }
]
```

### Get File Content
`GET /config/files/{file_path}`

Retrieves the content of a specific configuration file.

**Parameters:**
- `file_path` (path): Relative path to the configuration file

### Create Configuration File
`POST /config/files`

Creates a new configuration file.

**Request Body:**
```json
{
  "file_path": "config/agents/team_agents.json",
  "content": []  // Initial content (empty array for component files)
}
```

### Update Configuration File
`PUT /config/files/{file_path}`

Updates the entire content of a configuration file.

**Parameters:**
- `file_path` (path): Relative path to the configuration file

### Delete Configuration File
`DELETE /config/files/{file_path}`

Deletes a configuration file.

**Parameters:**
- `file_path` (path): Relative path to the configuration file

## Configuration Management

### Refresh Configurations
`POST /config/refresh`

Forces the configuration manager to reload all configuration files from disk.

## Error Handling Reference

### File Operation Errors

#### POST /config/files (Create File)
- **409 Conflict**: File already exists at the specified path
- **400 Bad Request**: Invalid file path format (e.g., absolute path when relative expected)
- **403 Forbidden**: File path is outside allowed configuration directories
- **400 Bad Request**: Invalid file extension (not .json, .yaml, or .yml)
- **400 Bad Request**: Invalid initial content (not a valid JSON/YAML array)
- **500 Internal Server Error**: File system errors (permissions, disk full, etc.)

#### GET /config/files/{file_path} (Get File)
- **404 Not Found**: File doesn't exist at the specified path
- **403 Forbidden**: File path is outside allowed configuration directories
- **500 Internal Server Error**: File read errors

#### PUT /config/files/{file_path} (Update File)
- **404 Not Found**: File doesn't exist at the specified path
- **400 Bad Request**: Invalid content format (not valid JSON/YAML)
- **400 Bad Request**: Content is not an array of components
- **403 Forbidden**: File path is outside allowed configuration directories
- **422 Unprocessable Entity**: Content validation fails (e.g., components missing required fields)
- **500 Internal Server Error**: File write errors

#### DELETE /config/files/{file_path} (Delete File)
- **404 Not Found**: File doesn't exist at the specified path
- **403 Forbidden**: File path is outside allowed configuration directories
- **409 Conflict**: File contains components that are referenced elsewhere
- **500 Internal Server Error**: File deletion errors

### Component Operation Errors

#### POST /config/components/{component_type} (Create Component)
- **400 Bad Request**: Both `project` and `workspace` specified
- **400 Bad Request**: Multiple projects exist but neither `project` nor `workspace` specified
- **404 Not Found**: Specified project doesn't exist
- **409 Conflict**: Multiple files with same name (when only filename provided)
- **409 Conflict**: Component with same name already exists in the target file
- **400 Bad Request**: Invalid component type
- **422 Unprocessable Entity**: Component validation fails (missing required fields)
- **403 Forbidden**: File is outside allowed configuration directories
- **500 Internal Server Error**: File write errors

#### PUT /config/components/{component_type}/{component_id} (Update Component)
- **404 Not Found**: Component doesn't exist
- **422 Unprocessable Entity**: Updated config validation fails
- **500 Internal Server Error**: File write errors

#### DELETE /config/components/{component_type}/{component_id} (Delete Component)
- **404 Not Found**: Component doesn't exist
- **409 Conflict**: Component is referenced by other components (e.g., agent references this MCP server)
- **500 Internal Server Error**: File write errors

### Validation Rules

1. **File Path Validation**:
   - Must be relative (no leading `/` or `C:\`)
   - Must be within configured directories from `.aurite` files
   - No path traversal (`../` not allowed)
   - Must have valid extension (.json, .yaml, .yml)

2. **Component Validation**:
   - Name must be unique within its type in the same file
   - Required fields based on component type
   - Referenced components must exist (e.g., llm_config_id, mcp_servers)

3. **File Content Validation**:
   - Must be valid JSON/YAML
   - Root must be an array
   - Each item must have `type` and `name` fields

### HTTP Status Code Summary
- **200 OK**: Successful operation
- **400 Bad Request**: Client error - invalid input format
- **403 Forbidden**: Operation not allowed (security/permission)
- **404 Not Found**: Resource doesn't exist
- **409 Conflict**: Operation conflicts with current state
- **422 Unprocessable Entity**: Input format is correct but content is invalid
- **500 Internal Server Error**: Server-side errors

### Example Error Response Format
```json
{
  "detail": "File already exists at path: config/agents/my_agents.json",
  "error_code": "FILE_EXISTS",
  "status_code": 409
}
```

## Examples

### Creating an Agent in Default Location

**Request:**
```bash
POST /config/components/agent
{
  "name": "My Assistant",
  "config": {
    "description": "A helpful assistant",
    "system_prompt": "You are a helpful AI assistant",
    "llm_config_id": "anthropic_claude",
    "mcp_servers": []
  }
}
```

**Response:**
```json
{
  "message": "Component 'My Assistant' created successfully",
  "component": {
    "name": "My Assistant",
    "type": "agent",
    "file_path": "config/agents/agents.json",
    "context": "project",
    "project_name": "my_project"
  }
}
```

### Creating a Component in Workspace

**Request:**
```bash
POST /config/components/mcp_server
{
  "name": "Shared Weather Server",
  "config": {
    "description": "Weather service shared across projects",
    "transport_type": "stdio",
    "server_path": "servers/weather.py"
  },
  "workspace": true,
  "file_path": "shared_servers.json"
}
```

**Response:**
```json
{
  "message": "Component 'Shared Weather Server' created successfully",
  "component": {
    "name": "Shared Weather Server",
    "type": "mcp_server",
    "file_path": "config/mcp_servers/shared_servers.json",
    "context": "workspace",
    "workspace_name": "my_workspace"
  }
}
```

### Handling Multiple Projects Error

**Request:**
```bash
POST /config/components/agent
{
  "name": "Test Agent",
  "config": {...}
}
```

**Response (400 Bad Request):**
```json
{
  "detail": "Multiple projects found. Please specify 'project' or 'workspace'",
  "error_code": "MULTIPLE_PROJECTS",
  "status_code": 400
}
```

## Best Practices

1. **Always check if a file exists before creating components** - Use `GET /config/files` to list existing files
2. **Use relative paths for portability** - Absolute paths will be rejected
3. **Specify project/workspace explicitly when multiple projects exist** - Avoids ambiguity
4. **Validate components before deployment** - Use the validation endpoint to catch errors early
5. **Include descriptive names and descriptions** - Makes configuration management easier
6. **Group related components in the same file** - Improves organization
7. **Use the refresh endpoint sparingly** - Only when files are modified outside the API
