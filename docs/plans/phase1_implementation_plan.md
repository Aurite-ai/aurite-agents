# MCP Host Cleanup - Technical Plan (Phase 1)

**Version:** 1.0
**Date:** 2025-04-06
**Related Plan:** `overarching_host_refactor_plan.md`

## 1. Overview

This document details the technical implementation steps for Phase 1 (Steps 1-3) of the MCP Host refactor. The goal of this phase is to remove specific server integrations (Storage, Memory) and the Workflow Manager from the core `MCPHost` class and `main.py`, simplifying the host to a generic MCP client orchestrator, and ensuring the basic server still runs.

## 2. Technical Implementation Steps

### Step 1: [COMPLETED] Remove Specific Server Logic from Host (`src/host/host.py`, `src/host/models.py`)

*   **Objective:** Remove direct dependencies and logic related to `StorageManager` and the `mem0` memory server from `MCPHost`.
*   **File:** `aurite-mcp/src/host/host.py`
    *   **Imports:** Remove `from .resources import StorageManager`.
    *   **`__init__`:**
        *   Remove `self._storage_manager = StorageManager()`.
        *   Remove `self.storage = self._storage_manager` property assignment.
        *   Remove the definition of `self._memory_config`.
    *   **`initialize`:**
        *   Remove the call `await self._storage_manager.initialize()`.
        *   Remove the conditional block checking `self._config.enable_memory` and the call to `self._initialize_client(self._memory_config)` within it.
        *   Remove the storage-specific permission registration block:
            ```python
            # Register permissions based on capabilities
            if "storage" in client_config.capabilities:
                await self._security_manager.register_server_permissions(...)
                # Remove the following line specifically:
                # await self._storage_manager.register_server_permissions(...)
            ```
            *(Note: Security manager permissions might be revisited later if needed for routers)*.
    *   **Methods:**
        *   Remove the entire `add_memories` method.
        *   Remove the entire `search_memories` method.
    *   **`shutdown`:**
        *   Remove the call `await self._storage_manager.shutdown()`.
*   **File:** `aurite-mcp/src/host/models.py`
    *   **`HostConfig` Model:** Remove the `enable_memory: bool = False` field.

### Step 2: [COMPLETED] Remove Workflow Manager & Prompt Execution Logic from Host (`src/host/host.py`)

*   **Objective:** Decouple `WorkflowManager` and related agent-level logic (`execute_prompt_with_tools`) from `MCPHost`.
*   **File:** `aurite-mcp/src/host/host.py`
    *   **Imports:** Remove `from .agent import WorkflowManager`.
    *   **`__init__`:**
        *   Remove `self._workflow_manager = WorkflowManager(host=self)`.
        *   Remove `self.workflows = self._workflow_manager` property assignment.
    *   **`initialize`:**
        *   Remove the call `await self._workflow_manager.initialize()`.
    *   **Methods:**
        *   Remove the entire `prepare_prompt_with_tools` method.
        *   Remove the entire `execute_prompt_with_tools` method. *(Decision: This logic will be reimplemented later within the `BaseAgent` class in Step 6)*.
        *   Remove the entire `register_workflow` method.
        *   Remove the entire `execute_workflow` method.
        *   Remove the entire `list_workflows` method.
        *   Remove the entire `get_workflow` method.
    *   **`shutdown`:**
        *   Remove the call `await self._workflow_manager.shutdown()`.

### Step 3: [COMPLETED] Refactor `main.py` and Test Core Host

*   **Objective:** Update the FastAPI application (`main.py`) to reflect the simplified `MCPHost` and verify basic server operation using the Postman collection.
*   **File:** `aurite-mcp/src/main.py`
    *   **Imports:**
        *   Remove `PreparePromptRequest`, `ExecutePromptRequest`, `ExecuteWorkflowRequest` Pydantic models.
    *   **`lifespan` function:**
        *   Remove the logic for reading `enable_memory_flag` from the host config JSON.
        *   Update the `HostConfig` instantiation to only pass `clients`: `host_pydantic_config = HostConfig(clients=client_configs)`.
    *   **Endpoints:**
        *   Remove the `/prepare_prompt` endpoint function `prepare_prompt`.
        *   Remove the `/execute_prompt` endpoint function `execute_prompt`.
        *   Remove the `/execute_workflow` endpoint function `execute_workflow`.
        *   Keep `/health` and `/status` endpoints.
*   **File:** `aurite-mcp/docs/testing/main_server.postman_collection.json`
    *   **Requests:**
        *   Remove the "Prepare Prompt" request item.
        *   Remove the "Execute Prompt" request item.
        *   *(Assumption: No workflow requests currently exist, but remove if any are found)*.
    *   **Testing:** Execute the remaining "Health Check" and "Get Status" requests against the running server after code changes to ensure they pass (Status 200 OK).

## 3. Next Steps

*   Phase 1 (Steps 1-3) is complete.
*   Proceed to Phase 2, starting with Step 4 (Implement Static MCP Component Exclusion) from the `overarching_host_refactor_plan.md`.
