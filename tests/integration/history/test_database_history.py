"""
Integration tests for database-backed session history management.
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest import TestCase

from openai.types.chat import ChatCompletionMessage
from sqlalchemy import create_engine

from aurite.lib.models.api.responses import AgentRunResult, LinearWorkflowExecutionResult, LinearWorkflowStepResult
from aurite.lib.storage.db.db_manager import StorageManager
from aurite.lib.storage.db.db_models import Base
from aurite.lib.storage.sessions.cache_manager import CacheManager
from aurite.lib.storage.sessions.session_manager import SessionManager


class TestDatabaseSessionHistory(TestCase):
    """Test session history management with database backend."""

    def setUp(self):
        """Set up test fixtures with temporary database and cache."""
        # Create temporary cache directory
        self.temp_cache_dir = tempfile.mkdtemp()
        self.cache_manager = CacheManager(cache_dir=Path(self.temp_cache_dir))

        # Create temporary SQLite database
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.engine = create_engine(f"sqlite:///{self.temp_db.name}")
        Base.metadata.create_all(self.engine)

        # Initialize storage manager with test database
        self.storage_manager = StorageManager(engine=self.engine)
        self.storage_manager.init_db()

        # Initialize session manager with both cache and database
        self.session_manager = SessionManager(cache_manager=self.cache_manager, storage_manager=self.storage_manager)

    def tearDown(self):
        """Clean up test resources."""
        # Clean up database
        if hasattr(self, "engine"):
            self.engine.dispose()
        if hasattr(self, "temp_db"):
            Path(self.temp_db.name).unlink(missing_ok=True)

        # Clean up cache directory
        if hasattr(self, "temp_cache_dir"):
            import shutil

            shutil.rmtree(self.temp_cache_dir, ignore_errors=True)

    def test_save_and_retrieve_agent_session_from_db(self):
        """Test saving an agent session to database and retrieving it after cache is cleared."""
        # Create test agent result
        agent_result = AgentRunResult(
            status="success",
            final_response=ChatCompletionMessage(role="assistant", content="Test response"),
            conversation_history=[
                {"role": "user", "content": "Test message"},
                {"role": "assistant", "content": "Test response"},
            ],
            session_id="db-agent-test-001",
            agent_name="Test Agent",
            error_message=None,
            exception=None,
        )

        # Save the agent result (should save to both cache and database)
        self.session_manager.save_agent_result(session_id="db-agent-test-001", agent_result=agent_result)

        # Clear the cache to force database retrieval
        self.cache_manager.clear_cache()

        # Retrieve the session (should come from database)
        retrieved_result = self.session_manager.get_session_result("db-agent-test-001")

        # Verify the result
        self.assertIsNotNone(retrieved_result)
        self.assertEqual(retrieved_result["status"], "success")
        self.assertEqual(retrieved_result["agent_name"], "Test Agent")
        self.assertEqual(len(retrieved_result["conversation_history"]), 2)

    def test_list_sessions_from_database(self):
        """Test listing sessions from database with filtering."""
        # Create multiple agent sessions
        for i in range(3):
            agent_result = AgentRunResult(
                status="success",
                final_response=ChatCompletionMessage(role="assistant", content=f"Response {i}"),
                conversation_history=[
                    {"role": "user", "content": f"Message {i}"},
                    {"role": "assistant", "content": f"Response {i}"},
                ],
                session_id=f"db-agent-list-{i:03d}",
                agent_name=f"Agent {i % 2}",  # Alternate between Agent 0 and Agent 1
                error_message=None,
                exception=None,
            )
            self.session_manager.save_agent_result(session_id=f"db-agent-list-{i:03d}", agent_result=agent_result)

        # Create a workflow session
        workflow_result = LinearWorkflowExecutionResult(
            workflow_name="Test Workflow",
            status="completed",
            step_results=[
                LinearWorkflowStepResult(
                    step_name="Step 1",
                    step_type="agent",
                    result={
                        "status": "success",
                        "final_response": {"content": "Step 1 response", "role": "assistant"},
                        "conversation_history": [
                            {"role": "user", "content": "Step 1 input"},
                            {"role": "assistant", "content": "Step 1 response"},
                        ],
                        "session_id": "db-workflow-step-001",
                        "agent_name": "Step Agent",
                    },
                )
            ],
            final_output="Final workflow output",
            session_id="db-workflow-001",
            error=None,
        )
        self.session_manager.save_workflow_result(session_id="db-workflow-001", workflow_result=workflow_result)

        # Clear cache to force database retrieval
        self.cache_manager.clear_cache()

        # Test 1: List all sessions
        all_sessions = self.session_manager.get_sessions_list()
        self.assertEqual(all_sessions["total"], 4)  # 3 agents + 1 workflow
        self.assertEqual(len(all_sessions["sessions"]), 4)

        # Test 2: Filter by agent name
        agent_0_sessions = self.session_manager.get_sessions_list(agent_name="Agent 0")
        self.assertEqual(agent_0_sessions["total"], 2)  # Agent 0 appears twice
        for session in agent_0_sessions["sessions"]:
            self.assertEqual(session.name, "Agent 0")
            self.assertFalse(session.is_workflow)

        # Test 3: Filter by workflow name
        workflow_sessions = self.session_manager.get_sessions_list(workflow_name="Test Workflow")
        self.assertEqual(workflow_sessions["total"], 1)
        self.assertEqual(workflow_sessions["sessions"][0].name, "Test Workflow")
        self.assertTrue(workflow_sessions["sessions"][0].is_workflow)

        # Test 4: Pagination
        paginated = self.session_manager.get_sessions_list(limit=2, offset=1)
        self.assertEqual(len(paginated["sessions"]), 2)
        self.assertEqual(paginated["total"], 4)
        self.assertEqual(paginated["offset"], 1)
        self.assertEqual(paginated["limit"], 2)

    def test_delete_session_from_database(self):
        """Test deleting a session from both cache and database."""
        # Create and save a test session
        agent_result = AgentRunResult(
            status="success",
            final_response=ChatCompletionMessage(role="assistant", content="To be deleted"),
            conversation_history=[
                {"role": "user", "content": "Delete me"},
                {"role": "assistant", "content": "To be deleted"},
            ],
            session_id="db-delete-test-001",
            agent_name="Delete Test Agent",
            error_message=None,
            exception=None,
        )
        self.session_manager.save_agent_result(session_id="db-delete-test-001", agent_result=agent_result)

        # Verify it exists
        result = self.session_manager.get_session_result("db-delete-test-001")
        self.assertIsNotNone(result)

        # Delete the session
        deleted = self.session_manager.delete_session("db-delete-test-001")
        self.assertTrue(deleted)

        # Clear cache to ensure we're checking database
        self.cache_manager.clear_cache()

        # Verify it's deleted from both cache and database
        result = self.session_manager.get_session_result("db-delete-test-001")
        self.assertIsNone(result)

        # Verify it doesn't appear in listings
        all_sessions = self.session_manager.get_sessions_list()
        session_ids = [s.session_id for s in all_sessions["sessions"]]
        self.assertNotIn("db-delete-test-001", session_ids)

    def test_workflow_with_child_sessions(self):
        """Test workflow sessions with child agent sessions are handled correctly."""
        # Create a workflow with child agent sessions
        workflow_result = LinearWorkflowExecutionResult(
            workflow_name="Parent Workflow",
            status="completed",
            step_results=[
                LinearWorkflowStepResult(
                    step_name="Agent Step 1",
                    step_type="agent",
                    result={
                        "status": "success",
                        "final_response": {"content": "Step 1 done", "role": "assistant"},
                        "conversation_history": [
                            {"role": "user", "content": "Do step 1"},
                            {"role": "assistant", "content": "Step 1 done"},
                        ],
                        "session_id": "db-workflow-child-001",
                        "agent_name": "Child Agent 1",
                    },
                ),
                LinearWorkflowStepResult(
                    step_name="Agent Step 2",
                    step_type="agent",
                    result={
                        "status": "success",
                        "final_response": {"content": "Step 2 done", "role": "assistant"},
                        "conversation_history": [
                            {"role": "user", "content": "Do step 2"},
                            {"role": "assistant", "content": "Step 2 done"},
                        ],
                        "session_id": "db-workflow-child-002",
                        "agent_name": "Child Agent 2",
                    },
                ),
            ],
            final_output="Workflow completed",
            session_id="db-workflow-parent-001",
            error=None,
        )

        # Save the workflow (with base_session_id)
        self.session_manager.save_workflow_result(
            session_id="db-workflow-parent-001",
            workflow_result=workflow_result,
            base_session_id="db-workflow-parent-001",
        )

        # Clear cache to force database retrieval
        self.cache_manager.clear_cache()

        # Retrieve the workflow session
        workflow_data = self.session_manager.get_session_result("db-workflow-parent-001")
        self.assertIsNotNone(workflow_data)
        self.assertEqual(workflow_data["workflow_name"], "Parent Workflow")
        self.assertEqual(len(workflow_data["step_results"]), 2)

        # Check metadata
        metadata = self.session_manager.get_session_metadata("db-workflow-parent-001")
        self.assertIsNotNone(metadata)
        self.assertTrue(metadata.is_workflow)
        self.assertEqual(metadata.name, "Parent Workflow")
        self.assertEqual(metadata.message_count, 4)  # 2 messages per child agent

    def test_cleanup_old_sessions(self):
        """Test cleanup of old sessions based on retention policy."""
        # Create sessions with different ages
        now = datetime.utcnow()

        # Create an old session (35 days ago)
        old_result = AgentRunResult(
            status="success",
            final_response=ChatCompletionMessage(role="assistant", content="Old response"),
            conversation_history=[{"role": "user", "content": "Old message"}],
            session_id="db-old-session-001",
            agent_name="Old Agent",
            error_message=None,
            exception=None,
        )
        self.session_manager.save_agent_result(session_id="db-old-session-001", agent_result=old_result)

        # Manually update the timestamp in the database to make it old
        with self.storage_manager.get_db_session() as db:
            from aurite.lib.storage.db.db_models import SessionDB

            session = db.get(SessionDB, "db-old-session-001")
            if session:
                session.last_updated = now - timedelta(days=35)
                session.created_at = now - timedelta(days=35)

        # Create recent sessions
        for i in range(3):
            recent_result = AgentRunResult(
                status="success",
                final_response=ChatCompletionMessage(role="assistant", content=f"Recent {i}"),
                conversation_history=[{"role": "user", "content": f"Recent message {i}"}],
                session_id=f"db-recent-session-{i:03d}",
                agent_name=f"Recent Agent {i}",
                error_message=None,
                exception=None,
            )
            self.session_manager.save_agent_result(session_id=f"db-recent-session-{i:03d}", agent_result=recent_result)

        # Run cleanup (delete sessions older than 30 days, keep max 10)
        # Note: Don't clear cache here as it interferes with the cleanup process
        self.session_manager.cleanup_old_sessions(days=30, max_sessions=10)

        # Check that old session is deleted
        old_session = self.session_manager.get_session_result("db-old-session-001")
        self.assertIsNone(old_session)

        # Check that recent sessions are kept
        all_sessions = self.session_manager.get_sessions_list()
        self.assertEqual(all_sessions["total"], 3)  # Only recent sessions remain

        session_ids = [s.session_id for s in all_sessions["sessions"]]
        self.assertNotIn("db-old-session-001", session_ids)
        for i in range(3):
            self.assertIn(f"db-recent-session-{i:03d}", session_ids)

    def test_database_fallback_to_cache(self):
        """Test that system falls back to cache when database operations fail."""
        # Save a session normally
        agent_result = AgentRunResult(
            status="success",
            final_response=ChatCompletionMessage(role="assistant", content="Fallback test"),
            conversation_history=[{"role": "user", "content": "Test fallback"}],
            session_id="db-fallback-test-001",
            agent_name="Fallback Agent",
            error_message=None,
            exception=None,
        )
        self.session_manager.save_agent_result(session_id="db-fallback-test-001", agent_result=agent_result)

        # Simulate database failure by disposing the engine
        self.storage_manager._engine.dispose()
        self.storage_manager._engine = None

        # Should still be able to retrieve from cache
        result = self.session_manager.get_session_result("db-fallback-test-001")
        self.assertIsNotNone(result)
        self.assertEqual(result["agent_name"], "Fallback Agent")

        # Should still be able to list sessions from cache
        sessions = self.session_manager.get_sessions_list()
        self.assertEqual(sessions["total"], 1)
        self.assertEqual(sessions["sessions"][0].session_id, "db-fallback-test-001")
