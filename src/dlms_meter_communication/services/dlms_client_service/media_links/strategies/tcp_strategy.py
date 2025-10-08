"""
TCP Strategy for DLMS/COSEM Meter Communication

This module implements the TCP-based media link strategy for DLMS/COSEM smart meter
communication. It provides a high-level interface for establishing TCP connections,
sending and receiving DLMS messages with proper wrapper headers, and managing
connection state.

The TCP strategy handles the complete communication flow:
1. Connection establishment and management
2. DLMS message wrapping with proper headers
3. Reliable message transmission and reception
4. Connection cleanup and error handling

This strategy is designed to work with any connection provider that implements
the ConnectionProvider interface, allowing for flexible network implementations
while maintaining a consistent DLMS communication protocol.
"""

from .base import MediaLinkStrategy
from ..providers.base import ConnectionProvider
from ....dlms_client_service.protocol.association.wrapper import Wrapper


class TCPStrategy(MediaLinkStrategy):
    """
    TCP-based media link strategy for DLMS/COSEM meter communication.

    This class implements the TCP communication strategy for DLMS/COSEM smart meters.
    It manages the complete communication lifecycle including connection establishment,
    message wrapping/unwrapping, and reliable data transmission over TCP networks.

    The strategy automatically handles DLMS wrapper headers, ensuring that all
    messages are properly formatted according to the DLMS/COSEM standard for
    TCP/UDP communication. It provides a clean interface for higher-level DLMS
    protocol implementations.

    Key Features:
    - Automatic DLMS message wrapping with proper headers
    - Connection state management and validation
    - Reliable message transmission with timeout handling
    - Support for any TCP-based connection provider
    - Comprehensive error handling and reporting

    Attributes:
        ip_address (str): IP address of the target meter
        port (int): TCP port number for the connection
        client_address (str): Client-side port identifier for DLMS addressing
        server_address (str): Server-side port identifier for DLMS addressing
        connection_provider (ConnectionProvider): Low-level connection handler
        message_wrapper (Wrapper): DLMS message wrapper for header management

    Usage Pattern:
        1. Create strategy with connection parameters
        2. Call open() to establish connection
        3. Use transact() to send/receive DLMS messages
        4. Call close() to clean up connection

    """

    def __init__(
        self,
        ip_address: str,
        port: int,
        client_address: str,
        server_address: str,
        connection_provider: ConnectionProvider,
    ) -> None:
        """
        Initialize the TCP strategy with connection parameters and provider.

        This constructor sets up the TCP strategy with the necessary parameters
        for DLMS/COSEM communication. It creates a message wrapper with the
        specified client and server addresses for proper DLMS header generation.

        Args:
            ip_address (str): IP address of the target DLMS/COSEM meter
                This should be a valid IPv4 or IPv6 address (e.g., "192.168.1.100")

            port (int): TCP port number for the connection
                Standard DLMS/COSEM port is 4059, but can be customized

            client_address (str): Client-side port identifier for DLMS addressing
                Common values: "1" (Client Management), "16" (Public Client)
                This identifies who is sending the message

            server_address (str): Server-side port identifier for DLMS addressing
                Common values: "1" (Management Logical Device), "127" (All-station)
                This identifies who should receive the message

            connection_provider (ConnectionProvider): Low-level connection handler
                This provider handles the actual TCP socket operations
                Must implement the ConnectionProvider interface

        Raises:
            TypeError: If any parameter has an invalid type
            ValueError: If any parameter has an invalid value
        """
        super().__init__()

        # Store network connection parameters
        self.ip_address = ip_address
        self.port = port

        # Store DLMS addressing parameters
        self.client_address = client_address
        self.server_address = server_address

        # Store the connection provider for low-level network operations
        self.connection_provider = connection_provider

        # Create DLMS message wrapper with client/server addressing
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
            if self.connection_provider is None:
                raise ConnectionError("Connection provider is not set")
            if self.connection_provider.is_connected():
                raise ConnectionError("Connection already established")

            self.connection_provider.connect()

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
            if self.connection_provider is None:
                raise ConnectionError("Connection provider is not set")
            if not self.connection_provider.is_connected():
                raise ConnectionError("Connection not established")

            self.connection_provider.disconnect()

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
            if self.connection_provider is None:
                raise ConnectionError("Connection provider is not set")
            if not self.connection_provider.is_connected():
                raise ConnectionError("Connection not established")

            # Check if payload is already wrapped, if not wrap it with DLMS header
            if not self.message_wrapper.is_wrapped(payload):
                payload = self.message_wrapper.wrap_dlms_message(payload)

            self.connection_provider.send(payload)
            wrapper_header = self.connection_provider.receive(8, timeout)

            # Extract payload length from the 4th field of the header
            # Receive the actual response payload based on the length from header
            payload_length = wrapper_header[3]
            payload = self.connection_provider.receive(payload_length, timeout)

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
        return self.connection_provider.is_connected()
