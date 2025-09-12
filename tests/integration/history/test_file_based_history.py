"""
Integration tests for file-based session history management.
Tests the SessionManager with CacheManager (no database).
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from openai.types.chat import ChatCompletionMessage

from aurite.lib.models.api.responses import AgentRunResult, LinearWorkflowExecutionResult, LinearWorkflowStepResult
from aurite.lib.storage.sessions.cache_manager import CacheManager
from aurite.lib.storage.sessions.session_manager import SessionManager


@pytest.fixture
def temp_cache_dir():
    """Create a temporary directory for cache files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cache_manager(temp_cache_dir):
    """Create a CacheManager with a temporary directory."""
    return CacheManager(cache_dir=temp_cache_dir)


@pytest.fixture
def session_manager(cache_manager):
    """Create a SessionManager with file-based caching only (no database)."""
    # Pass None for storage_manager to use file-based caching only
    return SessionManager(cache_manager=cache_manager, storage_manager=None)


class TestFileBasedSessionHistory:
    """Test session history management with file-based caching."""

    def test_save_and_retrieve_agent_session(self, session_manager, temp_cache_dir):
        """Test saving and retrieving an agent session."""
        # Create a sample agent result
        agent_result = AgentRunResult(
            status="success",
            final_response=ChatCompletionMessage(role="assistant", content="Hello, I'm an AI assistant."),
            conversation_history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hello, I'm an AI assistant."},
            ],
            agent_name="Test Agent",
            session_id="agent-test-123",
            error_message=None,
            exception=None,
        )

        # Save the agent result
        session_manager.save_agent_result("agent-test-123", agent_result)

        # Verify file was created
        session_file = temp_cache_dir / "agent-test-123.json"
        assert session_file.exists()

        # Retrieve the session result
        retrieved_result = session_manager.get_session_result("agent-test-123")
        assert retrieved_result is not None
        assert retrieved_result["agent_name"] == "Test Agent"
        assert retrieved_result["status"] == "success"
        assert len(retrieved_result["conversation_history"]) == 2

        # Retrieve session history
        history = session_manager.get_session_history("agent-test-123")
        assert history is not None
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_save_and_retrieve_workflow_session(self, session_manager, temp_cache_dir):
        """Test saving and retrieving a workflow session with child agents."""
        # Create sample workflow result with multiple agent steps
        workflow_result = LinearWorkflowExecutionResult(
            workflow_name="Test Workflow",
            status="completed",
            error=None,
            step_results=[
                LinearWorkflowStepResult(
                    step_name="Agent 1",
                    step_type="agent",
                    result={
                        "status": "success",
                        "final_response": {"role": "assistant", "content": "Response from Agent 1"},
                        "conversation_history": [
                            {"role": "user", "content": "Input to Agent 1"},
                            {"role": "assistant", "content": "Response from Agent 1"},
                        ],
                        "agent_name": "Agent 1",
                        "session_id": "workflow-test-456-0",
                    },
                ),
                LinearWorkflowStepResult(
                    step_name="Agent 2",
                    step_type="agent",
                    result={
                        "status": "success",
                        "final_response": {"role": "assistant", "content": "Response from Agent 2"},
                        "conversation_history": [
                            {"role": "user", "content": "Response from Agent 1"},
                            {"role": "assistant", "content": "Response from Agent 2"},
                        ],
                        "agent_name": "Agent 2",
                        "session_id": "workflow-test-456-1",
                    },
                ),
            ],
            final_output="Response from Agent 2",
            session_id="workflow-test-456",
        )

        # Save the workflow result
        session_manager.save_workflow_result("workflow-test-456", workflow_result, base_session_id="workflow-test-456")

        # Verify file was created
        session_file = temp_cache_dir / "workflow-test-456.json"
        assert session_file.exists()

        # Retrieve the workflow result
        retrieved_result = session_manager.get_session_result("workflow-test-456")
        assert retrieved_result is not None
        assert retrieved_result["workflow_name"] == "Test Workflow"
        assert retrieved_result["status"] == "completed"
        assert len(retrieved_result["step_results"]) == 2

        # Retrieve workflow history (should aggregate all agent conversations)
        history = session_manager.get_session_history("workflow-test-456")
        assert history is not None
        assert len(history) == 4  # 2 messages from each agent

    def test_session_metadata_extraction(self, session_manager):
        """Test that metadata is correctly extracted from sessions."""
        # Create and save an agent session
        agent_result = AgentRunResult(
            status="success",
            final_response=ChatCompletionMessage(role="assistant", content="Test response"),
            conversation_history=[
                {"role": "user", "content": "Test input"},
                {"role": "assistant", "content": "Test response"},
            ],
            agent_name="Metadata Test Agent",
            session_id="metadata-test-789",
            error_message=None,
            exception=None,
        )

        session_manager.save_agent_result("metadata-test-789", agent_result)

        # Get session metadata
        metadata = session_manager.get_session_metadata("metadata-test-789")
        assert metadata is not None
        assert metadata.session_id == "metadata-test-789"
        assert metadata.name == "Metadata Test Agent"
        assert metadata.message_count == 2
        assert metadata.is_workflow is False
        assert metadata.created_at is not None
        assert metadata.last_updated is not None

    def test_session_listing_and_filtering(self, session_manager):
        """Test listing sessions with filtering by agent or workflow name."""
        # Create multiple sessions
        for i in range(3):
            agent_result = AgentRunResult(
                status="success",
                final_response=ChatCompletionMessage(role="assistant", content=f"Response {i}"),
                conversation_history=[
                    {"role": "user", "content": f"Input {i}"},
                    {"role": "assistant", "content": f"Response {i}"},
                ],
                agent_name=f"Agent {i % 2}",  # Alternate between Agent 0 and Agent 1
                session_id=f"list-test-{i}",
                error_message=None,
                exception=None,
            )
            session_manager.save_agent_result(f"list-test-{i}", agent_result)

        # List all sessions
        all_sessions = session_manager.get_sessions_list()
        assert all_sessions["total"] >= 3

        # Filter by agent name
        agent_0_sessions = session_manager.get_sessions_list(agent_name="Agent 0")
        assert agent_0_sessions["total"] == 2  # Sessions 0 and 2

        agent_1_sessions = session_manager.get_sessions_list(agent_name="Agent 1")
        assert agent_1_sessions["total"] == 1  # Session 1

    def test_session_deletion(self, session_manager, temp_cache_dir):
        """Test deleting a session removes the file."""
        # Create and save a session
        agent_result = AgentRunResult(
            status="success",
            final_response=ChatCompletionMessage(role="assistant", content="To be deleted"),
            conversation_history=[
                {"role": "user", "content": "Delete me"},
                {"role": "assistant", "content": "To be deleted"},
            ],
            agent_name="Delete Test Agent",
            session_id="delete-test-999",
            error_message=None,
            exception=None,
        )

        session_manager.save_agent_result("delete-test-999", agent_result)

        # Verify file exists
        session_file = temp_cache_dir / "delete-test-999.json"
        assert session_file.exists()

        # Delete the session
        deleted = session_manager.delete_session("delete-test-999")
        assert deleted is True

        # Verify file is gone
        assert not session_file.exists()

        # Verify session cannot be retrieved
        result = session_manager.get_session_result("delete-test-999")
        assert result is None

    def test_workflow_cascade_deletion(self, session_manager, temp_cache_dir):
        """Test that deleting a workflow also deletes child agent sessions."""
        # Create a workflow with child agents
        workflow_result = LinearWorkflowExecutionResult(
            workflow_name="Cascade Delete Test",
            status="completed",
            error=None,
            step_results=[
                LinearWorkflowStepResult(
                    step_name="Child Agent",
                    step_type="agent",
                    result={
                        "status": "success",
                        "conversation_history": [{"role": "user", "content": "test"}],
                        "agent_name": "Child Agent",
                        "session_id": "cascade-workflow-0",
                    },
                )
            ],
            final_output="Done",
            session_id="cascade-workflow",
        )

        # Save workflow and child agent sessions
        session_manager.save_workflow_result("cascade-workflow", workflow_result, base_session_id="cascade-workflow")

        # Also save the child agent session separately (as would happen in real execution)
        child_result = AgentRunResult(
            status="success",
            final_response=None,
            conversation_history=[{"role": "user", "content": "test"}],
            agent_name="Child Agent",
            session_id="cascade-workflow-0",
            error_message=None,
            exception=None,
        )
        session_manager.save_agent_result("cascade-workflow-0", child_result, base_session_id="cascade-workflow")

        # Verify both files exist
        assert (temp_cache_dir / "cascade-workflow.json").exists()
        assert (temp_cache_dir / "cascade-workflow-0.json").exists()

        # Delete the workflow
        deleted = session_manager.delete_session("cascade-workflow")
        assert deleted is True

        # Verify child session is also deleted
        assert not (temp_cache_dir / "cascade-workflow-0.json").exists()

    def test_session_cleanup_by_age(self, session_manager):
        """Test cleaning up old sessions based on age."""
        # Create sessions with different timestamps
        datetime.utcnow()

        # Create an old session (31 days old)
        old_result = AgentRunResult(
            status="success",
            final_response=None,
            conversation_history=[{"role": "user", "content": "old"}],
            agent_name="Old Agent",
            session_id="old-session",
            error_message=None,
            exception=None,
        )
        session_manager.save_agent_result("old-session", old_result)

        # Manually update the timestamp to make it old
        session_data = session_manager._cache.get_result("old-session")
        old_date = datetime(2020, 1, 1).isoformat()  # Very old date
        session_data["created_at"] = old_date
        session_data["last_updated"] = old_date
        session_manager._cache.save_result("old-session", session_data)

        # Create a recent session
        recent_result = AgentRunResult(
            status="success",
            final_response=None,
            conversation_history=[{"role": "user", "content": "recent"}],
            agent_name="Recent Agent",
            session_id="recent-session",
            error_message=None,
            exception=None,
        )
        session_manager.save_agent_result("recent-session", recent_result)

        # Run cleanup (delete sessions older than 30 days)
        session_manager.cleanup_old_sessions(days=30, max_sessions=100)

        # Verify old session is deleted
        assert session_manager.get_session_result("old-session") is None

        # Verify recent session still exists
        assert session_manager.get_session_result("recent-session") is not None

    def test_session_cleanup_by_count(self, session_manager):
        """Test cleaning up sessions when exceeding max count."""
        # Create 5 sessions
        for i in range(5):
            result = AgentRunResult(
                status="success",
                final_response=None,
                conversation_history=[{"role": "user", "content": f"test {i}"}],
                agent_name=f"Agent {i}",
                session_id=f"count-test-{i}",
                error_message=None,
                exception=None,
            )
            session_manager.save_agent_result(f"count-test-{i}", result)

        # Run cleanup with max_sessions=3
        session_manager.cleanup_old_sessions(days=365, max_sessions=3)

        # Verify only 3 sessions remain
        all_sessions = session_manager.get_sessions_list(limit=100)
        # Filter to only our test sessions
        test_sessions = [s for s in all_sessions["sessions"] if s.session_id.startswith("count-test-")]
        assert len(test_sessions) <= 3

    def test_partial_session_id_matching(self, session_manager):
        """Test retrieving sessions with partial IDs."""
        # Create a session with a known ID
        result = AgentRunResult(
            status="success",
            final_response=None,
            conversation_history=[{"role": "user", "content": "test"}],
            agent_name="Partial Test Agent",
            session_id="agent-abc123def456",
            error_message=None,
            exception=None,
        )
        session_manager.save_agent_result("agent-abc123def456", result, base_session_id="agent-abc123def456")

        # Try to retrieve with partial ID (base_session_id)
        full_result, metadata = session_manager.get_full_session_details("agent-abc123def456")
        assert full_result is not None
        assert metadata is not None
        assert metadata.session_id == "agent-abc123def456"

    def test_add_message_to_history(self, session_manager):
        """Test adding individual messages to an existing session."""
        # Create initial session
        result = AgentRunResult(
            status="success",
            final_response=None,
            conversation_history=[{"role": "user", "content": "initial message"}],
            agent_name="Incremental Agent",
            session_id="incremental-test",
            error_message=None,
            exception=None,
        )
        session_manager.save_agent_result("incremental-test", result)

        # Add a new message
        new_message = {"role": "assistant", "content": "new response"}
        session_manager.add_message_to_history("incremental-test", new_message, "Incremental Agent")

        # Verify the message was added
        history = session_manager.get_session_history("incremental-test")
        assert len(history) == 2
        assert history[1]["content"] == "new response"
