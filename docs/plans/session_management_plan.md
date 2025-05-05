# Implementation Plan: Session Management (Postgres)

**Version:** 1.0
**Date:** 2025-05-05
**Goal:** Implement session management for agent conversation history using unique session IDs stored in the existing Postgres database to prevent history pollution between concurrent executions and fix related test failures.

## 1. Background

Currently, agent history persistence (`AgentConfig.include_history=True`) loads/saves history based solely on `agent_name`. This leads to history pollution in multi-session environments (API, Worker) and causes test failures in integration tests where the database state persists between test runs (`test_facade_integration.py`).

This plan introduces a `session_id` to isolate conversation histories.

## 2. Implementation Steps

The implementation will follow a bottom-up approach: Storage -> Agent -> Facade -> Executors -> Tests.

1.  **DB Schema (`src/storage/db_models.py`):**
    *   Add `session_id = Column(String, index=True, nullable=False)` to the `ConversationHistoryDB` model.
    *   **(Manual User Step):** Apply database migration (e.g., `ALTER TABLE conversation_history ADD COLUMN session_id VARCHAR; CREATE INDEX ix_conversation_history_session_id ON conversation_history (session_id);`). *Note: Existing history records will be orphaned.*

2.  **Storage Manager (`src/storage/db_manager.py`):**
    *   Update `load_history` signature: `load_history(self, agent_name: str, session_id: Optional[str], limit: Optional[int] = None)`.
        *   Add check: If `session_id` is `None`, log warning and return `[]`.
        *   Update SQLAlchemy query to filter by `ConversationHistoryDB.agent_name == agent_name` **and** `ConversationHistoryDB.session_id == session_id`.
    *   Update `save_full_history` signature: `save_full_history(self, agent_name: str, session_id: Optional[str], history: List[Dict[str, Any]])`.
        *   Add check: If `session_id` is `None`, log warning and return.
        *   Update deletion query (`session.query(ConversationHistoryDB).filter_by(...)`) to filter by `agent_name` **and** `session_id`.
        *   Ensure `session_id` is set on each new `ConversationHistoryDB` instance before adding to the session.

3.  **Agent (`src/agents/agent.py`):**
    *   Update `execute_agent` signature: `execute_agent(self, ..., session_id: Optional[str] = None)`.
    *   Inside the history block (`if self.config.include_history and self._storage_manager:`):
        *   Add `if session_id:` check around calls to `_storage_manager.load_history` and `_storage_manager.save_full_history`.
        *   Pass the `session_id` to these storage manager methods.
        *   Add a log warning if `session_id` is `None` but history is enabled.

4.  **Execution Facade (`src/execution/facade.py`):**
    *   Update `run_agent` signature: `run_agent(self, ..., session_id: Optional[str] = None)`. Pass `session_id` to `Agent.execute_agent`.
    *   Update `run_custom_workflow` signature: `run_custom_workflow(self, ..., session_id: Optional[str] = None)`. Pass `session_id` to `CustomWorkflowExecutor.execute`.
    *   Leave `run_simple_workflow` unchanged for now.

5.  **Custom Workflow Executor (`src/workflows/custom_workflow.py`):**
    *   Update `execute` signature: `execute(self, ..., session_id: Optional[str] = None)`.
    *   Update the call to the custom workflow's method to pass `session_id`: `await execute_method(..., session_id=session_id)`.

6.  **Custom Workflow Interface & Documentation:**
    *   The required signature for custom workflows becomes: `async def execute_workflow(self, initial_input: Any, executor: "ExecutionFacade", session_id: Optional[str] = None)`.
    *   Update relevant documentation (e.g., `README.md`, potentially a custom workflow guide) to reflect this new required parameter and explain that authors need to pass it down if calling `executor.run_agent`.

7.  **Testing:**
    *   **Unit Tests:**
        *   `tests/storage/test_db_manager.py`: Update history tests to use `session_id`.
        *   `tests/orchestration/agent/test_agent_unit.py`: Update history tests to provide `session_id` and verify it's passed to mocked storage.
        *   `tests/orchestration/facade/test_facade_unit.py`: Update tests to verify `session_id` passing to mocked `Agent`/`CustomWorkflowExecutor`.
        *   `tests/orchestration/workflow/test_custom_workflow_executor_unit.py`: Update tests to verify `session_id` passing to mocked `execute_workflow`.
    *   **Integration Tests:**
        *   `tests/orchestration/facade/test_facade_integration.py`: Generate unique `session_id`s per test and pass them to `run_agent`/`run_custom_workflow`. Verify original failures are resolved.
        *   `tests/orchestration/workflow/test_custom_workflow_executor_integration.py`: Update call to `executor.execute` to include `session_id`.
        *   `tests/fixtures/custom_workflows/example_workflow.py`: Update `execute_workflow` signature to accept `session_id` and pass it to `executor.run_agent`.

## 3. Rollback Plan

*   Revert changes to source files (`db_models.py`, `db_manager.py`, `agent.py`, `facade.py`, `custom_workflow.py`).
*   Revert changes to test files.
*   Apply reverse database migration (drop `session_id` column and index).
