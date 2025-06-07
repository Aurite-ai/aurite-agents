# Aurite Agents - Testing Guide

This document provides an overview of the testing philosophy, structure, and procedures for the Aurite Agents framework. It is intended for developers who are contributing to the project and need to run existing tests or write new ones.

## 1. Testing Philosophy

Our testing strategy is built on `pytest` and follows the layered architecture of the framework. The goal is to have a mix of unit and integration tests that ensure the correctness of individual components and their interactions within and across layers.

-   **Unit Tests:** Focused on a single class or function, mocking its dependencies to ensure isolation.
-   **Integration Tests:** Focused on the interaction between multiple components, often within the same architectural layer or between adjacent layers.

## 2. Running Tests

You can run tests using the `pytest` command from the root of the repository.

### Running All Tests

To run the entire test suite:

```bash
pytest
```

### Running Tests by Layer

Tests are organized by architectural layer and can be run using custom `pytest` markers. This is the most common way to run tests during development.

-   **Run API (Layer 1) Tests:**
    ```bash
    pytest -m api_integration
    ```
-   **Run Orchestration (Layer 2) Tests:**
    ```bash
    pytest -m orchestration
    ```
-   **Run Host (Layer 3) Tests:**
    ```bash
    pytest -m host
    ```

### Running Specific Tests

You can also run a specific file, class, or test function.

-   **Run a specific file:**
    ```bash
    pytest tests/host/test_host_lifecycle.py
    ```
-   **Run a specific test function:**
    ```bash
    pytest tests/host/test_host_lifecycle.py::test_host_initialization_error
    ```

## 3. Test Directory Structure

The `tests/` directory mirrors the layered structure of the `src/aurite/` directory to make it easy to locate relevant tests.

```
tests/
├── api/              # Layer 1: Entrypoints (FastAPI)
├── host/             # Layer 3: MCP Host System
├── orchestration/    # Layer 2: Orchestration
├── config/           # Tests for configuration loading
├── fixtures/         # Shared pytest fixtures (test data, setup objects)
├── mocks/            # Mock objects to simulate dependencies
└── conftest.py       # Global test configurations and hooks
```

-   `tests/api/`: Contains integration tests for the FastAPI entrypoint.
-   `tests/host/`: Contains unit and integration tests for the `MCPHost` and its managers.
-   `tests/orchestration/`: Contains unit and integration tests for the `HostManager`, `ExecutionFacade`, and component executors.
-   `tests/fixtures/`: Provides reusable data and configured object instances for tests.
-   `tests/mocks/`: Provides mock implementations of classes to isolate components for unit tests.

## 4. Fixtures and Configuration

`pytest` fixtures are used extensively to provide configured objects, mocks, and helper functions to tests.

#### **Global Configuration (`tests/conftest.py`)**

This file defines global settings for the test suite:
-   Registers custom markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.api_integration`, `@pytest.mark.orchestration`, `@pytest.mark.host`.
-   Configures `anyio` to use the `asyncio` backend for all asynchronous tests.

#### **Core Integration Fixture: `host_manager`**

-   **File:** `tests/fixtures/host_fixtures.py`
-   **Purpose:** This is the most important fixture for integration testing. It provides a fully initialized `Aurite` instance, which includes a running `MCPHost` connected to dummy MCP servers. It handles the complete setup and teardown of the core framework stack.
-   **Usage:** Any integration test that needs to interact with a realistic, running instance of the framework should use this fixture.

#### **API Testing Fixtures (`tests/api/conftest.py`)**

-   `api_client`: Provides a `fastapi.testclient.TestClient` instance for making synchronous HTTP requests to the API in tests.
-   `async_api_client`: Provides an `httpx.AsyncClient` for making asynchronous requests, necessary for features like Server-Sent Events (SSE).

#### **Host Layer Mocks (`tests/host/conftest.py`)**

This file provides mocked versions of the Host foundation managers (`MessageRouter`, `FilteringManager`, `RootManager`) to allow for isolated unit testing of the resource managers (`ToolManager`, etc.).

## 5. Testing by Layer

### Layer 1: Entrypoints (`tests/api/`)

-   **Approach:** Testing for this layer focuses exclusively on integration tests for the FastAPI application.
-   **Tools:** `pytest` and `fastapi.testclient.TestClient`.
-   **Scope:** These tests validate API endpoint signatures, request/response models, status codes, and error handling. They ensure that the API correctly interacts with the underlying Orchestration layer.
-   **Manual Testing:** The CLI (`src/bin/cli.py`) and Redis Worker (`src/bin/worker.py`) are not covered by automated tests and should be verified manually if changes are made.

### Layer 2: Orchestration (`tests/orchestration/`)

-   **Approach:** This layer uses a mix of unit and integration tests.
-   **Unit Tests:** Test individual components like `ExecutionFacade` or `SimpleWorkflowExecutor` in isolation by providing a mocked `MCPHost`.
-   **Integration Tests:** Use the `host_manager` fixture to test the end-to-end flow from the `ExecutionFacade` down through a real `MCPHost`, verifying the interaction between the Orchestration and Host layers.

### Layer 3: Host System (`tests/host/`)

-   **Approach:** This layer also uses a mix of unit and integration tests.
-   **Unit Tests:** Test individual managers (e.g., `ToolManager`, `FilteringManager`) by providing mocked dependencies.
-   **Integration Tests:** Use the `host_manager` fixture to test the full `MCPHost` lifecycle, including client connection, component discovery, and filtering logic against live (dummy) MCP servers.
