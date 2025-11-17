from __future__ import annotations

from .connection_factory import ConnectionFactory
from ...adapterss.connections.tcp_connection import TCPConnection
from dlms_meter_communication.schemas import CommunicationEndpoint


class TCPConnectionFactory(ConnectionFactory):
    def create_connection(self, endpoint: CommunicationEndpoint) -> TCPConnection:
        return TCPConnection(host=endpoint.ip, port=endpoint.port)
