# Aurite Framework API Test Coverage - Visual Overview

## API Structure & Test Coverage Map

```
Aurite Framework API
│
├── 🟢 /health (50% coverage)
│   └── ✅ GET /health - Health check
│
├── 🟡 /config/* - Configuration Manager (47% coverage)
│   ├── Component CRUD ✅ (8/8 tested)
│   │   ├── ✅ GET /components
│   │   ├── ✅ GET /components/{type}
│   │   ├── ✅ GET /components/{type}/{id}
│   │   ├── ✅ POST /components/{type}
│   │   ├── ✅ PUT /components/{type}/{id}
│   │   ├── ✅ DELETE /components/{type}/{id}
│   │   └── ✅ POST /components/{type}/{id}/validate
│   │
│   ├── Project & Workspace ❌ (0/11 tested)
│   │   ├── ❌ GET /projects
│   │   ├── ❌ POST /projects
│   │   ├── ❌ GET /projects/{id}
│   │   ├── ❌ PUT /projects/{id}
│   │   ├── ❌ DELETE /projects/{id}
│   │   ├── ❌ POST /projects/{id}/activate
│   │   ├── ❌ GET /projects/active
│   │   ├── ❌ GET /workspaces
│   │   ├── ❌ POST /workspaces
│   │   ├── ❌ GET /workspaces/{id}
│   │   └── ❌ PUT /workspaces/{id}
│   │
│   └── File Operations ⚠️ (1/8 tested)
│       ├── ❌ GET /sources
│       ├── ❌ GET /files
│       ├── ❌ POST /files
│       ├── ❌ GET /files/{path}
│       ├── ❌ PUT /files/{path}
│       ├── ❌ DELETE /files/{path}
│       ├── ✅ POST /refresh
│       └── ❌ POST /validate
│
├── 🟡 /tools/* - MCP Host Manager (42% coverage)
│   ├── Tool Operations ⚠️ (2/3 tested)
│   │   ├── ✅ GET /
│   │   ├── ❌ GET /{tool_name}
│   │   └── ✅ POST /{tool_name}/call
│   │
│   ├── Server Management ❌ (0/4 tested)
│   │   ├── ❌ GET /servers
│   │   ├── ❌ GET /servers/{name}
│   │   ├── ❌ GET /servers/{name}/tools
│   │   └── ❌ POST /servers/{name}/test
│   │
│   ├── Registration ⚠️ (2/3 tested)
│   │   ├── ❌ POST /register/config
│   │   ├── ✅ POST /register/{name}
│   │   └── ✅ DELETE /servers/{name}
│   │
│   └── Status ✅ (1/1 tested)
│       └── ✅ GET /status
│
├── 🟡 /execution/* - Execution Facade (38% coverage)
│   ├── Agent Execution ⚠️ (2/4 tested)
│   │   ├── ✅ POST /agents/{name}/run
│   │   ├── ✅ POST /agents/{name}/stream
│   │   ├── ❌ POST /agents/{name}/test
│   │   └── ❌ GET /agents/{name}/history
│   │
│   ├── Workflow Execution ⚠️ (2/6 tested)
│   │   ├── ✅ POST /workflows/simple/{name}/run
│   │   ├── ✅ POST /workflows/custom/{name}/run
│   │   ├── ❌ POST /workflows/simple/{name}/test
│   │   ├── ❌ POST /workflows/custom/{name}/test
│   │   ├── ❌ POST /workflows/custom/{name}/validate
│   │   └── ❌ GET /workflows/{name}/history
│   │
│   ├── History & Monitoring ❌ (0/4 tested)
│   │   ├── ❌ GET /history
│   │   ├── ❌ GET /history/{session_id}
│   │   ├── ❌ DELETE /history/{session_id}
│   │   └── ❌ POST /history/cleanup
│   │
│   └── Status ✅ (1/1 tested)
│       └── ✅ GET /status
│
└── 🔴 /system/* - System Management (0% coverage)
    ├── System Info ❌ (0/4 tested)
    │   ├── ❌ GET /info
    │   ├── ❌ GET /health
    │   ├── ❌ GET /version
    │   └── ❌ GET /capabilities
    │
    ├── Environment ❌ (0/4 tested)
    │   ├── ❌ GET /environment
    │   ├── ❌ PUT /environment
    │   ├── ❌ GET /dependencies
    │   └── ❌ POST /dependencies/check
    │
    └── Monitoring ❌ (0/3 tested)
        ├── ❌ GET /monitoring/metrics
        ├── ❌ GET /monitoring/logs (SSE)
        └── ❌ GET /monitoring/active
```

## Coverage Legend
- 🟢 Good Coverage (>70%)
- 🟡 Partial Coverage (30-70%)
- 🔴 Poor Coverage (<30%)
- ✅ Tested
- ⚠️ Partially Tested
- ❌ Not Tested

## Test Coverage by Component

### Configuration Manager (`/config/*`)
```
Total: 27 endpoints | Tested: 8 | Coverage: 30%
┌─────────────────────────┬────────┬──────────┐
│ Category                │ Tested │ Coverage │
├─────────────────────────┼────────┼──────────┤
│ Component CRUD          │ 8/8    │ 100% ✅  │
│ Project & Workspace     │ 0/11   │ 0% 🔴    │
│ File Operations         │ 1/8    │ 13% 🔴   │
└─────────────────────────┴────────┴──────────┘
```

### MCP Host Manager (`/tools/*`)
```
Total: 12 endpoints | Tested: 5 | Coverage: 42%
┌─────────────────────────┬────────┬──────────┐
│ Category                │ Tested │ Coverage │
├─────────────────────────┼────────┼──────────┤
│ Tool Operations         │ 2/3    │ 67% 🟡   │
│ Server Management       │ 0/4    │ 0% 🔴    │
│ Registration            │ 2/3    │ 67% 🟡   │
│ Status                  │ 1/1    │ 100% ✅  │
└─────────────────────────┴────────┴──────────┘
```

### Execution Facade (`/execution/*`)
```
Total: 15 endpoints | Tested: 5 | Coverage: 33%
┌─────────────────────────┬────────┬──────────┐
│ Category                │ Tested │ Coverage │
├─────────────────────────┼────────┼──────────┤
│ Agent Execution         │ 2/4    │ 50% 🟡   │
│ Workflow Execution      │ 2/6    │ 33% 🟡   │
│ History & Monitoring    │ 0/4    │ 0% 🔴    │
│ Status                  │ 1/1    │ 100% ✅  │
└─────────────────────────┴────────┴──────────┘
```

### System Management (`/system/*`)
```
Total: 11 endpoints | Tested: 0 | Coverage: 0%
┌─────────────────────────┬────────┬──────────┐
│ Category                │ Tested │ Coverage │
├─────────────────────────┼────────┼──────────┤
│ System Info             │ 0/4    │ 0% 🔴    │
│ Environment             │ 0/4    │ 0% 🔴    │
│ Monitoring              │ 0/3    │ 0% 🔴    │
└─────────────────────────┴────────┴──────────┘
```

## Test Implementation Roadmap

### Phase 1: Critical Gaps (Week 1)
- [ ] System health endpoints (`/system/health`, `/system/info`)
- [ ] Config file operations (`/config/files/*`)
- [ ] Execution history (`/execution/history/*`)

### Phase 2: Core Features (Week 2)
- [ ] Project management (`/config/projects/*`)
- [ ] Server status (`/tools/servers/*`)
- [ ] Agent/workflow testing endpoints

### Phase 3: Complete Coverage (Week 3)
- [ ] Environment management
- [ ] Monitoring endpoints
- [ ] Error scenarios for all endpoints

### Phase 4: Advanced Testing (Week 4)
- [ ] SSE streaming tests
- [ ] Performance benchmarks
- [ ] Integration test suites

## Quick Reference: Missing Critical Tests

### 🚨 High Priority (Security & Stability)
1. `/system/health` - No health monitoring
2. `/config/files/*` - No file operation tests
3. `/execution/history/*` - No session management tests
4. Authentication failures - No API key tests

### ⚠️ Medium Priority (Functionality)
1. `/tools/servers/*` - No server status tests
2. `/config/projects/*` - No project management tests
3. Error handling - Limited error scenario coverage

### 📝 Low Priority (Nice to Have)
1. SSE endpoints - Streaming not tested
2. Pagination - No limit/offset tests
3. Edge cases - Special characters, limits

## Test Artifacts Location

```
tests/
├── e2e/
│   └── api/
│       ├── config_manager_routes.json ✅
│       ├── mcp_host_routes.json ✅
│       ├── facade_routes.json ✅
│       ├── main_api.json ✅
│       └── system_routes.json ❌ (TO CREATE)
│
├── integration/
│   └── test-integration.ts ✅
│
└── unit/
    └── client/
        ├── ConfigManagerClient.test.ts ✅
        ├── ExecutionFacadeClient.test.ts ✅
        ├── MCPHostClient.test.ts ✅
        └── SystemClient.test.ts ❌ (TO CREATE)
```

## Related Documents
- [Detailed Test Coverage](./api_test_coverage.md)
- [API Reference](../usage/api_reference.md)
- [Testing README](../../frontend/tests/README.md)
