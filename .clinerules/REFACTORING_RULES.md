# Aurite Framework: Refactoring Rules

**Document Type:** Task-Specific Rules
**When to Use:** When improving existing code structure, readability, or performance without changing functionality. Read this document *after* `development_rules.md`.

## 1. Overview

This document provides specific best practices and the implementation plan template for refactoring efforts in the Aurite Framework. It ensures improvements maintain existing functionality while enhancing code quality.

## 2. Core Refactoring Principles

- **DRY (Don't Repeat Yourself):** Eliminate redundant code by abstracting common patterns into reusable functions or classes.
- **SRP (Single Responsibility Principle):** Ensure that every module, class, or function has one single, well-defined responsibility.
- **Readability:** Write code that is intuitive and easy for other developers to understand.
- **Simplicity:** Favor simple, straightforward solutions over complex ones.
- **Maintainability:** Structure code to be easily modified and extended in the future.

## 3. Refactoring Best Practices

- **Test First:** Ensure all existing tests pass before starting any refactoring. Your first step should be running the test suite.
- **Incremental Changes:** Make small, verifiable changes rather than large, monolithic rewrites. Each commit should represent a single, logical refactoring step.
- **Preserve Behavior:** The external-facing behavior and interfaces of the component must remain unchanged. Refactoring should not introduce or remove functionality.
- **Document Rationale:** Clearly explain *why* the refactoring improves the codebase in your plan and commit messages (e.g., "improves readability by...", "reduces complexity by...").
- **Clean Up:** After refactoring, remove any deprecated code, fix comments and docstrings to reflect the new structure, and ensure no linting errors are introduced.

## 4. Implementation Plan Template

```markdown
# Implementation Plan: [Refactoring Name]

**Type:** Refactoring
**Date:** YYYY-MM-DD
**Author:** [User's Name or blank]
**Design Doc:** [Link if applicable]

## Goal
[What code quality improvements will this achieve? (e.g., improve performance, reduce complexity, increase readability)]

## Context
[Why is this refactoring needed? What specific problems or code smells does it solve?]

## Current State Analysis
- **Code Smells:** [List specific issues with the current implementation (e.g., long method, duplicated code, tight coupling)]
- **Affected Files:** [List all files that will be modified]
- **Dependencies:** [List components that depend on the code being refactored and may need to be checked]

## Implementation Steps

[Organize your refactoring into logical phases. Each phase must result in a working state with all tests passing.]

### Phase 1: [Descriptive Phase Name, e.g., Initial Setup]
1.  **Action:** Run all relevant tests to establish a baseline. All tests must pass.
    *   **Verification:** Confirm test suite passes.
2.  **Action:** [First small refactoring step, e.g., Extract method `X` from class `Y` in `file.py`]
    *   **Verification:** Run tests again to ensure no behavior has changed.

### Phase 2: [Descriptive Phase Name, e.g., Core Refactoring]
3.  **Action:** [Next refactoring step]
    *   **Verification:** Run tests.
4.  **Action:** [Another refactoring step]
    *   **Verification:** Run tests.

[Continue with additional phases as needed]

## Risk Mitigation
- [ ] All existing tests pass before starting.
- [ ] Each phase maintains backward compatibility.
- [ ] Performance benchmarks remain stable (if applicable).

## Testing Strategy
See `tests/README.md` for testing guidelines and structure. The primary goal is to ensure no regressions are introduced.

## Documentation Updates
See `.clinerules/documentation_guide.md` for documentation update requirements. Focus on updating code comments and docstrings to reflect the new structure.

## Changelog
- v1.0 (YYYY-MM-DD): Initial plan
