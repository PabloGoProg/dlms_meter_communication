"""
Factory for creating TCP connection instances.

This module provides a concrete implementation of the ConnectionFactory
for creating TCP/IP network connections used in meter communication.
"""

from __future__ import annotations

from .connection_factory import ConnectionFactory
from ...adapterss.connections.tcp_connection import TCPConnection
from dlms_meter_communication.schemas import CommunicationEndpoint


class TCPConnectionFactory(ConnectionFactory):
    """
    Factory for creating TCP connection instances.

    This factory creates TCP/IP network connections configured with the appropriate
    host and port from the endpoint configuration.
    """

    def create_connection(self, endpoint: CommunicationEndpoint) -> TCPConnection:
        """
        Create a TCP connection instance.

        Args:
            endpoint: Communication endpoint configuration containing IP address
                     and port number

        Returns:
            TCPConnection: Configured TCP connection instance
        """
        return TCPConnection(host=endpoint.ip, port=endpoint.port)
