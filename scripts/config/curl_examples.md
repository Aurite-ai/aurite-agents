# Enhanced Create Component API Examples

The create component endpoint has been improved to automatically detect the best configuration source when no explicit project or workspace is specified.

## Basic Usage (Auto-Detection)

The simplest way to create an agent - the system will automatically choose the highest priority configuration source:

```bash
curl -X POST "http://localhost:8000/config/components/agents" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY_HERE" \
  -d '{
    "name": "my-agent",
    "config": {
      "type": "agent",
      "description": "My custom agent",
      "system_prompt": "You are a helpful assistant",
      "max_iterations": 10
    }
  }'
```

## Explicit Workspace Creation

To create an agent at the workspace level (shared across all projects):

```bash
curl -X POST "http://localhost:8000/config/components/agents" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY_HERE" \
  -d '{
    "name": "workspace-agent",
    "config": {
      "type": "agent",
      "description": "Agent available to all projects",
      "system_prompt": "You are a helpful assistant",
      "workspace": true,
      "max_iterations": 10
    }
  }'
```

## Explicit Project Creation

To create an agent in a specific project:

```bash
curl -X POST "http://localhost:8000/config/components/agents" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY_HERE" \
  -d '{
    "name": "project-agent",
    "config": {
      "type": "agent",
      "description": "Agent specific to a project",
      "system_prompt": "You are a helpful assistant",
      "project": "my-project-name",
      "max_iterations": 10
    }
  }'
```

## PowerShell Examples

For Windows PowerShell users, use backticks for line continuation:

```powershell
curl -X POST "http://localhost:8000/config/components/agents" `
  -H "Content-Type: application/json" `
  -H "X-API-Key: YOUR_API_KEY_HERE" `
  -d '{\"name\": \"my-agent\", \"config\": {\"type\": \"agent\", \"description\": \"My custom agent\", \"system_prompt\": \"You are a helpful assistant\", \"max_iterations\": 10}}'
```

Or use a JSON file approach:

1. Create `agent.json`:
```json
{
  "name": "my-agent",
  "config": {
    "type": "agent",
    "description": "My custom agent",
    "system_prompt": "You are a helpful assistant",
    "max_iterations": 10
  }
}
```

2. Use the file in curl:
```powershell
curl -X POST "http://localhost:8000/config/components/agents" -H "Content-Type: application/json" -H "X-API-Key: YOUR_API_KEY_HERE" -d "@agent.json"
```

## Success Response

All successful requests return:

```json
{
  "message": "Component created successfully"
}
```

## Key Improvements

1. **Smart Auto-Detection**: When no `project` or `workspace` is specified, the system automatically uses the highest priority configuration source
2. **Better Error Messages**: More helpful error messages when context cannot be determined
3. **Flexible Context Specification**: Support for both explicit project names and workspace-level creation
4. **Consistent Behavior**: Works the same way across all component types (agents, llms, mcp_servers, etc.)

## Priority Order

The system uses this priority order for auto-detection:

1. **Current project** (if you're in a project directory)
2. **Highest priority project** (if multiple projects exist)
3. **Workspace level** (if no projects or single project)
4. **User level** (fallback)

This ensures components are created in the most appropriate location without requiring explicit specification in most cases.
