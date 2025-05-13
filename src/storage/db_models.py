# src/storage/db_models.py
"""
Defines SQLAlchemy ORM models for database tables related to
agent configurations and history.
"""

import logging
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    Float,
    Index,
    JSON,
)

# Use generic JSON type for broader compatibility (SQLite unit tests)
# It falls back to TEXT on SQLite but uses native JSON/JSONB on PostgreSQL
# from sqlalchemy.dialects.postgresql import JSONB # Keep commented out or remove
from sqlalchemy.orm import DeclarativeBase  # Changed import

logger = logging.getLogger(__name__)


# Create a base class for declarative models
class Base(DeclarativeBase):  # Changed definition
    pass


class AgentConfigDB(Base):
    """SQLAlchemy model for storing Agent configurations."""

    __tablename__ = "agent_configs"

    # Use agent name as primary key for easy lookup/sync
    name = Column(String, primary_key=True, index=True)
    system_prompt = Column(Text, nullable=True)
    model = Column(String, nullable=True)
    temperature = Column(Float, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    max_iterations = Column(Integer, nullable=True)
    include_history = Column(Boolean, default=False, nullable=False)
    # Store lists as JSON - Column name will default to attribute name
    client_ids_json = Column(JSON, nullable=True)
    exclude_components_json = Column(JSON, nullable=True)
    evaluation = Column(String, nullable=True)
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<AgentConfigDB(name='{self.name}')>"


class WorkflowConfigDB(Base):
    """SQLAlchemy model for storing Simple Workflow configurations."""

    __tablename__ = "workflow_configs"

    name = Column(String, primary_key=True, index=True)
    # Store list of agent names as JSON - Column name will default to attribute name
    steps_json = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<WorkflowConfigDB(name='{self.name}')>"


class CustomWorkflowConfigDB(Base):
    """SQLAlchemy model for storing Custom Workflow configurations."""

    __tablename__ = "custom_workflow_configs"

    name = Column(String, primary_key=True, index=True)
    # Store Path object as string
    module_path = Column(String, nullable=False)
    class_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<CustomWorkflowConfigDB(name='{self.name}')>"


class LLMConfigDB(Base):
    """SQLAlchemy model for storing LLM configurations."""

    __tablename__ = "llm_configs"

    # Use llm_id as primary key
    llm_id = Column(String, primary_key=True, index=True)
    provider = Column(String, nullable=False, default="anthropic")
    model_name = Column(String, nullable=False)
    temperature = Column(Float, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    default_system_prompt = Column(Text, nullable=True)
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<LLMConfigDB(llm_id='{self.llm_id}', model_name='{self.model_name}')>"


class AgentHistoryDB(Base):
    """SQLAlchemy model for storing individual agent conversation turns."""

    __tablename__ = "agent_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Index agent_name, session_id, and timestamp for efficient history retrieval
    agent_name = Column(String, index=True, nullable=False)
    session_id = Column(String, index=True, nullable=False)  # Added session_id
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    # Store role ('user' or 'assistant')
    role = Column(String, nullable=False)
    # Store the list of content blocks (e.g., TextBlock, ToolUseBlock) as JSON
    # This matches the structure used by Anthropic's API messages
    # Column name will default to attribute name
    content_json = Column(JSON, nullable=False)

    # Add index for faster lookup by agent, session, and time
    __table_args__ = (
        Index(
            "ix_agent_history_agent_session_timestamp",
            "agent_name",
            "session_id",
            "timestamp",
        ),
    )

    def __repr__(self):
        return f"<AgentHistoryDB(id={self.id}, agent_name='{self.agent_name}', session_id='{self.session_id}', role='{self.role}', timestamp='{self.timestamp}')>"


# You can add helper functions here if needed, e.g., to convert
# Pydantic models to DB models or vice-versa, although this logic
# might be better placed within the StorageManager.
