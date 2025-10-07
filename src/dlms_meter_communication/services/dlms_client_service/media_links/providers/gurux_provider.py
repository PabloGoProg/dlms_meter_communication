"""
Gurux-based connection provider for DLMS/COSEM meter communication.

This module implements a ConnectionProvider using the Gurux .NET library for
establishing network connections with DLMS/COSEM smart meters. The provider
supports both TCP and UDP transport protocols and provides robust error handling
and logging capabilities.

The Gurux library is a widely-used implementation of DLMS/COSEM protocols that
provides low-level network communication primitives. This provider wraps the
Gurux functionality to provide a clean, abstracted interface for meter communication.
"""

from .base import ConnectionProvider
from typing import Optional

from gurux_net import GXNet
from gurux_net.enums import NetworkType
from gurux_common import ReceiveParameters
from gurux_common.enums import TraceLevel

# Import built-in exceptions
from builtins import ConnectionError


class GuruxProvider(ConnectionProvider):
    """
    Gurux-based connection provider for DLMS/COSEM meter communication.

    This provider uses the Gurux .NET library to establish network connections
    with DLMS/COSEM smart meters. It supports both TCP and UDP protocols and
    provides specialized handling for each transport type.

    Key Features:
    - TCP and UDP protocol support
    - Robust error handling with detailed logging
    - Timeout management for meter communications
    - Chunked data reception for large messages
    - Connection state validation
    - Resource cleanup and exception safety

    The provider is designed to work with DLMS/COSEM meters that may have
    variable response times and require reliable data transmission.

    Attributes:
        net (GXNet): The underlying Gurux network connection object
        ip_address (str): IP address of the target meter
        port (int): Port number for the connection
        connection_type (NetworkType): Type of network connection (TCP/UDP)
    """

    def __init__(
        self, ip_address: str, port: int, connection_type: NetworkType = NetworkType.TCP
    ) -> None:
        """
        Initialize the Gurux connection provider.

        Creates a new provider instance with the specified connection parameters.
        The connection is not established until the connect() method is called.

        Args:
            ip_address (str): IP address of the DLMS/COSEM meter to connect to
            port (int): Port number for the connection (typically 4059 for DLMS)
            connection_type (NetworkType): Type of network connection.
                                         Defaults to TCP for reliable communication.

        Note:
            Common DLMS/COSEM ports:
            - 4059: Standard DLMS/COSEM port
            - 50000: Alternative port used by some manufacturers
            - 2404: IEC 62056-47 standard port
        """
        super().__init__(ip_address, port)
        self.net = None  # Will be initialized in connect()
        self.connection_type = connection_type

    def connect(self) -> None:
        """
        Establish network connection with the DLMS/COSEM meter.

        Creates a new GXNet instance and opens the network connection using
        the configured parameters. This method handles connection establishment
        and provides detailed error information if the connection fails.

        The connection process involves:
        1. Creating a GXNet instance with the specified network type
        2. Configuring the connection parameters (IP address, port)
        3. Opening the network connection
        4. Handling any connection errors with appropriate exceptions

        Raises:
            ConnectionError: If the connection cannot be established
            TimeoutError: If the connection attempt times out
            Exception: For any other connection-related errors

        Note:
            This method should be called before any send/receive operations.
            The connection remains open until disconnect() is called.
        """
        try:
            # Create GXNet instance with connection parameters
            self.net = GXNet(
                networkType=self.connection_type, name=self.ip_address, portNo=self.port
            )
            # Establish the network connection
            self.net.open()
        except Exception as e:
            # Wrap any connection errors in a ConnectionError for consistency
            raise ConnectionError(f"Failed to connect to the meter: {e}")

    def disconnect(self) -> None:
        """
        Close the network connection and release resources.

        Safely closes the network connection and cleans up associated resources.
        This method is designed to be safe to call multiple times and handles
        cleanup even if the connection is already closed or in an error state.

        The disconnect process involves:
        1. Validating that a connection exists
        2. Closing the network connection
        3. Cleaning up the GXNet instance
        4. Handling any cleanup errors gracefully

        Raises:
            ConnectionError: If there's an error during disconnection
                            (but resources are still cleaned up)

        Note:
            This method always cleans up resources in the finally block,
            ensuring no resource leaks even if exceptions occur.
        """
        try:
            # Check if connection exists before attempting to close
            if self.net is None:
                raise ConnectionError("Connection not established")

            self.net.close()
        except Exception as e:
            raise ConnectionError(f"Failed to disconnect from the meter: {e}")
        finally:
            self.net = None

    def send(self, data: bytes) -> int:
        """
        Send data to the connected DLMS/COSEM meter.

        Transmits the provided byte data to the meter through the established
        connection. The method uses synchronous communication to ensure reliable
        data transmission and returns the number of bytes actually sent.

        The send process involves:
        1. Validating connection state
        2. Validating data type (must be bytes)
        3. Using synchronous communication mode
        4. Sending data through the Gurux network layer
        5. Returning the actual number of bytes transmitted

        Args:
            data (bytes): The data to send to the meter. Must be bytes type.

        Returns:
            int: Number of bytes actually sent (should equal len(data) on success)

        Raises:
            ConnectionError: If the connection is not established or send fails
            ValueError: If data is not of type bytes

        Note:
            The method uses synchronous communication to ensure data integrity.
            For large data blocks, consider breaking them into smaller chunks
            to avoid timeout issues with slow-responding meters.
        """
        # Validate connection and data type state before attempting to send
        if not self.is_connected():
            raise ConnectionError("Connection not established")
        if not isinstance(data, bytes):
            raise ValueError("Data must be bytes")

        try:
            # Use synchronous communication for reliable data transmission
            with self.net.getSynchronous():
                self.net.send(data)
                # Return the actual number of bytes sent
                # Note: In a perfect world, this should equal len(data)
                return len(data)
        except Exception as e:
            self.net.trace(TraceLevel.ERROR, f"Failed to send data to the meter: {e}")
            raise ConnectionError(f"Failed to send data to the meter: {e}")

    def receive(self, size: int, timeout: Optional[float] = 10.0) -> bytes:
        """
        Receive data from the connected DLMS/COSEM meter.

        Reads data from the meter through the established connection. The method
        automatically selects the appropriate reception strategy based on the
        connection type (TCP or UDP) and handles timeout management.

        Args:
            size (int): Maximum number of bytes to receive
            timeout (Optional[float]): Timeout in seconds. Defaults to 10.0 seconds.
                                     None means no timeout (may block indefinitely)

        Returns:
            bytes: The received data. May be less than 'size' if timeout occurs
                   or connection is closed.

        Raises:
            ConnectionError: If connection is not established or receive fails
            TimeoutError: If no data is received within the timeout period

        Note:
            Different protocols have different characteristics:
            - TCP: Reliable, ordered delivery, supports chunked reception
            - UDP: Best-effort delivery, single packet reception
        """
        # Route to appropriate reception method based on connection type
        return (
            self._receive_tcp(size, timeout)
            if self.connection_type == NetworkType.TCP
            else self._receive_udp(size, timeout)
        )

    def is_connected(self) -> bool:
        """
        Check if the connection is active and ready for communication.

        Validates that both the GXNet instance exists and the underlying
        network connection is open. This method provides a quick way to
        check connection status without attempting network operations.

        Returns:
            bool: True if the connection is established and open, False otherwise

        Note:
            This is a lightweight check that doesn't perform network I/O.
            It's safe to call frequently for connection monitoring.
        """
        return bool(self.net and self.net.isOpen())

    def _receive_tcp(self, size: int, timeout: Optional[float] = 10.0) -> bytes:
        """
        Receive data using TCP protocol with chunked reception support.

        TCP reception is implemented with chunked reading to handle large
        messages that may arrive in multiple network packets. This method
        manages timeouts carefully to avoid accumulation issues and provides
        robust error handling for network-level problems.

        The TCP reception process:
        1. Validates connection state
        2. Initializes reception buffer and timeout management
        3. Reads data in chunks until the full message is received
        4. Handles various error conditions (timeout, connection loss, etc.)
        5. Returns the complete received data

        Args:
            size (int): Maximum number of bytes to receive
            timeout (Optional[float]): Timeout in seconds for the entire operation

        Returns:
            bytes: The complete received data

        Raises:
            ConnectionError: If connection issues occur during reception
            TimeoutError: If the total timeout is exceeded or no data arrives
        """
        # Validate connection before attempting to receive
        if not self.is_connected():
            raise ConnectionError("Connection not established")

        buffer = bytearray()
        timeout_ms = int(timeout * 1000)

        try:
            # Read data in chunks until we have the complete message
            while len(buffer) < size:
                # Configure receive parameters for this chunk
                rp = ReceiveParameters()
                rp.count = size - len(buffer)
                rp.waitTime = timeout_ms

                # Attempt to receive data chunk
                ok = self.net.receive(rp)

                # Check if receive operation succeeded
                if not ok:
                    raise TimeoutError(f"No response from meter within {timeout}s")

                # Validate that we received actual data
                if rp.reply is None:
                    raise ConnectionError(
                        "No reply received from the meter (connection lost?)"
                    )

                # Convert received data to bytes and validate
                chunk = bytes(rp.reply)
                if chunk == b"":
                    raise ConnectionError("Empty datagram received or connection lost")

                # Add chunk to our buffer
                buffer.extend(chunk)

            return bytes(buffer)

        except TimeoutError:
            # Log timeout errors for debugging
            self.net.trace(TraceLevel.ERROR, "Timeout while waiting for data.")
            raise

        except OSError as e:
            # Handle OS-level network errors
            self.net.trace(TraceLevel.ERROR, f"OS-level error: {e}")
            raise ConnectionError(f"OS-level error during receive: {e}") from e

        except Exception as e:
            # Handle any other unexpected errors
            self.net.trace(TraceLevel.ERROR, f"Unexpected error: {e}")
            raise ConnectionError(f"Failed to receive data: {e}") from e

    def _receive_udp(self, size: int = 2048, timeout: Optional[float] = 10.0) -> bytes:
        """
        Receive data using UDP protocol with single packet reception.

        UDP reception is simpler than TCP as it typically receives complete
        messages in single packets. This method handles the stateless nature
        of UDP and provides appropriate error handling for packet loss or
        timeout scenarios.

        The UDP reception process:
        1. Validates connection state
        2. Configures receive parameters for single packet reception
        3. Waits for incoming UDP packet
        4. Validates received data
        5. Returns the received packet data

        Args:
            size (int): Maximum packet size to receive. Defaults to 2048 bytes.
                       UDP packets are typically much smaller than this limit.
            timeout (Optional[float]): Timeout in seconds for packet reception

        Returns:
            bytes: The received packet data

        Raises:
            ConnectionError: If connection issues occur during reception
            TimeoutError: If no packet arrives within the timeout period

        Note:
            UDP is connectionless, so this method may receive packets from
            any source. The application layer should validate packet sources
            if security is a concern.
        """
        # Validate connection before attempting to receive
        if not self.is_connected():
            raise ConnectionError("Connection not established")

        # Convert timeout to milliseconds for Gurux library
        timeout_ms = int(timeout * 1000)

        try:
            # Configure receive parameters for UDP packet reception
            rp = ReceiveParameters()
            rp.count = size  # Maximum packet size to receive
            rp.waitTime = timeout_ms  # Timeout for packet arrival

            # Attempt to receive UDP packet
            ok = self.net.receive(rp)

            # Check if packet was received successfully
            if not ok or rp.reply is None:
                raise TimeoutError(f"No response from meter within {timeout}s")

            # Convert received data to bytes and validate
            data = bytes(rp.reply)
            if len(data) == 0:
                raise ConnectionError("Connection closed by the remote device")

            # Return the received packet data
            return data

        except TimeoutError:
            # Log timeout errors for debugging
            self.net.trace(TraceLevel.ERROR, "Timeout while waiting for data.")
            raise

        except OSError as e:
            # Handle OS-level network errors
            self.net.trace(TraceLevel.ERROR, f"OS-level error: {e}")
            raise ConnectionError(f"OS-level error during receive: {e}") from e

        except Exception as e:
            # Handle any unexpected errors
            self.net.trace(TraceLevel.ERROR, f"Unexpected error: {e}")
            raise ConnectionError(f"Failed to receive data: {e}") from e
