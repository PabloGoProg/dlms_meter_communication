import uuid
import pytest
from uuid import UUID
import random

from dlms_meter_communication.repositories import (
    CommunicationEndpointRepository,
    DeviceRepository,
)
from dlms_meter_communication.schemas import (
    CommunicationEndpointCreate,
    CommunicationEndpointUpdate,
)
from sqlalchemy.exc import InvalidRequestError, NoResultFound
from dlms_meter_communication.models.enums import Medium, Profile

# Fixture to use the simulated database session for all tests
pytestmark = pytest.mark.usefixtures("db_session")


def __communication_endpoint(
    medium: Medium,
    device_id: UUID,
    is_primary: bool = True,
) -> CommunicationEndpointCreate:
    return CommunicationEndpointCreate(
        device_id=device_id,
        medium=medium,
        ip=f"127.0.0.{random.randint(1, 255)}" if medium == Medium.TCP else None,
        port=12345 if medium == Medium.TCP else None,
        serial_port=f"COM{random.randint(1, 99)}" if medium == Medium.SERIAL else None,
        baud_rate=9600 if medium == Medium.SERIAL else None,
        profile=Profile.WRAPPER,
        is_primary=is_primary,
    )


def test_create_communication_endpoint(db_session, sample_device):
    """
    Test that store() creates a communication endpoint successfully.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    communication_endpoint_repository = CommunicationEndpointRepository(db_session)
    comm_endpoint_data = __communication_endpoint(Medium.TCP, device.id)
    communication_endpoint = communication_endpoint_repository.store(comm_endpoint_data)

    assert communication_endpoint is not None
    assert communication_endpoint.device_id == device.id
    assert communication_endpoint.medium == comm_endpoint_data.medium
    assert communication_endpoint.profile == comm_endpoint_data.profile
    assert communication_endpoint.ip == comm_endpoint_data.ip
    assert communication_endpoint.port == comm_endpoint_data.port
    assert communication_endpoint.serial_port == comm_endpoint_data.serial_port
    assert communication_endpoint.baud_rate == comm_endpoint_data.baud_rate
    assert communication_endpoint.is_primary is comm_endpoint_data.is_primary


def test_create_invalid_tcp_communication_endpoint(db_session, sample_device):
    """
    Test that store() raises InvalidRequestError when TCP endpoint lacks required IP and port.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    communication_endpoint_repository = CommunicationEndpointRepository(db_session)

    with pytest.raises(InvalidRequestError):
        communication_endpoint_repository.store(
            CommunicationEndpointCreate(
                device_id=device.id,
                medium=Medium.TCP,
                profile=Profile.WRAPPER,
                ip=None,
                port=None,
            )
        )


def test_create_invalid_serial_communication_endpoint(db_session, sample_device):
    """
    Test that store() raises InvalidRequestError when serial endpoint lacks required parameters.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    communication_endpoint_repository = CommunicationEndpointRepository(db_session)
    with pytest.raises(InvalidRequestError):
        communication_endpoint_repository.store(
            CommunicationEndpointCreate(
                device_id=device.id,
                medium=Medium.SERIAL,
                profile=Profile.WRAPPER,
                serial_port=None,
                baud_rate=None,
            )
        )


def test_get_communication_endpoint_by_id(
    db_session,
    sample_device,
):
    """
    Test that show() retrieves a communication endpoint successfully.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    communication_endpoint_repository = CommunicationEndpointRepository(db_session)
    comm_endpoint_data = __communication_endpoint(Medium.TCP, device.id)
    communication_endpoint = communication_endpoint_repository.store(comm_endpoint_data)

    retrieved_communication_endpoint = communication_endpoint_repository.show(
        communication_endpoint.id
    )

    assert retrieved_communication_endpoint is not None
    assert retrieved_communication_endpoint.device_id == device.id
    assert retrieved_communication_endpoint.medium == comm_endpoint_data.medium
    assert retrieved_communication_endpoint.profile == comm_endpoint_data.profile
    assert retrieved_communication_endpoint.ip == comm_endpoint_data.ip
    assert retrieved_communication_endpoint.port == comm_endpoint_data.port
    assert (
        retrieved_communication_endpoint.serial_port == comm_endpoint_data.serial_port
    )
    assert retrieved_communication_endpoint.baud_rate == comm_endpoint_data.baud_rate


def test_get_communication_endpoint_by_id_non_existent(db_session):
    """
    Test that show() returns None for a non-existent communication endpoint ID.
    """
    communication_endpoint_repository = CommunicationEndpointRepository(db_session)
    retrieved_communication_endpoint = communication_endpoint_repository.show(
        uuid.uuid4()
    )
    assert retrieved_communication_endpoint is None


def test_index_empty(db_session):
    """
    Test that index() returns an empty list when no communication endpoints exist.
    """
    communication_endpoint_repository = CommunicationEndpointRepository(db_session)
    endpoints = communication_endpoint_repository.index()
    assert len(endpoints) == 0


def test_index_non_empty(db_session, sample_device):
    """
    Test that index() returns a non-empty list when communication endpoints exist.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    communication_endpoint_repository = CommunicationEndpointRepository(db_session)
    communication_endpoint = communication_endpoint_repository.store(
        __communication_endpoint(Medium.TCP, device.id)
    )

    endpoints = communication_endpoint_repository.index()

    assert len(endpoints) == 1
    assert endpoints[0].id == communication_endpoint.id


def test_index_by_device_id(db_session, sample_device):
    """
    Test that index_by_device_id() returns all endpoints for a specific device.
    """
    device_repository = DeviceRepository(db_session)
    device1 = device_repository.store(sample_device())
    device2 = device_repository.store(sample_device())

    communication_endpoint_repository = CommunicationEndpointRepository(db_session)
    communication_endpoint1 = communication_endpoint_repository.store(
        __communication_endpoint(Medium.TCP, device1.id)
    )
    communication_endpoint2 = communication_endpoint_repository.store(
        __communication_endpoint(Medium.TCP, device1.id)
    )
    communication_endpoint3 = communication_endpoint_repository.store(
        __communication_endpoint(Medium.TCP, device2.id)
    )

    communication_endpoints = communication_endpoint_repository.index_by_device_id(
        device1.id
    )
    assert len(communication_endpoints) == 2

    communication_endpoint_ids = [
        comm_endpoint.id for comm_endpoint in communication_endpoints
    ]
    assert communication_endpoint1.id in communication_endpoint_ids
    assert communication_endpoint2.id in communication_endpoint_ids
    assert communication_endpoint3.id not in communication_endpoint_ids


def test_get_primary_by_device_id(db_session, sample_device):
    """
    Test that get_primary_by_device_id() returns the primary endpoint for a device.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    communication_endpoint_repository = CommunicationEndpointRepository(db_session)
    primary_endpoint = communication_endpoint_repository.store(
        __communication_endpoint(Medium.TCP, device.id)
    )
    secondary_endpoint = communication_endpoint_repository.store(
        __communication_endpoint(Medium.TCP, device.id, is_primary=False)
    )

    primary = communication_endpoint_repository.get_primary_by_device_id(device.id)
    assert primary is not None
    assert primary.id == primary_endpoint.id
    assert primary.is_primary is True
    assert primary.id != secondary_endpoint.id


def test_get_primary_by_device_id_none(db_session, sample_device):
    """
    Test that get_primary_by_device_id() returns None when device has no primary endpoint.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    communication_endpoint_repository = CommunicationEndpointRepository(db_session)
    primary = communication_endpoint_repository.get_primary_by_device_id(device.id)

    assert primary is None


def test_first_endpoint_becomes_primary(db_session, sample_device):
    """
    Test that the first endpoint for a device automatically becomes primary.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    communication_endpoint_repository = CommunicationEndpointRepository(db_session)
    endpoint1 = communication_endpoint_repository.store(
        __communication_endpoint(Medium.TCP, device.id, is_primary=False)
    )

    assert endpoint1.is_primary


def test_update_communication_endpoint(db_session, sample_device):
    """
    Test that update() modifies an existing communication endpoint successfully.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    communication_endpoint_repository = CommunicationEndpointRepository(db_session)
    comm_endpoint_data = __communication_endpoint(Medium.TCP, device.id)
    endpoint = communication_endpoint_repository.store(comm_endpoint_data)

    updated_endpoint = communication_endpoint_repository.update(
        endpoint.id,
        CommunicationEndpointUpdate(ip="192.168.1.1", port=54321, is_primary=False),
    )

    assert updated_endpoint is not None
    assert updated_endpoint.ip == "192.168.1.1"
    assert updated_endpoint.port == 54321
    assert updated_endpoint.is_primary is False
    assert updated_endpoint.medium == comm_endpoint_data.medium
    assert updated_endpoint.profile == comm_endpoint_data.profile


def test_update_set_primary_demotes_previous(db_session, sample_device):
    """
    Test that setting a new primary endpoint demotes the previous primary.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    communication_endpoint_repository = CommunicationEndpointRepository(db_session)
    primary_endpoint = communication_endpoint_repository.store(
        __communication_endpoint(Medium.TCP, device.id)
    )
    secondary_endpoint = communication_endpoint_repository.store(
        __communication_endpoint(Medium.TCP, device.id, is_primary=False)
    )

    assert primary_endpoint.is_primary is True
    assert secondary_endpoint.is_primary is False

    # Update secondary to become primary
    updated_secondary = communication_endpoint_repository.update(
        secondary_endpoint.id,
        CommunicationEndpointUpdate(is_primary=True),
    )

    assert updated_secondary.is_primary is True
    assert primary_endpoint.is_primary is False


def test_update_non_existent(db_session):
    """
    Test that update() raises NoResultFound for a non-existent endpoint ID.
    """
    communication_endpoint_repository = CommunicationEndpointRepository(db_session)

    with pytest.raises(NoResultFound):
        communication_endpoint_repository.update(
            uuid.uuid4(),
            CommunicationEndpointUpdate(ip="127.0.0.1"),
        )


def test_destroy_communication_endpoint(db_session, sample_device):
    """
    Test that destroy() removes a non-primary communication endpoint successfully.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    communication_endpoint_repository = CommunicationEndpointRepository(db_session)
    primary_endpoint = communication_endpoint_repository.store(
        __communication_endpoint(Medium.TCP, device.id)
    )
    secondary_endpoint = communication_endpoint_repository.store(
        __communication_endpoint(Medium.TCP, device.id, is_primary=False)
    )

    # Delete secondary endpoint
    communication_endpoint_repository.destroy(secondary_endpoint.id)

    # Verify it's deleted
    deleted_endpoint = communication_endpoint_repository.show(secondary_endpoint.id)
    assert deleted_endpoint is None

    # Verify primary still exists
    primary = communication_endpoint_repository.show(primary_endpoint.id)
    assert primary is not None


def test_destroy_primary_endpoint_error(db_session, sample_device):
    """
    Test that destroy() raises InvalidRequestError when attempting to delete a primary endpoint.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    communication_endpoint_repository = CommunicationEndpointRepository(db_session)
    primary_endpoint = communication_endpoint_repository.store(
        __communication_endpoint(Medium.TCP, device.id, is_primary=True)
    )

    with pytest.raises(InvalidRequestError):
        communication_endpoint_repository.destroy(primary_endpoint.id)


def test_destroy_non_existent(db_session):
    """
    Test that destroy() raises NoResultFound for a non-existent endpoint ID.
    """
    communication_endpoint_repository = CommunicationEndpointRepository(db_session)
    with pytest.raises(NoResultFound):
        communication_endpoint_repository.destroy(uuid.uuid4())


def test_create_serial_endpoint(db_session, sample_device):
    """
    Test that store() creates a serial communication endpoint successfully.
    """
    device_repository = DeviceRepository(db_session)
    device = device_repository.store(sample_device())

    communication_endpoint_repository = CommunicationEndpointRepository(db_session)
    endpoint = communication_endpoint_repository.store(
        __communication_endpoint(Medium.SERIAL, device.id)
    )

    created_endpoint = communication_endpoint_repository.show(endpoint.id)

    assert created_endpoint is not None
    assert created_endpoint.device_id == device.id
    assert created_endpoint.medium == Medium.SERIAL
    assert created_endpoint.profile == Profile.WRAPPER
    assert created_endpoint.serial_port == endpoint.serial_port
    assert created_endpoint.baud_rate == endpoint.baud_rate
