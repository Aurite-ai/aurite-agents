# Framework Overview

This document provides a detailed overview of the Aurite Agents framework architecture.

## Architecture

The framework follows a layered architecture:

```text
+-----------------------------------------------------------------+
| Layer 1: Entrypoints (src/bin)                                  |
| +--------------+   +----------------+   +---------------------+ |
| | CLI          |   | API Server     |   | Worker              | |
| | (cli.py)     |   | (api.py)       |   | (worker.py)         | |
| +--------------+   +----------------+   +---------------------+ |
|        |                 |                  |                   |
|        +-------+---------+--------+---------+                   |
|                v                  v                             |
+----------------|------------------|-----------------------------+
                 |                  |
                 v                  v
+----------------+------------------+-----------------------------+
| Layer 2: Orchestration                                          |
| +-------------------------------------------------------------+ |
| | Host Manager (host_manager.py)                              | |
| |-------------------------------------------------------------| |
| | Purpose:                                                    | |
| | - Load Host JSON Config                                     | |
| | - Init/Shutdown MCP Host & Storage Manager (optional)       | |
| | - Holds Agent/Workflow Configs                              | |
| | - Dynamic Registration & DB Sync (optional)                 | |
| | - Owns ExecutionFacade                                      | |
| +-------------------------------------------------------------+ |
|                       |                                         |
|                       v                                         |
+-----------------------+-----------------------------------------+
                        |
                        v
+-----------------------+-----------------------------------------+
| Layer 2.5: Execution Facade & Executors                         |
| +-------------------------------------------------------------+ |
| | ExecutionFacade (execution/facade.py)                       | |
| |-------------------------------------------------------------| |
| | Purpose: Unified interface (run_agent, run_simple_workflow, | |
| |          run_custom_workflow) for execution.                | |
| | Delegates to specific Executors.                            | |
| | Passes Storage Manager to Agent execution if available.     | |
| +-------------------------------------------------------------+ |
| | Agent (agents/agent.py) - Executes itself                   | |
| | SimpleWorkflowExecutor (workflows/simple_workflow.py)       | |
| | CustomWorkflowExecutor (workflows/custom_workflow.py)       | |
| +-------------------------------------------------------------+ |
|                       |                                         |
|                       v (Uses MCP Host & Storage Manager)       |
+-----------------------+-----------------------------------------+
                        |
                        v
+-----------------------+-----------------------------------------+
| Layer 3: Host Infrastructure (MCP Host System)                  |
| +-------------------------------------------------------------+ |
| | MCP Host (host.py)                                          | |
| |-------------------------------------------------------------| |
| | Purpose:                                                    | |
| | - Manage Client Connections                                 | |
| | - Handle Roots/Security                                     | |
| | - Register/Execute Tools, Prompts, Resources                | |
| | - Component Discovery/Filtering                             | |
| +-------------------------------------------------------------+ |
|                       |                                         |
|                       v                                         |
+-----------------------+-----------------------------------------+
                        |
                        v
+-----------------------+-----------------------------------------+
| Layer 4: External Capabilities                                  |
| +-------------------------------------------------------------+ |
| | MCP Servers (e.g., src/packaged_servers/, external)         | |
| |-------------------------------------------------------------| |
| | Purpose:                                                    | |
| | - Implement MCP Protocol                                    | |
| | - Provide Tools, Prompts, Resources                         | |
| | - Handle Discovery (ListTools, etc.)                        | |
| +-------------------------------------------------------------+ |
+-----------------------------------------------------------------+
```

*   **Layer 4: External Capabilities:** MCP Servers providing tools/prompts/resources.
*   **Layer 3: Host Infrastructure:** The `MCPHost` manages connections and low-level MCP interactions.
*   **Layer 2.5: Execution Facade & Executors:** The `ExecutionFacade` provides a unified interface for running components, delegating to specific executors (`Agent`, `SimpleWorkflowExecutor`, `CustomWorkflowExecutor`). It also passes the `StorageManager` instance (if available) to the `Agent` during execution.
*   **Layer 2: Orchestration:** The `HostManager` loads configuration, manages the `MCPHost` and optional `StorageManager` lifecycle, handles dynamic registration (syncing to DB if enabled), and owns the `ExecutionFacade`.
*   **Layer 1: Entrypoints:** API (now modularized into `src/bin/api/api.py` and `src/bin/api/routes/`), CLI, and Worker interfaces interact with the `HostManager` (and through it, the `ExecutionFacade`).
