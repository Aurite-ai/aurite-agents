# MCP Server Management Enhancements - Technical Plan (Phase 2)

**Version:** 1.0
**Date:** 2025-04-06
**Related Plan:** `overarching_host_refactor_plan.md`

## 1. Overview

This document details the technical implementation steps for Phase 2 (Steps 4-5) of the MCP Host refactor. This plan focuses on Step 4: Implementing static exclusion of MCP components (prompts, resources, tools) based on a configuration list.

## 2. Technical Implementation Steps

### Step 4: [COMPLETED] Implement Static MCP Component Exclusion

*   **Objective:** Allow specific MCP prompts, resources, and tools to be excluded from the host's available components based on a list of their names provided in the client configuration.
*   **Rationale:** Filtering logic will be implemented within the respective managers (`PromptManager`, `ResourceManager`, `ToolManager`) to maintain separation of concerns.

*   **4.1. [COMPLETED] Update `ClientConfig` Model:**
    *   **File:** `aurite-mcp/src/host/models.py`
    *   **Action:** Added an optional `exclude` field (list of strings) to the `ClientConfig` Pydantic model.

*   **4.2. [COMPLETED] Implement Filtering Logic in Managers:**
    *   **File:** `aurite-mcp/src/host/host.py` (`_initialize_client` method)
        *   **Action:** Pass the `config.exclude` list from the `ClientConfig` to the `register_client_prompts`, `register_client_resources`, and `register_tool` methods of the corresponding managers when they are called during client initialization.
    *   **File:** `aurite-mcp/src/host/resources/prompts.py` (`PromptManager`)
        *   **Action:** Modify `register_client_prompts` to accept the optional `exclude_list`. Filter out prompts where `prompt.name` is present in the `exclude_list` before registration. Add debug logging for excluded prompts.
    *   **File:** `aurite-mcp/src/host/resources/resources.py` (`ResourceManager`)
        *   **Action:** Modify `register_client_resources` to accept the optional `exclude_list`. Filter out resources where `resource.name` is present in the `exclude_list` before registration. Add debug logging for excluded resources.
    *   **File:** `aurite-mcp/src/host/resources/tools.py` (`ToolManager`)
        *   **Action:** Modified `register_tool` to accept the optional `exclude_list`. Check if `tool_name` is present in the `exclude_list` at the beginning of the method and return early if it is. Add debug logging for excluded tools. Removed redundant registration loop from `discover_client_tools` to ensure exclusions are applied correctly by the host.

*   **4.3. [COMPLETED] Add/Update Tests:**
    *   **Objective:** Verify that excluded components are correctly filtered and inaccessible.
    *   **Location:** `aurite-mcp/tests/host/test_exclusion.py`.
    *   **Actions:**
        *   Create test configurations including `exclude` lists.
        *   Assert that listing functions (`list_prompts`, `list_resources`, `list_tools`) do not return excluded items.
        *   Assert that attempts to access or execute excluded items raise appropriate "Not Found" errors.
