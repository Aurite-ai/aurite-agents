# src/storage/db_manager.py
"""
Provides the StorageManager class to interact with the database
for persisting configurations and agent history.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Type, TypeVar  # Added Type, TypeVar
from pathlib import Path
from sqlalchemy.engine import Engine  # Import Engine for type hint
from sqlalchemy import delete  # Import delete

# Assuming models are accessible from here
from pydantic import BaseModel as PydanticBaseModel  # Alias BaseModel
from ..config.config_models import (
    AgentConfig,
    WorkflowConfig,
    CustomWorkflowConfig,
    LLMConfig,
)

# Import DB connection utilities and models
# Use the new factory function name and the modified get_db_session
from .db_connection import get_db_session, create_db_engine
from .db_models import (
    Base as SQLAlchemyBase,  # Alias Base
    AgentConfigDB,
    WorkflowConfigDB,
    CustomWorkflowConfigDB,
    AgentHistoryDB,
    LLMConfigDB,  # Added LLMConfigDB
)

logger = logging.getLogger(__name__)

# Define TypeVars for generic function signature
PydanticModelType = TypeVar("PydanticModelType", bound=PydanticBaseModel)
DBModelType = TypeVar("DBModelType", bound=SQLAlchemyBase)


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
            logger.info(
                f"StorageManager initialized with provided engine: {self._engine.url}"
            )
        else:
            # Attempt to create default engine if none provided
            logger.info(
                "No engine provided to StorageManager, attempting to create default engine."
            )
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

    def _sync_config(
        self,
        db_session,
        db_model_cls: Type[DBModelType],  # Use TypeVar for the class
        pydantic_config: PydanticBaseModel,  # Use TypeVar for the instance
        pk_field: str = "name",
    ):
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
            "content": "content_json",  # Added mapping for history content
            # Add other mappings here if needed in the future
        }

        for db_col_name, model_field in db_model_cls.__table__.columns.items():
            # Skip primary key and timestamp fields managed by DB/SQLAlchemy
            if model_field.primary_key or db_col_name in ["created_at", "last_updated"]:
                continue

            # Determine the corresponding Pydantic field name
            pydantic_field_name = db_col_name
            # Find the Pydantic name if the DB column name is in the map's values
            for p_name, db_name in field_map.items():
                if db_name == db_col_name:
                    pydantic_field_name = p_name
                    break  # Found the mapping

            # Get value from Pydantic config using the determined field name
            pydantic_value = getattr(pydantic_config, pydantic_field_name, None)

            # Handle specific type conversions before adding to data_to_save
            if isinstance(pydantic_value, Path):
                # Store Path as string using the DB column name
                data_to_save[db_col_name] = str(pydantic_value)
            elif isinstance(pydantic_value, (list, dict)):
                # Check if the DB column is intended for JSON
                if db_col_name.endswith("_json"):
                    # Store list/dict directly using the DB column name
                    data_to_save[db_col_name] = pydantic_value  # type: ignore[assignment] # Ignore list/dict vs str mismatch
                else:
                    # Log a warning if trying to save list/dict to non-JSON field
                    logger.warning(
                        f"Attempting to save list/dict from pydantic field '{pydantic_field_name}' "
                        f"to non-JSON DB column '{db_col_name}' for {db_model_cls.__name__} '{pk_value}'. Skipping."
                    )
                    continue  # Skip this field if it's a list/dict but not a JSON column
            elif pydantic_value is not None:
                # Store other types directly using the DB column name
                data_to_save[db_col_name] = pydantic_value
            # If pydantic_value is None, we don't add it to data_to_save,
            # allowing DB defaults or existing values (on update) to persist.

        # Now, apply the prepared data_to_save to the DB record
        if db_record:
            # Update existing record
            logger.debug(
                f"Updating existing {db_model_cls.__name__} record for '{pk_value}'"
            )
            for key, value in data_to_save.items():
                setattr(db_record, key, value)
            # last_updated is handled by onupdate=datetime.utcnow
        else:
            # Create new record
            logger.debug(
                f"Creating new {db_model_cls.__name__} record for '{pk_value}'"
            )
            # Add the primary key value for creation
            data_to_save[pk_field] = pk_value
            # Create instance using the prepared data
            db_record = db_model_cls(**data_to_save)
            db_session.add(db_record)
        # Commit is handled by the get_db_session context manager

    def sync_agent_config(self, config: AgentConfig):
        """Saves or updates an AgentConfig in the database."""
        if not self._engine:
            return  # Do nothing if DB is not configured
        # Pass the engine to get_db_session
        with get_db_session(engine=self._engine) as db:
            if db:
                try:
                    self._sync_config(db, AgentConfigDB, config)
                except Exception as e:
                    logger.error(
                        f"Failed to sync AgentConfig '{config.name}': {e}",
                        exc_info=True,
                    )
                    # Exception is caught and rolled back by get_db_session

    def sync_workflow_config(self, config: WorkflowConfig):
        """Saves or updates a WorkflowConfig in the database."""
        if not self._engine:
            return
        # Pass the engine to get_db_session
        with get_db_session(engine=self._engine) as db:
            if db:
                try:
                    self._sync_config(db, WorkflowConfigDB, config)
                except Exception as e:
                    logger.error(
                        f"Failed to sync WorkflowConfig '{config.name}': {e}",
                        exc_info=True,
                    )

    def sync_custom_workflow_config(self, config: CustomWorkflowConfig):
        """Saves or updates a CustomWorkflowConfig in the database."""
        if not self._engine:
            return
        # Pass the engine to get_db_session
        with get_db_session(engine=self._engine) as db:
            if db:
                try:
                    self._sync_config(db, CustomWorkflowConfigDB, config)
                except Exception as e:
                    logger.error(
                        f"Failed to sync CustomWorkflowConfig '{config.name}': {e}",
                        exc_info=True,
                    )

    def sync_llm_config(self, config: LLMConfig):
        """Saves or updates an LLMConfig in the database."""
        if not self._engine:
            return
        with get_db_session(engine=self._engine) as db:
            if db:
                try:
                    # Use 'llm_id' as the primary key field
                    self._sync_config(db, LLMConfigDB, config, pk_field="llm_id")
                except Exception as e:
                    logger.error(
                        f"Failed to sync LLMConfig '{config.llm_id}': {e}",
                        exc_info=True,
                    )

    def sync_all_configs(
        self,
        agents: Dict[str, AgentConfig],
        workflows: Dict[str, WorkflowConfig],
        custom_workflows: Dict[str, CustomWorkflowConfig],
        llm_configs: Dict[str, LLMConfig],  # Added llm_configs argument
    ):
        """Syncs all provided configurations to the database in a single transaction."""
        if not self._engine:
            logger.warning("Database not configured. Skipping config sync.")
            return

        logger.info("Syncing all loaded configurations to database...")
        # Pass the engine to get_db_session
        with get_db_session(engine=self._engine) as db:
            if not db:
                logger.error("Failed to get DB session for config sync.")
                return  # Cannot proceed without a session

            try:
                # Sync Agents
                for config in agents.values():
                    self._sync_config(db, AgentConfigDB, config)
                logger.debug(f"Synced {len(agents)} agent configs.")

                # Sync Workflows
                for config in workflows.values():
                    self._sync_config(
                        db,
                        WorkflowConfigDB,
                        config,
                    )  # type: ignore[assignment] # Ignore WorkflowConfig vs AgentConfig mismatch
                logger.debug(f"Synced {len(workflows)} workflow configs.")

                # Sync Custom Workflows
                for config in custom_workflows.values():
                    self._sync_config(
                        db,
                        CustomWorkflowConfigDB,
                        config,  # type: ignore[assignment] # Ignore CustomWorkflowConfig vs AgentConfig mismatch
                    )
                logger.debug(f"Synced {len(custom_workflows)} custom workflow configs.")

                # Sync LLM Configs
                for config in llm_configs.values():
                    self._sync_config(
                        db,
                        LLMConfigDB,
                        config,
                        pk_field="llm_id",  # Specify primary key field
                    )  # type: ignore[assignment] # Ignore LLMConfig vs AgentConfig mismatch
                logger.debug(f"Synced {len(llm_configs)} LLM configs.")

                # Commit happens automatically when exiting 'with' block if no errors
                logger.info("Successfully synced all configurations to database.")

            except Exception as e:
                logger.error(f"Failed during bulk config sync: {e}", exc_info=True)
                # Rollback happens automatically in get_db_session context manager

    # --- History Methods ---

    # NOTE: Making these synchronous for now as SQLAlchemy session operations
    # within the context manager are typically synchronous. If async driver (e.g., asyncpg)
    # and async sessions are used later, these would need `async def`.
    def load_history(
        self, agent_name: str, session_id: Optional[str], limit: int = 50
    ) -> List[Dict[str, Any]]:
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

        logger.debug(
            f"Loading history for agent '{agent_name}', session '{session_id}' (limit: {limit})"
        )
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
                            AgentHistoryDB.session_id
                            == session_id,  # Added session_id filter
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
                        content_data = (
                            record.content_json
                        )  # Read from content_json column
                        parsed_content = None
                        if isinstance(content_data, str):
                            # Attempt to parse if stored as a JSON string
                            try:
                                parsed_content = json.loads(
                                    content_data
                                )  # Parse string
                            except json.JSONDecodeError:
                                # If parsing fails, assume it was a raw string user input
                                logger.warning(
                                    f"Failed to parse content_json for history ID {record.id} as JSON. Assuming raw string content."
                                )
                                # Format the raw string into the expected structure
                                parsed_content = [
                                    {"type": "text", "text": content_data}
                                ]
                        elif content_data is None:
                            logger.warning(
                                f"History record ID {record.id} has null content_json."
                            )
                            parsed_content = [
                                {"type": "text", "text": "[Missing content]"}
                            ]
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
                        history_params = history_params[
                            -limit:
                        ]  # Slice to get the last N items

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
            logger.warning(
                f"Attempted to save history for agent '{agent_name}' without a session_id. Skipping save."
            )
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
                    logger.debug(
                        f"Cleared previous history for agent '{agent_name}', session '{session_id}'."
                    )

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
