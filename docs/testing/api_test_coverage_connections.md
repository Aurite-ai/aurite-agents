# Aurite Framework API Test Coverage - Component Connections

## Overview

This document maps the connections between API components, test files, documentation, and TypeScript clients to provide a complete picture of the testing ecosystem.

## Component Connection Matrix

### 1. Configuration Manager (`/config/*`)

| Component      | Router File                                          | Route Docs                                   | Postman Collection                                                                                            | TS Client                                    | TS Tests                                                 | Coverage |
| -------------- | ---------------------------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | -------------------------------------------- | -------------------------------------------------------- | -------- |
| Config Manager | `src/aurite/bin/api/routes/config_manager_routes.py` | `docs/usage/routes/config_manager_routes.md` | `tests/e2e/api/config_manager_components.json`, `config_manager_files.json`, & `config_manager_projects.json` | `frontend/src/routes/ConfigManagerClient.ts` | `frontend/tests/unit/client/ConfigManagerClient.test.ts` | 100%     |

**Key Connections:**

- Router imports: `ConfigManager` from `aurite.config.config_manager`
- Depends on: `get_config_manager` dependency
- Used by: ExecutionFacade for agent/workflow configs

### 2. MCP Host Manager (`/tools/*`)

| Component | Router File                                    | Route Docs                             | Postman Collection                   | TS Client                              | TS Tests                                           | Coverage |
| --------- | ---------------------------------------------- | -------------------------------------- | ------------------------------------ | -------------------------------------- | -------------------------------------------------- | -------- |
| MCP Host  | `src/aurite/bin/api/routes/mcp_host_routes.py` | `docs/usage/routes/mcp_host_routes.md` | `tests/e2e/api/mcp_host_routes.json` | `frontend/src/routes/MCPHostClient.ts` | `frontend/tests/unit/client/MCPHostClient.test.ts` | 100%     |

**Key Connections:**

- Router imports: `MCPHost` from `aurite.host.host`
- Depends on: `get_host` dependency
- Works with: ConfigManager for server configurations
- Used by: ExecutionFacade for tool execution

### 3. Execution Facade (`/execution/*`)

| Component        | Router File                                  | Route Docs                           | Postman Collection                 | TS Client                                      | TS Tests                                                   | Coverage |
| ---------------- | -------------------------------------------- | ------------------------------------ | ---------------------------------- | ---------------------------------------------- | ---------------------------------------------------------- | -------- |
| Execution Facade | `src/aurite/bin/api/routes/facade_routes.py` | `docs/usage/routes/facade_routes.md` | `tests/e2e/api/facade_routes.json` | `frontend/src/routes/ExecutionFacadeClient.ts` | `frontend/tests/unit/client/ExecutionFacadeClient.test.ts` | 38%      |

**Key Connections:**

- Router imports: `ExecutionFacade` from `aurite.execution.facade`
- Depends on: `get_execution_facade` dependency
- Uses: ConfigManager for agent/workflow configs
- Uses: MCPHost for tool execution
- Manages: Session history and caching

### 4. System Management (`/system/*`)

| Component | Router File                                  | Route Docs                           | Postman Collection                 | TS Client                             | TS Tests                                          | Coverage |
| --------- | -------------------------------------------- | ------------------------------------ | ---------------------------------- | ------------------------------------- | ------------------------------------------------- | -------- |
| System    | `src/aurite/bin/api/routes/system_routes.py` | `docs/usage/routes/system_routes.md` | `tests/e2e/api/system_routes.json` | `frontend/src/routes/SystemClient.ts` | `frontend/tests/unit/routes/SystemClient.test.ts` | 100%     |

**Key Connections:**

- Router imports: System utilities, psutil (optional)
- Depends on: `get_host_manager` dependency
- Monitors: All other components' health
- Provides: System metrics and diagnostics

### 5. Main API (`/`)

| Component | Router File                 | Route Docs                    | Postman Collection            | TS Client | TS Tests | Coverage |
| --------- | --------------------------- | ----------------------------- | ----------------------------- | --------- | -------- | -------- |
| Main API  | `src/aurite/bin/api/api.py` | `docs/usage/api_reference.md` | `tests/e2e/api/main_api.json` | N/A       | N/A      | 50%      |

**Key Connections:**

- Imports all routers with prefixes:
  - `/config` → config_manager_routes
  - `/tools` → mcp_host_routes
  - `/execution` → facade_routes
  - `/system` → system_routes
- Manages: FastAPI app lifecycle
- Provides: Exception handlers, CORS, middleware

## Dependency Flow

```
api.py (Main Entry Point)
    │
    ├── Dependencies (get_* functions)
    │   ├── get_api_key → Security
    │   ├── get_config_manager → ConfigManager
    │   ├── get_host → MCPHost
    │   ├── get_execution_facade → ExecutionFacade
    │   └── get_host_manager → Aurite
    │
    └── Routers (with prefixes)
        ├── /config → config_manager_routes.py
        ├── /tools → mcp_host_routes.py
        ├── /execution → facade_routes.py
        └── /system → system_routes.py
```

## Integration Test Coverage

The TypeScript integration test (`frontend/tests/integration/test-integration.ts`) covers:

1. **Execution Facade Status** ✅
2. **MCP Host Status** ✅
3. **List Tools** ✅
4. **List Registered Servers** ✅
5. **List Agent Configurations** ✅
6. **Run Agent** ✅
7. **Get Agent Config** ✅
8. **Stream Agent Response** ✅
9. **File Listing Operations** ✅
10. **File CRUD Operations** ✅
11. **Component CRUD Operations** ✅
12. **Validation** ✅
13. **Global Validation** ✅
14. **Duplicate Component Creation** ✅

## Missing Components

### Documentation

- [x] `docs/usage/routes/system_routes.md` - System routes documentation

### Postman Collections

- [x] `tests/e2e/api/system_routes.json` - System routes tests

### TypeScript Client

- [x] `frontend/src/routes/SystemClient.ts` - System management client

### TypeScript Tests

- [x] `frontend/tests/unit/client/SystemClient.test.ts` - System client tests

## Test Data Dependencies

### Configuration Files Required

- `config/agents/agents.json` - Must contain "Weather Agent"
- `config/mcp_servers/mcp_servers.json` - Must contain "weather_server"
- `config/simple_workflows/workflows.json` - Must contain "Weather Planning Workflow"
- `custom_workflows/example_workflow.py` - Must define "ExampleCustomWorkflow"

### Environment Variables

- `API_KEY` - Required for authentication
- `WEATHER_API_KEY` - Required for weather_server (if using real API)

## API Authentication Flow

```
Client Request
    │
    ├── Header: X-API-Key: {api_key}
    │
    └── Security Dependency
        │
        └── get_api_key()
            │
            ├── Check Header
            ├── Validate Key
            └── Return or 401
```

## Error Handling Chain

```
Router Endpoint
    │
    ├── Try Operation
    │   └── Service Call
    │
    └── Catch Exception
        │
        ├── ConfigurationError → 404
        ├── AgentExecutionError → 500
        ├── WorkflowExecutionError → 500
        ├── FileNotFoundError → 404
        └── Generic Exception → 500
```

## Testing Best Practices

### 1. Test Organization

```
tests/
├── e2e/api/
│   ├── {router_name}_routes.json
│   └── environment.json (shared variables)
├── integration/
│   └── test-integration.ts
└── unit/client/
    └── {ClientName}.test.ts
```

### 2. Test Naming Convention

- Postman: `{HTTP_METHOD} {Endpoint Description}`
- TypeScript: `should {expected behavior} when {condition}`

### 3. Test Data Management

- Use environment variables for dynamic values
- Create setup/teardown scripts
- Avoid hardcoded test data

### 4. Coverage Tracking

- Update `api_test_coverage_visual.md` when adding tests
- Track both positive and negative test cases
- Include edge cases and error scenarios

## Quick Links

- [Visual Coverage Overview](./api_test_coverage_visual.md)
- [API Reference](../usage/api_reference.md)
- [Frontend Testing README](https://github.com/Aurite-ai/aurite-agents/blob/main/frontend/tests/README.md)
