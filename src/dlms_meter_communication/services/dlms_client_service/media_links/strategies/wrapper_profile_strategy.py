"""
Wrapper Profile Strategy for DLMS/COSEM Meter Communication

This module implements the IP-Oriented communication profile link strategy for DLMS/COSEM smart meter
communication. It provides a high-level interface for establishing TCP or UDP connections,
sending and receiving DLMS messages with proper wrapper headers, and managing
connection state.

The IP-Oriented communication profile strategy handles the complete communication flow:
1. Connection establishment and management
2. DLMS message wrapping with proper headers
3. Reliable message transmission and reception
4. Connection cleanup and error handling

This strategy is designed to work with any connection provider that implements
the ConnectionProvider interface, allowing for flexible network implementations
while maintaining a consistent DLMS communication protocol.
"""

from .base import MediaLinkStrategy
from dlms_meter_communication.services.dlms_client_service.utils.enums import (
    ConnectionProviderType,
    ConnectionMediaType,
)
from ....dlms_client_service.protocol.association.wrapper import Wrapper


class WrapperProfileStrategy(MediaLinkStrategy):
    def __init__(
        self,
        ip_address: str,
        port: int,
        client_address: str,
        server_address: str,
        connection_provider_type: ConnectionProviderType = ConnectionProviderType.GURUX,
        connection_media_type: ConnectionMediaType = ConnectionMediaType.TCP,
    ) -> None:
        super().__init__(connection_provider_type, connection_media_type)

        self.ip_address = ip_address
        self.port = port
        self.client_address = client_address
        self.server_address = server_address

        self.message_wrapper = Wrapper(
            source_wport=client_address,
            destination_wport=server_address,
        )

    def open(self) -> None:
        """
        Establish a TCP connection to the DLMS/COSEM meter.

        This method opens the connection to the target meter using the configured
        connection provider. It performs validation checks to ensure the connection
        can be established safely and handles any errors that occur during the process.

        Raises:
            ConnectionError: If connection provider is not set
            ConnectionError: If connection is already established
            ConnectionError: If connection establishment fails
            TimeoutError: If connection timeout occurs
            OSError: If network-level errors occur
        """
        try:
            self._mount_connection_provider(self.ip_address, self.port)
            if self._connection_provider.is_connected():
                raise ConnectionError("Connection already established")

            self._connection_provider.connect()

        except Exception as e:
            raise ConnectionError(f"Failed to open connection: {e}") from e

    def close(self) -> None:
        """
        Close the TCP connection to the DLMS/COSEM meter.

        This method gracefully closes the connection to the target meter using the
        configured connection provider. It performs validation checks to ensure
        the connection can be closed safely and handles any errors that occur.

        Raises:
            ConnectionError: If connection provider is not set
            ConnectionError: If no connection is established
            ConnectionError: If connection closure fails
            OSError: If network-level errors occur during closure
        """
        try:
            if self._connection_provider is None:
                raise ConnectionError("Connection provider is not set")
            if not self._connection_provider.is_connected():
                raise ConnectionError("Connection not established")

            self._connection_provider.disconnect()

        except Exception as e:
            raise ConnectionError(f"Failed to close connection: {e}") from e

    def transact(self, payload: bytes, timeout: float = 10.0) -> bytes:
        """
        Send a DLMS message and receive the response from the meter.

        This method performs a complete request-response transaction with the DLMS/COSEM
        meter. It handles message wrapping, transmission, and response reception with
        proper timeout management and error handling.

        Args:
            payload (bytes): The DLMS message data to send to the meter
                This can be raw DLMS data or already wrapped data

            timeout (float, optional): Timeout in seconds for the transaction.
                Defaults to 10.0 seconds. This applies to both send and receive operations.

        Returns:
            bytes: The response payload from the meter (without wrapper header)
                This is the actual DLMS response data that can be processed
                by higher-level protocol implementations.

        Raises:
            ConnectionError: If connection provider is not set
            ConnectionError: If connection is not established
            ConnectionError: If transaction fails at any stage
            TimeoutError: If operation exceeds the specified timeout
            ValueError: If payload is invalid or empty
        """
        try:
            if self._connection_provider is None:
                raise ConnectionError("Connection provider is not set")
            if not self._connection_provider.is_connected():
                raise ConnectionError("Connection not established")

            # Check if payload is already wrapped, if not wrap it with DLMS header
            if not self.message_wrapper.is_wrapped(payload):
                payload = self.message_wrapper.wrap_dlms_message(payload)

            self._connection_provider.send(payload)
            wrapper_header = self._connection_provider.receive(8, timeout)

            # Extract payload length from the 4th field of the header
            # Receive the actual response payload based on the length from header
            payload_length = wrapper_header[3]
            payload = self._connection_provider.receive(payload_length, timeout)

            return payload

        except Exception as e:
            raise ConnectionError(f"Failed to transact data: {e}") from e

    def is_open(self) -> bool:
        """
        Check if the TCP connection to the meter is currently open.

        Returns:
            bool: True if the connection is open and active, False otherwise
        """
        # Delegate to the connection provider to check actual connection state
        return (
            self._connection_provider.is_connected()
            if self._connection_provider
            else False
        )
