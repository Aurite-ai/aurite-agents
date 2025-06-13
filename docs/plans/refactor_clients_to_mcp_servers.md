# Implementation Plan: Refactor "clients" to "mcp_servers"

**Version:** 1.0
**Date:** 2025-06-06
**Author(s):** Ryan, Gemini
**Related Design Document (Optional):** N/A

## 1. Goals
*   Refactor user-facing configuration fields for improved clarity and intuitiveness.
*   Introduce `mcp_servers` as an alias for `clients` in `ProjectConfig`.
*   Introduce `name` as an alias for `client_id` in `ClientConfig`.
*   Introduce `mcp_servers` as an alias for `client_ids` in `AgentConfig`.
*   Ensure 100% backward compatibility for all existing configuration files.
*   Isolate the aliasing and backward-compatibility logic entirely within the Pydantic model layer (`src/aurite/config/config_models.py`).

## 2. Scope
*   **In Scope:**
    *   Modification of `src/aurite/config/config_models.py`.
*   **Out of Scope:**
    *   Changes to `src/aurite/config/component_manager.py`.
    *   Changes to `src/aurite/config/project_manager.py`.
    *   Changes to `src/aurite/host_manager.py`.
    *   Changes to any internal application logic that consumes the validated configuration models.

## 3. Implementation Steps

The entire implementation will be focused on a single file, using Pydantic validators to handle the aliasing and merging gracefully.

**File to Modify:** `src/aurite/config/config_models.py`

1.  **Step 1.1: Update `ClientConfig` to support `name` as an alias for `client_id`**
    *   **Action:**
        *   In the `ClientConfig` model, add a new optional field: `name: Optional[str] = None`.
        *   Modify the existing `client_id` field to be optional initially: `client_id: Optional[str] = None`.
        *   Add a `root_validator` with `pre=True`. This validator will perform the following logic on the raw dictionary before standard validation:
            1.  Get the values of `name` and `client_id` from the input data.
            2.  If `name` is provided, set `client_id` to its value. This makes `name` the preferred alias.
            3.  If `name` and `client_id` are both provided and differ, log a warning that `name` is being used.
            4.  If after this aliasing, `client_id` is still `None`, raise a `ValueError` because an identifier is required.
        *   Change the `client_id` field back to a required field (`client_id: str`) so that after the `pre=True` validator runs, the model guarantees its presence for the rest of the application.

2.  **Step 1.2: Update `ProjectConfig` to support `mcp_servers` as an alias for `clients`**
    *   **Action:**
        *   In the `ProjectConfig` model, add a new optional field: `mcp_servers: Optional[Dict[str, ClientConfig]] = Field(default_factory=dict)`.
        *   Add a `root_validator` with `pre=True`. This validator will:
            1.  Check if `mcp_servers` exists in the raw input data and is a dictionary.
            2.  If so, it will merge the contents of the `mcp_servers` dictionary into the `clients` dictionary.
            3.  If a key exists in both, the value from `mcp_servers` will overwrite the one from `clients`, and a warning will be logged.
            4.  This ensures that projects can be defined using `clients`, `mcp_servers`, or both, and they will be correctly consolidated into the internal `clients` field.

3.  **Step 1.3: Update `AgentConfig` to support `mcp_servers` as an alias for `client_ids`**
    *   **Action:**
        *   In the `AgentConfig` model, add a new optional field: `mcp_servers: Optional[List[str]] = None`.
        *   Add a `root_validator` with `pre=True`. This validator will:
            1.  Initialize `client_ids` to an empty list if it's not present.
            2.  Check if `mcp_servers` exists in the raw input data and is a list.
            3.  If so, it will extend the `client_ids` list with the items from `mcp_servers`.
            4.  This allows an agent's tool access to be defined using `client_ids`, the new `mcp_servers` field, or both.

## 4. Testing Strategy
*   **Unit Tests:** After implementation, we will need to create a new test file `tests/config/test_config_model_aliases.py` to verify the new aliasing and backward-compatibility logic.
    *   **Test `ClientConfig`:**
        *   Test that a config with only `name` passes validation and `client_id` is correctly populated.
        *   Test that a config with only `client_id` passes validation.
        *   Test that a config with both (matching and differing) works as expected.
        *   Test that a config with neither `name` nor `client_id` raises a `ValueError`.
    *   **Test `ProjectConfig`:**
        *   Test that a project with only `mcp_servers` populates the `clients` field correctly.
        *   Test that a project with only `clients` works as before.
        *   Test that a project with both `clients` and `mcp_servers` correctly merges them.
    *   **Test `AgentConfig`:**
        *   Test that an agent with only `mcp_servers` populates `client_ids` correctly.
        *   Test that an agent with only `client_ids` works as before.
        *   Test that an agent with both correctly merges them into `client_ids`.
*   **Integration Tests:** No new integration tests are required, as the existing test suite, which relies on the configuration system, will serve as a regression test. If all existing tests pass after the changes, it confirms that the backward compatibility was implemented successfully and the rest of the application is unaffected.
