# src/storage/db_manager.py
"""
Provides the StorageManager class to interact with the database
for persisting configurations and agent history.
"""

import json # Added import
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

# Assuming models are accessible from here
from ..host.models import (
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
)

# Import DB connection utilities and models
from .db_connection import get_db_session, get_engine
from .db_models import Base, AgentConfigDB, WorkflowConfigDB, CustomWorkflowConfigDB, AgentHistoryDB

logger = logging.getLogger(__name__)

class StorageManager:
    """
    Manages database interactions for storing and retrieving configurations
    and agent conversation history.
    """

    def __init__(self):
        """Initializes the StorageManager."""
        # Engine and session factory are managed globally in db_connection
        # We might store the engine locally if needed, but primarily use get_db_session
        self._engine = get_engine()
        if not self._engine:
            logger.warning("StorageManager initialized, but DB engine is not available. Persistence will be disabled.")
        else:
            logger.info("StorageManager initialized with available DB engine.")

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
            Base.metadata.create_all(bind=self._engine)
            logger.info("Database schema initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}", exc_info=True)
            # Depending on the error, we might want to raise it
            # For now, log the error and continue; subsequent operations will likely fail.

    # --- Configuration Sync Methods ---

    def _sync_config(self, db_session, db_model_cls, pydantic_config, pk_field='name'):
        """Generic helper to sync a single Pydantic config to a DB model."""
        pk_value = getattr(pydantic_config, pk_field)
        db_record = db_session.get(db_model_cls, pk_value)

        # Prepare data from Pydantic model, converting types as needed
        data_to_save = {}
        # Map Pydantic field names to DB column names where they differ
        field_map = {
            "client_ids": "client_ids_json",
            "exclude_components": "exclude_components_json",
            "steps": "steps_json",
            "content": "content_json", # Added mapping for history content
            # Add other mappings here if needed in the future
        }

        for db_col_name, model_field in db_model_cls.__table__.columns.items():
            # Skip primary key and timestamp fields managed by DB/SQLAlchemy
            if model_field.primary_key or db_col_name in ['created_at', 'last_updated']:
                continue

            # Determine the corresponding Pydantic field name
            pydantic_field_name = db_col_name
            # Find the Pydantic name if the DB column name is in the map's values
            for p_name, db_name in field_map.items():
                if db_name == db_col_name:
                    pydantic_field_name = p_name
                    break # Found the mapping

            # Get value from Pydantic config using the determined field name
            pydantic_value = getattr(pydantic_config, pydantic_field_name, None)

            # Handle specific type conversions before adding to data_to_save
            if isinstance(pydantic_value, Path):
                # Store Path as string using the DB column name
                data_to_save[db_col_name] = str(pydantic_value)
            elif isinstance(pydantic_value, (list, dict)):
                # Check if the DB column is intended for JSON
                if db_col_name.endswith('_json'):
                    # Store list/dict directly using the DB column name
                    data_to_save[db_col_name] = pydantic_value
                else:
                    # Log a warning if trying to save list/dict to non-JSON field
                    logger.warning(
                        f"Attempting to save list/dict from pydantic field '{pydantic_field_name}' "
                        f"to non-JSON DB column '{db_col_name}' for {db_model_cls.__name__} '{pk_value}'. Skipping."
                    )
            elif pydantic_value is not None:
                 # Store other types directly using the DB column name
                 data_to_save[db_col_name] = pydantic_value
            # If pydantic_value is None, we don't add it to data_to_save,
            # allowing DB defaults or existing values (on update) to persist.

        # Now, apply the prepared data_to_save to the DB record
        if db_record:
            # Update existing record
            logger.debug(f"Updating existing {db_model_cls.__name__} record for '{pk_value}'")
            for key, value in data_to_save.items():
                setattr(db_record, key, value)
            # last_updated is handled by onupdate=datetime.utcnow
        else:
            # Create new record
            logger.debug(f"Creating new {db_model_cls.__name__} record for '{pk_value}'")
            # Add the primary key value for creation
            data_to_save[pk_field] = pk_value
            # Create instance using the prepared data
            db_record = db_model_cls(**data_to_save)
            db_session.add(db_record)
        # Commit is handled by the get_db_session context manager

    def sync_agent_config(self, config: AgentConfig):
        """Saves or updates an AgentConfig in the database."""
        if not self._engine: return # Do nothing if DB is not configured
        with get_db_session() as db:
            if db:
                try:
                    self._sync_config(db, AgentConfigDB, config)
                except Exception as e:
                    logger.error(f"Failed to sync AgentConfig '{config.name}': {e}", exc_info=True)
                    # Exception is caught and rolled back by get_db_session

    def sync_workflow_config(self, config: WorkflowConfig):
        """Saves or updates a WorkflowConfig in the database."""
        if not self._engine: return
        with get_db_session() as db:
            if db:
                try:
                    self._sync_config(db, WorkflowConfigDB, config)
                except Exception as e:
                    logger.error(f"Failed to sync WorkflowConfig '{config.name}': {e}", exc_info=True)

    def sync_custom_workflow_config(self, config: CustomWorkflowConfig):
        """Saves or updates a CustomWorkflowConfig in the database."""
        if not self._engine: return
        with get_db_session() as db:
            if db:
                try:
                    self._sync_config(db, CustomWorkflowConfigDB, config)
                except Exception as e:
                    logger.error(f"Failed to sync CustomWorkflowConfig '{config.name}': {e}", exc_info=True)

    def sync_all_configs(
        self,
        agents: Dict[str, AgentConfig],
        workflows: Dict[str, WorkflowConfig],
        custom_workflows: Dict[str, CustomWorkflowConfig]
    ):
        """Syncs all provided configurations to the database in a single transaction."""
        if not self._engine:
            logger.warning("Database not configured. Skipping config sync.")
            return

        logger.info("Syncing all loaded configurations to database...")
        with get_db_session() as db:
            if not db:
                logger.error("Failed to get DB session for config sync.")
                return # Cannot proceed without a session

            try:
                # Sync Agents
                for config in agents.values():
                    self._sync_config(db, AgentConfigDB, config)
                logger.debug(f"Synced {len(agents)} agent configs.")

                # Sync Workflows
                for config in workflows.values():
                    self._sync_config(db, WorkflowConfigDB, config)
                logger.debug(f"Synced {len(workflows)} workflow configs.")

                # Sync Custom Workflows
                for config in custom_workflows.values():
                    self._sync_config(db, CustomWorkflowConfigDB, config)
                logger.debug(f"Synced {len(custom_workflows)} custom workflow configs.")

                # Commit happens automatically when exiting 'with' block if no errors
                logger.info("Successfully synced all configurations to database.")

            except Exception as e:
                logger.error(f"Failed during bulk config sync: {e}", exc_info=True)
                # Rollback happens automatically in get_db_session context manager

    # --- History Methods ---

    # NOTE: Making these synchronous for now as SQLAlchemy session operations
    # within the context manager are typically synchronous. If async driver (e.g., asyncpg)
    # and async sessions are used later, these would need `async def`.
    def load_history(self, agent_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Loads recent conversation history for a specific agent.
        Returns history in the format expected by Anthropic API messages:
        List[{'role': str, 'content': List[Dict[str, Any]]}]
        """
        if not self._engine: return []

        logger.debug(f"Loading history for agent '{agent_name}' (limit: {limit})")
        history_params: List[Dict[str, Any]] = []
        with get_db_session() as db:
            if db:
                try:
                    # Query AgentHistoryDB, filter by agent_name, order by timestamp ascending, limit
                    # Order ascending so the list is in chronological order for the LLM
                    history_records = (
                        db.query(AgentHistoryDB)
                        .filter(AgentHistoryDB.agent_name == agent_name)
                        .order_by(AgentHistoryDB.timestamp.asc())
                        # Consider if limit should be applied here or after fetching all?
                        # Applying limit here is more efficient for large histories.
                        # If we need the *most recent* N turns, order by desc() and limit().
                        # Let's assume we want the start of the conversation up to N turns for now.
                        #.limit(limit) # Revisit if we need *last* N turns
                        .all()
                    )

                    # Convert results to the required format
                    for record in history_records:
                        # Ensure content is loaded correctly from the correct column
                        content_data = record.content_json # Read from content_json column
                        if isinstance(content_data, str):
                             # Attempt to parse if SQLite stored it as a string
                             try:
                                 content_data = json.loads(content_data) # Parse string
                             except json.JSONDecodeError:
                                 logger.error(f"Failed to parse content JSON string for history record ID {record.id}", exc_info=True)
                                 content_data = [{"type": "text", "text": "[Error loading content]"}]
                        elif content_data is None:
                             logger.warning(f"History record ID {record.id} has null content_json.")
                             content_data = [{"type": "text", "text": "[Missing content]"}]
                        # If content_data is already a list/dict (from native JSON type), use it directly

                        history_params.append({
                            "role": record.role,
                            "content": content_data # Use the processed content_data
                        })

                    # If we wanted only the last N turns:
                    if len(history_params) > limit > 0:
                         history_params = history_params[-limit:] # Slice to get the last N items

                    logger.debug(f"Loaded {len(history_params)} history turns for agent '{agent_name}'.")

                except Exception as e:
                    logger.error(f"Failed to load history for agent '{agent_name}': {e}", exc_info=True)
                    # Return empty list on error
                    return []
            else:
                 logger.error("Failed to get DB session for loading history.")
                 return [] # Return empty list if session fails

        return history_params

    def save_full_history(self, agent_name: str, conversation: List[Dict[str, Any]]):
        """
        Saves the entire conversation history for an agent.
        Clears previous history for the agent before saving the new one.
        """
        if not self._engine: return

        # Filter out any potential None values in conversation list defensively
        valid_conversation = [turn for turn in conversation if turn is not None]
        if not valid_conversation:
             logger.warning(f"Attempted to save empty or invalid history for agent '{agent_name}'. Skipping.")
             return

        logger.debug(f"Saving full history for agent '{agent_name}' ({len(valid_conversation)} turns)")
        with get_db_session() as db:
            if db:
                try:
                    # Delete existing history for this agent first
                    delete_stmt = AgentHistoryDB.__table__.delete().where(AgentHistoryDB.agent_name == agent_name)
                    db.execute(delete_stmt)
                    logger.debug(f"Cleared previous history for agent '{agent_name}'.")

                    # Add new history turns
                    new_history_records = []
                    for turn in valid_conversation:
                        # Ensure content is serializable (should be dict/list from Anthropic)
                        content_to_save = turn.get("content")
                        role = turn.get("role")

                        if not role or content_to_save is None:
                             logger.warning(f"Skipping history turn with missing role or content for agent '{agent_name}': {turn}")
                             continue

                        new_history_records.append(
                            AgentHistoryDB(
                                agent_name=agent_name,
                                role=role,
                                content_json=content_to_save # Correctly map to content_json column
                            )
                        )

                    if new_history_records:
                        db.add_all(new_history_records)
                        logger.debug(f"Added {len(new_history_records)} new history turns for agent '{agent_name}'.")

                    # Commit happens automatically via context manager
                except Exception as e:
                    logger.error(f"Failed to save history for agent '{agent_name}': {e}", exc_info=True)
                    # Rollback happens automatically via context manager
            else:
                 logger.error("Failed to get DB session for saving history.")
