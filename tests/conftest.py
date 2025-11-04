from sqlmodel import Session
from sqlalchemy import event
from sqlalchemy.orm import SessionTransaction
import pytest
import uuid

from typing import Callable
from uuid import UUID
import random

from dlms_meter_communication.schemas import (
    DeviceCreate,
    DeviceUpdate,
    CommunicationEndpointCreate,
    DeviceAddressingCreate,
    DeviceAddressingUpdate,
)
from dlms_meter_communication.models.enums import Medium, Profile
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


@pytest.fixture(scope="function")
def sample_communication_endpoint() -> Callable[
    [UUID, Medium], CommunicationEndpointCreate
]:
    """
    Factory fixture for creating communication endpoints.

    Args:
        device_id: UUID of the device
        medium: Communication medium (TCP or SERIAL)

    Returns:
        Callable that generates CommunicationEndpointCreate instances
    """

    def factory(
        device_id: UUID, medium: Medium = Medium.TCP
    ) -> CommunicationEndpointCreate:
        return CommunicationEndpointCreate(
            device_id=device_id,
            medium=medium,
            profile=Profile.WRAPPER,
            ip=f"127.0.0.{random.randint(1, 255)}" if medium == Medium.TCP else None,
            port=random.randint(1000, 65535) if medium == Medium.TCP else None,
            serial_port=f"COM{random.randint(1, 99)}"
            if medium == Medium.SERIAL
            else None,
            baud_rate=random.choice([9600, 19200, 38400, 57600, 115200])
            if medium == Medium.SERIAL
            else None,
            is_primary=True,
        )

    return factory


@pytest.fixture(scope="function")
def sample_device_addressing() -> Callable[[UUID], DeviceAddressingCreate]:
    """
    Factory fixture for creating device addressing configurations.

    Args:
        endpoint_id: UUID of the communication endpoint

    Returns:
        Callable that generates DeviceAddressingCreate instances
    """

    def factory(endpoint_id: UUID) -> DeviceAddressingCreate:
        return DeviceAddressingCreate(
            endpoint_id=endpoint_id,
            client_address=random.randint(1, 255),
            server_address=random.randint(1, 255),
            use_logical_name=random.choice([True, False]),
        )

    return factory


@pytest.fixture(scope="function")
def sample_device_addressing_update() -> Callable[[], DeviceAddressingUpdate]:
    """
    Factory fixture for creating device addressing update data.

    Returns:
        Callable that generates DeviceAddressingUpdate instances
    """

    def factory() -> DeviceAddressingUpdate:
        return DeviceAddressingUpdate(
            client_address=random.randint(1, 255),
            server_address=random.randint(1, 255),
            use_logical_name=random.choice([True, False]),
        )

    return factory
