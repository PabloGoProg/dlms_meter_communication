"""
Test suite for DeviceRepository.

This module contains unit tests for the DeviceRepository class, covering
all CRUD operations including create, read, update, and delete operations
for device entities.
"""

from dlms_meter_communication.repositories import DeviceRepository
from dlms_meter_communication.schemas import DeviceUpdate, DeviceCreate

import uuid
import pytest
from sqlalchemy.exc import IntegrityError, NoResultFound

# Fixture to use the simulated database session for all tests
pytestmark = pytest.mark.usefixtures("db_session")


def test_get_all_devices_empty(db_session):
    """
    Test that index() returns an empty list when no devices exist.
    """
    device_repository = DeviceRepository(db_session)
    devices = device_repository.index()
    assert len(devices) == 0


def test_get_all_devices_non_empty(db_session, sample_device):
    """
    Test that index() returns a non-empty list when devices exist.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())
    devices = device_repository.index()
    assert len(devices) == 1
    assert devices[0].id == device.id


def test_get_device_by_id_non_existent(db_session):
    """
    Test that show() returns None for a non-existent device ID.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.show(uuid.uuid4())
    assert device is None


def test_get_device_by_id_existing(db_session, sample_device):
    """
    Test that show() returns the device for an existing ID.
    """
    device_repository = DeviceRepository(db_session)
    created = device_repository.store(sample_device())
    fetched = device_repository.show(created.id)
    assert fetched is not None
    assert fetched.id == created.id


def test_create_device(db_session, sample_device):
    """
    Test that store() creates a device successfully.

    Verifies that:
    - A device can be created with all required fields
    - The created device has the correct attributes
    - The device can be retrieved by its ID
    - All device properties match the input data
    """
    device_repository = DeviceRepository(db_session)
    data = sample_device()
    device = device_repository.store(data)

    created_device = device_repository.show(device.id)

    assert created_device is not None
    assert created_device.name == data.name
    assert created_device.serial_number == data.serial_number
    assert created_device.brand == data.brand
    assert created_device.model == data.model


def test_create_device_duplicate_serial_raises(db_session, sample_device):
    """
    Test that storing two devices with the same serial_number raises IntegrityError.
    """
    device_repository = DeviceRepository(db_session)
    first = device_repository.store(sample_device())
    dup = DeviceCreate(
        name=first.name,
        serial_number=first.serial_number,
        brand=first.brand,
        model=first.model,
    )
    with pytest.raises(IntegrityError):
        device_repository.store(dup)


def test_update_device(db_session, sample_device, sample_device_update):
    """
    Test that update() modifies an existing device successfully.

    Verifies that:
    - A device can be updated with new values
    - All device attributes can be modified
    - The updated device retains all new values
    - All fields are correctly persisted
    """
    device_repository = DeviceRepository(db_session)

    device = device_repository.store(sample_device())

    update_data = sample_device_update()
    updated_device = device_repository.update(
        device.id,
        update_data,
    )

    assert updated_device is not None
    assert updated_device.name == update_data.name
    assert updated_device.serial_number == update_data.serial_number
    assert updated_device.brand == update_data.brand
    assert updated_device.model == update_data.model


def test_update_device_partial_fields(db_session, sample_device):
    """
    Test that update() with partial fields only changes provided attributes.
    """
    device_repository = DeviceRepository(db_session)
    device_data = sample_device()
    device = device_repository.store(device_data)

    partial = DeviceUpdate(name="Only Name Changed")
    updated = device_repository.update(device.id, partial)

    assert updated.name == "Only Name Changed"
    assert updated.serial_number == device_data.serial_number
    assert updated.brand == device_data.brand
    assert updated.model == device_data.model


def test_update_non_existent_device_raises(db_session, sample_device_update):
    """
    Test that update() on non-existent device raises NoResultFound.
    """
    device_repository = DeviceRepository(db_session)
    with pytest.raises(NoResultFound):
        device_repository.update(uuid.uuid4(), sample_device_update())


def test_delete_device(db_session, sample_device):
    """
    Test that destroy() removes a device from the database.

    Verifies that:
    - A device can be deleted successfully
    - The device no longer exists after deletion
    - Attempting to retrieve a deleted device returns None
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())
    device_repository.remove(device.id)
    deleted_device = device_repository.show(device.id)
    assert deleted_device is None


def test_remove_non_existent_device_raises(db_session):
    """
    Test that remove() on non-existent device raises NoResultFound.
    """
    device_repository = DeviceRepository(db_session)
    with pytest.raises(NoResultFound):
        device_repository.remove(uuid.uuid4())


def test_destroy_non_existent_device_raises(db_session):
    """
    Test that destroy() on non-existent device raises NoResultFound.
    """
    device_repository = DeviceRepository(db_session)
    with pytest.raises(NoResultFound):
        device_repository.destroy(uuid.uuid4())
