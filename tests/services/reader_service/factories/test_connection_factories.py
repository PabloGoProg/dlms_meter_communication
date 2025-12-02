"""
Tests for the connection factories in the reader service.

Tests that the factories create the expected implementations and propagate the relevant information from the `CommunicationEndpoint`.
"""

import uuid
from unittest.mock import patch

from dlms_meter_communication.models.enums import Medium, Profile
from dlms_meter_communication.schemas import CommunicationEndpoint
from dlms_meter_communication.services.reader_service.adapterss.connections.serial_connection import (
    SerialConnection,
)
from dlms_meter_communication.services.reader_service.adapterss.connections.tcp_connection import (
    TCPConnection,
)
from dlms_meter_communication.services.reader_service.factories.connections.serial_conn_factory import (
    SerialConnectionFactory,
)
from dlms_meter_communication.services.reader_service.factories.connections.tcp_conn_factory import (
    TCPConnectionFactory,
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
        "ip": "192.0.2.10",
        "port": 4059,
        "serial_port": "COM1",
        "baud_rate": 9600,
        "is_primary": True,
    }
    data.update(overrides)
    return CommunicationEndpoint(**data)


def test_tcp_connection_factory_usa_endpoint_para_configurar_tcp_connection() -> None:
    """
    Tests that the TCP connection factory uses the endpoint to configure the TCP connection.
    """

    endpoint = _build_endpoint()
    factory = TCPConnectionFactory()

    with patch(
        "dlms_meter_communication.services.reader_service.factories.connections.tcp_conn_factory.TCPConnection"
    ) as mock_tcp_connection:
        mock_instance = mock_tcp_connection.return_value
        connection = factory.create_connection(endpoint)

    mock_tcp_connection.assert_called_once_with(host=endpoint.ip, port=endpoint.port)
    assert connection is mock_instance


def test_tcp_connection_factory_retorna_instancia_tcp_connection_configurada() -> None:
    """
    Tests that the TCP connection factory returns a configured TCP connection.
    """

    endpoint = _build_endpoint(ip="198.51.100.20", port=8000)
    factory = TCPConnectionFactory()

    connection = factory.create_connection(endpoint)

    assert isinstance(connection, TCPConnection)
    assert connection._host == endpoint.ip
    assert connection._port == endpoint.port
    assert not connection.is_connected()


def test_serial_connection_factory_crea_instancia_serial_connection() -> None:
    """
    Tests that the serial connection factory creates a serial connection.
    """

    endpoint = _build_endpoint(
        medium=Medium.SERIAL,
        profile=Profile.HDLC_TUNNELING,
        ip=None,
        port=None,
        serial_port="ttyUSB0",
        baud_rate=19200,
    )
    factory = SerialConnectionFactory()

    connection = factory.create_connection(endpoint)

    assert isinstance(connection, SerialConnection)
    assert connection.baudrate == endpoint.baud_rate
    assert connection.max_tx_pdu == 1024
    assert connection.max_rx_pdu == 1024
    assert connection.timeout == 10.0
