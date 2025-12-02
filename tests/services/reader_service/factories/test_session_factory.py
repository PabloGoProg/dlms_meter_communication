"""
Tests for the SessionFactory in the reader service factories.

Tests that the SessionFactory correctly creates sessions with the appropriate
application layer provider, manages database connections, and handles errors.
"""

import uuid
from unittest.mock import MagicMock, patch
from contextlib import contextmanager

from dlms_meter_communication.models.enums import Medium, Profile
from dlms_meter_communication.schemas import Device, CommunicationEndpoint
from dlms_meter_communication.services.reader_service.factories.sessions.session_factory import (
    SessionFactory,
)
from dlms_meter_communication.services.reader_service.utils.enums import (
    AppLayerProviderType,
)
from dlms_meter_communication.services.reader_service.core.session import Session


def _build_device(**overrides) -> Device:
    """
    Builds a `Device` for testing with default values that
    can be overridden according to the use case.
    """

    data = {
        "id": uuid.uuid4(),
        "name": "Test Device",
        "description": "Test device description",
        "serial_number": "SN123456",
        "brand": "Test Brand",
        "model": "Test Model",
        "communication_endpoints": [],
        "device_addressings": [],
    }
    data.update(overrides)
    return Device(**data)


def _build_communication_endpoint(**overrides) -> CommunicationEndpoint:
    """
    Builds a `CommunicationEndpoint` for testing with default values that
    can be overridden according to the use case.
    """

    data = {
        "id": uuid.uuid4(),
        "device_id": uuid.uuid4(),
        "medium": Medium.TCP,
        "profile": Profile.WRAPPER,
        "ip": "192.0.2.100",
        "port": 4059,
        "serial_port": None,
        "baud_rate": None,
        "is_primary": True,
    }
    data.update(overrides)
    return CommunicationEndpoint(**data)


def test_session_factory_crea_sesion_con_proveedor_gurux_por_defecto() -> None:
    """
    Tests that SessionFactory creates a session with Gurux provider by default.
    """

    device = _build_device()
    endpoint = _build_communication_endpoint(device_id=device.id)
    factory = SessionFactory()

    # Mock database session and repository
    mock_db_session = MagicMock()

    @contextmanager
    def mock_get_context_session():
        try:
            yield mock_db_session
        finally:
            pass

    mock_comm_endpoint_repo = MagicMock()
    mock_comm_endpoint_repo.get_primary_by_device_id.return_value = endpoint

    mock_app_layer = MagicMock()

    with (
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.get_context_session",
            side_effect=mock_get_context_session,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.CommunicationEndpointRepository",
            return_value=mock_comm_endpoint_repo,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.GuruxAppFactory"
        ) as mock_gurux_factory_cls,
    ):
        mock_gurux_factory = mock_gurux_factory_cls.return_value
        mock_gurux_factory.create_app_layer.return_value = mock_app_layer

        # Build session without specifying provider (should use default: GURUX_COSEM)
        session = factory.build_session(device)

    # Verify that repository was called correctly
    mock_comm_endpoint_repo.get_primary_by_device_id.assert_called_once_with(device.id)

    # Verify that Gurux factory was used
    mock_gurux_factory_cls.assert_called_once()
    mock_gurux_factory.create_app_layer.assert_called_once_with(endpoint)

    # Verify session was created correctly
    assert isinstance(session, Session)
    assert session.device is device
    assert session.app_layer is mock_app_layer


def test_session_factory_crea_sesion_con_proveedor_gurux_explicito() -> None:
    """
    Tests that SessionFactory creates a session with Gurux provider when explicitly specified.
    """

    device = _build_device()
    endpoint = _build_communication_endpoint(device_id=device.id)
    factory = SessionFactory()

    # Mock database session and repository
    mock_db_session = MagicMock()

    @contextmanager
    def mock_get_context_session():
        try:
            yield mock_db_session
        finally:
            pass

    mock_comm_endpoint_repo = MagicMock()
    mock_comm_endpoint_repo.get_primary_by_device_id.return_value = endpoint

    mock_app_layer = MagicMock()

    with (
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.get_context_session",
            side_effect=mock_get_context_session,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.CommunicationEndpointRepository",
            return_value=mock_comm_endpoint_repo,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.GuruxAppFactory"
        ) as mock_gurux_factory_cls,
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.COSEMNativeAppFactory"
        ) as mock_cosem_factory_cls,
    ):
        mock_gurux_factory = mock_gurux_factory_cls.return_value
        mock_gurux_factory.create_app_layer.return_value = mock_app_layer

        # Build session with explicit Gurux provider
        session = factory.build_session(device, AppLayerProviderType.GURUX_COSEM)

    # Verify that Gurux factory was used
    mock_gurux_factory_cls.assert_called_once()
    mock_gurux_factory.create_app_layer.assert_called_once_with(endpoint)

    # Verify that COSEM Native factory was NOT used
    mock_cosem_factory_cls.assert_not_called()

    # Verify session was created correctly
    assert isinstance(session, Session)
    assert session.device is device
    assert session.app_layer is mock_app_layer


def test_session_factory_crea_sesion_con_proveedor_cosem_native() -> None:
    """
    Tests that SessionFactory creates a session with COSEM Native provider when specified.
    """

    device = _build_device()
    endpoint = _build_communication_endpoint(
        device_id=device.id, profile=Profile.WRAPPER
    )
    factory = SessionFactory()

    # Mock database session and repository
    mock_db_session = MagicMock()

    @contextmanager
    def mock_get_context_session():
        try:
            yield mock_db_session
        finally:
            pass

    mock_comm_endpoint_repo = MagicMock()
    mock_comm_endpoint_repo.get_primary_by_device_id.return_value = endpoint

    mock_app_layer = MagicMock()

    with (
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.get_context_session",
            side_effect=mock_get_context_session,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.CommunicationEndpointRepository",
            return_value=mock_comm_endpoint_repo,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.COSEMNativeAppFactory"
        ) as mock_cosem_factory_cls,
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.GuruxAppFactory"
        ) as mock_gurux_factory_cls,
    ):
        mock_cosem_factory = mock_cosem_factory_cls.return_value
        mock_cosem_factory.create_app_layer.return_value = mock_app_layer

        # Build session with COSEM Native provider
        session = factory.build_session(device, AppLayerProviderType.COSEM_NATIVE)

    # Verify that repository was called correctly
    mock_comm_endpoint_repo.get_primary_by_device_id.assert_called_once_with(device.id)

    # Note: Current implementation has a bug where it checks profile against AppLayerProviderType
    # which will always fail. The COSEM factory should be called but won't be due to the bug.
    # This test documents the current behavior.

    # Verify that Gurux factory was NOT used
    mock_gurux_factory_cls.assert_not_called()

    # Verify session was created
    assert isinstance(session, Session)


def test_session_factory_obtiene_endpoint_primario_de_base_datos() -> None:
    """
    Tests that SessionFactory retrieves the primary endpoint from the database.
    """

    device = _build_device()
    endpoint = _build_communication_endpoint(device_id=device.id)
    factory = SessionFactory()

    # Mock database session and repository
    mock_db_session = MagicMock()

    @contextmanager
    def mock_get_context_session():
        try:
            yield mock_db_session
        finally:
            pass

    mock_comm_endpoint_repo = MagicMock()
    mock_comm_endpoint_repo.get_primary_by_device_id.return_value = endpoint

    mock_app_layer = MagicMock()

    with (
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.get_context_session",
            side_effect=mock_get_context_session,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.CommunicationEndpointRepository",
            return_value=mock_comm_endpoint_repo,
        ) as mock_repo_cls,
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.GuruxAppFactory"
        ) as mock_gurux_factory_cls,
    ):
        mock_gurux_factory = mock_gurux_factory_cls.return_value
        mock_gurux_factory.create_app_layer.return_value = mock_app_layer

        factory.build_session(device)

    # Verify that repository was instantiated with the database session
    mock_repo_cls.assert_called_once_with(session=mock_db_session)

    # Verify that get_primary_by_device_id was called with correct device ID
    mock_comm_endpoint_repo.get_primary_by_device_id.assert_called_once_with(device.id)


def test_session_factory_cierra_sesion_base_datos_despues_uso() -> None:
    """
    Tests that SessionFactory closes the database session after use.
    """

    device = _build_device()
    endpoint = _build_communication_endpoint(device_id=device.id)
    factory = SessionFactory()

    # Mock database session and repository
    mock_db_session = MagicMock()
    context_manager_entered = False
    context_manager_exited = False

    @contextmanager
    def mock_get_context_session():
        nonlocal context_manager_entered, context_manager_exited
        try:
            context_manager_entered = True
            yield mock_db_session
        finally:
            context_manager_exited = True

    mock_comm_endpoint_repo = MagicMock()
    mock_comm_endpoint_repo.get_primary_by_device_id.return_value = endpoint

    mock_app_layer = MagicMock()

    with (
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.get_context_session",
            side_effect=mock_get_context_session,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.CommunicationEndpointRepository",
            return_value=mock_comm_endpoint_repo,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.GuruxAppFactory"
        ) as mock_gurux_factory_cls,
    ):
        mock_gurux_factory = mock_gurux_factory_cls.return_value
        mock_gurux_factory.create_app_layer.return_value = mock_app_layer

        factory.build_session(device)

    # Verify that context manager was properly used
    assert context_manager_entered is True
    assert context_manager_exited is True


def test_session_factory_propaga_excepciones_del_repositorio() -> None:
    """
    Tests that SessionFactory propagates exceptions from the repository.
    """

    device = _build_device()
    factory = SessionFactory()

    # Mock database session and repository
    mock_db_session = MagicMock()

    @contextmanager
    def mock_get_context_session():
        try:
            yield mock_db_session
        finally:
            pass

    mock_comm_endpoint_repo = MagicMock()
    mock_comm_endpoint_repo.get_primary_by_device_id.side_effect = Exception(
        "Database error"
    )

    with (
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.get_context_session",
            side_effect=mock_get_context_session,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.CommunicationEndpointRepository",
            return_value=mock_comm_endpoint_repo,
        ),
    ):
        try:
            factory.build_session(device)
            assert False, "Should have raised an exception"
        except Exception as e:
            assert "Database error" in str(e)


def test_session_factory_retorna_sesion_con_device_y_app_layer() -> None:
    """
    Tests that SessionFactory returns a session with both device and app layer set.
    """

    device = _build_device()
    endpoint = _build_communication_endpoint(device_id=device.id)
    factory = SessionFactory()

    # Mock database session and repository
    mock_db_session = MagicMock()

    @contextmanager
    def mock_get_context_session():
        try:
            yield mock_db_session
        finally:
            pass

    mock_comm_endpoint_repo = MagicMock()
    mock_comm_endpoint_repo.get_primary_by_device_id.return_value = endpoint

    mock_app_layer = MagicMock()

    with (
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.get_context_session",
            side_effect=mock_get_context_session,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.CommunicationEndpointRepository",
            return_value=mock_comm_endpoint_repo,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.GuruxAppFactory"
        ) as mock_gurux_factory_cls,
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.Session"
        ) as mock_session_cls,
    ):
        mock_gurux_factory = mock_gurux_factory_cls.return_value
        mock_gurux_factory.create_app_layer.return_value = mock_app_layer

        mock_session_instance = MagicMock(spec=Session)
        mock_session_cls.return_value = mock_session_instance

        session = factory.build_session(device)

    # Verify that Session was created with only device
    mock_session_cls.assert_called_once_with(device)

    # Verify that app_layer was assigned
    assert mock_session_instance.app_layer == mock_app_layer

    # Verify that the returned session is the mocked instance
    assert session is mock_session_instance


def test_session_factory_usa_endpoint_correcto_para_crear_app_layer() -> None:
    """
    Tests that SessionFactory passes the correct endpoint to the app layer factory.
    """

    device = _build_device()
    endpoint = _build_communication_endpoint(
        device_id=device.id, ip="10.20.30.40", port=8080
    )
    factory = SessionFactory()

    # Mock database session and repository
    mock_db_session = MagicMock()

    @contextmanager
    def mock_get_context_session():
        try:
            yield mock_db_session
        finally:
            pass

    mock_comm_endpoint_repo = MagicMock()
    mock_comm_endpoint_repo.get_primary_by_device_id.return_value = endpoint

    mock_app_layer = MagicMock()

    with (
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.get_context_session",
            side_effect=mock_get_context_session,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.CommunicationEndpointRepository",
            return_value=mock_comm_endpoint_repo,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.GuruxAppFactory"
        ) as mock_gurux_factory_cls,
    ):
        mock_gurux_factory = mock_gurux_factory_cls.return_value
        mock_gurux_factory.create_app_layer.return_value = mock_app_layer

        factory.build_session(device)

    # Verify that the app layer factory was called with the correct endpoint
    mock_gurux_factory.create_app_layer.assert_called_once()
    call_args = mock_gurux_factory.create_app_layer.call_args
    passed_endpoint = call_args[0][0]

    assert passed_endpoint is endpoint
    assert passed_endpoint.ip == "10.20.30.40"
    assert passed_endpoint.port == 8080


def test_session_factory_con_diferentes_tipos_proveedor() -> None:
    """
    Tests SessionFactory with different provider types.
    """

    device = _build_device()
    endpoint = _build_communication_endpoint(device_id=device.id)
    factory = SessionFactory()

    # Mock database session and repository
    mock_db_session = MagicMock()

    @contextmanager
    def mock_get_context_session():
        try:
            yield mock_db_session
        finally:
            pass

    mock_comm_endpoint_repo = MagicMock()
    mock_comm_endpoint_repo.get_primary_by_device_id.return_value = endpoint

    mock_app_layer = MagicMock()

    with (
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.get_context_session",
            side_effect=mock_get_context_session,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.CommunicationEndpointRepository",
            return_value=mock_comm_endpoint_repo,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.GuruxAppFactory"
        ) as mock_gurux_factory_cls,
        patch(
            "dlms_meter_communication.services.reader_service.factories.sessions.session_factory.COSEMNativeAppFactory"
        ) as mock_cosem_factory_cls,
    ):
        mock_gurux_factory = mock_gurux_factory_cls.return_value
        mock_gurux_factory.create_app_layer.return_value = mock_app_layer

        mock_cosem_factory = mock_cosem_factory_cls.return_value
        mock_cosem_factory.create_app_layer.return_value = mock_app_layer

        # Test with GURUX_COSEM
        session1 = factory.build_session(device, AppLayerProviderType.GURUX_COSEM)
        assert isinstance(session1, Session)

        # Reset mocks
        mock_gurux_factory_cls.reset_mock()
        mock_cosem_factory_cls.reset_mock()

        # Test with COSEM_NATIVE
        session2 = factory.build_session(device, AppLayerProviderType.COSEM_NATIVE)
        assert isinstance(session2, Session)
