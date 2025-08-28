"""
Database migration utilities for Aurite Framework.
Supports migration between SQLite and PostgreSQL databases.
"""

import logging
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .db_models import AgentHistoryDB, ComponentDB
from .db_models import Base as SQLAlchemyBase

logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Migrate data between different database backends (SQLite <-> PostgreSQL)."""

    def __init__(self, source_url: str, target_url: str):
        """
        Initialize the migrator with source and target database URLs.

        Args:
            source_url: SQLAlchemy database URL for the source database
            target_url: SQLAlchemy database URL for the target database
        """
        self.source_url = source_url
        self.target_url = target_url
        self.source_engine: Optional[Engine] = None
        self.target_engine: Optional[Engine] = None

    def connect(self) -> bool:
        """
        Establish connections to both source and target databases.

        Returns:
            True if both connections successful, False otherwise
        """
        try:
            # Create source engine
            logger.info("Connecting to source database...")
            self.source_engine = create_engine(self.source_url)

            # Test source connection
            with self.source_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Source database connection successful")

            # Create target engine
            logger.info("Connecting to target database...")
            self.target_engine = create_engine(self.target_url)

            # Test target connection
            with self.target_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Target database connection successful")

            return True

        except Exception as e:
            logger.error(f"Failed to connect to databases: {e}")
            return False

    def create_target_schema(self) -> bool:
        """
        Create the database schema in the target database.

        Returns:
            True if schema created successfully, False otherwise
        """
        if not self.target_engine:
            logger.error("Target engine not initialized")
            return False

        try:
            logger.info("Creating schema in target database...")
            SQLAlchemyBase.metadata.create_all(bind=self.target_engine)
            logger.info("Schema created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create schema: {e}")
            return False

    def migrate_components(self) -> int:
        """
        Migrate component configurations from source to target.

        Returns:
            Number of components migrated
        """
        if not self.source_engine or not self.target_engine:
            logger.error("Engines not initialized")
            return 0

        count = 0
        try:
            with Session(self.source_engine) as source_session:
                with Session(self.target_engine) as target_session:
                    # Query all components from source
                    logger.info("Migrating component configurations...")
                    components = source_session.query(ComponentDB).all()

                    for comp in components:
                        # Create new component in target
                        new_comp = ComponentDB(
                            name=comp.name,
                            component_type=comp.component_type,
                            config=comp.config,
                            created_at=comp.created_at,
                            last_updated=comp.last_updated,
                        )
                        # Use merge to handle potential duplicates
                        target_session.merge(new_comp)
                        count += 1

                        if count % 10 == 0:
                            logger.debug(f"Migrated {count} components...")

                    target_session.commit()
                    logger.info(f"Successfully migrated {count} components")

        except Exception as e:
            logger.error(f"Failed to migrate components: {e}")

        return count

    def migrate_history(self, batch_size: int = 1000) -> int:
        """
        Migrate agent history from source to target in batches.

        Args:
            batch_size: Number of records to process at a time

        Returns:
            Number of history records migrated
        """
        if not self.source_engine or not self.target_engine:
            logger.error("Engines not initialized")
            return 0

        total_count = 0
        try:
            with Session(self.source_engine) as source_session:
                # Get total count for progress reporting
                total_records = source_session.query(AgentHistoryDB).count()
                logger.info(f"Migrating {total_records} history records...")

                # Process in batches to handle large datasets
                offset = 0
                while True:
                    with Session(self.target_engine) as target_session:
                        # Query batch from source
                        batch = (
                            source_session.query(AgentHistoryDB)
                            .order_by(AgentHistoryDB.id)
                            .offset(offset)
                            .limit(batch_size)
                            .all()
                        )

                        if not batch:
                            break

                        for hist in batch:
                            # Create new history record in target
                            new_hist = AgentHistoryDB(
                                agent_name=hist.agent_name,
                                session_id=hist.session_id,
                                timestamp=hist.timestamp,
                                role=hist.role,
                                content_json=hist.content_json,
                            )
                            target_session.add(new_hist)
                            total_count += 1

                        target_session.commit()
                        offset += batch_size

                        # Progress reporting
                        progress = min(100, (total_count / total_records * 100)) if total_records > 0 else 100
                        logger.info(f"Migration progress: {total_count}/{total_records} records ({progress:.1f}%)")

                logger.info(f"Successfully migrated {total_count} history records")

        except Exception as e:
            logger.error(f"Failed to migrate history: {e}")

        return total_count

    def migrate_all(self) -> tuple[int, int]:
        """
        Perform complete migration from source to target database.

        Returns:
            Tuple of (components_migrated, history_records_migrated)
        """
        logger.info("Starting database migration...")

        # Connect to databases
        if not self.connect():
            logger.error("Failed to connect to databases")
            return (0, 0)

        # Create schema in target
        if not self.create_target_schema():
            logger.error("Failed to create target schema")
            return (0, 0)

        # Migrate data
        components = self.migrate_components()
        history = self.migrate_history()

        logger.info(f"Migration complete: {components} components, {history} history records")
        return (components, history)

    def verify_migration(self) -> bool:
        """
        Verify that migration was successful by comparing record counts.

        Returns:
            True if counts match, False otherwise
        """
        if not self.source_engine or not self.target_engine:
            logger.error("Engines not initialized")
            return False

        try:
            with Session(self.source_engine) as source_session:
                with Session(self.target_engine) as target_session:
                    # Compare component counts
                    source_components = source_session.query(ComponentDB).count()
                    target_components = target_session.query(ComponentDB).count()

                    # Compare history counts
                    source_history = source_session.query(AgentHistoryDB).count()
                    target_history = target_session.query(AgentHistoryDB).count()

                    logger.info(f"Source: {source_components} components, {source_history} history records")
                    logger.info(f"Target: {target_components} components, {target_history} history records")

                    if source_components == target_components and source_history == target_history:
                        logger.info("Migration verification successful - counts match")
                        return True
                    else:
                        logger.warning("Migration verification failed - counts do not match")
                        return False

        except Exception as e:
            logger.error(f"Failed to verify migration: {e}")
            return False


def build_database_url(db_type: str, **kwargs) -> Optional[str]:
    """
    Helper function to build a database URL from parameters.

    Args:
        db_type: Database type ('sqlite' or 'postgres'/'postgresql')
        **kwargs: Database-specific parameters
            For SQLite: path
            For PostgreSQL: host, port, user, password, name

    Returns:
        SQLAlchemy database URL or None if invalid
    """
    if db_type == "sqlite":
        path = kwargs.get("path", ".aurite_db/aurite.db")
        from pathlib import Path

        abs_path = Path(path).absolute()
        return f"sqlite:///{abs_path}"

    elif db_type in ["postgres", "postgresql"]:
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 5432)
        user = kwargs.get("user")
        password = kwargs.get("password")
        name = kwargs.get("name")

        if not all([user, password, name]):
            logger.error("PostgreSQL requires user, password, and name parameters")
            return None

        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"

    else:
        logger.error(f"Unsupported database type: {db_type}")
        return None
