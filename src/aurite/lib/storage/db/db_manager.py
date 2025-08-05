# src/storage/db_manager.py
"""
Provides the StorageManager class to interact with the database
for persisting configurations and agent history.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func
from sqlalchemy.engine import Engine
from sqlalchemy.orm.session import Session

from .db_connection import create_db_engine, get_db_session
from .db_models import AgentHistoryDB, ComponentDB
from .db_models import Base as SQLAlchemyBase

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Manages database interactions for storing and retrieving configurations
    and agent conversation history.
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
            logger.info(f"StorageManager initialized with provided engine: {self._engine.url}")
        else:
            # Attempt to create default engine if none provided
            logger.info("No engine provided to StorageManager, attempting to create default engine.")
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

        logger.info("Initializing database schema...")
        try:
            SQLAlchemyBase.metadata.create_all(bind=self._engine)  # Use the alias
            logger.info("Database schema initialized successfully.")
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

    # --- History Methods ---

    # NOTE: Making these synchronous for now as SQLAlchemy session operations
    # within the context manager are typically synchronous. If async driver (e.g., asyncpg)
    # and async sessions are used later, these would need `async def`.
    def load_history(self, agent_name: str, session_id: Optional[str], limit: int = 50) -> List[Dict[str, Any]]:
        """
        Loads recent conversation history for a specific agent and session.
        Returns history in the format expected by Anthropic API messages:
        List[{'role': str, 'content': List[Dict[str, Any]]}]
        """
        if not self._engine:
            return []
        if not session_id:
            logger.warning(
                f"Attempted to load history for agent '{agent_name}' without a session_id. Returning empty list."
            )
            return []

        logger.debug(f"Loading history for agent '{agent_name}', session '{session_id}' (limit: {limit})")
        history_params: List[Dict[str, Any]] = []
        # Pass the engine to get_db_session
        with get_db_session(engine=self._engine) as db:
            if db:
                try:
                    # Query AgentHistoryDB, filter by agent_name AND session_id, order by timestamp ascending
                    # Order ascending so the list is in chronological order for the LLM
                    history_records = (
                        db.query(AgentHistoryDB)
                        .filter(
                            AgentHistoryDB.agent_name == agent_name,
                            AgentHistoryDB.session_id == session_id,  # Added session_id filter
                        )
                        .order_by(AgentHistoryDB.timestamp.asc())
                        # Consider if limit should be applied here or after fetching all?
                        # Applying limit here is more efficient for large histories.
                        # If we need the *most recent* N turns, order by desc() and limit().
                        # Let's assume we want the start of the conversation up to N turns for now.
                        # .limit(limit) # Revisit if we need *last* N turns
                        .all()
                    )

                    # Convert results to the required format
                    for record in history_records:
                        # Ensure content is loaded correctly from the correct column
                        content_data = record.content_json  # Read from content_json column
                        parsed_content = None
                        if isinstance(content_data, str):
                            # Attempt to parse if stored as a JSON string
                            try:
                                parsed_content = json.loads(content_data)  # Parse string
                            except json.JSONDecodeError:
                                # If parsing fails, assume it was a raw string user input
                                logger.warning(
                                    f"Failed to parse content_json for history ID {record.id} as JSON. Assuming raw string content."
                                )
                                # Format the raw string into the expected structure
                                parsed_content = [{"type": "text", "text": content_data}]
                        elif content_data is None:
                            logger.warning(f"History record ID {record.id} has null content_json.")
                            parsed_content = [{"type": "text", "text": "[Missing content]"}]
                        else:
                            # If content_data is already a list/dict (from native JSON type), use it directly
                            parsed_content = content_data

                        history_params.append(
                            {
                                "role": record.role,
                                "content": parsed_content,  # Use the processed content
                            }
                        )

                    # If we wanted only the last N turns:
                    if len(history_params) > limit > 0:
                        history_params = history_params[-limit:]  # Slice to get the last N items

                    logger.debug(
                        f"Loaded {len(history_params)} history turns for agent '{agent_name}', session '{session_id}'."
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to load history for agent '{agent_name}', session '{session_id}': {e}",
                        exc_info=True,
                    )
                    # Return empty list on error
                    return []
            else:
                logger.error("Failed to get DB session for loading history.")
                return []  # Return empty list if session fails

        return history_params

    def save_full_history(
        self,
        agent_name: str,
        session_id: Optional[str],
        conversation: List[Dict[str, Any]],
    ):
        """
        Saves the entire conversation history for a specific agent and session.
        Clears previous history for that specific agent/session before saving the new one.
        """
        if not self._engine:
            return
        if not session_id:
            logger.warning(f"Attempted to save history for agent '{agent_name}' without a session_id. Skipping save.")
            return

        # Filter out any potential None values in conversation list defensively
        valid_conversation = [turn for turn in conversation if turn is not None]
        if not valid_conversation:
            logger.warning(
                f"Attempted to save empty or invalid history for agent '{agent_name}', session '{session_id}'. Skipping."
            )
            return

        logger.debug(
            f"Saving full history for agent '{agent_name}', session '{session_id}' ({len(valid_conversation)} turns)"
        )
        # Pass the engine to get_db_session
        with get_db_session(engine=self._engine) as db:
            if db:
                try:
                    # Delete existing history for this agent and session first
                    # Use functional delete
                    delete_stmt = delete(AgentHistoryDB).where(
                        AgentHistoryDB.agent_name == agent_name,
                        AgentHistoryDB.session_id == session_id,
                    )
                    db.execute(delete_stmt)
                    logger.debug(f"Cleared previous history for agent '{agent_name}', session '{session_id}'.")

                    # Add new history turns
                    new_history_records = []
                    for turn in valid_conversation:
                        # Ensure content is serializable (should be dict/list from Anthropic)
                        content_to_save = turn.get("content")
                        role = turn.get("role")

                        if not role or content_to_save is None:
                            logger.warning(
                                f"Skipping history turn with missing role or content for agent '{agent_name}': {turn}"
                            )
                            continue

                        new_history_records.append(
                            AgentHistoryDB(
                                agent_name=agent_name,
                                session_id=session_id,  # Added session_id
                                role=role,
                                content_json=content_to_save,  # Correctly map to content_json column
                            )
                        )

                    if new_history_records:
                        db.add_all(new_history_records)
                        logger.debug(
                            f"Added {len(new_history_records)} new history turns for agent '{agent_name}', session '{session_id}'."
                        )

                    # Commit happens automatically via context manager
                except Exception as e:
                    logger.error(
                        f"Failed to save history for agent '{agent_name}', session '{session_id}': {e}",
                        exc_info=True,
                    )
                    # Rollback happens automatically via context manager
            else:
                logger.error("Failed to get DB session for saving history.")

    def get_session_history(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get history for a specific session regardless of agent.
        Returns history in the format expected by Anthropic API messages.
        """
        if not self._engine:
            return None

        logger.debug(f"Getting history for session '{session_id}'")
        history_params: List[Dict[str, Any]] = []

        with get_db_session(engine=self._engine) as db:
            if db:
                try:
                    # Query by session_id only, ordered by timestamp
                    history_records = (
                        db.query(AgentHistoryDB)
                        .filter(AgentHistoryDB.session_id == session_id)
                        .order_by(AgentHistoryDB.timestamp.asc())
                        .all()
                    )

                    # Convert to Anthropic format
                    for record in history_records:
                        content_data = record.content_json
                        parsed_content = None

                        if isinstance(content_data, str):
                            try:
                                parsed_content = json.loads(content_data)
                            except json.JSONDecodeError:
                                parsed_content = [{"type": "text", "text": content_data}]
                        elif content_data is None:
                            parsed_content = [{"type": "text", "text": "[Missing content]"}]
                        else:
                            parsed_content = content_data

                        history_params.append(
                            {
                                "role": record.role,
                                "content": parsed_content,
                            }
                        )

                    return history_params if history_params else None

                except Exception as e:
                    logger.error(f"Failed to get session history for '{session_id}': {e}", exc_info=True)
                    return None
            else:
                logger.error("Failed to get DB session for session history.")
                return None

    def get_sessions_by_agent(self, agent_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List all sessions for a specific agent with metadata.
        Applies retention policy during retrieval.
        """
        if not self._engine:
            return []

        logger.debug(f"Getting sessions for agent '{agent_name}' (limit: {limit})")
        sessions = []

        with get_db_session(engine=self._engine) as db:
            if db:
                try:
                    # First, apply retention policy
                    self.cleanup_old_sessions()

                    # Get distinct sessions with metadata
                    session_data = (
                        db.query(
                            AgentHistoryDB.session_id,
                            func.min(AgentHistoryDB.timestamp).label("created_at"),
                            func.max(AgentHistoryDB.timestamp).label("last_updated"),
                            func.count(AgentHistoryDB.id).label("message_count"),
                        )
                        .filter(AgentHistoryDB.agent_name == agent_name)
                        .group_by(AgentHistoryDB.session_id)
                        .order_by(func.max(AgentHistoryDB.timestamp).desc())
                        .limit(limit)
                        .all()
                    )

                    for row in session_data:
                        sessions.append(
                            {
                                "session_id": row.session_id,
                                "agent_name": agent_name,
                                "created_at": row.created_at.isoformat() if row.created_at else None,
                                "last_updated": row.last_updated.isoformat() if row.last_updated else None,
                                "message_count": row.message_count,
                            }
                        )

                    return sessions

                except Exception as e:
                    logger.error(f"Failed to get sessions for agent '{agent_name}': {e}", exc_info=True)
                    return []
            else:
                logger.error("Failed to get DB session for agent sessions.")
                return []

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a specific session's history.
        Returns True if any records were deleted, False otherwise.
        """
        if not self._engine:
            return False

        logger.debug(f"Deleting session '{session_id}'")

        with get_db_session(engine=self._engine) as db:
            if db:
                try:
                    # Delete all history records for this session
                    delete_stmt = delete(AgentHistoryDB).where(AgentHistoryDB.session_id == session_id)
                    result = db.execute(delete_stmt)
                    deleted_count = result.rowcount

                    if deleted_count > 0:
                        logger.info(f"Deleted {deleted_count} history records for session '{session_id}'")
                        return True
                    else:
                        logger.debug(f"No records found for session '{session_id}'")
                        return False

                except Exception as e:
                    logger.error(f"Failed to delete session '{session_id}': {e}", exc_info=True)
                    return False
            else:
                logger.error("Failed to get DB session for session deletion.")
                return False

    def get_session_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a session including timestamps and message count.
        """
        if not self._engine:
            return None

        logger.debug(f"Getting metadata for session '{session_id}'")

        with get_db_session(engine=self._engine) as db:
            if db:
                try:
                    # Get session metadata
                    metadata = (
                        db.query(
                            AgentHistoryDB.agent_name,
                            func.min(AgentHistoryDB.timestamp).label("created_at"),
                            func.max(AgentHistoryDB.timestamp).label("last_updated"),
                            func.count(AgentHistoryDB.id).label("message_count"),
                        )
                        .filter(AgentHistoryDB.session_id == session_id)
                        .group_by(AgentHistoryDB.agent_name)
                        .first()
                    )

                    if metadata:
                        return {
                            "session_id": session_id,
                            "agent_name": metadata.agent_name,
                            "created_at": metadata.created_at.isoformat() if metadata.created_at else None,
                            "last_updated": metadata.last_updated.isoformat() if metadata.last_updated else None,
                            "message_count": metadata.message_count,
                        }
                    else:
                        return None

                except Exception as e:
                    logger.error(f"Failed to get metadata for session '{session_id}': {e}", exc_info=True)
                    return None
            else:
                logger.error("Failed to get DB session for session metadata.")
                return None

    def cleanup_old_sessions(self, days: int = 30, max_sessions: int = 50):
        """
        Clean up old sessions based on retention policy.
        Deletes sessions older than specified days and keeps only the most recent max_sessions.
        """
        if not self._engine:
            return

        logger.debug(f"Cleaning up sessions older than {days} days, keeping max {max_sessions}")

        with get_db_session(engine=self._engine) as db:
            if db:
                try:
                    cutoff_date = datetime.utcnow() - timedelta(days=days)

                    # First, delete sessions older than cutoff date
                    old_sessions = (
                        db.query(AgentHistoryDB.session_id)
                        .filter(AgentHistoryDB.timestamp < cutoff_date)
                        .distinct()
                        .all()
                    )

                    for session in old_sessions:
                        delete_stmt = delete(AgentHistoryDB).where(AgentHistoryDB.session_id == session.session_id)
                        db.execute(delete_stmt)

                    if old_sessions:
                        logger.info(f"Deleted {len(old_sessions)} sessions older than {days} days")

                    # Then, check if we have too many sessions
                    session_count = db.query(func.count(func.distinct(AgentHistoryDB.session_id))).scalar()

                    if session_count > max_sessions:
                        # Get sessions to keep (most recent)
                        sessions_to_keep = (
                            db.query(
                                AgentHistoryDB.session_id, func.max(AgentHistoryDB.timestamp).label("last_updated")
                            )
                            .group_by(AgentHistoryDB.session_id)
                            .order_by(func.max(AgentHistoryDB.timestamp).desc())
                            .limit(max_sessions)
                            .subquery()
                        )

                        # Delete sessions not in the keep list
                        delete_stmt = delete(AgentHistoryDB).where(
                            ~AgentHistoryDB.session_id.in_(db.query(sessions_to_keep.c.session_id))
                        )
                        result = db.execute(delete_stmt)

                        if result.rowcount > 0:
                            logger.info(f"Deleted {result.rowcount} records to maintain {max_sessions} session limit")

                except Exception as e:
                    logger.error(f"Failed to cleanup old sessions: {e}", exc_info=True)
