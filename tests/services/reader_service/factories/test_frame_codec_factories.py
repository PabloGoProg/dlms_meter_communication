"""
Tests for the frame codec factories in the reader service.

Tests that the factories create the expected implementations and configure the expected parameters.
"""

import uuid
from unittest.mock import patch

from dlms_meter_communication.models.enums import Medium, Profile
from dlms_meter_communication.schemas import CommunicationEndpoint
from dlms_meter_communication.services.reader_service.adapterss.codecs.hdlc_frame_codec import (
    HDLCFrameCodec,
)
from dlms_meter_communication.services.reader_service.adapterss.codecs.wrapper_codec import (
    WrapperCodec,
)
from dlms_meter_communication.services.reader_service.factories.frame_codecs.hdlc_framer_factory import (
    HDLCFramerFactory,
)
from dlms_meter_communication.services.reader_service.factories.frame_codecs.wrapper_framer_factory import (
    WrapperFramerFactory,
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
        "ip": "192.0.2.100",
        "port": 4060,
        "serial_port": "ttyS0",
        "baud_rate": 115200,
        "is_primary": True,
    }
    data.update(overrides)
    return CommunicationEndpoint(**data)


def test_wrapper_framer_factory_invoca_wrapper_codec_con_parametros_constantes() -> (
    None
):
    """
    Tests that the wrapper framer factory invokes the wrapper codec with constant parameters.
    """

    endpoint = _build_endpoint()
    factory = WrapperFramerFactory()

    with patch(
        "dlms_meter_communication.services.reader_service.factories.frame_codecs.wrapper_framer_factory.WrapperCodec"
    ) as mock_wrapper_codec:
        mock_instance = mock_wrapper_codec.return_value
        codec = factory.create_frame_codec(endpoint)

    mock_wrapper_codec.assert_called_once_with(source_wport=16, destination_wport=1)
    assert codec is mock_instance


def test_wrapper_framer_factory_retorna_wrapper_codec_configurado() -> None:
    """
    Tests that the wrapper framer factory returns a configured wrapper codec.
    """

    endpoint = _build_endpoint(profile=Profile.WRAPPER)
    factory = WrapperFramerFactory()

    codec = factory.create_frame_codec(endpoint)

    assert isinstance(codec, WrapperCodec)
    assert codec._src_wport == 16
    assert codec._dst_wport == 1


def test_hdlc_framer_factory_crea_instancia_hdlc_frame_codec() -> None:
    """
    Tests that the HDLC framer factory creates an HDLC frame codec.
    """

    endpoint = _build_endpoint(medium=Medium.SERIAL, profile=Profile.HDLC_TUNNELING)
    factory = HDLCFramerFactory()

    codec = factory.create_frame_codec(endpoint)

    assert isinstance(codec, HDLCFrameCodec)
    assert codec.address == 0x81
    assert codec.control == 0x10
