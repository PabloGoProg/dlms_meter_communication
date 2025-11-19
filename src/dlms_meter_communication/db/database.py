"""
Database configuration and session management.

This module provides database connectivity setup, session management,
and initialization functions for the DLMS meter communication system.
It uses SQLModel for ORM functionality and PostgreSQL as the database backend.
"""

from contextlib import contextmanager

from sqlmodel import create_engine, Session
from ..core.config import config
from sqlmodel import SQLModel

# Create database engine using the database URL from configuration
# The engine manages the connection pool and database connectivity
should_echo_sql = config.node_env == "development"
engine = create_engine(config.db_url, echo=should_echo_sql)


def init_db():
    """
    Initialize the database by creating all tables.

    This function creates all database tables defined in the SQLModel metadata.
    It should be called once when setting up the application or during
    database migrations.

    Raises:
        Exception: If table creation fails.
    """
    SQLModel.metadata.create_all(bind=engine)


def get_session():
    """
    Create a database session.
    """
    with Session(engine) as session:
        try:
            yield session
            # Commit all changes if no exceptions occurred
            session.commit()
        except Exception as e:
            # Rollback changes on error
            session.rollback()
            raise e
        finally:
            # Ensure session is always closed
            session.close()


@contextmanager
def get_context_session():
    """
    Create a database session context manager.

    This function generates a database session using the SQLModel Session.
    The session is automatically committed on successful operations and
    rolled back on exceptions. The session is properly closed when exiting
    the context.

    Yields:
        Session: A database session object for performing operations.

    Note:
        This is a generator function designed to be used as a context manager
        or with dependency injection frameworks like FastAPI.

    Example:
        ```python
        for session in get_session():
            # Use session for database operations
            devices = session.exec(select(Device))
            break
        ```

    Raises:
        Exception: Propagates any exception that occurs during database operations.
    """
    with Session(engine) as session:
        try:
            yield session
            # Commit all changes if no exceptions occurred
            session.commit()
        except Exception as e:
            # Rollback changes on error
            session.rollback()
            raise e
