"""
Base interface for DLMS/COSEM connection providers.

This module defines the abstract contract that connection providers must implement
to establish and manage low-level network connections for DLMS/COSEM meter communication.
Connection providers handle the actual transport layer (TCP, UDP, serial, etc.) and
are used by MediaLinkStrategy implementations to perform the physical communication
with smart meters.

The architecture follows a layered approach:
- ConnectionProvider: Handles low-level network connections
- MediaLinkStrategy: Handles DLMS/COSEM framing and protocol logic
- DLMS Client: Handles application-level DLMS operations

This separation allows for flexible combinations of transport mechanisms and
protocol implementations.
"""

from abc import ABC, abstractmethod
from typing import Optional


class ConnectionProvider(ABC):
    """
    Abstract base class for DLMS/COSEM connection providers.

    Connection providers are responsible for managing the low-level network
    connections used to communicate with DLMS/COSEM smart meters. They handle
    the actual transport mechanism (TCP sockets, UDP, serial ports, etc.) and
    provide a unified interface for sending and receiving raw byte data.

    Implementations should handle connection establishment, data transmission,
    reception with timeout capabilities, and connection state management.
    The provider is responsible for ensuring reliable data transfer and
    proper resource cleanup.

    This interface is designed to work in conjunction with MediaLinkStrategy
    implementations, which handle the higher-level DLMS/COSEM protocol framing
    and message processing.

    Attributes:
        ip_address (str): IP address of the target meter
        port (int): Port number for the connection
    """

    def __init__(self, ip_address: str, port: int) -> None:
        """
        Initialize the connection provider.

        Args:
            ip_address (str): IP address of the target meter
            port (int): Port number for the connection
        """
        self.ip_address = ip_address
        self.port = port

    @abstractmethod
    def connect(self) -> None:
        """
        Establishes the network connection with the DLMS/COSEM meter.

        This method must establish the physical or logical connection with the remote
        device. Implementations must handle the configuration of connection parameters
        specific to the transport type (port, IP address, serial port parameters, etc.).

        Raises:
            ConnectionError: If the connection cannot be established
            TimeoutError: If the connection exceeds the time limit
        """
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        """
        Closes the network connection and releases associated resources.

        This method must close the connection safely, releasing all network resources
        and associated buffers. It must be safe to call this method multiple times
        without causing errors.

        Implementations must ensure that any pending buffers are cleared and that
        the connection is terminated in an orderly manner.
        """
        raise NotImplementedError

    @abstractmethod
    def send(self, data: bytes) -> int:
        """
        Sends data through the connection.

        Sends the provided data through the established connection. The method returns
        the number of bytes that were effectively sent, which is important for
        validating transmission integrity.

        Args:
            data: The data to send as bytes

        Returns:
            int: Number of bytes effectively sent

        Raises:
            ConnectionError: If the connection is not established or is lost
            TimeoutError: If sending exceeds the time limit
            ValueError: If the provided data is not valid
        """
        raise NotImplementedError

    @abstractmethod
    def receive(self, size: int, timeout: Optional[float] = 10.0) -> bytes:
        """
        Receives data from the connection.

        Reads data from the connection until the specified size is completed or
        until the timeout is exhausted. This method is fundamental for communication
        with DLMS/COSEM meters that may have variable response times.

        Args:
            size: Maximum number of bytes to receive
            timeout: Time limit in seconds for reception. If None,
                    there is no time limit (may block indefinitely)

        Returns:
            bytes: The received data. May be less than 'size' if the
                   timeout is exhausted or the connection is closed

        Raises:
            ConnectionError: If the connection is not established or is lost
            TimeoutError: If reception exceeds the time limit
        """
        raise NotImplementedError

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Checks if the connection is active and ready for communication.

        This method allows checking the connection state without attempting to
        perform network operations. It is useful for pre-validation before
        sending data or for connection state monitoring.

        Returns:
            bool: True if the connection is established and ready to use,
                  False otherwise
        """
        raise NotImplementedError
