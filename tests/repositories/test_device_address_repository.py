"""
Test suite for DeviceAddressingRepository.

This module contains unit tests for the DeviceAddressingRepository class, covering
all CRUD operations including create, read, update, and delete operations
for device addressing entities.
"""

import pytest
import uuid
from uuid import UUID
import random

from dlms_meter_communication.repositories import (
    DeviceAddressingRepository,
    CommunicationEndpointRepository,
    DeviceRepository,
)
from dlms_meter_communication.schemas import (
    DeviceAddressingUpdate,
)
from sqlalchemy.exc import InvalidRequestError, NoResultFound

# Fixture to use the simulated database session for all tests
pytestmark = pytest.mark.usefixtures("db_session")


def test_index_empty(db_session):
    """
    Test that index() returns an empty list when no device addressings exist.
    """
    repository = DeviceAddressingRepository(db_session)
    addressings = repository.index()
    assert len(addressings) == 0


def test_index_non_empty(db_session, sample_device, sample_device_addressing):
    """
    Test that index() returns a non-empty list when device addressings exist.
    """
    # Setup: Create device, endpoint, and addressing
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    addressing_repository = DeviceAddressingRepository(db_session)
    addressing = addressing_repository.store(sample_device_addressing(device.id))

    addressings = addressing_repository.index()
    assert len(addressings) == 1
    assert addressings[0].id == addressing.id


def test_index_by_device_id_empty(db_session, sample_device):
    """
    Test that index_by_endpoint_id() returns an empty list when no addressings exist for an endpoint.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    addressing_repository = DeviceAddressingRepository(db_session)
    addressings = addressing_repository.index_by_device_id(device.id)
    assert len(addressings) == 0


def test_index_by_device_id_non_empty(
    db_session, sample_device, sample_device_addressing
):
    """
    Test that index_by_endpoint_id() returns addressings for a specific endpoint.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    addressing_repository = DeviceAddressingRepository(db_session)
    addressing1 = addressing_repository.store(sample_device_addressing(device.id))
    addressing2 = addressing_repository.store(sample_device_addressing(device.id))

    addressings = addressing_repository.index_by_device_id(device.id)
    assert len(addressings) == 2
    assert addressing1.id in [a.id for a in addressings]
    assert addressing2.id in [a.id for a in addressings]


def test_show_non_existent(db_session):
    """
    Test that show() returns None for a non-existent device addressing ID.
    """
    repository = DeviceAddressingRepository(db_session)
    addressing = repository.show(uuid.uuid4())
    assert addressing is None


def test_show_existing(db_session, sample_device, sample_device_addressing):
    """
    Test that show() returns the device addressing for an existing ID.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    addressing_repository = DeviceAddressingRepository(db_session)
    created = addressing_repository.store(sample_device_addressing(device.id))

    fetched = addressing_repository.show(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.device_id == device.id
    assert fetched.client_address == created.client_address
    assert fetched.server_address == created.server_address
    assert fetched.use_logical_name == created.use_logical_name


def test_store_success(db_session, sample_device, sample_device_addressing):
    """
    Test that store() creates a device addressing successfully.

    Verifies that:
    - A device addressing can be created with all required fields
    - The created addressing has the correct attributes
    - The addressing can be retrieved by its ID
    - All addressing properties match the input data
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    addressing_repository = DeviceAddressingRepository(db_session)
    data = sample_device_addressing(device.id)
    addressing = addressing_repository.store(data)

    created_addressing = addressing_repository.show(addressing.id)

    assert created_addressing is not None
    assert created_addressing.device_id == data.device_id
    assert created_addressing.client_address == data.client_address
    assert created_addressing.server_address == data.server_address
    assert created_addressing.use_logical_name == data.use_logical_name


def test_store_nonexistent_endpoint_raises(db_session, sample_device_addressing):
    """
    Test that store() raises NoResultFound when device doesn't exist.
    """
    addressing_repository = DeviceAddressingRepository(db_session)
    data = sample_device_addressing(uuid.uuid4())

    with pytest.raises(NoResultFound):
        addressing_repository.store(data)


def test_store_duplicate_raises(db_session, sample_device, sample_device_addressing):
    """
    Test that store() raises InvalidRequestError when duplicate addressing exists.

    Duplicate means same endpoint_id, server_address, and client_address combination.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    addressing_repository = DeviceAddressingRepository(db_session)
    data = sample_device_addressing(device.id)
    addressing_repository.store(data)

    with pytest.raises(InvalidRequestError):
        addressing_repository.store(data)


def test_update_success(
    db_session,
    sample_device,
    sample_device_addressing,
    sample_device_addressing_update,
):
    """
    Test that update() modifies an existing device addressing successfully.

    Verifies that:
    - A device addressing can be updated with new values
    - All addressing attributes can be modified
    - The updated addressing retains all new values
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    addressing_repository = DeviceAddressingRepository(db_session)
    addressing = addressing_repository.store(sample_device_addressing(device.id))

    update_data = sample_device_addressing_update()
    updated = addressing_repository.update(addressing.id, update_data)

    assert updated is not None
    assert updated.device_id == device.id
    assert updated.client_address == update_data.client_address
    assert updated.server_address == update_data.server_address
    assert updated.use_logical_name == update_data.use_logical_name


def test_update_partial_fields(db_session, sample_device, sample_device_addressing):
    """
    Test that update() with partial fields only changes provided attributes.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    addressing_repository = DeviceAddressingRepository(db_session)
    data = sample_device_addressing(device.id)
    addressing = addressing_repository.store(data)

    original_client = addressing.client_address
    original_server = addressing.server_address

    partial = DeviceAddressingUpdate(use_logical_name=False)
    updated = addressing_repository.update(addressing.id, partial)

    assert updated.use_logical_name is False
    assert updated.client_address == original_client
    assert updated.server_address == original_server


def test_update_nonexistent_raises(db_session, sample_device_addressing_update):
    """
    Test that update() on non-existent device addressing raises NoResultFound.
    """
    addressing_repository = DeviceAddressingRepository(db_session)
    update_data = sample_device_addressing_update()

    with pytest.raises(NoResultFound):
        addressing_repository.update(uuid.uuid4(), update_data)


def test_destroy_success(db_session, sample_device, sample_device_addressing):
    """
    Test that destroy() removes a device addressing from the database.

    Verifies that:
    - A device addressing can be deleted successfully
    - The addressing no longer exists after deletion
    - Attempting to retrieve a deleted addressing returns None
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    addressing_repository = DeviceAddressingRepository(db_session)
    addressing = addressing_repository.store(sample_device_addressing(device.id))

    addressing_repository.destroy(addressing.id)

    deleted_addressing = addressing_repository.show(addressing.id)
    assert deleted_addressing is None


def test_destroy_nonexistent_raises(db_session):
    """
    Test that destroy() on non-existent device addressing raises NoResultFound.
    """
    addressing_repository = DeviceAddressingRepository(db_session)

    with pytest.raises(NoResultFound):
        addressing_repository.destroy(uuid.uuid4())
