"""Engine and session setup for DB interactions."""

import logging
from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from .config import Settings
from . import models

logger = logging.getLogger(__name__)


class SessionFactory:
    """
    Lightweight session factory bound to a firebase database URL.
    """

    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(
            database_url,
            pool_pre_ping=True,
            future=True,
            connect_args={"connect_timeout": 3},
            poolclass=NullPool,
        )
        self._SessionLocal = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            future=True,
        )

    def __call__(self) -> Session:
        """
        Create a new Session instance.
        """
        return self._SessionLocal()

    def check_connection(self, raise_on_error: bool = False) -> bool:
        """
        Health check with database connection.
        """
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except OperationalError as exc:
            logger.warning("Database unreachable: %s", exc)
            if raise_on_error:
                raise
            return False


def create_all_tables(settings: Settings) -> None:
    """
    Convenience helper to create all tables defined in models.Base.
    In case of database restart/ new connection, call this to ensure tables are created before ingestion.
    """
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
        connect_args={"connect_timeout": 3},
        poolclass=NullPool,
    )
    models.Base.metadata.create_all(bind=engine)

