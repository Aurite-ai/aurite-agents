# MCP Host System Refactor - Overarching Plan

**Version:** 1.0
**Date:** 2025-04-06

## 1. Overview

This document outlines the high-level plan for refactoring the `aurite-mcp` Host system. The primary goal is to improve separation of concerns by making the `MCPHost` class a generic orchestrator for MCP servers and moving specific server integrations (storage, memory) and agent/workflow logic into dedicated components (Routers, Agents, Workflows).

This plan is based on the brainstorming session on 2025-04-06.

## 2. Implementation Phases and Steps

The refactoring will proceed in the following phases and sequential steps:

### Phase 1: Host Cleanup & Simplification [COMPLETED]

*   **Goal:** Simplify `MCPHost` to a generic MCP client orchestrator and verify core functionality.
*   **Detailed Plan:** `aurite-mcp/docs/plans/host_cleanup_plan.md`

1.  **[COMPLETED] Remove Specific Server Logic from Host:**
    *   Removed direct integration of storage (`src/host/resources/storage.py`) from `MCPHost`.
    *   Removed direct integration of memory (`src/memory/mem0_server.py` references and `enable_memory` flag logic) from `MCPHost`.
    *   Updated `MCPHost` initialization and methods accordingly.

2.  **[COMPLETED] Remove Workflow Manager from Host:**
    *   Removed `WorkflowManager` (`src/host/agent/workflows.py`) integration from `MCPHost`.
    *   Decided to move `execute_prompt_with_tools` logic to `BaseAgent` (Step 6).
    *   Updated `MCPHost` initialization and methods accordingly.

3.  **[COMPLETED] Refactor `main.py` and Test Core Host:**
    *   Updated `src/main.py` FastAPI application to reflect the removal of storage, memory, and workflow endpoints/logic tied directly to the host.
    *   Adapted existing Postman tests (`docs/testing/main_server.postman_collection.json`) and verified the core, simplified `MCPHost` functionality (`/health`, `/status`).

### Phase 2: MCP Server Management Enhancements

*   **Goal:** Add features for more granular control over MCP server components and introduce routing capabilities.

4.  **Implement Static MCP Component Exclusion:**
    *   Add an optional `exclude: Optional[List[str]] = None` field to the `ClientConfig` model (`src/host/models.py`).
    *   Modify `MCPHost` or relevant managers (`ToolManager`, `PromptManager`, `ResourceManager`) to filter out components (tools, prompts, resources) listed in the `exclude` list during discovery or listing operations (e.g., `list_tools`, `list_prompts`, `list_resources`). Ensure excluded components are not available for execution.

5.  **Create Base Router Class:**
    *   Define a new `BaseRouter` class (`src/routers/base_router.py`).
    *   This class should utilize an `MCPHost` instance to interact with specific MCP servers based on its configuration.
    *   Implement a concrete `StorageRouter` as a first example, encapsulating logic for interacting with different storage MCP servers (e.g., SQL, vector DB). It will manage the `ClientConfig` for these servers.
    *   Write tests for `StorageRouter` to ensure it correctly initializes the host and routes requests to the appropriate storage server.

### Phase 3: Agent and Workflow Implementation

*   **Goal:** Build the new agent and workflow abstractions on top of the refactored host and routers.

6.  **Create Base Agent Class:**
    *   Define a new `BaseAgent` class (`src/agents/base_agent.py`).
    *   This class will handle the core LLM interaction loop, incorporating the `execute_prompt_with_tools` logic (moved from `MCPHost`).
    *   It should be able to use `MCPHost` directly or via `Routers` to access tools/prompts/resources.
    *   Test the `BaseAgent` with a simple planning MCP server (like the existing `planning_server.py` or a simplified version) to verify tool use and prompt execution.

7.  **Create Base Workflow Class:**
    *   Define a new `BaseWorkflow` class (`src/agents/base_workflow.py` - potentially refactoring the existing one significantly or creating anew).
    *   This class will define sequences or graphs of steps, potentially using `BaseAgent` instances or directly calling tools via `MCPHost`/`Routers`.
    *   Refactor the concept of `WorkflowStep` if necessary.
    *   Test with a more comprehensive planning server example, demonstrating multi-step execution.

8.  **Integrate New Components into `main.py`:**
    *   Update `src/main.py` to expose functionality from the new `Routers`, `Agents`, and `Workflows`.
    *   Define new API endpoints as needed (e.g., `/routers/storage/execute`, `/agents/planning/execute`, `/workflows/plan_and_execute/start`).
    *   Update Postman collection or create new tests for these endpoints.
    *   *(Deferred: Implement dynamic routing based on `routing_weight` after core components are stable).*