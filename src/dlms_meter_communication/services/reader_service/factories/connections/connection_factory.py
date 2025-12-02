"""
Abstract factory for creating connection instances.

This module defines the base factory interface for creating different types of
physical connections (Serial, TCP, etc.) used in DLMS communication.
"""

from abc import ABC, abstractmethod

from ...ports import IConnection
from dlms_meter_communication.schemas import CommunicationEndpoint


class ConnectionFactory(ABC):
    """
    Abstract base class for connection factories.

    This factory is responsible for creating connection instances that handle
    the physical layer of communication (Serial, TCP/IP, etc.).
    """

    @abstractmethod
    def create_connection(self, endpoint: CommunicationEndpoint) -> IConnection:
        """
        Create a connection instance for the given communication endpoint.

        Args:
            endpoint: Communication endpoint configuration

        Returns:
            IConnection: Connection instance

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError
