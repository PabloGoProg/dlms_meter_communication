"""
Tests for the application layer factories in the reader service.

Tests that the Gurux app factory creates the expected Gurux COSEM app layer
with proper configuration from device data retrieved from the database.
"""

import uuid
from unittest.mock import MagicMock, patch
from contextlib import contextmanager

from dlms_meter_communication.models.enums import Medium, Profile
from dlms_meter_communication.schemas import (
    Device,
    CommunicationEndpoint,
    DeviceAddressing,
)
from dlms_meter_communication.services.reader_service.adapterss.app_layers.gurux_cosem_app import (
    GuruxCOSEMApp,
)
from dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory import (
    GuruxAppFactory,
)

from gurux_dlms.enums import InterfaceType, Authentication
from gurux_net.enums import NetworkType
from gurux_common.enums import TraceLevel


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


def _build_device_addressing(**overrides) -> DeviceAddressing:
    """
    Builds a `DeviceAddressing` for testing with default values that
    can be overridden according to the use case.
    """

    data = {
        "id": uuid.uuid4(),
        "device_id": uuid.uuid4(),
        "client_address": 16,
        "server_address": 1,
        "use_logical_name": True,
    }
    data.update(overrides)
    return DeviceAddressing(**data)


def test_gurux_app_factory_con_perfil_wrapper_crea_cliente_con_interface_wrapper() -> (
    None
):
    """
    Tests that the Gurux app factory creates a client with WRAPPER interface type
    when the endpoint profile is WRAPPER.
    """

    device = _build_device()
    endpoint = _build_communication_endpoint(
        device_id=device.id, profile=Profile.WRAPPER
    )
    addressing = _build_device_addressing(
        device_id=device.id, client_address=32, server_address=1
    )

    factory = GuruxAppFactory()

    # Mock the database session and repositories
    mock_session = MagicMock()

    @contextmanager
    def mock_get_context_session():
        try:
            yield mock_session
        finally:
            pass

    mock_comm_endpoint_repo = MagicMock()
    mock_comm_endpoint_repo.get_primary_by_device_id.return_value = endpoint

    mock_device_addressing_repo = MagicMock()
    mock_device_addressing_repo.index_by_device_id.return_value = [addressing]

    with (
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.get_context_session",
            side_effect=mock_get_context_session,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.CommunicationEndpointRepository",
            return_value=mock_comm_endpoint_repo,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.DeviceAddressingRepository",
            return_value=mock_device_addressing_repo,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.GXDLMSClient"
        ) as mock_gx_client_cls,
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.GXNet"
        ) as mock_gx_net_cls,
    ):
        mock_gx_client = mock_gx_client_cls.return_value
        mock_gx_media = mock_gx_net_cls.return_value

        app_layer = factory.create_app_layer(device)

    # Verify that repositories were called correctly
    mock_comm_endpoint_repo.get_primary_by_device_id.assert_called_once_with(device.id)
    mock_device_addressing_repo.index_by_device_id.assert_called_once_with(device.id)

    # Verify that GXDLMSClient was created with WRAPPER interface type
    mock_gx_client_cls.assert_called_once_with(
        interfaceType=InterfaceType.WRAPPER,
        clientAddress=addressing.client_address,
        serverAddress=addressing.server_address,
        forAuthentication=Authentication.LOW,
        password=None,
        useLogicalNameReferencing=addressing.use_logical_name,
    )

    # Verify that GXNet was created with correct parameters
    mock_gx_net_cls.assert_called_once_with(
        networkType=NetworkType.TCP,
        name=endpoint.ip,
        port=endpoint.port,
    )

    # Verify that the app layer is a GuruxCOSEMApp instance
    assert isinstance(app_layer, GuruxCOSEMApp)
    assert app_layer.client is mock_gx_client
    assert app_layer.media is mock_gx_media

    # Verify that session was closed
    mock_session.close.assert_called_once()


def test_gurux_app_factory_con_perfil_hdlc_crea_cliente_con_interface_hdlc() -> None:
    """
    Tests that the Gurux app factory creates a client with HDLC interface type
    when the endpoint profile is HDLC_TUNNELING.
    """

    device = _build_device()
    endpoint = _build_communication_endpoint(
        device_id=device.id,
        medium=Medium.SERIAL,
        profile=Profile.HDLC_TUNNELING,
        ip=None,
        port=None,
        serial_port="COM3",
        baud_rate=9600,
    )
    addressing = _build_device_addressing(
        device_id=device.id,
        client_address=16,
        server_address=17,
        use_logical_name=False,
    )

    factory = GuruxAppFactory()

    # Mock the database session and repositories
    mock_session = MagicMock()

    @contextmanager
    def mock_get_context_session():
        try:
            yield mock_session
        finally:
            pass

    mock_comm_endpoint_repo = MagicMock()
    mock_comm_endpoint_repo.get_primary_by_device_id.return_value = endpoint

    mock_device_addressing_repo = MagicMock()
    mock_device_addressing_repo.index_by_device_id.return_value = [addressing]

    with (
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.get_context_session",
            side_effect=mock_get_context_session,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.CommunicationEndpointRepository",
            return_value=mock_comm_endpoint_repo,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.DeviceAddressingRepository",
            return_value=mock_device_addressing_repo,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.GXDLMSClient"
        ) as mock_gx_client_cls,
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.GXNet"
        ) as mock_gx_net_cls,
    ):
        mock_gx_client = mock_gx_client_cls.return_value
        mock_gx_media = mock_gx_net_cls.return_value

        app_layer = factory.create_app_layer(device)

    # Verify that repositories were called correctly
    mock_comm_endpoint_repo.get_primary_by_device_id.assert_called_once_with(device.id)
    mock_device_addressing_repo.index_by_device_id.assert_called_once_with(device.id)

    # Verify that GXDLMSClient was created with HDLC interface type
    mock_gx_client_cls.assert_called_once_with(
        interfaceType=InterfaceType.HDLC,
        clientAddress=addressing.client_address,
        serverAddress=addressing.server_address,
        forAuthentication=Authentication.LOW,
        password=None,
        useLogicalNameReferencing=addressing.use_logical_name,
    )

    # Verify that GXNet was created (even for serial, as per implementation)
    mock_gx_net_cls.assert_called_once_with(
        networkType=NetworkType.TCP,
        name=endpoint.ip,
        port=endpoint.port,
    )

    # Verify that the app layer is a GuruxCOSEMApp instance
    assert isinstance(app_layer, GuruxCOSEMApp)
    assert app_layer.client is mock_gx_client
    assert app_layer.media is mock_gx_media

    # Verify that session was closed
    mock_session.close.assert_called_once()


def test_gurux_app_factory_usa_direcciones_correctas_del_addressing() -> None:
    """
    Tests that the Gurux app factory uses the correct client and server addresses
    from the device addressing configuration.
    """

    device = _build_device()
    endpoint = _build_communication_endpoint(
        device_id=device.id, ip="10.0.0.50", port=8080
    )
    addressing = _build_device_addressing(
        device_id=device.id,
        client_address=100,
        server_address=200,
        use_logical_name=True,
    )

    factory = GuruxAppFactory()

    # Mock the database session and repositories
    mock_session = MagicMock()

    @contextmanager
    def mock_get_context_session():
        try:
            yield mock_session
        finally:
            pass

    mock_comm_endpoint_repo = MagicMock()
    mock_comm_endpoint_repo.get_primary_by_device_id.return_value = endpoint

    mock_device_addressing_repo = MagicMock()
    mock_device_addressing_repo.index_by_device_id.return_value = [addressing]

    with (
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.get_context_session",
            side_effect=mock_get_context_session,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.CommunicationEndpointRepository",
            return_value=mock_comm_endpoint_repo,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.DeviceAddressingRepository",
            return_value=mock_device_addressing_repo,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.GXDLMSClient"
        ) as mock_gx_client_cls,
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.GXNet"
        ) as mock_gx_net_cls,
    ):
        app_layer = factory.create_app_layer(device)

    # Verify that GXDLMSClient was created with correct addresses
    mock_gx_client_cls.assert_called_once_with(
        interfaceType=InterfaceType.WRAPPER,
        clientAddress=100,
        serverAddress=200,
        forAuthentication=Authentication.LOW,
        password=None,
        useLogicalNameReferencing=True,
    )

    # Verify that GXNet was created with endpoint's IP and port
    mock_gx_net_cls.assert_called_once_with(
        networkType=NetworkType.TCP,
        name="10.0.0.50",
        port=8080,
    )

    # Verify that the app layer is a GuruxCOSEMApp instance
    assert isinstance(app_layer, GuruxCOSEMApp)


def test_gurux_app_factory_cierra_sesion_cuando_ocurre_excepcion() -> None:
    """
    Tests that the Gurux app factory closes the database session even when
    an exception occurs during app layer creation.
    """

    device = _build_device()

    factory = GuruxAppFactory()

    # Mock the database session and repositories
    mock_session = MagicMock()

    @contextmanager
    def mock_get_context_session():
        try:
            yield mock_session
        finally:
            pass

    mock_comm_endpoint_repo = MagicMock()
    # Simulate an exception when trying to get the endpoint
    mock_comm_endpoint_repo.get_primary_by_device_id.side_effect = Exception(
        "Database error"
    )

    with (
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.get_context_session",
            side_effect=mock_get_context_session,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.CommunicationEndpointRepository",
            return_value=mock_comm_endpoint_repo,
        ),
    ):
        try:
            factory.create_app_layer(device)
        except Exception:
            pass  # Expected exception

    # Verify that session was closed even after exception
    mock_session.close.assert_called_once()


def test_gurux_app_factory_retorna_gurux_cosem_app_configurado() -> None:
    """
    Tests that the Gurux app factory returns a properly configured GuruxCOSEMApp
    instance with the correct client and media dependencies.
    """

    device = _build_device()
    endpoint = _build_communication_endpoint(device_id=device.id)
    addressing = _build_device_addressing(device_id=device.id)

    factory = GuruxAppFactory()

    # Mock the database session and repositories
    mock_session = MagicMock()

    @contextmanager
    def mock_get_context_session():
        try:
            yield mock_session
        finally:
            pass

    mock_comm_endpoint_repo = MagicMock()
    mock_comm_endpoint_repo.get_primary_by_device_id.return_value = endpoint

    mock_device_addressing_repo = MagicMock()
    mock_device_addressing_repo.index_by_device_id.return_value = [addressing]

    with (
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.get_context_session",
            side_effect=mock_get_context_session,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.CommunicationEndpointRepository",
            return_value=mock_comm_endpoint_repo,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.DeviceAddressingRepository",
            return_value=mock_device_addressing_repo,
        ),
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.GXDLMSClient"
        ) as mock_gx_client_cls,
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.GXNet"
        ) as mock_gx_net_cls,
        patch(
            "dlms_meter_communication.services.reader_service.factories.app_layers.gurux_app_factory.GuruxCOSEMApp"
        ) as mock_gurux_app_cls,
    ):
        mock_gx_client = mock_gx_client_cls.return_value
        mock_gx_media = mock_gx_net_cls.return_value
        mock_gurux_app = mock_gurux_app_cls.return_value

        app_layer = factory.create_app_layer(device)

    # Verify that GuruxCOSEMApp was instantiated with correct dependencies
    mock_gurux_app_cls.assert_called_once_with(
        client=mock_gx_client,
        media=mock_gx_media,
        trace_level=TraceLevel.OFF,
        invocation_counter=0,
    )

    # Verify that the returned instance is the mocked app
    assert app_layer is mock_gurux_app

    # Verify that session was closed
    mock_session.close.assert_called_once()
