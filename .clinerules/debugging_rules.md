# Aurite Framework: Debugging Rules

**Document Type:** Task-Specific Rules
**When to Use:** When diagnosing and fixing bugs, errors, or unexpected behavior. Read this document *after* `development_rules.md`.

## 1. Overview

This document provides strategies and a template for debugging issues in the Aurite Framework. The primary goal of debugging is to **isolate the problem** before attempting a fix. A thorough, methodical approach is often faster than making assumptions.

## 2. Core Debugging Strategies

### 2.1 Isolate the Problem
Before writing any fix, you must isolate the root cause. Use the following techniques, often in combination. Remember that taking the time to do this thoroughly is the fastest path to a correct solution.

*   **Add Logging:** Insert temporary logging statements (`print()`, `logging.debug()`) in the suspected code paths to trace execution flow and inspect variable states.
*   **Write Simple Test Scripts:** Create small, standalone Python scripts (`scripts/debug_*.py`) that import the problematic component and reproduce the error with minimal code. This is highly effective for isolating issues.
*   **Use `python -c`:** For very simple checks, use the terminal to execute a single line of Python code to test a specific function or interaction without creating a file.
    *   `python -c "from my_module import my_func; print(my_func('test'))"`

### 2.2 Investigate External Packages
Do not assume how external packages (e.g., `litellm`, `fastapi`) work. Review their code directly.

1.  **Find the Package:** Use `pip show [package_name]` to find its location in the virtual environment.
2.  **Explore the Code:** Use the `list_files` tool on the location from `pip show` to see the package's file structure.
3.  **Read the Source:** Use `read_file` to examine the relevant source code within the package to understand its logic.

### 2.3 Reproduce with a Failing Test
The most reliable way to confirm a bug and validate a fix is to write a test that fails because of the bug, and then passes once the fix is applied.

## 3. Implementation Plan Template

```markdown
# Implementation Plan: [Bug Fix Description]

**Type:** Bug Fix
**Date:** YYYY-MM-DD
**Author:** [User's Name or blank]
**Issue:** [Link to issue/bug report if applicable]

## Goal
[What bug will be fixed? What behavior will be corrected?]

## Context
[How was the bug discovered? What is the impact?]

## Root Cause Analysis
- **Expected Behavior:** [What should happen]
- **Actual Behavior:** [What is happening]
- **Root Cause:** [Why it's happening, based on the isolation steps]
- **Affected Components:** [List affected files/methods]

## Implementation Steps

[Organize your fix into logical phases. Start with reproducing the bug, then fix, then verify.]

### Phase 1: Reproduce and Test
1.  **Action:** Add a failing test that reproduces the bug in `tests/`.
2.  **Verification:** Run the new test and confirm that it fails as expected.

### Phase 2: Implement Fix
3.  **Action:** Apply the code change to fix the bug in `src/`.
4.  **Verification:** Run the failing test from Phase 1 and confirm it now passes.

### Phase 3: Verify No Regression
5.  **Action:** Run all related tests for the affected component(s).
6.  **Verification:** Confirm that all tests pass and no new issues were introduced.
7.  **Action:** Remove any temporary debugging code (e.g., logging statements).

## Testing Strategy
See `tests/README.md` for testing guidelines and structure.

## Documentation Updates
See `.clinerules/documentation_guide.md` for documentation update requirements.

## Changelog
- v1.0 (YYYY-MM-DD): Initial plan
