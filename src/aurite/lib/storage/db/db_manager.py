# src/storage/db_manager.py
"""
Provides the StorageManager class to interact with the database
for persisting configurations and session data.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.engine import Engine
from sqlalchemy.orm.session import Session

from .db_connection import create_db_engine, get_db_session
from .db_models import Base as SQLAlchemyBase
from .db_models import ComponentDB, SessionDB

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Manages database interactions for storing and retrieving configurations
    and session data (including agent conversation history).
    """

    def __init__(self, engine: Optional[Engine] = None):
        """
        Initializes the StorageManager.

        Args:
            engine: An optional SQLAlchemy Engine instance. If None, attempts
                    to create a default engine using environment variables.
        """
        if engine:
            self._engine = engine
            logger.info("StorageManager initialized with provided engine.")
        else:
            # Attempt to create default engine if none provided
            logger.debug("No engine provided to StorageManager, attempting to create default engine.")
            self._engine = create_db_engine()  # type: ignore[assignment] # Ignore None vs Engine mismatch

        if not self._engine:
            logger.warning(
                "StorageManager initialized, but DB engine is not available (either not provided or creation failed). Persistence will be disabled."
            )
        # No else needed, create_db_engine logs success if it returns an engine

    def init_db(self):
        """
        Initializes the database by creating tables defined in db_models.
        Should be called once during application startup if DB is enabled.
        """
        if not self._engine:
            logger.error("Cannot initialize database: DB engine is not available.")
            return

        logger.debug("Initializing database schema...")
        try:
            SQLAlchemyBase.metadata.create_all(bind=self._engine)  # Use the alias
            logger.debug("Database schema initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}", exc_info=True)
            # Depending on the error, we might want to raise it
            # For now, log the error and continue; subsequent operations will likely fail.

    # --- Configuration Sync Methods ---

    def _upsert_component(self, db: Session, component_type: str, config: Dict[str, Any]):
        """
        Helper to create or update a single component in the database.
        """
        component_name = config.get("name")
        if not component_name:
            logger.warning(f"Skipping component of type '{component_type}' due to missing 'name'.")
            return

        # Attempt to find existing record
        db_record = db.get(ComponentDB, component_name)

        # Serialize config to JSON-compatible format
        # Pydantic's model_dump_json can be useful here if we have the model instance
        # For now, we assume `config` is a dict that can be serialized.
        # A more robust solution would handle non-serializable types like Path.
        serializable_config = json.loads(json.dumps(config, default=str))

        if db_record:
            # Update existing record
            if db_record.component_type != component_type:
                logger.warning(
                    f"Component '{component_name}' exists with type '{db_record.component_type}', "
                    f"but trying to update with type '{component_type}'. Skipping update."
                )
                return
            logger.debug(f"Updating existing component record for '{component_name}'")
            db_record.config = serializable_config
        else:
            # Create new record
            logger.debug(f"Creating new component record for '{component_name}'")
            db_record = ComponentDB(
                name=component_name,
                component_type=component_type,
                config=serializable_config,
            )
            db.add(db_record)

    def sync_index_to_db(self, component_index: Dict[str, Dict[str, Dict[str, Any]]]):
        """
        Syncs a component index to the database in a single transaction.
        This will add new components and update existing ones.
        """
        if not self._engine:
            logger.warning("Database not configured. Skipping config sync.")
            return

        logger.info("Syncing component index to database...")
        with get_db_session(engine=self._engine) as db:
            if not db:
                logger.error("Failed to get DB session for config sync.")
                return

            try:
                total_synced = 0
                for component_type, components in component_index.items():
                    for component_config in components.values():
                        self._upsert_component(db, component_type, component_config)
                        total_synced += 1
                logger.info(f"Successfully synced {total_synced} components to the database.")
            except Exception as e:
                logger.error(f"Failed during bulk component sync: {e}", exc_info=True)
                # Rollback is handled by the context manager

    def load_index_from_db(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Loads the entire component index from the database.
        """
        if not self._engine:
            logger.warning("Database not configured. Returning empty index.")
            return {}

        logger.info("Loading component index from database...")
        component_index: Dict[str, Dict[str, Dict[str, Any]]] = {}
        with get_db_session(engine=self._engine) as db:
            if not db:
                logger.error("Failed to get DB session for loading index.")
                return {}

            try:
                all_components = db.query(ComponentDB).all()
                for record in all_components:
                    component_type = record.component_type
                    component_name = record.name
                    config = record.config

                    # Ensure the component type key exists
                    component_index.setdefault(component_type, {})
                    component_index[component_type][component_name] = config

                logger.info(f"Successfully loaded {len(all_components)} components from the database.")
                return component_index
            except Exception as e:
                logger.error(f"Failed to load component index from database: {e}", exc_info=True)
                return {}

    def delete_component(self, component_name: str) -> bool:
        """
        Deletes a component from the database.
        """
        if not self._engine:
            logger.warning("Database not configured. Cannot delete component.")
            return False

        logger.info(f"Deleting component '{component_name}' from database...")
        with self.get_db_session() as db:
            if not db:
                logger.error("Failed to get DB session for component deletion.")
                return False

            try:
                # Find the record to delete
                db_record = db.get(ComponentDB, component_name)
                if db_record:
                    db.delete(db_record)
                    logger.info(f"Successfully deleted component '{component_name}'.")
                    return True
                else:
                    logger.warning(f"Component '{component_name}' not found in database.")
                    return False
            except Exception as e:
                logger.error(f"Failed to delete component '{component_name}': {e}", exc_info=True)
                return False

    def get_db_session(self):
        """
        Provides a transactional database session context.
        """
        return get_db_session(self._engine)

    # --- Session Management Methods (NEW) ---

    def save_session(self, session_data: Dict[str, Any]) -> bool:
        """
        Saves a complete session to the database.

        Args:
            session_data: Complete session data including execution_result and metadata

        Returns:
            True if saved successfully, False otherwise
        """
        if not self._engine:
            logger.debug("Database not configured. Cannot save session.")
            return False

        session_id = session_data.get("session_id")
        if not session_id:
            logger.warning("Cannot save session without session_id")
            return False

        logger.debug(f"Saving session '{session_id}' to database")

        with get_db_session(engine=self._engine) as db:
            if not db:
                logger.error("Failed to get DB session for saving session")
                return False

            try:
                # Check if session already exists
                existing = db.get(SessionDB, session_id)

                if existing:
                    # Update existing session
                    existing.base_session_id = session_data.get("base_session_id")
                    existing.name = session_data.get("name", "Unknown")
                    existing.result_type = session_data.get("result_type", "agent")
                    existing.is_workflow = session_data.get("result_type") == "workflow"
                    existing.message_count = session_data.get("message_count", 0)
                    existing.execution_result = session_data.get("execution_result", {})
                    existing.agents_involved = session_data.get("agents_involved")
                    existing.last_updated = datetime.utcnow()
                    logger.debug(f"Updated existing session '{session_id}' in database")
                else:
                    # Create new session
                    new_session = SessionDB(
                        session_id=session_id,
                        base_session_id=session_data.get("base_session_id"),
                        name=session_data.get("name", "Unknown"),
                        result_type=session_data.get("result_type", "agent"),
                        is_workflow=session_data.get("result_type") == "workflow",
                        message_count=session_data.get("message_count", 0),
                        execution_result=session_data.get("execution_result", {}),
                        agents_involved=session_data.get("agents_involved"),
                        created_at=datetime.fromisoformat(session_data["created_at"])
                        if "created_at" in session_data and session_data["created_at"]
                        else datetime.utcnow(),
                        last_updated=datetime.fromisoformat(session_data["last_updated"])
                        if "last_updated" in session_data and session_data["last_updated"]
                        else datetime.utcnow(),
                    )
                    db.add(new_session)
                    logger.debug(f"Created new session '{session_id}' in database")

                return True

            except Exception as e:
                logger.error(f"Failed to save session '{session_id}': {e}", exc_info=True)
                return False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a complete session from the database.

        Args:
            session_id: The session ID to retrieve

        Returns:
            Complete session data as a dictionary, or None if not found
        """
        if not self._engine:
            return None

        logger.debug(f"Loading session '{session_id}' from database")

        with get_db_session(engine=self._engine) as db:
            if not db:
                logger.error("Failed to get DB session for loading session")
                return None

            try:
                session = db.get(SessionDB, session_id)
                if session:
                    return {
                        "session_id": session.session_id,
                        "base_session_id": session.base_session_id,
                        "execution_result": session.execution_result,
                        "result_type": session.result_type,
                        "created_at": session.created_at.isoformat() if session.created_at else None,
                        "last_updated": session.last_updated.isoformat() if session.last_updated else None,
                        "name": session.name,
                        "message_count": session.message_count,
                        "agents_involved": session.agents_involved,
                    }
                return None

            except Exception as e:
                logger.error(f"Failed to load session '{session_id}': {e}", exc_info=True)
                return None

    def get_sessions_list(
        self, agent_name: Optional[str] = None, workflow_name: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Lists sessions with optional filtering.

        Args:
            agent_name: Filter by agent name
            workflow_name: Filter by workflow name
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (list of session metadata dictionaries, total count)
        """
        if not self._engine:
            return [], 0

        logger.debug(f"Listing sessions (agent={agent_name}, workflow={workflow_name}, limit={limit}, offset={offset})")

        with get_db_session(engine=self._engine) as db:
            if not db:
                logger.error("Failed to get DB session for listing sessions")
                return [], 0

            try:
                # Build base query
                query = db.query(SessionDB)

                if workflow_name:
                    query = query.filter(SessionDB.is_workflow is True, SessionDB.name == workflow_name)
                elif agent_name:
                    query = query.filter(SessionDB.is_workflow is False, SessionDB.name == agent_name)

                # Get total count before pagination
                total_count = query.count()

                # Order by last_updated descending
                query = query.order_by(SessionDB.last_updated.desc())

                # Apply pagination
                query = query.offset(offset).limit(limit)

                sessions = []
                for session in query.all():
                    sessions.append(
                        {
                            "session_id": session.session_id,
                            "base_session_id": session.base_session_id,
                            "name": session.name,
                            "result_type": session.result_type,
                            "is_workflow": session.is_workflow,
                            "message_count": session.message_count,
                            "agents_involved": session.agents_involved,
                            "created_at": session.created_at.isoformat() if session.created_at else None,
                            "last_updated": session.last_updated.isoformat() if session.last_updated else None,
                        }
                    )

                return sessions, total_count

            except Exception as e:
                logger.error(f"Failed to list sessions: {e}", exc_info=True)
                return [], 0

    def delete_session(self, session_id: str) -> bool:
        """
        Deletes a session from the database.

        Args:
            session_id: The session to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self._engine:
            return False

        logger.debug(f"Deleting session '{session_id}' from database")

        with get_db_session(engine=self._engine) as db:
            if not db:
                logger.error("Failed to get DB session for deleting session")
                return False

            try:
                session = db.get(SessionDB, session_id)
                if session:
                    # If it's a workflow, also delete child sessions
                    if session.is_workflow and session.base_session_id:
                        child_sessions = (
                            db.query(SessionDB)
                            .filter(
                                SessionDB.base_session_id == session.base_session_id, SessionDB.session_id != session_id
                            )
                            .all()
                        )
                        for child in child_sessions:
                            db.delete(child)
                            logger.debug(f"Deleted child session '{child.session_id}'")

                    db.delete(session)
                    logger.info(f"Deleted session '{session_id}' from database")
                    return True
                else:
                    logger.debug(f"Session '{session_id}' not found in database")
                    return False

            except Exception as e:
                logger.error(f"Failed to delete session '{session_id}': {e}", exc_info=True)
                return False

    def cleanup_old_sessions(self, days: int = 30, max_sessions: int = 50):
        """
        Clean up old sessions based on retention policy.

        Args:
            days: Delete sessions older than this many days
            max_sessions: Maximum number of sessions to keep
        """
        if not self._engine:
            return

        logger.debug(f"Cleaning up sessions older than {days} days, keeping max {max_sessions}")

        with get_db_session(engine=self._engine) as db:
            if not db:
                logger.error("Failed to get DB session for cleanup")
                return

            try:
                cutoff_date = datetime.utcnow() - timedelta(days=days)

                # Delete old sessions
                old_sessions = db.query(SessionDB).filter(SessionDB.last_updated < cutoff_date).all()

                for session in old_sessions:
                    db.delete(session)

                if old_sessions:
                    logger.info(f"Deleted {len(old_sessions)} sessions older than {days} days")

                # Check if we have too many sessions
                session_count = db.query(func.count(SessionDB.session_id)).scalar()

                if session_count > max_sessions:
                    # Get sessions to delete (oldest first)
                    sessions_to_delete = (
                        db.query(SessionDB)
                        .order_by(SessionDB.last_updated.asc())
                        .limit(session_count - max_sessions)
                        .all()
                    )

                    for session in sessions_to_delete:
                        db.delete(session)

                    if sessions_to_delete:
                        logger.info(
                            f"Deleted {len(sessions_to_delete)} sessions to maintain {max_sessions} session limit"
                        )

            except Exception as e:
                logger.error(f"Failed to cleanup old sessions: {e}", exc_info=True)

    # --- Legacy History Methods (DEPRECATED) ---
    # These methods are kept for backward compatibility but should not be used for new code

    def load_history(self, agent_name: str, session_id: Optional[str], limit: int = 50) -> List[Dict[str, Any]]:
        """
        DEPRECATED: Use get_session() instead.
        Loads recent conversation history for a specific agent and session.
        """
        logger.warning("load_history is deprecated. Use get_session() instead.")
        if not session_id:
            return []

        session_data = self.get_session(session_id)
        if session_data and "execution_result" in session_data:
            result = session_data["execution_result"]
            if "conversation_history" in result:
                history = result["conversation_history"]
                return history[-limit:] if len(history) > limit else history
        return []

    def save_full_history(
        self,
        agent_name: str,
        session_id: Optional[str],
        conversation: List[Dict[str, Any]],
    ):
        """
        DEPRECATED: Use save_session() instead.
        Saves the entire conversation history for a specific agent and session.
        """
        logger.warning("save_full_history is deprecated. Use save_session() instead.")
        if not session_id:
            return

        # Convert to new session format
        session_data = {
            "session_id": session_id,
            "name": agent_name,
            "result_type": "agent",
            "execution_result": {
                "conversation_history": conversation,
                "agent_name": agent_name,
            },
            "message_count": len(conversation),
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
        }
        self.save_session(session_data)

    def get_session_history(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        DEPRECATED: Use get_session() instead.
        Get history for a specific session regardless of agent.
        """
        logger.warning("get_session_history is deprecated. Use get_session() instead.")
        session_data = self.get_session(session_id)
        if session_data and "execution_result" in session_data:
            result = session_data["execution_result"]
            if "conversation_history" in result:
                return result["conversation_history"]
        return None
