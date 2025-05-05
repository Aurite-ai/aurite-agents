# tests/storage/test_db_manager.py
"""
Unit tests for the StorageManager class.

These tests should ideally use an in-memory SQLite database or mocking
to isolate the StorageManager logic from a live PostgreSQL instance.
"""

import pytest
import os
import sqlalchemy # Import sqlalchemy for create_engine patch
from pathlib import Path
from unittest.mock import patch, MagicMock

# Assuming models and manager are importable
from src.host.models import AgentConfig, WorkflowConfig, CustomWorkflowConfig
from src.storage.db_manager import StorageManager
from src.storage.db_models import Base, AgentConfigDB, WorkflowConfigDB, CustomWorkflowConfigDB, AgentHistoryDB
from src.storage.db_connection import get_engine, get_db_session, _engine, _SessionFactory

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
    # Declare upfront that we are modifying the module's globals
    global _engine, _SessionFactory

    # Store original values
    original_engine = _engine
    original_session_factory = _SessionFactory

    # Ensure module globals are reset for this test run
    _engine = None
    _SessionFactory = None

    # Patch environment for the DB connection logic
    with patch.dict(os.environ, {"AURITE_ENABLE_DB": "true"}):
        # Patch create_engine directly where it's called by get_engine
        # to force SQLite usage for this fixture.
        with patch('sqlalchemy.create_engine', return_value=sqlalchemy.create_engine(TEST_DB_URL)) as mock_create_engine:

            # Now, get the engine (which should use the patched create_engine)
            engine = get_engine() # This call should now use the mocked create_engine
            assert engine is not None, "Failed to create test engine using patched create_engine"
            # Verify the engine URL is indeed SQLite
            assert str(engine.url) == TEST_DB_URL, f"Engine URL mismatch: expected {TEST_DB_URL}, got {engine.url}"

            # Create tables for the SQLite engine
            try:
                Base.metadata.create_all(bind=engine)
                print("\nIn-memory SQLite DB tables created.")
                yield engine # Yield the engine for potential use, or just yield None
            finally:
                # Teardown: Drop tables and reset globals to original state
                print("\nTearing down in-memory SQLite DB...")
                if engine: # Check if engine was created before trying to drop
                    Base.metadata.drop_all(bind=engine)
                # Restore original module globals
                _engine = original_engine
                _SessionFactory = original_session_factory
                print("In-memory SQLite DB teardown complete.")


@pytest.fixture
def storage_manager_instance() -> StorageManager:
    """Provides a StorageManager instance connected to the test DB."""
    # The setup_test_db fixture ensures the engine is ready
    manager = StorageManager()
    assert manager._engine is not None, "StorageManager failed to get test engine"
    return manager

# --- Test Cases ---

# Note: These first two tests run *without* the setup_test_db fixture's effects
# because they test scenarios where the DB connection *should* fail or be disabled.
# We instantiate StorageManager directly within the patched context.

def test_storage_manager_init_no_db(monkeypatch):
    """Test StorageManager init when DB is disabled."""
    monkeypatch.setenv("AURITE_ENABLE_DB", "false")
    # Force reset of globals so they are re-evaluated by get_engine
    global _engine, _SessionFactory
    # Reset globals *before* instantiation within the patch
    global _engine, _SessionFactory
    _engine = None
    _SessionFactory = None

    # Patch the get_engine used by StorageManager's init
    with patch('src.storage.db_manager.get_engine', return_value=None):
        manager = StorageManager()
        assert manager._engine is None
    # Also test init_db doesn't raise error (it checks self._engine)
    manager.init_db() # Should log error but not fail test

def test_storage_manager_init_db_error(monkeypatch):
    """Test StorageManager init when DB URL is invalid."""
    monkeypatch.setenv("AURITE_ENABLE_DB", "true")
    # Patch get_database_url to return None simulating missing env vars
    # Reset globals *before* instantiation within the patch
    global _engine, _SessionFactory
    _engine = None
    _SessionFactory = None

    # Patch the get_engine used by StorageManager's init
    with patch('src.storage.db_manager.get_engine', return_value=None):
        manager = StorageManager()
        assert manager._engine is None
        # init_db should not raise error, just log
        manager.init_db() # Should log error but not fail test


# --- Config Sync Tests (These use the fixtures) ---

# Apply the setup_test_db fixture explicitly to tests needing the DB
def test_sync_agent_config_create(setup_test_db, storage_manager_instance: StorageManager):
    """Test creating a new agent config."""
    manager = storage_manager_instance
    agent_conf = AgentConfig(name="TestAgent1", model="test-model", system_prompt="Test prompt")

    manager.sync_agent_config(agent_conf)

    # Verify in DB
    with get_db_session() as db:
        assert db is not None
        db_record = db.get(AgentConfigDB, "TestAgent1")
        assert db_record is not None
        assert db_record.name == "TestAgent1"
        assert db_record.model == "test-model"
        assert db_record.system_prompt == "Test prompt"
        assert db_record.include_history is False # Default

def test_sync_agent_config_update(setup_test_db, storage_manager_instance: StorageManager):
    """Test updating an existing agent config."""
    manager = storage_manager_instance
    agent_conf1 = AgentConfig(name="TestAgent2", model="model-v1", temperature=0.5)
    manager.sync_agent_config(agent_conf1)

    # Verify initial state
    with get_db_session() as db:
        assert db is not None
        db_record1 = db.get(AgentConfigDB, "TestAgent2")
        assert db_record1 is not None
        assert db_record1.model == "model-v1"
        assert db_record1.temperature == 0.5

    # Update config
    agent_conf2 = AgentConfig(name="TestAgent2", model="model-v2", temperature=0.8, include_history=True)
    manager.sync_agent_config(agent_conf2)

    # Verify updated state
    with get_db_session() as db:
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
    wf_conf = WorkflowConfig(name="TestWF1", steps=["Agent1", "Agent2"], description="My WF")
    manager.sync_workflow_config(wf_conf)

    with get_db_session() as db:
        assert db is not None
        db_record = db.get(WorkflowConfigDB, "TestWF1")
        assert db_record is not None
        assert db_record.name == "TestWF1"
        assert db_record.steps == ["Agent1", "Agent2"] # Check JSONB list storage
        assert db_record.description == "My WF"

def test_sync_custom_workflow_config(setup_test_db, storage_manager_instance: StorageManager):
    """Test syncing a custom workflow config."""
    manager = storage_manager_instance
    # Note: Path object needs conversion for DB storage (handled by _sync_config)
    cwf_conf = CustomWorkflowConfig(name="TestCWF1", module_path=Path("path/to/workflow.py"), class_name="MyWorkflow")
    manager.sync_custom_workflow_config(cwf_conf)

    with get_db_session() as db:
        assert db is not None
        db_record = db.get(CustomWorkflowConfigDB, "TestCWF1")
        assert db_record is not None
        assert db_record.name == "TestCWF1"
        assert db_record.module_path == "path/to/workflow.py" # Stored as string
        assert db_record.class_name == "MyWorkflow"

def test_sync_all_configs(setup_test_db, storage_manager_instance: StorageManager):
    """Test syncing multiple configs at once."""
    manager = storage_manager_instance
    agents = {"AgentA": AgentConfig(name="AgentA", model="a"), "AgentB": AgentConfig(name="AgentB", model="b")}
    workflows = {"WFA": WorkflowConfig(name="WFA", steps=["AgentA"])}
    custom_workflows = {"CWFA": CustomWorkflowConfig(name="CWFA", module_path=Path("p/c.py"), class_name="C")}

    manager.sync_all_configs(agents, workflows, custom_workflows)

    with get_db_session() as db:
        assert db is not None
        assert db.get(AgentConfigDB, "AgentA") is not None
        assert db.get(AgentConfigDB, "AgentB") is not None
        assert db.get(WorkflowConfigDB, "WFA") is not None
        assert db.get(CustomWorkflowConfigDB, "CWFA") is not None
        assert db.query(AgentConfigDB).count() == 2
        assert db.query(WorkflowConfigDB).count() == 1
        assert db.query(CustomWorkflowConfigDB).count() == 1

# --- History Tests ---

def test_save_and_load_history_empty(setup_test_db, storage_manager_instance: StorageManager):
    """Test loading history when none exists."""
    manager = storage_manager_instance
    history = manager.load_history("HistoryAgent1")
    assert history == []

def test_save_and_load_history_basic(setup_test_db, storage_manager_instance: StorageManager):
    """Test saving and loading a simple conversation."""
    manager = storage_manager_instance
    agent_name = "HistoryAgent2"
    conversation = [
        {"role": "user", "content": [{"type": "text", "text": "Hello"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "Hi there!"}]},
    ]

    manager.save_full_history(agent_name, conversation)

    # Load back and verify
    loaded_history = manager.load_history(agent_name)
    assert len(loaded_history) == 2
    assert loaded_history[0]["role"] == "user"
    assert loaded_history[0]["content"] == [{"type": "text", "text": "Hello"}]
    assert loaded_history[1]["role"] == "assistant"
    assert loaded_history[1]["content"] == [{"type": "text", "text": "Hi there!"}]

def test_save_full_history_clears_previous(setup_test_db, storage_manager_instance: StorageManager):
    """Test that save_full_history replaces existing history."""
    manager = storage_manager_instance
    agent_name = "HistoryAgent3"
    conv1 = [{"role": "user", "content": [{"type": "text", "text": "First"}]}]
    conv2 = [{"role": "user", "content": [{"type": "text", "text": "Second"}]}]

    manager.save_full_history(agent_name, conv1)
    history1 = manager.load_history(agent_name)
    assert len(history1) == 1
    assert history1[0]["content"][0]["text"] == "First"

    manager.save_full_history(agent_name, conv2)
    history2 = manager.load_history(agent_name)
    assert len(history2) == 1 # Should only contain conv2
    assert history2[0]["content"][0]["text"] == "Second"

def test_load_history_limit(setup_test_db, storage_manager_instance: StorageManager):
    """Test the limit parameter for loading history."""
    manager = storage_manager_instance
    agent_name = "HistoryAgent4"
    conversation = [
        {"role": "user", "content": [{"type": "text", "text": "Turn 1"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "Turn 2"}]},
        {"role": "user", "content": [{"type": "text", "text": "Turn 3"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "Turn 4"}]},
    ]
    manager.save_full_history(agent_name, conversation)

    # Load last 2 turns
    loaded_history = manager.load_history(agent_name, limit=2)
    assert len(loaded_history) == 2
    assert loaded_history[0]["content"][0]["text"] == "Turn 3" # Should be the last N turns
    assert loaded_history[1]["content"][0]["text"] == "Turn 4"

    # Load last 5 turns (more than available)
    loaded_history_more = manager.load_history(agent_name, limit=5)
    assert len(loaded_history_more) == 4 # Returns all available

    # Load with limit 0 (should return all?) - Check behavior
    loaded_history_zero = manager.load_history(agent_name, limit=0)
    assert len(loaded_history_zero) == 4 # Limit 0 or less means no limit

# TODO: Add tests for edge cases (e.g., invalid conversation format for saving)
# TODO: Add tests for error handling during DB operations (might require mocking session)
