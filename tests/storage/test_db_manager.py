# tests/storage/test_db_manager.py
"""
Unit tests for the StorageManager class.

These tests should ideally use an in-memory SQLite database or mocking
to isolate the StorageManager logic from a live PostgreSQL instance.
"""

import pytest
import os
import sqlalchemy  # Import sqlalchemy for create_engine patch
from pathlib import Path
from unittest.mock import patch

# Assuming models and manager are importable
from aurite.config.config_models import AgentConfig, WorkflowConfig, CustomWorkflowConfig
from aurite.storage.db_manager import StorageManager
from aurite.storage.db_models import (
    Base,
    AgentConfigDB,
    WorkflowConfigDB,
    CustomWorkflowConfigDB,
)

# Import only what's needed now: get_db_session and the new create_db_engine
from aurite.storage.db_connection import get_db_session

# Use pytest-asyncio for async tests if needed, but manager methods are sync for now
# pytestmark = pytest.mark.anyio

# --- Test Setup ---

# Use SQLite in-memory for testing speed and isolation
TEST_DB_URL = "sqlite:///:memory:"


# Removed autouse=True - apply this fixture only where needed
@pytest.fixture(scope="function")
def setup_test_db():
    """
    Fixture to set up and tear down an in-memory SQLite DB for each test.
    It patches the db_connection module's globals and functions to force
    the use of the in-memory SQLite database.
    """
    # No need for globals or complex patching now with DI

    # Create an engine specifically for this test function
    engine = sqlalchemy.create_engine(TEST_DB_URL)
    assert engine is not None, "Failed to create test engine"
    assert str(engine.url) == TEST_DB_URL

    # Patch environment just to ensure StorageManager attempts connection if needed
    # (though storage_manager_instance fixture will provide the engine directly)
    with patch.dict(os.environ, {"AURITE_ENABLE_DB": "true"}):
        # Create tables for the SQLite engine
        try:
            Base.metadata.create_all(bind=engine)
            print("\nIn-memory SQLite DB tables created.")
            yield engine  # Yield the engine for potential use, or just yield None
        finally:
            # Teardown: Drop tables
            print("\nTearing down in-memory SQLite DB...")
            if engine:  # Check if engine was created before trying to drop
                Base.metadata.drop_all(bind=engine)
            print("In-memory SQLite DB teardown complete.")


@pytest.fixture
def storage_manager_instance(
    setup_test_db,
) -> StorageManager:  # Depend on setup_test_db fixture
    """
    Provides a StorageManager instance connected to the test DB engine
    yielded by the setup_test_db fixture.
    """
    test_engine = setup_test_db  # Get the engine yielded by the fixture
    assert test_engine is not None, "setup_test_db fixture did not yield a valid engine"
    # Pass the specific test engine to the manager
    manager = StorageManager(engine=test_engine)
    assert manager._engine is test_engine, (
        "StorageManager did not use the provided engine"
    )
    # Also need to adapt get_db_session calls within tests or ensure the fixture provides a working session mechanism
    # For now, let's assume get_db_session will work with the injected engine
    return manager


# --- Test Cases ---

# Note: These first two tests run *without* the setup_test_db fixture's effects
# because they test scenarios where the DB connection *should* fail or be disabled.
# We instantiate StorageManager directly within the patched context.


def test_storage_manager_init_no_db(monkeypatch):
    """Test StorageManager init when DB is disabled."""
    monkeypatch.setenv("AURITE_ENABLE_DB", "false")
    # No globals to reset

    # Instantiate StorageManager without an engine. Since AURITE_ENABLE_DB is false,
    # HostManager wouldn't normally call create_db_engine. To simulate this for
    # direct StorageManager instantiation, patch create_db_engine *where it's called*.
    with patch(
        "src.storage.db_manager.create_db_engine", return_value=None
    ) as mock_create:
        manager = StorageManager()  # Should now use the mocked create_db_engine
        assert manager._engine is None
        mock_create.assert_called_once()  # Verify it was called by __init__
    # Also test init_db doesn't raise error (it checks self._engine)
    manager.init_db()  # Should log error but not fail test


def test_storage_manager_init_db_error(monkeypatch):
    """Test StorageManager init when DB URL is invalid."""
    monkeypatch.setenv("AURITE_ENABLE_DB", "true")
    # No globals to reset

    # Patch get_database_url used by create_db_engine
    with patch("src.storage.db_connection.get_database_url", return_value=None):
        # Instantiate StorageManager without an engine; its internal call to
        # create_db_engine will call the patched get_database_url and return None.
        manager = StorageManager()  # Should call create_db_engine internally
        assert manager._engine is None
        # init_db should not raise error, just log
        manager.init_db()  # Should log error but not fail test


# --- Config Sync Tests (These use the fixtures) ---


# Apply the setup_test_db fixture explicitly to tests needing the DB
def test_sync_agent_config_create(
    setup_test_db, storage_manager_instance: StorageManager
):
    """Test creating a new agent config."""
    manager = storage_manager_instance
    agent_conf = AgentConfig(
        name="TestAgent1", model="test-model", system_prompt="Test prompt"
    )

    manager.sync_agent_config(agent_conf)

    # Verify in DB using the engine from the fixture
    with get_db_session(engine=setup_test_db) as db:
        assert db is not None
        db_record = db.get(AgentConfigDB, "TestAgent1")
        assert db_record is not None
        assert db_record.name == "TestAgent1"
        assert db_record.model == "test-model"
        assert db_record.system_prompt == "Test prompt"
        assert db_record.include_history is False  # Default


def test_sync_agent_config_update(
    setup_test_db, storage_manager_instance: StorageManager
):
    """Test updating an existing agent config."""
    manager = storage_manager_instance
    agent_conf1 = AgentConfig(name="TestAgent2", model="model-v1", temperature=0.5)
    manager.sync_agent_config(agent_conf1)

    # Verify initial state using the engine from the fixture
    with get_db_session(engine=setup_test_db) as db:
        assert db is not None
        db_record1 = db.get(AgentConfigDB, "TestAgent2")
        assert db_record1 is not None
        assert db_record1.model == "model-v1"
        assert db_record1.temperature == 0.5

    # Update config
    agent_conf2 = AgentConfig(
        name="TestAgent2", model="model-v2", temperature=0.8, include_history=True
    )
    manager.sync_agent_config(agent_conf2)

    # Verify updated state using the engine from the fixture
    with get_db_session(engine=setup_test_db) as db:
        assert db is not None
        # Re-fetch the record in the new session
        db_record2 = db.get(AgentConfigDB, "TestAgent2")
        assert db_record2 is not None
        assert db_record2.model == "model-v2"
        assert db_record2.temperature == 0.8
        assert db_record2.include_history is True


def test_sync_workflow_config(setup_test_db, storage_manager_instance: StorageManager):
    """Test syncing a simple workflow config."""
    manager = storage_manager_instance
    wf_conf = WorkflowConfig(
        name="TestWF1", steps=["Agent1", "Agent2"], description="My WF"
    )
    manager.sync_workflow_config(wf_conf)

    # Verify using the engine from the fixture
    with get_db_session(engine=setup_test_db) as db:
        assert db is not None
        db_record = db.get(WorkflowConfigDB, "TestWF1")
        assert db_record is not None
        assert db_record.name == "TestWF1"
        # Assert against the correct attribute name
        assert db_record.steps_json == ["Agent1", "Agent2"]
        assert db_record.description == "My WF"


def test_sync_custom_workflow_config(
    setup_test_db, storage_manager_instance: StorageManager
):
    """Test syncing a custom workflow config."""
    manager = storage_manager_instance
    # Note: Path object needs conversion for DB storage (handled by _sync_config)
    cwf_conf = CustomWorkflowConfig(
        name="TestCWF1",
        module_path=Path("path/to/workflow.py"),
        class_name="MyWorkflow",
    )
    manager.sync_custom_workflow_config(cwf_conf)

    # Verify using the engine from the fixture
    with get_db_session(engine=setup_test_db) as db:
        assert db is not None
        db_record = db.get(CustomWorkflowConfigDB, "TestCWF1")
        assert db_record is not None
        assert db_record.name == "TestCWF1"
        assert db_record.module_path == "path/to/workflow.py"  # Stored as string
        assert db_record.class_name == "MyWorkflow"


def test_sync_all_configs(setup_test_db, storage_manager_instance: StorageManager):
    """Test syncing multiple configs at once."""
    manager = storage_manager_instance
    agents = {
        "AgentA": AgentConfig(name="AgentA", model="a"),
        "AgentB": AgentConfig(name="AgentB", model="b"),
    }
    workflows = {"WFA": WorkflowConfig(name="WFA", steps=["AgentA"])}
    custom_workflows = {
        "CWFA": CustomWorkflowConfig(
            name="CWFA", module_path=Path("p/c.py"), class_name="C"
        )
    }

    llm_configs = {}
    manager.sync_all_configs(agents, workflows, custom_workflows, llm_configs)

    # Verify using the engine from the fixture
    with get_db_session(engine=setup_test_db) as db:
        assert db is not None
        assert db.get(AgentConfigDB, "AgentA") is not None
        assert db.get(AgentConfigDB, "AgentB") is not None
        assert db.get(WorkflowConfigDB, "WFA") is not None
        assert db.get(CustomWorkflowConfigDB, "CWFA") is not None
        assert db.query(AgentConfigDB).count() == 2
        assert db.query(WorkflowConfigDB).count() == 1
        assert db.query(CustomWorkflowConfigDB).count() == 1


# --- History Tests ---


def test_save_and_load_history_empty(
    setup_test_db, storage_manager_instance: StorageManager
):
    """Test loading history when none exists for a specific session."""
    manager = storage_manager_instance
    agent_name = "HistoryAgent1"
    session_id = "session_empty"
    # Test loading with session_id when no history exists
    history = manager.load_history(agent_name, session_id)
    assert history == []
    # Test loading without session_id (should return empty and log warning)
    history_no_session = manager.load_history(agent_name, None)
    assert history_no_session == []


def test_save_and_load_history_basic(
    setup_test_db, storage_manager_instance: StorageManager
):
    """Test saving and loading a simple conversation for a specific session."""
    manager = storage_manager_instance
    agent_name = "HistoryAgent2"
    session_id = "session_basic"
    conversation = [
        {"role": "user", "content": [{"type": "text", "text": "Hello"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "Hi there!"}]},
    ]

    # Test saving without session_id (should do nothing and log warning)
    manager.save_full_history(agent_name, None, conversation)
    assert (
        manager.load_history(agent_name, session_id) == []
    )  # Verify nothing was saved

    # Save with session_id
    manager.save_full_history(agent_name, session_id, conversation)

    # Load back and verify for the correct session
    loaded_history = manager.load_history(agent_name, session_id)
    assert len(loaded_history) == 2
    assert loaded_history[0]["role"] == "user"
    assert loaded_history[0]["content"] == [{"type": "text", "text": "Hello"}]
    assert loaded_history[1]["role"] == "assistant"
    assert loaded_history[1]["content"] == [{"type": "text", "text": "Hi there!"}]


def test_save_full_history_clears_previous(
    setup_test_db, storage_manager_instance: StorageManager
):
    """Test that save_full_history replaces existing history for a specific session."""
    manager = storage_manager_instance
    agent_name = "HistoryAgent3"
    session_id = "session_clear"
    conv1 = [{"role": "user", "content": [{"type": "text", "text": "First"}]}]
    conv2 = [{"role": "user", "content": [{"type": "text", "text": "Second"}]}]

    manager.save_full_history(agent_name, session_id, conv1)
    history1 = manager.load_history(agent_name, session_id)
    assert len(history1) == 1
    assert history1[0]["content"][0]["text"] == "First"

    manager.save_full_history(
        agent_name, session_id, conv2
    )  # Save again for the same session
    history2 = manager.load_history(agent_name, session_id)
    assert len(history2) == 1  # Should only contain conv2
    assert history2[0]["content"][0]["text"] == "Second"


def test_load_history_limit(setup_test_db, storage_manager_instance: StorageManager):
    """Test the limit parameter for loading history for a specific session."""
    manager = storage_manager_instance
    agent_name = "HistoryAgent4"
    session_id = "session_limit"
    conversation = [
        {"role": "user", "content": [{"type": "text", "text": "Turn 1"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "Turn 2"}]},
        {"role": "user", "content": [{"type": "text", "text": "Turn 3"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "Turn 4"}]},
    ]
    manager.save_full_history(agent_name, session_id, conversation)

    # Load last 2 turns for this session
    loaded_history = manager.load_history(agent_name, session_id, limit=2)
    assert len(loaded_history) == 2
    assert (
        loaded_history[0]["content"][0]["text"] == "Turn 3"
    )  # Should be the last N turns
    assert loaded_history[1]["content"][0]["text"] == "Turn 4"

    # Load last 5 turns (more than available) for this session
    loaded_history_more = manager.load_history(agent_name, session_id, limit=5)
    assert len(loaded_history_more) == 4  # Returns all available

    # Load with limit 0 (should return all?) for this session
    loaded_history_zero = manager.load_history(agent_name, session_id, limit=0)
    assert len(loaded_history_zero) == 4  # Limit 0 or less means no limit


def test_history_session_isolation(
    setup_test_db, storage_manager_instance: StorageManager
):
    """Test that history is isolated between different sessions for the same agent."""
    manager = storage_manager_instance
    agent_name = "HistoryAgent5"
    session_id_1 = "session_iso_1"
    session_id_2 = "session_iso_2"

    conv1 = [{"role": "user", "content": [{"type": "text", "text": "Session 1 Msg"}]}]
    conv2 = [{"role": "user", "content": [{"type": "text", "text": "Session 2 Msg"}]}]

    # Save history for session 1
    manager.save_full_history(agent_name, session_id_1, conv1)
    # Save history for session 2
    manager.save_full_history(agent_name, session_id_2, conv2)

    # Load history for session 1
    history1 = manager.load_history(agent_name, session_id_1)
    assert len(history1) == 1
    assert history1[0]["content"][0]["text"] == "Session 1 Msg"

    # Load history for session 2
    history2 = manager.load_history(agent_name, session_id_2)
    assert len(history2) == 1
    assert history2[0]["content"][0]["text"] == "Session 2 Msg"

    # Verify loading non-existent session returns empty
    history_other = manager.load_history(agent_name, "session_other")
    assert history_other == []


# TODO: Add tests for edge cases (e.g., invalid conversation format for saving)
# TODO: Add tests for error handling during DB operations (might require mocking session)
