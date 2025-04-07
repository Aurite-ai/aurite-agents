# MCP Host System Refactor - Overarching Plan

**Version:** 1.1 *(Incremented version due to plan change)*
**Date:** 2025-04-06 *(Original date kept, or update if desired)*

## 1. Overview

This document outlines the high-level plan for refactoring the `aurite-mcp` Host system. The primary goal is to improve separation of concerns by making the `MCPHost` class a generic orchestrator for MCP servers and moving specific server integrations (storage, memory) and agent/workflow logic into dedicated components (Agents, Workflows).

This plan is based on the brainstorming session on 2025-04-06 and updated on [Current Date or Date of this change].

## 2. Implementation Phases and Steps

The refactoring will proceed in the following phases and sequential steps:

### Phase 1: Host Cleanup & Simplification [COMPLETED]

*   **Goal:** Simplify `MCPHost` to a generic MCP client orchestrator and verify core functionality.
*   **Detailed Plan:** `aurite-mcp/docs/plans/host_cleanup_plan.md` (or `phase1_implementation_plan.md` if that's the final name)

1.  **[COMPLETED] Remove Specific Server Logic from Host:**
    *   Removed direct integration of storage (`src/host/resources/storage.py`) from `MCPHost`.
    *   Removed direct integration of memory (`src/memory/mem0_server.py` references and `enable_memory` flag logic) from `MCPHost`.
    *   Updated `MCPHost` initialization and methods accordingly.

2.  **[COMPLETED] Remove Workflow Manager from Host:**
    *   Removed `WorkflowManager` (`src/host/agent/workflows.py`) integration from `MCPHost`.
    *   Decided to move `execute_prompt_with_tools` logic to `Agent` (Now Step 5).
    *   Updated `MCPHost` initialization and methods accordingly.

3.  **[COMPLETED] Refactor `main.py` and Test Core Host:**
    *   Updated `src/main.py` FastAPI application to reflect the removal of storage, memory, and workflow endpoints/logic tied directly to the host.
    *   Adapted existing Postman tests (`docs/testing/main_server.postman_collection.json`) and verified the core, simplified `MCPHost` functionality (`/health`, `/status`).

### Phase 2: MCP Server Management Enhancements [IN PROGRESS or COMPLETED]

*   **Goal:** Add features for more granular control over MCP server components and introduce routing capabilities.
*   **Detailed Plan:** `aurite-mcp/docs/plans/phase2_implementation_plan.md`

4.  **[COMPLETED] Implement Static MCP Component Exclusion:**
    *   Added an optional `exclude: Optional[List[str]] = None` field to the `ClientConfig` model (`src/host/models.py`).
    *   Modified `MCPHost` and relevant managers (`ToolManager`, `PromptManager`, `ResourceManager`) to filter out components (tools, prompts, resources) listed in the `exclude` list during registration.
    *   Added tests to verify exclusion (`tests/host/test_exclusion.py`).
    *(Add any other steps planned/completed for Phase 2 here)*

### Phase 3: Agent Implementation and Model Refinement

*   **Goals:**
    *   A. Implement the core `Agent` class abstraction, enabling modular agent logic separate from the `MCPHost`.
    *   B. Refine the shared Pydantic configuration models (`src/host/models.py`) to effectively support both Host and Agent configuration needs.
*   **Detailed Plan:** `aurite-mcp/docs/plans/phase3_implementation_plan.md` *(Link to the detailed technical plan to be created)*

5.  **Define and Implement Agent Abstraction:** *(High-level action)*
    *   Create the foundational `Agent` class structure within the `src/agents/` directory.
    *   Transfer the primary responsibility for orchestrating LLM calls and tool execution logic from `MCPHost` to the new `Agent` class, establishing clear separation of concerns.

6.  **Refine Configuration Models for Agent Support:** *(High-level action)*
    *   Analyze and refactor the Pydantic models (`RootConfig`, `ClientConfig`, `HostConfig`) located in `src/host/models.py`.
    *   Design and implement `AgentConfig` to allow flexible configuration of agent-specific settings (like LLM parameters) and **link it to a single `HostConfig` instance** which defines the available MCP clients. *(Updated description)*
    *   Ensure the model hierarchy provides a clear and logical structure for configuration management across the system.

7.  **Establish Basic Agent Functionality and Testing:** *(High-level outcome)*
    *   Implement the initial end-to-end flow for configuring an `Agent` and executing a simple task using the **linked `MCPHost`'s capabilities**. *(Updated phrasing)*
    *   Develop foundational tests to verify the core `Agent` functionality, including configuration loading and interaction with host components.

*(Add subsequent high-level steps for Phase 3 as needed)*

### Phase 4: Workflow Implementation and FastAPI Integration
*   **Goals:**
*   A. Build the new workflow abstraction on top of the new agent class, and the refactored host.
1.  **Create New Workflow Class:**
    *   Define a new `Workflow` class (`src/agents/workflow.py` - potentially refactoring the existing one significantly or creating anew).
    *   This class will define sequences or graphs of steps, potentially using `Agent` instances or directly calling tools via `MCPHost`.
    *   Refactor the concept of `WorkflowStep` if necessary.
    *   Test with a more comprehensive planning server example, demonstrating multi-step execution.

2.  **Integrate New Components into `main.py`:**
    *   Update `src/main.py` to expose functionality from the new `Agents`, and `Workflows`.
    *   Define new API endpoints as needed (e.g., `/routers/storage/execute`, `/agents/planning/execute`, `/workflows/plan_and_execute/start`).
    *   Update Postman collection or create new tests for these endpoints.
    *   *(Deferred: Implement dynamic routing based on `routing_weight` after core components are stable).*

Improve discovery system to work with client_ids
When to use server networking vs direct function calls?
Clean up and simplify. Make barebones examples in fixtures. Review tests
implement storage solutions to test agents and workflows