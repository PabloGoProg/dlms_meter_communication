"""
HDLC Profile Strategy for DLMS/COSEM Meter Communication

This module implements the HDLC (High-Level Data Link Control) communication profile
strategy for DLMS/COSEM smart meter communication. It provides support for:
- Serial communication (RS-232, RS-485)
- HDLC tunneling over TCP/UDP
- Proper HDLC framing and error detection

The HDLC profile strategy handles the complete communication flow:
1. Connection establishment and management
2. DLMS message framing with HDLC protocol
3. Reliable message transmission and reception
4. Connection cleanup and error handling

This strategy supports multiple transport mechanisms:
- Serial ports for direct meter connection
- TCP/UDP for HDLC tunneling over IP networks
- Integration with both Gurux and Socket providers
"""

from .base import MediaLinkStrategy
from dlms_meter_communication.services.dlms_client_service.utils.enums import (
    ConnectionProviderType,
    ConnectionMediaType,
)
from ....dlms_client_service.protocol.association.hdlc import HDLCFrame


class HDLCProfileStrategy(MediaLinkStrategy):
    """
    HDLC Profile Strategy for DLMS/COSEM meter communication.

    This strategy implements the HDLC protocol for DLMS/COSEM communication,
    supporting both serial connections and HDLC tunneling over IP networks.
    It provides proper HDLC framing, error detection, and flow control.
    """

    def __init__(
        self,
        ip_address: str = "127.0.0.1",
        port: int = 4059,  # Default DLMS HDLC port
        client_address: int = 0x01,  # HDLC client address
        server_address: int = 0x81,  # HDLC server address
        connection_provider_type: ConnectionProviderType = ConnectionProviderType.GURUX,
        connection_media_type: ConnectionMediaType = ConnectionMediaType.TCP,
    ) -> None:
        """
        Initialize HDLC Profile Strategy.

        Args:
            ip_address: IP address for connection (used for TCP/UDP tunneling)
            port: Port number for connection
            client_address: HDLC client address (usually 0x01)
            server_address: HDLC server address (usually 0x81)
            connection_provider_type: Provider implementation to use
            connection_media_type: Media type (TCP, UDP, SERIAL)
        """
        super().__init__(connection_provider_type, connection_media_type)

        self.ip_address = ip_address
        self.port = port
        self.client_address = client_address
        self.server_address = server_address

        # Initialize HDLC frame handler for client messages
        self.client_hdlc = HDLCFrame(
            address=client_address,
            control=0x10,  # Information frame
        )

        # Initialize HDLC frame handler for server messages
        self.server_hdlc = HDLCFrame(
            address=server_address,
            control=0x10,  # Information frame
        )

    def open(self) -> None:
        """
        Establish connection to the DLMS/COSEM meter using HDLC protocol.

        This method opens the connection to the target meter using the configured
        connection provider. For HDLC tunneling over IP, it establishes the underlying
        network connection. For serial connections, it opens the serial port.

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
            raise ConnectionError(f"Failed to open HDLC connection: {e}") from e

    def close(self) -> None:
        """
        Close the HDLC connection to the DLMS/COSEM meter.

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
            raise ConnectionError(f"Failed to close HDLC connection: {e}") from e

    def transact(self, payload: bytes, timeout: float = 10.0) -> bytes:
        """
        Send a DLMS message using HDLC protocol and receive the response.

        This method performs a complete request-response transaction with the DLMS/COSEM
        meter using HDLC framing. It handles message framing, transmission, and response
        reception with proper timeout management and error handling.

        Args:
            payload: The DLMS message data to send to the meter
                This should be raw DLMS data without any framing
            timeout: Timeout in seconds for the transaction
                Defaults to 10.0 seconds. This applies to both send and receive operations

        Returns:
            bytes: The response payload from the meter (without HDLC framing)
                This is the actual DLMS response data that can be processed
                by higher-level protocol implementations

        Raises:
            ConnectionError: If connection provider is not set
            ConnectionError: If connection is not established
            ConnectionError: If transaction fails at any stage
            TimeoutError: If operation exceeds the specified timeout
            ValueError: If payload is invalid or HDLC frame is malformed
        """
        try:
            if self._connection_provider is None:
                raise ConnectionError("Connection provider is not set")
            if not self._connection_provider.is_connected():
                raise ConnectionError("Connection not established")

            # Check if payload is already HDLC framed
            if self.client_hdlc.is_hdlc_frame(payload):
                # Already framed, send directly
                framed_payload = payload
            else:
                # Frame the DLMS payload with HDLC
                framed_payload = self.client_hdlc.create_frame(payload)

            # Send the HDLC frame
            self._connection_provider.send(framed_payload)

            # Receive response - for HDLC, we need to handle variable frame sizes
            # First, try to receive a reasonable amount of data
            response_data = self._connection_provider.receive(2048, timeout)

            # Parse the HDLC frame to extract DLMS payload
            try:
                dlms_payload, _, _ = self.server_hdlc.parse_frame(response_data)
                return dlms_payload
            except ValueError:
                # If parsing fails, the response might be larger or fragmented
                # Try to receive more data and parse again
                additional_data = self._connection_provider.receive(2048, timeout)
                response_data += additional_data
                dlms_payload, _, _ = self.server_hdlc.parse_frame(response_data)
                return dlms_payload

        except Exception as e:
            raise ConnectionError(f"Failed to transact HDLC data: {e}") from e

    def is_open(self) -> bool:
        """
        Check if the HDLC connection to the meter is currently open.

        Returns:
            bool: True if the connection is open and active, False otherwise
        """
        # Delegate to the connection provider to check actual connection state
        return (
            self._connection_provider.is_connected()
            if self._connection_provider
            else False
        )
