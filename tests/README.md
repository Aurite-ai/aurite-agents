# 🔧 Aurite Agents Testing Guide

This document outlines the strategy, structure, and best practices for writing and running tests for the Aurite Agents framework. Adherence to these guidelines is crucial for maintaining a flexible, robust, and developer-friendly test suite.

## 1. Core Philosophy: Test Behavior, Not Implementation

The fundamental principle of our test suite is to **focus on *what* a component does (its public contract), not *how* it does it (its internal implementation).** This ensures our tests are resilient to refactoring and code changes that don't alter the component's public-facing behavior.

-   **Test Public APIs:** Tests should only interact with the public methods and functions of a component.
-   **Isolate the System Under Test (SUT):** Use mocks and test doubles to isolate the component being tested from its dependencies. A change in a dependency should not break the tests of the component that uses it.
-   **Assert on Outcomes:** Tests should verify the final result or outcome of an action, not the intermediate state of internal variables.

## 2. Test Structure

Our test suite is organized by both type and framework layer, following the "Test Pyramid" model.

```
tests/
├── unit/
│   ├── host/
│   └── orchestration/
├── integration/
│   ├── host/
│   └── orchestration/
├── e2e/
├── fixtures/
├── mocks/
└── README.md
```

-   **`unit/`:** For fast, isolated tests that verify a single class or function. All external dependencies MUST be mocked.
-   **`integration/`:** For tests that verify the interaction between a few, closely related components. Mocks should only be used for external services (like databases or LLM APIs) or components from other layers.
-   **`e2e/`:** For end-to-end tests that run through a full user workflow with minimal mocking, verifying the system as a whole.

## 3. Fixture & Mock Strategy: A Tiered, Bottom-Up Approach

Our strategy for fixtures and mocks prioritizes test clarity and isolation, promoting reuse only when a clear need arises.

1.  **Default to Local:** Begin by defining mocks and fixtures directly within the test file that needs them. This keeps tests self-contained and easy to understand.
2.  **Promote When Shared:** If you find yourself writing the same fixture setup in a second or third test file *within the same component's test directory* (e.g., `tests/unit/host/`), refactor it into that directory's `conftest.py`.
3.  **Default to `scope='function'`:** Always use the default function scope for fixtures unless the setup cost is prohibitively high. This guarantees test isolation.

## 4. How to Run Tests

Tests can be run from the root of the repository using `pytest`.

**Run all tests:**
```bash
pytest
```

**Run all tests for a specific layer (using markers):**
```bash
# Run all Host layer tests
pytest -m host

# Run all Orchestration layer tests
pytest -m orchestration
```

**Run all tests of a specific type:**
```bash
# Run all unit tests
pytest -m unit

# Run all integration tests
pytest -m integration
```

**Run a single test file:**
```bash
pytest tests/unit/host/test_tool_manager.py
