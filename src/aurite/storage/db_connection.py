# src/storage/db_connection.py
"""
Handles database connection setup (SQLAlchemy engine, sessions).
Reads connection details from environment variables.
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from contextlib import contextmanager
from typing import Optional, Generator

logger = logging.getLogger(__name__)

# Removed global singletons for engine and session factory
# _engine: Optional[Engine] = None
# _SessionFactory: Optional[sessionmaker[Session]] = None


def get_database_url() -> Optional[str]:
    """Constructs the database URL from environment variables."""
    db_user = os.getenv("AURITE_DB_USER")
    db_password = os.getenv("AURITE_DB_PASSWORD")
    db_host = os.getenv("AURITE_DB_HOST", "localhost")
    db_port = os.getenv("AURITE_DB_PORT", "5432")
    db_name = os.getenv("AURITE_DB_NAME")

    if not all([db_user, db_password, db_name]):
        logger.warning(
            "Database connection variables (AURITE_DB_USER, AURITE_DB_PASSWORD, AURITE_DB_NAME) are not fully set. Cannot construct URL."
        )
        return None

    # Using psycopg2 driver for PostgreSQL
    return (
        f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )


# Renamed to indicate it's a factory creating a *new* engine instance
def create_db_engine() -> Optional[Engine]:
    """
    Creates and returns a new SQLAlchemy engine based on environment variables.
    Returns None if the database URL cannot be constructed or engine creation fails.
    """
    db_url = get_database_url()
    if not db_url:
        logger.info("Database URL not configured, cannot create engine.")
        return None

    try:
        # TODO: Add pool configuration options if needed (pool_size, max_overflow)
        engine = create_engine(db_url, echo=False)  # Set echo=True for debugging SQL
        logger.info(f"SQLAlchemy engine created for {engine.url}.")
        return engine
    except Exception as e:
        logger.error(
            f"Failed to create SQLAlchemy engine for URL {db_url}: {e}", exc_info=True
        )
        return None


# Removed get_engine() singleton function


# Renamed to indicate it's a factory creating a *new* session factory
def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """
    Creates and returns a new SQLAlchemy session factory bound to the given engine.
    """
    logger.debug(f"Creating SQLAlchemy session factory for engine: {engine.url}")
    # Removed error handling here; assume engine is valid if passed in.
    # Let potential errors during sessionmaker creation propagate.
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Removed get_session_factory() singleton function


@contextmanager
def get_db_session(
    engine: Optional[Engine],
) -> Generator[Optional[Session], None, None]:
    """
    Provides a transactional database session context using the provided engine.
    If engine is None, yields None.
    """
    if not engine:
        logger.warning("No engine provided to get_db_session. Cannot create session.")
        yield None
        return

    # Create a new factory and session for this context
    try:
        SessionFactory = create_session_factory(engine)
        session: Session = SessionFactory()
    except Exception as e:
        logger.error(
            f"Failed to create session factory or session for engine {engine.url}: {e}",
            exc_info=True,
        )
        yield None
        return

    try:
        yield session
        session.commit()
        logger.debug("Database session committed successfully.")
    except Exception as e:
        logger.error(f"Database session error: {e}", exc_info=True)
        session.rollback()
        logger.warning("Database session rolled back due to error.")
        raise  # Re-raise the exception after rollback
    finally:
        session.close()
        logger.debug("Database session closed.")


# Example usage (primarily for db_manager.py):
# with get_db_session() as db:
#     if db:
#         # Perform database operations using db session
#         result = db.query(...)
#         db.add(...)
#     else:
#         # Handle case where DB session could not be created
#         print("Could not connect to database.")
