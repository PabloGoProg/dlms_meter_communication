"""
Factory for creating serial connection instances.

This module provides a concrete implementation of the ConnectionFactory
for creating serial port connections used in meter communication.
"""

from __future__ import annotations

from .connection_factory import ConnectionFactory
from ...adapterss.connections.serial_connection import SerialConnection
from dlms_meter_communication.schemas import CommunicationEndpoint


class SerialConnectionFactory(ConnectionFactory):
    """
    Factory for creating serial connection instances.

    This factory creates serial port connections configured with the appropriate
    baud rate and other serial communication parameters from the endpoint.
    """

    def create_connection(self, endpoint: CommunicationEndpoint) -> SerialConnection:
        """
        Create a serial connection instance.

        Args:
            endpoint: Communication endpoint configuration containing serial parameters
                     such as baud rate

        Returns:
            SerialConnection: Configured serial connection instance
        """
        return SerialConnection(
            baudrate=endpoint.baud_rate,
        )
