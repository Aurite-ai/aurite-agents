# src/storage/db_models.py
"""
Defines SQLAlchemy ORM models for database tables related to
agent configurations and history.
"""

import logging
from datetime import datetime

from sqlalchemy import (
    JSON,
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


class AgentHistoryDB(Base):
    """SQLAlchemy model for storing individual agent conversation turns."""

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
