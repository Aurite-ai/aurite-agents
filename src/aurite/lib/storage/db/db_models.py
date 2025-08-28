# src/storage/db_models.py
"""
Defines SQLAlchemy ORM models for database tables related to
agent configurations and history.
"""

import logging
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


# Create a base class for declarative models
class Base(DeclarativeBase):
    pass


class ComponentDB(Base):
    """SQLAlchemy model for storing all component configurations."""

    __tablename__ = "components"

    # Use component name as primary key for easy lookup/sync
    name = Column(String, primary_key=True, index=True)
    component_type = Column(String, nullable=False, index=True)

    # Store the entire component configuration as JSON
    config = Column(JSON, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (Index("ix_component_type_name", "component_type", "name", unique=True),)

    def __repr__(self):
        return f"<ComponentDB(name='{self.name}', component_type='{self.component_type}')>"


class SessionDB(Base):
    """SQLAlchemy model for storing complete session data including execution results and metadata."""

    __tablename__ = "sessions"

    # Primary key
    session_id = Column(String, primary_key=True, index=True)

    # Base session ID for tracking workflow relationships
    base_session_id = Column(String, index=True, nullable=True)

    # Session metadata
    name = Column(String, nullable=False)  # Agent or workflow name
    result_type = Column(String, nullable=False)  # "agent" or "workflow"
    is_workflow = Column(Boolean, default=False, nullable=False)
    message_count = Column(Integer, default=0, nullable=False)

    # Complete execution result stored as JSON
    execution_result = Column(JSON, nullable=False)

    # For workflows: mapping of child session_id -> agent_name
    agents_involved = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("ix_session_base_id", "base_session_id"),
        Index("ix_session_name_type", "name", "result_type"),
        Index("ix_session_workflow", "is_workflow"),
        Index("ix_session_timestamps", "created_at", "last_updated"),
    )

    def __repr__(self):
        return f"<SessionDB(session_id='{self.session_id}', name='{self.name}', type='{self.result_type}')>"


# Legacy model - kept for backward compatibility but deprecated
class AgentHistoryDB(Base):
    """
    DEPRECATED: Legacy model for storing individual agent conversation turns.
    Kept for backward compatibility during migration.
    New implementations should use SessionDB instead.
    """

    __tablename__ = "agent_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Index agent_name, session_id, and timestamp for efficient history retrieval
    agent_name = Column(String, index=True, nullable=False)
    session_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    # Store role ('user' or 'assistant')
    role = Column(String, nullable=False)
    # Store the list of content blocks (e.g., TextBlock, ToolUseBlock) as JSON
    # This matches the structure used by Anthropic's API messages
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
