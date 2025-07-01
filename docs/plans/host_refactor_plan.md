# Implementation Plan: MCPHost Client Resolution Refactoring

**Version:** 1.0
**Date:** 2025-07-01
**Author(s):** Gemini, Ryan

## 1. Goals
*   To refactor the `MCPHost` class in `src/aurite/host/host.py` to eliminate duplicated code.
*   To centralize the logic for client discovery, filtering, and resolution into a single private helper method.
*   To improve the maintainability and readability of the `get_prompt`, `execute_tool`, and `read_resource` methods.

## 2. Scope
*   **In Scope:**
    *   The file `src/aurite/host/host.py`.
    *   Creation of one new private method: `_resolve_target_client_for_component`.
    *   Modification of three existing public methods: `get_prompt`, `execute_tool`, `read_resource`.
    *   Adding a `Literal` import from `typing`.
*   **Out of Scope:**
    *   Any changes to other files, including `FilteringManager` or any of the resource managers (`ToolManager`, etc.).
    *   Changes to the testing suite (this will be handled separately after the implementation is approved and complete).

## 3. Implementation Steps

### Step 1: Add the `_resolve_target_client_for_component` Method

*   **File(s):** `src/aurite/host/host.py`
*   **Action:**
    *   Add a new private method `_resolve_target_client_for_component` to the `MCPHost` class.
    *   The method will accept `component_name`, `component_type`, `client_name`, and `agent_config` as arguments.
    *   It will contain the combined logic for discovering, filtering, and resolving a single target client ID, raising `ValueError` for failures (e.g., not found, ambiguous, disallowed).
*   **Verification:**
    *   The method signature and logic match the previously discussed proposal.

### Step 2: Refactor the `execute_tool` Method

*   **File(s):** `src/aurite/host/host.py`
*   **Action:**
    *   Replace the entire body of the `execute_tool` method with two lines:
        1.  A call to `await self._resolve_target_client_for_component(...)` with `component_type="tool"` to get the `target_client_id`.
        2.  A call to `await self.tools.execute_tool(...)`, passing the resolved `target_client_id`.
*   **Verification:**
    *   The method is significantly simplified and correctly uses the new helper method.

### Step 3: Refactor the `get_prompt` Method

*   **File(s):** `src/aurite/host/host.py`
*   **Action:**
    *   Replace the entire body of the `get_prompt` method.
    *   The new body will call `await self._resolve_target_client_for_component(...)` with `component_type="prompt"` to get the `target_client_id`.
    *   It will then call `await self.prompts.get_prompt(...)` with the resolved `target_client_id`.
*   **Verification:**
    *   The method is significantly simplified and correctly uses the new helper method.

### Step 4: Refactor the `read_resource` Method

*   **File(s):** `src/aurite/host/host.py`
*   **Action:**
    *   Replace the entire body of the `read_resource` method.
    *   The new body will call `await self._resolve_target_client_for_component(...)` with `component_type="resource"` to get the `target_client_id`.
    *   It will then call `await self.resources.get_resource(...)` with the resolved `target_client_id`.
*   **Verification:**
    *   The method is significantly simplified and correctly uses the new helper method.

### Step 5: Add Required Import

*   **File(s):** `src/aurite/host/host.py`
*   **Action:**
    *   Add `Literal` to the `typing` import statement at the top of the file to support the `component_type` argument in the new helper method.
*   **Verification:**
    *   The import is present and correct.

## 4. Testing Strategy
*   **Unit Tests:** After the refactoring is complete, existing unit tests for `MCPHost` must be run to ensure no regressions have been introduced. The tests for `execute_tool`, `get_prompt`, and `read_resource` should be reviewed to ensure they still provide adequate coverage for success, ambiguity, and failure cases.
*   **Manual Verification:** No manual verification is required for this refactoring task beyond the successful execution of the test suite.
