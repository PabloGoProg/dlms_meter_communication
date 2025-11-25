"""
Tests for the link layer factories in the reader service.

Tests that each factory uses the correct collaborator factories (frame codecs and connections) according to the medium of the endpoint and that injects the expected dependencies into the implementation of the link layer.
"""

import uuid
from unittest.mock import patch

from dlms_meter_communication.models.enums import Medium, Profile
from dlms_meter_communication.schemas import CommunicationEndpoint
from dlms_meter_communication.services.reader_service.adapterss.link_layers.hdlc_link_layer import (
    HDLCLinkLayer,
)
from dlms_meter_communication.services.reader_service.adapterss.link_layers.tcp_wrapper_link_layer import (
    TCPWrapperLinkLayer,
)
from dlms_meter_communication.services.reader_service.factories.link_layers.hdlc_link_layer_factory import (
    HDLCLinkLayerFactory,
)
from dlms_meter_communication.services.reader_service.factories.link_layers.wrapper_link_layer_factory import (
    TCPWrapperLinkLayerFactory,
)


def _build_endpoint(**overrides) -> CommunicationEndpoint:
    """
    Builds a `CommunicationEndpoint` for testing with default values that
    can be overridden according to the use case.
    """

    data = {
        "id": uuid.uuid4(),
        "device_id": uuid.uuid4(),
        "medium": Medium.TCP,
        "profile": Profile.WRAPPER,
        "ip": "192.0.2.50",
        "port": 4061,
        "serial_port": "ttyUSB1",
        "baud_rate": 57600,
        "is_primary": True,
    }
    data.update(overrides)
    return CommunicationEndpoint(**data)


def test_tcp_wrapper_link_layer_factory_con_endpoint_serial_usa_serial_connection() -> (
    None
):
    """
    Tests that the TCP wrapper link layer factory uses the serial connection factory when the endpoint is serial.
    """

    endpoint = _build_endpoint(medium=Medium.SERIAL)
    factory = TCPWrapperLinkLayerFactory()

    with (
        patch(
            "dlms_meter_communication.services.reader_service.factories.link_layers.wrapper_link_layer_factory.WrapperFramerFactory"
        ) as mock_codec_factory_cls,
        patch(
            "dlms_meter_communication.services.reader_service.factories.link_layers.wrapper_link_layer_factory.SerialConnectionFactory"
        ) as mock_serial_factory_cls,
        patch(
            "dlms_meter_communication.services.reader_service.factories.link_layers.wrapper_link_layer_factory.TCPConnectionFactory"
        ) as mock_tcp_factory_cls,
    ):
        mock_codec_factory = mock_codec_factory_cls.return_value
        mock_serial_factory = mock_serial_factory_cls.return_value

        codec_instance = object()
        connection_instance = object()
        mock_codec_factory.create_frame_codec.return_value = codec_instance
        mock_serial_factory.create_connection.return_value = connection_instance

        link_layer = factory.create_link_layer(endpoint)

    mock_codec_factory_cls.assert_called_once_with()
    mock_serial_factory_cls.assert_called_once_with()
    mock_tcp_factory_cls.assert_not_called()

    mock_codec_factory.create_frame_codec.assert_called_once_with(endpoint)
    mock_serial_factory.create_connection.assert_called_once_with(endpoint)

    assert isinstance(link_layer, TCPWrapperLinkLayer)
    assert link_layer._codec is codec_instance  # noqa: SLF001
    assert link_layer._connection is connection_instance  # noqa: SLF001


def test_tcp_wrapper_link_layer_factory_con_endpoint_tcp_usa_tcp_connection() -> None:
    endpoint = _build_endpoint(medium=Medium.TCP)
    factory = TCPWrapperLinkLayerFactory()

    with (
        patch(
            "dlms_meter_communication.services.reader_service.factories.link_layers.wrapper_link_layer_factory.WrapperFramerFactory"
        ) as mock_codec_factory_cls,
        patch(
            "dlms_meter_communication.services.reader_service.factories.link_layers.wrapper_link_layer_factory.SerialConnectionFactory"
        ) as mock_serial_factory_cls,
        patch(
            "dlms_meter_communication.services.reader_service.factories.link_layers.wrapper_link_layer_factory.TCPConnectionFactory"
        ) as mock_tcp_factory_cls,
    ):
        mock_codec_factory = mock_codec_factory_cls.return_value
        mock_tcp_factory = mock_tcp_factory_cls.return_value

        codec_instance = object()
        connection_instance = object()
        mock_codec_factory.create_frame_codec.return_value = codec_instance
        mock_tcp_factory.create_connection.return_value = connection_instance

        link_layer = factory.create_link_layer(endpoint)

    mock_codec_factory_cls.assert_called_once_with()
    mock_serial_factory_cls.assert_not_called()
    mock_tcp_factory_cls.assert_called_once_with()

    mock_codec_factory.create_frame_codec.assert_called_once_with(endpoint)
    mock_tcp_factory.create_connection.assert_called_once_with(endpoint)

    assert isinstance(link_layer, TCPWrapperLinkLayer)
    assert link_layer._codec is codec_instance  # noqa: SLF001
    assert link_layer._connection is connection_instance  # noqa: SLF001


# def test_hdlc_link_layer_factory_con_endpoint_serial_usa_serial_connection() -> None:
#     endpoint = _build_endpoint(medium=Medium.SERIAL, profile=Profile.HDLC_TUNNELING)
#     factory = HDLCLinkLayerFactory()

#     with (
#         patch(
#             "dlms_meter_communication.services.reader_service.factories.link_layers.hdlc_link_layer_factory.HDLCFramerFactory"
#         ) as mock_codec_factory_cls,
#         patch(
#             "dlms_meter_communication.services.reader_service.factories.link_layers.hdlc_link_layer_factory.SerialConnectionFactory"
#         ) as mock_serial_factory_cls,
#         patch(
#             "dlms_meter_communication.services.reader_service.factories.link_layers.hdlc_link_layer_factory.TCPConnectionFactory"
#         ) as mock_tcp_factory_cls,
#     ):
#         mock_codec_factory = mock_codec_factory_cls.return_value
#         mock_serial_factory = mock_serial_factory_cls.return_value

#         codec_instance = object()
#         connection_instance = object()
#         mock_codec_factory.create_frame_codec.return_value = codec_instance
#         mock_serial_factory.create_connection.return_value = connection_instance

#         link_layer = factory.create_link_layer(endpoint)

#     mock_codec_factory_cls.assert_called_once_with()
#     mock_serial_factory_cls.assert_called_once_with()
#     mock_tcp_factory_cls.assert_not_called()

#     mock_codec_factory.create_frame_codec.assert_called_once_with(endpoint)
#     mock_serial_factory.create_connection.assert_called_once_with(endpoint)

#     assert isinstance(link_layer, HDLCLinkLayer)
#     assert link_layer._codec is codec_instance  # noqa: SLF001
#     assert link_layer._connection is connection_instance  # noqa: SLF001


# def test_hdlc_link_layer_factory_con_endpoint_tcp_usa_tcp_connection() -> None:
#     endpoint = _build_endpoint(medium=Medium.TCP, profile=Profile.HDLC_TUNNELING)
#     factory = HDLCLinkLayerFactory()

#     with (
#         patch(
#             "dlms_meter_communication.services.reader_service.factories.link_layers.hdlc_link_layer_factory.HDLCFramerFactory"
#         ) as mock_codec_factory_cls,
#         patch(
#             "dlms_meter_communication.services.reader_service.factories.link_layers.hdlc_link_layer_factory.SerialConnectionFactory"
#         ) as mock_serial_factory_cls,
#         patch(
#             "dlms_meter_communication.services.reader_service.factories.link_layers.hdlc_link_layer_factory.TCPConnectionFactory"
#         ) as mock_tcp_factory_cls,
#     ):
#         mock_codec_factory = mock_codec_factory_cls.return_value
#         mock_tcp_factory = mock_tcp_factory_cls.return_value

#         codec_instance = object()
#         connection_instance = object()
#         mock_codec_factory.create_frame_codec.return_value = codec_instance
#         mock_tcp_factory.create_connection.return_value = connection_instance

#         link_layer = factory.create_link_layer(endpoint)

#     mock_codec_factory_cls.assert_called_once_with()
#     mock_serial_factory_cls.assert_not_called()
#     mock_tcp_factory_cls.assert_called_once_with()

#     mock_codec_factory.create_frame_codec.assert_called_once_with(endpoint)
#     mock_tcp_factory.create_connection.assert_called_once_with(endpoint)

#     assert isinstance(link_layer, HDLCLinkLayer)
#     assert link_layer._codec is codec_instance  # noqa: SLF001
#     assert link_layer._connection is connection_instance  # noqa: SLF001
