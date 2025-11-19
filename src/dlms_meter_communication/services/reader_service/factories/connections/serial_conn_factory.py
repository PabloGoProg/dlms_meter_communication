from __future__ import annotations

from .connection_factory import ConnectionFactory
from ...adapterss.connections.serial_connection import SerialConnection
from dlms_meter_communication.schemas import CommunicationEndpoint


class SerialConnectionFactory(ConnectionFactory):
    def create_connection(self, endpoint: CommunicationEndpoint) -> SerialConnection:
        return SerialConnection(
            baudrate=endpoint.baud_rate,
        )
