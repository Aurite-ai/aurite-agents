# Overarching Development Plan

This document outlines the high-level plan for reviewing and improving the `aurite-mcp` codebase. Detailed plans for each phase will be created separately.

## Phase 1: FastAPI Server (`src/main.py`) Review and Testing (Completed)

*   **Goal:** Ensure the main FastAPI server is functional, robust, and testable.
*   **Status:** Completed.
*   **Summary:**
    1.  Reviewed `src/main.py` and identified areas for improvement (config loading, security, dependencies, error handling). (Completed)
    2.  Developed a detailed plan in `docs/plans/main_server_plan.md`. (Completed)
    3.  Implemented the refactoring plan for `src/main.py`, including adding `ServerConfig`, dependencies, API key auth, feature flag for memory, and fixing startup issues. (Completed)
    4.  Verified core functionality (`/health`, `/status`, `/prepare_prompt`, `/execute_prompt`) using Newman tests defined in `docs/testing/main_server.postman_collection.json`. (Completed)
    5.  Documented Newman execution in `docs/testing_infrastructure.md`. (Completed)

## Phase 2: Host System (`src/host/`) Review

*   **Goal:** Evaluate the host system architecture for potential over-engineering and opportunities for simplification, improved flexibility, and readability.
*   **Steps:**
    1.  Review all files within `src/host/` and relevant documentation (`docs/host/`).
    2.  Develop a detailed plan for any proposed refactoring or simplification.
    3.  Implement agreed-upon changes.
    4.  Verify changes through existing or new tests.

## Phase 3: Base Workflow (`src/agents/base_*.py`) Review

*   **Goal:** Assess the base workflow components (`base_workflow.py`, `base_utils.py`, `base_models.py`) for potential over-engineering and opportunities for simplification and increased flexibility.
*   **Steps:**
    1.  Review the relevant base agent files and documentation (`docs/agents/`).
    2.  Develop a detailed plan for any proposed refactoring or simplification.
    3.  Implement agreed-upon changes.
    4.  Verify changes through existing or new tests.
