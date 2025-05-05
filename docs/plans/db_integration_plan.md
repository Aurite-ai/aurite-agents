# Database Integration Implementation Plan

**Version:** 1.1
**Date:** 2025-05-05
**Status:** In Progress
**Related Design Doc:** `docs/storage/db_design.md`

## 1. Goal

Implement optional database persistence (using PostgreSQL) for agent/workflow configurations and agent conversation history, controlled by an environment variable flag (`AURITE_ENABLE_DB`).

## 2. Implementation Steps

**Phase 1: Setup & Storage Layer Implementation** (Steps 1-6 COMPLETE)

1.  **Add Dependencies:** **COMPLETE**
    *   Modified `pyproject.toml` to include `alembic`. (`sqlalchemy` and `psycopg2-binary` already present).
    *   Dependencies installed via `pip install -e .[dev]`.
2.  **Create Storage Directory Structure:** **COMPLETE**
    *   Created `src/storage/`.
    *   Created empty files: `__init__.py`, `db_connection.py`, `db_models.py`, `db_manager.py`.
3.  **Define Environment Variables:** **COMPLETE**
    *   Added `AURITE_ENABLE_DB`, `AURITE_DB_HOST`, `AURITE_DB_PORT`, `AURITE_DB_USER`, `AURITE_DB_PASSWORD`, `AURITE_DB_NAME` to `.env.example`.
    *   Variables added to local `.env`.
4.  **Implement DB Connection (`src/storage/db_connection.py`):** **COMPLETE**
    *   Implemented `get_database_url`, `get_engine`, `get_session_factory`, `get_db_session`.
5.  **Implement DB Models (`src/storage/db_models.py`):** **COMPLETE**
    *   Defined `Base` and models: `AgentConfigDB`, `WorkflowConfigDB`, `CustomWorkflowConfigDB`, `AgentHistoryDB`. Used `JSONB` for JSON fields.
6.  **Implement Storage Manager (`src/storage/db_manager.py`):** **COMPLETE** (Initial implementation, history methods pending DB fix)
    *   Created `StorageManager` class.
    *   Implemented `__init__`, `init_db`.
    *   Implemented config sync methods: `_sync_config`, `sync_agent_config`, `sync_workflow_config`, `sync_custom_workflow_config`, `sync_all_configs`.
    *   Implemented history methods: `load_history`, `save_full_history` (with DB logic).

**Phase 2: Integration with Core Framework** (Steps 7-9 COMPLETE)

7.  **Integrate `StorageManager` into `HostManager` (`src/host_manager.py`):** **COMPLETE**
    *   Added `storage_manager` attribute and instantiation logic based on `AURITE_ENABLE_DB`.
    *   Added calls to `init_db` and `sync_all_configs` in `initialize`.
    *   Added calls to `sync_*_config` in registration methods.
    *   Passed `storage_manager` to `ExecutionFacade`.
8.  **Update `ExecutionFacade` (`src/execution/facade.py`):** **COMPLETE**
    *   Modified `__init__` to accept and store `storage_manager`.
    *   Modified `_execute_component` to pass `storage_manager` to `Agent.execute_agent`.
9.  **Integrate History into `Agent` (`src/agents/agent.py`):** **COMPLETE**
    *   Modified `execute_agent` signature to accept `storage_manager`.
    *   Added history loading logic using `storage_manager.load_history`.
    *   Added history saving logic using `storage_manager.save_full_history`.
    *   Removed the `TODO` comment.

**Phase 3: Testing & Documentation** (Steps 10-12 PENDING)

10. **Refine DB Models & Unit Tests:**
    *   **Modify `src/storage/db_models.py`:** Change `JSONB` type to generic `sqlalchemy.JSON` to allow compatibility with SQLite for unit tests.
    *   **Run `tests/storage/test_db_manager.py`:** Execute the existing unit tests against the modified models using the in-memory SQLite setup provided by the `setup_test_db` fixture. Fix any issues arising from the type change or logic errors.
11. **Implement Integration Test Infrastructure:**
    *   **Create `tests/fixtures/db_fixtures.py`:** Define a new fixture (e.g., `integration_storage_manager`) with `scope="module"`. This fixture will connect to the *real* PostgreSQL test database using credentials from `.env`. It must handle `create_all` before yielding and `drop_all` after yielding to ensure a clean state between test module runs.
    *   **Create `tests/mocks/mock_db.py`:** Define a fixture `mock_storage_manager` that returns `MagicMock(spec=StorageManager)` for unit testing components that *use* the `StorageManager`.
    *   **Modify `tests/fixtures/host_fixtures.py::host_manager`:** Inject the `integration_storage_manager` fixture *only if* `AURITE_ENABLE_DB` is true (using `request.getfixturevalue` conditionally might work, or restructuring how `storage_manager` is passed). If `AURITE_ENABLE_DB` is false, ensure `None` is passed for the `storage_manager`.
12. **Write Integration Tests:**
    *   Add new tests (or modify existing ones, likely in `tests/orchestration/`) specifically designed to run with `AURITE_ENABLE_DB=true`.
    *   These tests should verify:
        *   Initial config sync from JSON to PostgreSQL works.
        *   Dynamic registration saves configs to PostgreSQL.
        *   Agent history loading/saving works correctly against PostgreSQL when `include_history` is true.
13. **Documentation:**
    *   Update `README.md` and relevant design/architecture docs.
    *   Document environment variables.
    *   Update `docs/storage/db_design.md` status.

## 3. Anticipated Issues

*   **Database Setup:** Ensuring PostgreSQL is running and accessible, especially in different environments (local dev, CI, deployment). Managing test databases.
*   **SQLAlchemy/Async:** Handling async database operations correctly with SQLAlchemy and `asyncpg` (PostgreSQL async driver). Ensuring session management is correct in an async context.
*   **Schema Mismatches:** Keeping SQLAlchemy models (`db_models.py`) in sync with Pydantic models (`host/models.py`).
*   **Performance:** Potential minor overhead from DB interactions, although likely acceptable.
*   **Error Handling:** Robustly handling DB connection errors, transaction failures, etc.
*   **Migrations:** Initial schema creation is covered, but future schema changes will require setting up and using Alembic.
