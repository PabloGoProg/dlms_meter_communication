from sqlmodel import Session
from sqlalchemy import event
from sqlalchemy.orm import SessionTransaction
import pytest
import uuid

from typing import Callable
from dlms_meter_communication.schemas import (
    DeviceCreate,
    DeviceUpdate,
)
from dlms_meter_communication.db import engine as app_engine


@pytest.fixture(scope="function")
def db_session():
    """
    Creates an isolated database session for testing.
    it uses a savepoint to isolate the changes from the main transaction.

    Returns:
      Session: A simulated database session for testing.
    """
    conn = app_engine.connect()
    transaction = conn.begin()
    session = Session(bind=conn)

    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(s: Session, t: SessionTransaction):
        if t.nested and not t.is_active:
            s.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        conn.close()


@pytest.fixture(scope="function")
def sample_device() -> Callable[[], DeviceCreate]:
    def factory() -> DeviceCreate:
        return DeviceCreate(
            name=f"Test Device {uuid.uuid4()}",
            serial_number=f"SN-{uuid.uuid4()}",
            brand=f"Test Brand {uuid.uuid4()}",
            model=f"Test Model {uuid.uuid4()}",
        )

    return factory


@pytest.fixture(scope="function")
def sample_device_update() -> Callable[[], DeviceUpdate]:
    def factory() -> DeviceUpdate:
        return DeviceUpdate(
            name=f"Updated Test Device {uuid.uuid4()}",
            serial_number=f"SN-{uuid.uuid4()}",
            brand=f"Updated Test Brand {uuid.uuid4()}",
            model=f"Updated Test Model {uuid.uuid4()}",
        )

    return factory
