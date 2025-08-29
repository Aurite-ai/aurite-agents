# src/storage/db_connection.py
"""
Handles database connection setup (SQLAlchemy engine, sessions).
Reads connection details from environment variables.
"""

import logging
import os
import urllib.parse
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

# Removed global singletons for engine and session factory
# _engine: Optional[Engine] = None
# _SessionFactory: Optional[sessionmaker[Session]] = None


def get_database_url() -> Optional[str]:
    """Constructs the database URL based on AURITE_DB_TYPE environment variable.

    Supports:
    - sqlite (default): Local file-based database, zero configuration
    - postgresql/postgres: Network database for production/multi-user scenarios
    """
    db_type = os.getenv("AURITE_DB_TYPE", "sqlite").lower()

    if db_type == "sqlite":
        # Default to .aurite_db directory in current working directory
        db_path = os.getenv("AURITE_DB_PATH", ".aurite_db/aurite.db")

        # Ensure directory exists (handle existing directory gracefully)
        db_dir = Path(db_path).parent
        try:
            db_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # Directory might already exist or have permission issues
            if not db_dir.exists():
                logger.error(f"Failed to create directory for SQLite database: {e}")
                return None
            # If directory exists, that's fine, continue

        # Use absolute path for SQLite
        abs_path = Path(db_path).absolute()
        logger.info(f"Using SQLite database at: {abs_path}")
        return f"sqlite:///{abs_path}"

    elif db_type in ["postgresql", "postgres"]:
        # PostgreSQL configuration
        db_user = os.getenv("AURITE_DB_USER")
        db_password = os.getenv("AURITE_DB_PASSWORD")
        db_host = os.getenv("AURITE_DB_HOST", "localhost")  # Changed default from "postgres" to "localhost"
        db_port = os.getenv("AURITE_DB_PORT", "5432")
        db_name = os.getenv("AURITE_DB_NAME")

        if not all([db_user, db_password, db_name]):
            logger.warning(
                "PostgreSQL connection variables (AURITE_DB_USER, AURITE_DB_PASSWORD, AURITE_DB_NAME) are not fully set. Cannot construct URL."
            )
            return None

        # Using psycopg2 driver for PostgreSQL
        logger.info(f"Using PostgreSQL database: {db_name} at {db_host}:{db_port}")
        return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    else:
        logger.error(f"Unsupported database type: {db_type}. Supported types: sqlite, postgresql/postgres")
        return None


# Renamed to indicate it's a factory creating a *new* engine instance
def create_db_engine() -> Optional[Engine]:
    """
    Creates and returns a new SQLAlchemy engine based on environment variables.
    Returns None if the database URL cannot be constructed or engine creation fails.

    Applies appropriate settings based on database type:
    - SQLite: Enables foreign keys, WAL mode for better concurrency
    - PostgreSQL: Configurable connection pooling
    """
    db_url = get_database_url()
    if not db_url:
        logger.info("Database URL not configured, cannot create engine.")
        return None

    try:
        # Configure engine based on database type
        if "sqlite" in db_url:
            # SQLite-specific settings
            engine = create_engine(
                db_url,
                echo=False,  # Set echo=True for debugging SQL
                connect_args={
                    "check_same_thread": False  # Allow multiple threads with SQLite
                },
            )

            # Apply SQLite optimizations
            with engine.connect() as conn:
                conn.execute(text("PRAGMA foreign_keys=ON"))  # Enable foreign key constraints
                conn.execute(text("PRAGMA journal_mode=WAL"))  # Write-Ahead Logging for better concurrency
                conn.execute(text("PRAGMA synchronous=NORMAL"))  # Balance between safety and speed
                conn.commit()

            logger.info(f"SQLite engine created with optimizations for {engine.url}.")
        else:
            # PostgreSQL settings
            # TODO: Add pool configuration options if needed (pool_size, max_overflow)
            engine = create_engine(db_url, echo=False)  # Set echo=True for debugging SQL
            logger.info(f"PostgreSQL engine created for {engine.url}.")

        return engine
    except Exception:

        def sanitize_db_url(url: str) -> str:
            # Only redact password for PostgreSQL URLs that match the format
            try:
                parsed = urllib.parse.urlparse(url)
                if parsed.scheme.startswith("postgresql"):
                    # Reconstruct netloc with username and redacted password if present
                    username = parsed.username or ""
                    host = parsed.hostname or ""
                    port = f":{parsed.port}" if parsed.port else ""
                    # Use *** for password if any username is set
                    password = ":***" if username else ""
                    # Rebuild netloc
                    netloc = f"{username}{password}@{host}{port}"
                    # Build sanitized URL
                    sanitized = urllib.parse.urlunparse(
                        (
                            parsed.scheme,
                            netloc,
                            parsed.path,
                            parsed.params,
                            parsed.query,
                            parsed.fragment,
                        )
                    )
                    return sanitized
            except Exception:
                pass
            # For non-postgres URLs or on error, return as-is
            return url

        sanitize_db_url(db_url) if db_url else None
        logger.error("Failed to create SQLAlchemy engine. Check your database environment variables")
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
