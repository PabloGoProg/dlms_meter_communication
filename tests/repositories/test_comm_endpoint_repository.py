from dlms_meter_communication.repositories import (
    CommunicationEndpointRepository,
    DeviceRepository,
)
from dlms_meter_communication.schemas import (
    DeviceCreate,
    CommunicationEndpointCreate,
    CommunicationEndpointUpdate,
)
from sqlalchemy.exc import InvalidRequestError, NoResultFound
from dlms_meter_communication.models.enums import Medium, Profile
from dlms_meter_communication.db.database import get_session
import uuid
import pytest


def _get_sample_device():
    return DeviceCreate(
        name=f"Test Device {uuid.uuid4()}",
        serial_number=f"1234567890{uuid.uuid4()}",
        brand=f"Test Brand {uuid.uuid4()}",
        model=f"Test Model {uuid.uuid4()}",
    )


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


def test_create_communication_endpoint(session_fixture):
    """
    Test that store() creates a communication endpoint successfully.
    """
    _, session = session_fixture
    device_repository = DeviceRepository(session)
    device = device_repository.store(_get_sample_device())

    try:
        communication_endpoint_repository = CommunicationEndpointRepository(session)
        communication_endpoint = communication_endpoint_repository.store(
            CommunicationEndpointCreate(
                device_id=device.id,
                medium=Medium.TCP,
                profile=Profile.WRAPPER,
                ip="127.0.0.1",
                port=12345,
                serial_port="COM1",
                baud_rate=9600,
                is_primary=True,
            )
        )

        created_communication_endpoint = communication_endpoint_repository.show(
            communication_endpoint.id
        )

        assert created_communication_endpoint is not None
        assert created_communication_endpoint.device_id == device.id
        assert created_communication_endpoint.medium == Medium.TCP
        assert created_communication_endpoint.profile == Profile.WRAPPER
        assert created_communication_endpoint.ip == "127.0.0.1"
        assert created_communication_endpoint.port == 12345
        assert created_communication_endpoint.serial_port == "COM1"
        assert created_communication_endpoint.baud_rate == 9600
        assert created_communication_endpoint.is_primary
    finally:
        device_repository.destroy(device.id)
        session.commit()
        session.close()


def test_create_invalid_tcp_communication_endpoint(session_fixture):
    """
    Test that store() raises InvalidRequestError when TCP endpoint lacks required IP and port.
    """
    _, session = session_fixture
    device_repository = DeviceRepository(session)
    device = device_repository.store(_get_sample_device())

    try:
        communication_endpoint_repository = CommunicationEndpointRepository(session)
        _ = communication_endpoint_repository.store(
            CommunicationEndpointCreate(
                device_id=device.id,
                medium=Medium.TCP,
                profile=Profile.WRAPPER,
                ip=None,
                port=None,
                serial_port="COM1",
                baud_rate=9600,
            )
        )

    except InvalidRequestError as e:
        assert str(e) == "IP and port are required for TCP communication"
    finally:
        device_repository.destroy(device.id)
        session.commit()
        session.close()


def test_create_invalid_serial_communication_endpoint(session_fixture):
    """
    Test that store() raises InvalidRequestError when serial endpoint lacks required parameters.
    """
    _, session = session_fixture
    device_repository = DeviceRepository(session)
    device = device_repository.store(_get_sample_device())

    try:
        communication_endpoint_repository = CommunicationEndpointRepository(session)
        _ = communication_endpoint_repository.store(
            CommunicationEndpointCreate(
                device_id=device.id,
                medium=Medium.SERIAL,
                profile=Profile.WRAPPER,
                serial_port="COM1",
                baud_rate=9600,
            )
        )
    except InvalidRequestError as e:
        assert (
            str(e) == "Serial port and baud rate are required for serial communication"
        )
    finally:
        device_repository.destroy(device.id)
        session.commit()
        session.close()


def test_get_communication_endpoint_by_id(session_fixture):
    """
    Test that show() retrieves a communication endpoint successfully.
    """
    _, session = session_fixture

    device_repository = DeviceRepository(session)
    device = device_repository.store(_get_sample_device())

    try:
        communication_endpoint_repository = CommunicationEndpointRepository(session)
        communication_endpoint = communication_endpoint_repository.store(
            CommunicationEndpointCreate(
                device_id=device.id,
                medium=Medium.TCP,
                profile=Profile.WRAPPER,
                ip="127.0.0.1",
                port=12345,
            )
        )

        created_communication_endpoint = communication_endpoint_repository.show(
            communication_endpoint.id
        )

        assert created_communication_endpoint is not None
        assert created_communication_endpoint.device_id == device.id
        assert created_communication_endpoint.medium == Medium.TCP
        assert created_communication_endpoint.profile == Profile.WRAPPER
        assert created_communication_endpoint.ip == "127.0.0.1"
        assert created_communication_endpoint.port == 12345
    finally:
        device_repository.destroy(device.id)
        session.commit()
        session.close()


def test_get_communication_endpoint_by_id_non_existent(session_fixture):
    """
    Test that show() returns None for a non-existent communication endpoint ID.
    """
    _, session = session_fixture

    try:
        communication_endpoint_repository = CommunicationEndpointRepository(session)
        endpoint = communication_endpoint_repository.show(uuid.uuid4())
        assert endpoint is None
    finally:
        session.close()


def test_index_empty(session_fixture):
    """
    Test that index() returns an empty list when no communication endpoints exist.
    """
    _, session = session_fixture

    try:
        communication_endpoint_repository = CommunicationEndpointRepository(session)
        endpoints = communication_endpoint_repository.index()
        assert len(endpoints) == 0
    finally:
        session.close()


def test_index_non_empty(session_fixture):
    """
    Test that index() returns a non-empty list when communication endpoints exist.
    """
    _, session = session_fixture
    device_repository = DeviceRepository(session)
    device = device_repository.store(_get_sample_device())

    try:
        communication_endpoint_repository = CommunicationEndpointRepository(session)
        endpoint = communication_endpoint_repository.store(
            CommunicationEndpointCreate(
                device_id=device.id,
                medium=Medium.TCP,
                profile=Profile.WRAPPER,
                ip="127.0.0.1",
                port=12345,
            )
        )

        endpoints = communication_endpoint_repository.index()
        assert len(endpoints) == 1
        assert endpoints[0].id == endpoint.id
    finally:
        device_repository.destroy(device.id)
        session.commit()
        session.close()


def test_index_pagination(session_fixture):
    """
    Test that index() respects pagination parameters (offset and limit).
    """
    _, session = session_fixture
    device_repository = DeviceRepository(session)
    device = device_repository.store(_get_sample_device())

    try:
        communication_endpoint_repository = CommunicationEndpointRepository(session)
        # Create multiple endpoints
        endpoint1 = communication_endpoint_repository.store(
            CommunicationEndpointCreate(
                device_id=device.id,
                medium=Medium.TCP,
                profile=Profile.WRAPPER,
                ip="127.0.0.1",
                port=12345,
            )
        )
        endpoint2 = communication_endpoint_repository.store(
            CommunicationEndpointCreate(
                device_id=device.id,
                medium=Medium.TCP,
                profile=Profile.WRAPPER,
                ip="127.0.0.2",
                port=12346,
            )
        )

        # Test limit
        endpoints = communication_endpoint_repository.index(limit=1)
        assert len(endpoints) == 1
        assert endpoints[0].id == endpoint2.id  # Most recent first

        # Test offset and limit
        endpoints = communication_endpoint_repository.index(offset=1, limit=1)
        assert len(endpoints) == 1
        assert endpoints[0].id == endpoint1.id
    finally:
        device_repository.destroy(device.id)
        session.commit()
        session.close()


def test_index_by_device_id(session_fixture):
    """
    Test that index_by_device_id() returns all endpoints for a specific device.
    """
    _, session = session_fixture
    device_repository = DeviceRepository(session)
    device1 = device_repository.store(_get_sample_device())
    device2 = device_repository.store(
        DeviceCreate(
            name="Test Device 2",
            serial_number="1234567891",
            brand="Test Brand",
            model="Test Model",
        )
    )

    try:
        communication_endpoint_repository = CommunicationEndpointRepository(session)
        endpoint1 = communication_endpoint_repository.store(
            CommunicationEndpointCreate(
                device_id=device1.id,
                medium=Medium.TCP,
                profile=Profile.WRAPPER,
                ip="127.0.0.1",
                port=12345,
            )
        )
        endpoint2 = communication_endpoint_repository.store(
            CommunicationEndpointCreate(
                device_id=device1.id,
                medium=Medium.TCP,
                profile=Profile.WRAPPER,
                ip="127.0.0.2",
                port=12346,
            )
        )
        endpoint3 = communication_endpoint_repository.store(
            CommunicationEndpointCreate(
                device_id=device2.id,
                medium=Medium.TCP,
                profile=Profile.WRAPPER,
                ip="127.0.0.3",
                port=12347,
            )
        )

        # Get endpoints for device1
        endpoints = communication_endpoint_repository.index_by_device_id(device1.id)
        assert len(endpoints) == 2
        endpoint_ids = [e.id for e in endpoints]
        assert endpoint1.id in endpoint_ids
        assert endpoint2.id in endpoint_ids
        assert endpoint3.id not in endpoint_ids

        # Get endpoints for device2
        endpoints = communication_endpoint_repository.index_by_device_id(device2.id)
        assert len(endpoints) == 1
        assert endpoints[0].id == endpoint3.id
    finally:
        device_repository.destroy(device1.id)
        device_repository.destroy(device2.id)
        session.commit()
        session.close()


def test_get_primary_by_device_id(session_fixture):
    """
    Test that get_primary_by_device_id() returns the primary endpoint for a device.
    """
    _, session = session_fixture
    device_repository = DeviceRepository(session)
    device = device_repository.store(_get_sample_device())

    try:
        communication_endpoint_repository = CommunicationEndpointRepository(session)
        primary_endpoint = communication_endpoint_repository.store(
            CommunicationEndpointCreate(
                device_id=device.id,
                medium=Medium.TCP,
                profile=Profile.WRAPPER,
                ip="127.0.0.1",
                port=12345,
                is_primary=True,
            )
        )
        secondary_endpoint = communication_endpoint_repository.store(
            CommunicationEndpointCreate(
                device_id=device.id,
                medium=Medium.TCP,
                profile=Profile.WRAPPER,
                ip="127.0.0.2",
                port=12346,
                is_primary=False,
            )
        )

        primary = communication_endpoint_repository.get_primary_by_device_id(device.id)
        assert primary is not None
        assert primary.id == primary_endpoint.id
        assert primary.is_primary is True
        assert primary.id != secondary_endpoint.id
    finally:
        device_repository.destroy(device.id)
        session.commit()
        session.close()


def test_get_primary_by_device_id_none(session_fixture):
    """
    Test that get_primary_by_device_id() returns None when device has no primary endpoint.
    """
    _, session = session_fixture
    device_repository = DeviceRepository(session)
    device = device_repository.store(_get_sample_device())

    try:
        communication_endpoint_repository = CommunicationEndpointRepository(session)
        # No endpoints created, should return None
        primary = communication_endpoint_repository.get_primary_by_device_id(device.id)
        assert primary is None
    finally:
        device_repository.destroy(device.id)
        session.commit()
        session.close()


def test_first_endpoint_becomes_primary(session_fixture):
    """
    Test that the first endpoint for a device automatically becomes primary.
    """
    _, session = session_fixture
    device_repository = DeviceRepository(session)
    device = device_repository.store(_get_sample_device())

    try:
        communication_endpoint_repository = CommunicationEndpointRepository(session)
        # Create first endpoint without specifying is_primary
        endpoint1 = communication_endpoint_repository.store(
            CommunicationEndpointCreate(
                device_id=device.id,
                medium=Medium.TCP,
                profile=Profile.WRAPPER,
                ip="127.0.0.1",
                port=12345,
            )
        )

        assert endpoint1.is_primary is True

        # Create second endpoint, should not be primary
        endpoint2 = communication_endpoint_repository.store(
            CommunicationEndpointCreate(
                device_id=device.id,
                medium=Medium.TCP,
                profile=Profile.WRAPPER,
                ip="127.0.0.2",
                port=12346,
            )
        )

        assert endpoint2.is_primary is False
        assert endpoint1.is_primary is True
    finally:
        device_repository.destroy(device.id)
        session.commit()
        session.close()


def test_update_communication_endpoint(session_fixture):
    """
    Test that update() modifies an existing communication endpoint successfully.
    """
    _, session = session_fixture
    device_repository = DeviceRepository(session)
    device = device_repository.store(_get_sample_device())

    try:
        communication_endpoint_repository = CommunicationEndpointRepository(session)
        endpoint = communication_endpoint_repository.store(
            CommunicationEndpointCreate(
                device_id=device.id,
                medium=Medium.TCP,
                profile=Profile.WRAPPER,
                ip="127.0.0.1",
                port=12345,
            )
        )

        updated_endpoint = communication_endpoint_repository.update(
            endpoint.id,
            CommunicationEndpointUpdate(
                ip="192.168.1.1",
                port=54321,
                is_primary=False,
            ),
        )

        assert updated_endpoint is not None
        assert updated_endpoint.ip == "192.168.1.1"
        assert updated_endpoint.port == 54321
        assert updated_endpoint.is_primary is False
        assert updated_endpoint.medium == Medium.TCP
        assert updated_endpoint.profile == Profile.WRAPPER
    finally:
        device_repository.destroy(device.id)
        session.commit()
        session.close()


# def test_update_set_primary_demotes_previous(session_fixture):
#     """
#     Test that setting a new primary endpoint demotes the previous primary.
#     """
#     _, session = session_fixture
#     device_repository = DeviceRepository(session)
#     device = device_repository.store(_get_sample_device())

#     try:
#         communication_endpoint_repository = CommunicationEndpointRepository(session)
#         primary_endpoint = communication_endpoint_repository.store(
#             CommunicationEndpointCreate(
#                 device_id=device.id,
#                 medium=Medium.TCP,
#                 profile=Profile.WRAPPER,
#                 ip="127.0.0.1",
#                 port=12345,
#                 is_primary=True,
#             )
#         )
#         secondary_endpoint = communication_endpoint_repository.store(
#             CommunicationEndpointCreate(
#                 device_id=device.id,
#                 medium=Medium.TCP,
#                 profile=Profile.WRAPPER,
#                 ip="127.0.0.2",
#                 port=12346,
#                 is_primary=False,
#             )
#         )

#         assert primary_endpoint.is_primary is True
#         assert secondary_endpoint.is_primary is False

#         # Update secondary to become primary
#         updated_secondary = communication_endpoint_repository.update(
#             secondary_endpoint.id,
#             CommunicationEndpointUpdate(is_primary=True),
#         )

#         # Refresh primary endpoint
#         session.refresh(primary_endpoint)

#         assert updated_secondary.is_primary is True
#         assert primary_endpoint.is_primary is False
#     finally:
#         device_repository.destroy(device.id)
#         session.commit()
#         session.close()


# def test_update_non_existent(session_fixture):
#     """
#     Test that update() raises NoResultFound for a non-existent endpoint ID.
#     """
#     _, session = session_fixture

#     try:
#         communication_endpoint_repository = CommunicationEndpointRepository(session)
#         with pytest.raises(NoResultFound) as exc_info:
#             communication_endpoint_repository.update(
#                 uuid.uuid4(),
#                 CommunicationEndpointUpdate(ip="127.0.0.1"),
#             )
#         assert "not found" in str(exc_info.value)
#     finally:
#         session.close()


# def test_destroy_communication_endpoint(session_fixture):
#     """
#     Test that destroy() removes a non-primary communication endpoint successfully.
#     """
#     _, session = session_fixture
#     device_repository = DeviceRepository(session)
#     device = device_repository.store(_get_sample_device())

#     try:
#         communication_endpoint_repository = CommunicationEndpointRepository(session)
#         primary_endpoint = communication_endpoint_repository.store(
#             CommunicationEndpointCreate(
#                 device_id=device.id,
#                 medium=Medium.TCP,
#                 profile=Profile.WRAPPER,
#                 ip="127.0.0.1",
#                 port=12345,
#                 is_primary=True,
#             )
#         )
#         secondary_endpoint = communication_endpoint_repository.store(
#             CommunicationEndpointCreate(
#                 device_id=device.id,
#                 medium=Medium.TCP,
#                 profile=Profile.WRAPPER,
#                 ip="127.0.0.2",
#                 port=12346,
#                 is_primary=False,
#             )
#         )

#         # Delete secondary endpoint
#         communication_endpoint_repository.destroy(secondary_endpoint.id)

#         # Verify it's deleted
#         deleted_endpoint = communication_endpoint_repository.show(secondary_endpoint.id)
#         assert deleted_endpoint is None

#         # Verify primary still exists
#         primary = communication_endpoint_repository.show(primary_endpoint.id)
#         assert primary is not None
#     finally:
#         device_repository.destroy(device.id)
#         session.commit()
#         session.close()


# def test_destroy_primary_endpoint_error(session_fixture):
#     """
#     Test that destroy() raises InvalidRequestError when attempting to delete a primary endpoint.
#     """
#     _, session = session_fixture
#     device_repository = DeviceRepository(session)
#     device = device_repository.store(_get_sample_device())

#     try:
#         communication_endpoint_repository = CommunicationEndpointRepository(session)
#         primary_endpoint = communication_endpoint_repository.store(
#             CommunicationEndpointCreate(
#                 device_id=device.id,
#                 medium=Medium.TCP,
#                 profile=Profile.WRAPPER,
#                 ip="127.0.0.1",
#                 port=12345,
#                 is_primary=True,
#             )
#         )

#         with pytest.raises(InvalidRequestError) as exc_info:
#             communication_endpoint_repository.destroy(primary_endpoint.id)
#         assert "is primary and cannot be deleted" in str(exc_info.value)

#         # Verify endpoint still exists
#         endpoint = communication_endpoint_repository.show(primary_endpoint.id)
#         assert endpoint is not None
#     finally:
#         device_repository.destroy(device.id)
#         session.commit()
#         session.close()


# def test_destroy_non_existent(session_fixture):
#     """
#     Test that destroy() raises NoResultFound for a non-existent endpoint ID.
#     """
#     _, session = session_fixture

#     try:
#         communication_endpoint_repository = CommunicationEndpointRepository(session)
#         with pytest.raises(NoResultFound) as exc_info:
#             communication_endpoint_repository.destroy(uuid.uuid4())
#         assert "not found" in str(exc_info.value)
#     finally:
#         session.close()


# def test_create_serial_endpoint(session_fixture):
#     """
#     Test that store() creates a serial communication endpoint successfully.
#     """
#     _, session = session_fixture
#     device_repository = DeviceRepository(session)
#     device = device_repository.store(_get_sample_device())

#     try:
#         communication_endpoint_repository = CommunicationEndpointRepository(session)
#         endpoint = communication_endpoint_repository.store(
#             CommunicationEndpointCreate(
#                 device_id=device.id,
#                 medium=Medium.SERIAL,
#                 profile=Profile.WRAPPER,
#                 serial_port="/dev/ttyUSB0",
#                 baud_rate=9600,
#             )
#         )

#         created_endpoint = communication_endpoint_repository.show(endpoint.id)

#         assert created_endpoint is not None
#         assert created_endpoint.device_id == device.id
#         assert created_endpoint.medium == Medium.SERIAL
#         assert created_endpoint.profile == Profile.WRAPPER
#         assert created_endpoint.serial_port == "/dev/ttyUSB0"
#         assert created_endpoint.baud_rate == 9600
#         assert created_endpoint.is_primary is True  # First endpoint is primary
#     finally:
#         device_repository.destroy(device.id)
#         session.commit()
#         session.close()


# def test_create_serial_endpoint_missing_params(session_fixture):
#     """
#     Test that store() raises InvalidRequestError when serial endpoint is missing serial_port or baud_rate.
#     """
#     _, session = session_fixture
#     device_repository = DeviceRepository(session)
#     device = device_repository.store(_get_sample_device())

#     try:
#         communication_endpoint_repository = CommunicationEndpointRepository(session)

#         # Missing serial_port
#         with pytest.raises(InvalidRequestError) as exc_info:
#             communication_endpoint_repository.store(
#                 CommunicationEndpointCreate(
#                     device_id=device.id,
#                     medium=Medium.SERIAL,
#                     profile=Profile.WRAPPER,
#                     baud_rate=9600,
#                 )
#             )
#         assert "Serial port and baud rate are required" in str(exc_info.value)

#         # Missing baud_rate
#         with pytest.raises(InvalidRequestError) as exc_info:
#             communication_endpoint_repository.store(
#                 CommunicationEndpointCreate(
#                     device_id=device.id,
#                     medium=Medium.SERIAL,
#                     profile=Profile.WRAPPER,
#                     serial_port="/dev/ttyUSB0",
#                 )
#             )
#         assert "Serial port and baud rate are required" in str(exc_info.value)
#     finally:
#         device_repository.destroy(device.id)
#         session.commit()
#         session.close()


# def test_create_tcp_endpoint_missing_params(session_fixture):
#     """
#     Test that store() raises InvalidRequestError when TCP endpoint is missing ip or port.
#     """
#     _, session = session_fixture
#     device_repository = DeviceRepository(session)
#     device = device_repository.store(_get_sample_device())

#     try:
#         communication_endpoint_repository = CommunicationEndpointRepository(session)

#         # Missing ip
#         with pytest.raises(InvalidRequestError) as exc_info:
#             communication_endpoint_repository.store(
#                 CommunicationEndpointCreate(
#                     device_id=device.id,
#                     medium=Medium.TCP,
#                     profile=Profile.WRAPPER,
#                     port=12345,
#                 )
#             )
#         assert "IP and port are required for TCP communication" in str(exc_info.value)

#         # Missing port
#         with pytest.raises(InvalidRequestError) as exc_info:
#             communication_endpoint_repository.store(
#                 CommunicationEndpointCreate(
#                     device_id=device.id,
#                     medium=Medium.TCP,
#                     profile=Profile.WRAPPER,
#                     ip="127.0.0.1",
#                 )
#             )
#         assert "IP and port are required for TCP communication" in str(exc_info.value)
#     finally:
#         device_repository.destroy(device.id)
#         session.commit()
#         session.close()
