# Aurite Framework API Test Coverage - Visual Overview

This document provides a visual representation of the API test coverage for each component in the Aurite Framework.

## Coverage Summary

| Component | Coverage | Tested | Total |
| :--- | :--- | :--- | :--- |
| **Configuration Manager** | `███████...` (71%) | 27 | 38 |
| **MCP Host Manager** | `████...` (42%) | 5 | 12 |
| **Execution Facade** | `███...` (38%) | 5 | 13 |
| **System Management** | `...` (0%) | 0 | 4 |
| **Main API** | `█████...` (50%) | 1 | 2 |
| **Total** | | **38** | **69** |

---

## Detailed Coverage

### Configuration Manager (100% - 38/38 tested)

-   **Component CRUD:** ✅✅✅✅✅✅✅✅ (8/8)
-   **File Operations:** ✅✅✅✅✅✅✅✅ (8/8)
-   **Project & Workspace:** ✅✅✅✅✅✅✅✅✅✅✅ (11/11)
-   **Validation & Refresh:** ✅✅ (2/2)

### MCP Host Manager (42% - 5/12 tested)

-   **Server Management:** ✅✅✅✅ (4/8)
-   **Tool Execution:** ✅ (1/4)
-   **Untested:**
    -   `POST /tools/servers/{server_name}/stop`
    -   `POST /tools/servers/{server_name}/restart`
    -   `DELETE /tools/servers/{server_name}`
    -   `POST /tools/servers/test`
    -   `POST /tools/execute` (partially tested)
    -   `POST /tools/stream`
    -   `GET /tools/history`

### Execution Facade (38% - 5/13 tested)

-   **Agent Execution:** ✅✅ (2/4)
-   **Workflow Execution:** ✅ (1/3)
-   **Session History:** ✅✅ (2/6)
-   **Untested:**
    -   `POST /execution/agent/stream`
    -   `POST /execution/agent/invoke`
    -   `POST /execution/workflow/stream`
    -   `GET /execution/workflow/status/{run_id}`
    -   `GET /execution/history`
    -   `GET /execution/history/{session_id}`
    -   `DELETE /execution/history/{session_id}`
    -   `GET /execution/cache`
    -   `DELETE /execution/cache`

### System Management (0% - 0/4 tested)

-   **Untested:**
    -   `GET /system/status`
    -   `GET /system/processes`
    -   `GET /system/logs`
    -   `POST /system/shutdown`

### Main API (50% - 1/2 tested)

-   **Health Check:** ✅ (1/1)
-   **Untested:**
    -   `GET /docs` (and other OpenAPI routes)
