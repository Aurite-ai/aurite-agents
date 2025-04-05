# Overarching Development Plan

This document outlines the high-level plan for reviewing and improving the `aurite-mcp` codebase. Detailed plans for each phase will be created separately.

## Phase 1: FastAPI Server (`src/main.py`) Review and Testing

*   **Goal:** Ensure the main FastAPI server is functional, robust, and testable.
*   **Steps:**
    1.  Review `src/main.py` and related dependencies to understand current functionality and identify potential issues.
    2.  Develop a detailed plan (`docs/plans/main_server_plan.md`) for fixes, improvements (simplification, readability, flexibility), and testing.
    3.  Implement the plan, including creating a Postman/Newman collection for endpoint testing.
    4.  Verify functionality through testing.

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
