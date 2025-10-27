"""
Test suite for DeviceRepository.

This module contains unit tests for the DeviceRepository class, covering
all CRUD operations including create, read, update, and delete operations
for device entities.
"""

from dlms_meter_communication.repositories import DeviceRepository
from dlms_meter_communication.schemas import DeviceCreate, DeviceUpdate
from dlms_meter_communication.db.database import get_session
import uuid
import pytest


@pytest.fixture(scope="function")
def session_fixture():
    """
    Create a database session for testing.

    Returns:
        tuple: A tuple containing the session generator and the session object.
    """
    session_gen = get_session()
    session = next(session_gen)
    return session_gen, session


def test_get_all_devices(session_fixture):
    """
    Test that index() returns an empty list when no devices exist.

    Verifies that the repository correctly handles the case when there are
    no devices in the database.
    """
    _, session = session_fixture

    try:
        device_repository = DeviceRepository(session)
        devices = device_repository.index()
        assert len(devices) == 0
    finally:
        session.close()


def test_get_device_by_id(session_fixture):
    """
    Test that show() returns None for a non-existent device ID.

    Verifies that the repository correctly returns None when attempting
    to retrieve a device that does not exist in the database.
    """
    _, session = session_fixture
    sample_uuid = uuid.uuid4()

    try:
        device_repository = DeviceRepository(session)
        device = device_repository.show(sample_uuid)
        assert device is None
    finally:
        session.close()


def test_create_device(session_fixture):
    """
    Test that store() creates a device successfully.

    Verifies that:
    - A device can be created with all required fields
    - The created device has the correct attributes
    - The device can be retrieved by its ID
    - All device properties match the input data
    """
    _, session = session_fixture

    try:
        device_repository = DeviceRepository(session)
        device = device_repository.store(
            DeviceCreate(
                name="Test Device",
                serial_number="1234567890",
                brand="Test Brand",
                model="Test Model",
            )
        )

        created_device = device_repository.show(device.id)

        assert created_device is not None
        assert created_device.name == "Test Device"
        assert created_device.serial_number == "1234567890"
        assert created_device.brand == "Test Brand"
        assert created_device.model == "Test Model"
    finally:
        session.close()


def test_update_device(session_fixture):
    """
    Test that update() modifies an existing device successfully.

    Verifies that:
    - A device can be updated with new values
    - All device attributes can be modified
    - The updated device retains all new values
    - All fields are correctly persisted
    """
    _, session = session_fixture

    try:
        device_repository = DeviceRepository(session)

        device = device_repository.store(
            DeviceCreate(
                name="Test Device",
                serial_number="1234567890",
                brand="Test Brand",
                model="Test Model",
            )
        )
        updated_device = device_repository.update(
            device.id,
            DeviceUpdate(
                name="Updated Device",
                serial_number="1234567891",
                brand="Updated Brand",
                model="Updated Model",
            ),
        )

        assert updated_device is not None
        assert updated_device.name == "Updated Device"
        assert updated_device.serial_number == "1234567891"
        assert updated_device.brand == "Updated Brand"
        assert updated_device.model == "Updated Model"
    finally:
        session.close()


def test_delete_device(session_fixture):
    """
    Test that destroy() removes a device from the database.

    Verifies that:
    - A device can be deleted successfully
    - The device no longer exists after deletion
    - Attempting to retrieve a deleted device returns None
    """
    _, session = session_fixture

    try:
        device_repository = DeviceRepository(session)
        device = device_repository.store(
            DeviceCreate(
                name="Test Device",
                serial_number="1234567890",
                brand="Test Brand",
                model="Test Model",
            )
        )
        device_repository.destroy(device.id)
        deleted_device = device_repository.show(device.id)
        assert deleted_device is None
    finally:
        session.close()
