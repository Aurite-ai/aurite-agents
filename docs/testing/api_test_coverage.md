# Aurite Framework API Test Coverage Document

## Overview

This document provides a comprehensive mapping of all API endpoints in the Aurite Framework, their current test coverage status in Postman collections, and recommendations for expanding test coverage.

**Last Updated:** January 10, 2025

## Test Coverage Legend

- ✅ **Tested** - Endpoint has test coverage in Postman collections
- ⚠️ **Partial** - Endpoint has basic tests but missing important scenarios
- ❌ **Not Tested** - No test coverage exists
- 🔄 **Integration Only** - Tested only in TypeScript integration tests

## Summary Statistics

| Router | Total Endpoints | Tested | Partial | Not Tested | Coverage % |
|--------|----------------|---------|---------|------------|------------|
| Configuration Manager | 17 | 8 | 0 | 9 | 47% |
| MCP Host | 12 | 5 | 0 | 7 | 42% |
| Execution Facade | 13 | 5 | 0 | 8 | 38% |
| System | 12 | 0 | 0 | 12 | 0% |
| Main API | 2 | 1 | 0 | 1 | 50% |
| **TOTAL** | **56** | **19** | **0** | **37** | **34%** |

## 1. Configuration Manager Routes (`/config/*`)

### Component CRUD Operations

| Method | Endpoint | Status | Postman Test | Notes |
|--------|----------|--------|--------------|-------|
| GET | `/config/components` | ✅ | List Component Types | Tests array response and includes expected types |
| GET | `/config/components/{component_type}` | ✅ | List Components by Type | Tests for agent type only |
| GET | `/config/components/{component_type}/{component_id}` | ✅ | Get Component by ID | Tests Weather Agent retrieval |
| POST | `/config/components/{component_type}` | ✅ | Create Component | Basic test, missing complex scenarios |
| PUT | `/config/components/{component_type}/{component_id}` | ✅ | Update Component | Tests Weather Agent update |
| DELETE | `/config/components/{component_type}/{component_id}` | ✅ | Delete Component (Non-existent) | Tests 404 scenario |
| DELETE | `/config/components/{component_type}/{component_id}` | ✅ | Delete Component (Existing) | Note: Actual deletion not implemented |
| POST | `/config/components/{component_type}/{component_id}/validate` | ✅ | Validate Component | Tests Weather Agent validation |

### Project & Workspace Management

| Method | Endpoint | Status | Postman Test | Notes |
|--------|----------|--------|--------------|-------|
| GET | `/config/projects` | ❌ | - | Not tested |
| POST | `/config/projects` | ❌ | - | Not tested |
| GET | `/config/projects/{project_id}` | ❌ | - | Not tested |
| PUT | `/config/projects/{project_id}` | ❌ | - | Not tested |
| DELETE | `/config/projects/{project_id}` | ❌ | - | Not tested |
| POST | `/config/projects/{project_id}/activate` | ❌ | - | Not tested |
| GET | `/config/projects/active` | ❌ | - | Not tested |
| GET | `/config/workspaces` | ❌ | - | Not tested |
| POST | `/config/workspaces` | ❌ | - | Not tested |
| GET | `/config/workspaces/{workspace_id}` | ❌ | - | Not tested |
| PUT | `/config/workspaces/{workspace_id}` | ❌ | - | Not tested |

### Configuration File Operations

| Method | Endpoint | Status | Postman Test | Notes |
|--------|----------|--------|--------------|-------|
| GET | `/config/sources` | ❌ | - | Not tested |
| GET | `/config/files` | ❌ | - | Not tested |
| POST | `/config/files` | ❌ | - | Not tested |
| GET | `/config/files/{file_path}` | ❌ | - | Not tested |
| PUT | `/config/files/{file_path}` | ❌ | - | Not tested |
| DELETE | `/config/files/{file_path}` | ❌ | - | Not tested |
| POST | `/config/refresh` | ✅ | Refresh Configurations | Tests success response |
| POST | `/config/validate` | ❌ | - | Not tested |

### Missing Test Scenarios for Config Manager

1. **Component Creation with Options**
   - Create with specific project
   - Create with workspace flag
   - Create with custom file_path
   - Multiple projects conflict scenario (400 error)

2. **Error Scenarios**
   - 409 Conflict - Component already exists
   - 404 Not Found - Component/project/file not found
   - 422 Unprocessable Entity - Validation failures
   - 400 Bad Request - Invalid input

3. **Complex Workflows**
   - Create component → Update → Validate → Delete
   - File operations with components
   - Project switching and activation

## 2. MCP Host Routes (`/tools/*`)

### Tool Discovery & Execution

| Method | Endpoint | Status | Postman Test | Notes |
|--------|----------|--------|--------------|-------|
| GET | `/tools` | ✅ | List Tools | Tests array response |
| GET | `/tools/{tool_name}` | ❌ | - | Not tested |
| POST | `/tools/{tool_name}/call` | ✅ | Call Weather Lookup Tool | Tests weather_lookup execution |

### Runtime Server Management

| Method | Endpoint | Status | Postman Test | Notes |
|--------|----------|--------|--------------|-------|
| GET | `/tools/servers` | ❌ | - | Not tested |
| GET | `/tools/servers/{server_name}` | ❌ | - | Not tested |
| GET | `/tools/servers/{server_name}/tools` | ❌ | - | Not tested |
| POST | `/tools/servers/{server_name}/test` | ❌ | - | Not tested |

### Server Registration

| Method | Endpoint | Status | Postman Test | Notes |
|--------|----------|--------|--------------|-------|
| POST | `/tools/register/config` | ❌ | - | Not tested |
| POST | `/tools/register/{server_name}` | ✅ | Register Weather Server By Name | Tests success response |
| DELETE | `/tools/servers/{server_name}` | ✅ | Unregister Weather Server | Tests unregistration |

### Host Status

| Method | Endpoint | Status | Postman Test | Notes |
|--------|----------|--------|--------------|-------|
| GET | `/tools/status` | ✅ | Get Host Status | Tests active status and tool_count |

### Missing Test Scenarios for MCP Host

1. **Server Lifecycle**
   - Register → List → Get Status → Execute Tool → Unregister
   - Test server connection before registration
   - Multiple server registration

2. **Error Scenarios**
   - Tool not found (404)
   - Server not registered (404)
   - Registration timeout
   - Connection failures

3. **Tool Execution**
   - Various tool input schemas
   - Tool execution errors
   - Missing required parameters

## 3. Execution Facade Routes (`/execution/*`)

### Agent Execution

| Method | Endpoint | Status | Postman Test | Notes |
|--------|----------|--------|--------------|-------|
| POST | `/execution/agents/{agent_name}/run` | ✅ | Run Weather Agent | Tests weather query response |
| POST | `/execution/agents/{agent_name}/stream` | ✅ | Stream Weather Agent | Basic streaming test |
| POST | `/execution/agents/{agent_name}/test` | ❌ | - | Not tested |
| GET | `/execution/agents/{agent_name}/history` | ❌ | - | Not tested |

### Workflow Execution

| Method | Endpoint | Status | Postman Test | Notes |
|--------|----------|--------|--------------|-------|
| POST | `/execution/workflows/simple/{workflow_name}/run` | ✅ | Run Simple Workflow | Tests Weather Planning Workflow |
| POST | `/execution/workflows/custom/{workflow_name}/run` | ✅ | Run Custom Workflow | Tests ExampleCustomWorkflow |
| POST | `/execution/workflows/simple/{workflow_name}/test` | ❌ | - | Not tested |
| POST | `/execution/workflows/custom/{workflow_name}/test` | ❌ | - | Not tested |
| POST | `/execution/workflows/custom/{workflow_name}/validate` | ❌ | - | Not tested |
| GET | `/execution/workflows/{workflow_name}/history` | ❌ | - | Not tested |

### Execution History & Monitoring

| Method | Endpoint | Status | Postman Test | Notes |
|--------|----------|--------|--------------|-------|
| GET | `/execution/history` | ❌ | - | Not tested |
| GET | `/execution/history/{session_id}` | ❌ | - | Not tested |
| DELETE | `/execution/history/{session_id}` | ❌ | - | Not tested |
| POST | `/execution/history/cleanup` | ❌ | - | Not tested |

### Facade Status

| Method | Endpoint | Status | Postman Test | Notes |
|--------|----------|--------|--------------|-------|
| GET | `/execution/status` | ✅ | Get Facade Status | Tests active status |

### Missing Test Scenarios for Execution Facade

1. **Session Management**
   - Create session → Execute → Get History → Delete
   - Pagination tests for history
   - Session cleanup with custom parameters

2. **Streaming**
   - Event type validation
   - Error events in stream
   - Connection interruption handling

3. **Error Scenarios**
   - Agent not found (404)
   - Workflow execution failures
   - Invalid input data

## 4. System Routes (`/system/*`)

### System Information

| Method | Endpoint | Status | Postman Test | Notes |
|--------|----------|--------|--------------|-------|
| GET | `/system/info` | ❌ | - | Not tested |
| GET | `/system/health` | ❌ | - | Not tested |
| GET | `/system/version` | ❌ | - | Not tested |
| GET | `/system/capabilities` | ❌ | - | Not tested |

### Environment Management

| Method | Endpoint | Status | Postman Test | Notes |
|--------|----------|--------|--------------|-------|
| GET | `/system/environment` | ❌ | - | Not tested |
| PUT | `/system/environment` | ❌ | - | Not tested |
| GET | `/system/dependencies` | ❌ | - | Not tested |
| POST | `/system/dependencies/check` | ❌ | - | Not tested |

### Real-time Monitoring

| Method | Endpoint | Status | Postman Test | Notes |
|--------|----------|--------|--------------|-------|
| GET | `/system/monitoring/metrics` | ❌ | - | Not tested |
| GET | `/system/monitoring/logs` | ❌ | - | Not tested (SSE stream) |
| GET | `/system/monitoring/active` | ❌ | - | Not tested |

### Missing Test Scenarios for System Routes

1. **Health Monitoring**
   - Component health checks
   - Degraded vs unhealthy states
   - Issue reporting

2. **Environment Variables**
   - Sensitive variable masking
   - Update non-sensitive variables
   - Validation of updates

3. **Streaming Logs**
   - SSE connection handling
   - Log format validation
   - Heartbeat messages

## 5. Main API Routes (`/`)

| Method | Endpoint | Status | Postman Test | Notes |
|--------|----------|--------|--------------|-------|
| GET | `/health` | ✅ | Health Check | Tests OK status |
| GET | `/{full_path:path}` | ❌ | - | Catch-all route, returns 404 |

## Priority Recommendations

### High Priority (Core Functionality)
1. **System Routes** - Complete health and monitoring endpoints
2. **Config Manager** - File operations and project management
3. **Execution History** - Session management and cleanup

### Medium Priority (Enhanced Testing)
1. **MCP Host** - Server status and tool discovery
2. **Error Scenarios** - All 4xx and 5xx responses
3. **Complex Workflows** - Multi-step operations

### Low Priority (Edge Cases)
1. **Streaming Endpoints** - SSE handling
2. **Pagination** - Large dataset handling
3. **Performance Tests** - Load and stress testing

## Test Implementation Guidelines

### For Each Endpoint Test:
1. **Happy Path** - Normal successful operation
2. **Error Cases** - 400, 404, 409, 422, 500 responses
3. **Edge Cases** - Empty data, special characters, limits
4. **Authentication** - Missing/invalid API key

### Test Organization:
- Group related endpoints in folders
- Use environment variables for configuration
- Include pre-request scripts for setup
- Add comprehensive test assertions
- Document expected vs actual behavior

## Next Steps

1. **Immediate Actions**
   - Create System Routes collection
   - Expand Config Manager tests for file operations
   - Add execution history tests

2. **Documentation Updates**
   - Update this document as tests are added
   - Create test scenario documentation
   - Add example requests/responses

3. **Automation**
   - Set up Newman for CI/CD integration
   - Create test data fixtures
   - Implement cleanup scripts

## Related Documents

- [API Reference](../usage/api_reference.md)
- [Configuration Manager Routes](../usage/routes/config_manager_routes.md)
- [MCP Host Routes](../usage/routes/mcp_host_routes.md)
- [Execution Facade Routes](../usage/routes/facade_routes.md)
- [System Routes](../usage/routes/system_routes.md)
