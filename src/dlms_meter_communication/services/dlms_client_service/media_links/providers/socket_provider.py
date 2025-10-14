"""
Socket-based connection provider for DLMS/COSEM meter communication.

This module provides a robust implementation of network communication for DLMS/COSEM
smart meters using native Python socket operations. It supports both TCP and UDP
protocols with comprehensive error handling, timeout management, and security features.

The SocketProvider class is designed to handle the low-level network communication
required for DLMS meter interactions, providing a reliable foundation for higher-level
protocol implementations.

Key Features:
- TCP and UDP protocol support with proper socket management
- Comprehensive input validation and security checks
- Robust error handling with detailed exception information
- Timeout management for all network operations
- Resource cleanup and connection state management
- Protection against common network attacks (DoS, buffer overflow)
- Thread-safe operations where applicable

Security Considerations:
- Input validation prevents buffer overflow attacks
- Size limits prevent memory exhaustion attacks
- Timeout limits prevent resource exhaustion
- Proper exception handling prevents information leakage
- Connection state validation prevents use-after-free scenarios
"""

from .base import ConnectionProvider
import socket
import logging
from typing import Optional, Tuple
import ipaddress

from ....dlms_client_service.utils.enums import ConnectionMediaType

# Configure logging for this module
logger = logging.getLogger(__name__)

# Security and performance constants
MAX_BUFFER_SIZE = 1024 * 1024  # 1MB maximum buffer size to prevent DoS attacks
MAX_TIMEOUT = 300.0  # 5 minutes maximum timeout to prevent resource exhaustion
MIN_TIMEOUT = 0.1  # 100ms minimum timeout for responsiveness
DEFAULT_TIMEOUT = 10.0  # 10 seconds default timeout
DEFAULT_BUFFER_SIZE = 1024  # 1KB default buffer size for TCP operations


class SocketProvider(ConnectionProvider):
    """
    Native socket-based connection provider for DLMS/COSEM meter communication.

    This provider implements network communication using Python's built-in socket
    library, providing direct control over TCP and UDP connections. It is designed
    to be lightweight, secure, and reliable for industrial meter communication.

    The provider handles all aspects of network communication including:
    - Connection establishment and teardown
    - Data transmission with error recovery
    - Data reception with timeout handling
    - Connection state monitoring
    - Resource cleanup and exception safety

    Security Features:
    - Input validation for all parameters
    - Buffer size limits to prevent DoS attacks
    - Timeout limits to prevent resource exhaustion
    - Connection state validation
    - Proper exception handling without information leakage

    Thread Safety:
    - Individual instances are not thread-safe
    - Multiple instances can be used concurrently
    - Socket operations are atomic at the OS level

    Attributes:
        sock (socket.socket): The underlying socket object (None when disconnected)
        _peer (Tuple[str, int]): The remote endpoint (ip_address, port)
        connection_type (ConnectionInterfaceType): The protocol type (TCP/UDP)
        timeout (float): Default timeout for operations in seconds
        _is_connected (bool): Internal connection state flag
    """

    def __init__(
        self,
        ip_address: str,
        port: int,
        media_type: ConnectionMediaType = ConnectionMediaType.TCP,
        timeout: Optional[float] = DEFAULT_TIMEOUT,
    ) -> None:
        """
        Initialize the socket provider with connection parameters.

        This constructor validates all input parameters and sets up the provider
        for network communication. It does not establish the actual connection
        (that happens in the connect() method).

        Args:
            ip_address (str): IP address of the target meter (IPv4 or IPv6)
            port (int): Port number for the connection (1-65535)
            connection_interface_type (ConnectionInterfaceType): Protocol type (TCP/UDP)
            timeout (Optional[float]): Default timeout in seconds (0.1-300.0)

        Raises:
            ValueError: If any parameter is invalid
            TypeError: If parameter types are incorrect

        Example:
            >>> provider = SocketProvider("192.168.1.100", 4059, ConnectionInterfaceType.TCP)
            >>> provider.connect()
        """
        # Validate and store IP address
        self._validate_ip_address(ip_address)

        # Validate and store port number
        self._validate_port(port)

        # Validate and store timeout
        self._validate_timeout(timeout)

        # Call parent constructor with validated parameters
        super().__init__(ip_address, port)

        # Initialize connection state variables
        self.sock: Optional[socket.socket] = (
            None  # Socket object (None when disconnected)
        )
        self._peer: Optional[Tuple[str, int]] = None  # Remote endpoint tuple
        self.media_type = media_type  # Protocol type
        self.timeout = timeout or DEFAULT_TIMEOUT  # Operation timeout
        self._is_connected = False  # Internal connection state flag

        logger.debug(
            f"SocketProvider initialized: {ip_address}:{port} ({media_type.name})"
        )

    def connect(self) -> None:
        """
        Establish a network connection with the DLMS/COSEM meter.

        This method creates and configures the appropriate socket type based on
        the connection interface type, then establishes the connection to the
        remote meter. It includes comprehensive error handling and resource
        cleanup in case of failure.

        The connection process involves:
        1. Validating current connection state
        2. Creating and configuring the socket
        3. Establishing the network connection
        4. Updating internal state variables

        Raises:
            ConnectionError: If already connected or connection fails
            TimeoutError: If connection exceeds timeout limit
            OSError: If underlying socket operations fail
            ValueError: If connection parameters are invalid

        Example:
            >>> provider = SocketProvider("192.168.1.100", 4059)
            >>> provider.connect()  # Establishes TCP connection
        """
        # Check if already connected to prevent multiple connections
        if self._is_connected and self.sock is not None:
            raise ConnectionError("Socket already connected - disconnect first")

        try:
            # Create and configure the socket based on connection type
            self._create_socket()

            # Establish connection for connection-oriented protocols
            if self.media_type in (
                ConnectionMediaType.TCP,
                ConnectionMediaType.UDP,
            ):
                # For TCP, this establishes the connection
                # For UDP, this just sets the remote endpoint
                self.sock.connect(self._peer)
                logger.info(
                    f"Connected to {self.ip_address}:{self.port} via {self.media_type.name}"
                )
            else:
                raise NotImplementedError(
                    f"Connection type {self.media_type.name} is not implemented"
                )

            # Update connection state
            self._is_connected = True

        except socket.timeout as e:
            # Handle timeout during connection
            self._cleanup_connection()
            raise TimeoutError(
                f"Connection timeout to {self.ip_address}:{self.port}: {e}"
            ) from e
        except OSError as e:
            # Handle network-level errors
            self._cleanup_connection()
            raise ConnectionError(
                f"Network error connecting to {self.ip_address}:{self.port}: {e}"
            ) from e
        except Exception as e:
            # Handle any other unexpected errors
            self._cleanup_connection()
            raise ConnectionError(f"Unexpected error connecting to meter: {e}") from e

    def disconnect(self) -> None:
        """
        Gracefully close the network connection and clean up resources.

        This method safely closes the socket connection and resets all internal
        state variables. It includes error handling to ensure cleanup happens
        even if the socket close operation fails.

        The disconnection process:
        1. Closes the socket connection
        2. Resets internal state variables
        3. Logs the disconnection event

        Raises:
            ConnectionError: If disconnection fails unexpectedly

        Example:
            >>> provider.disconnect()  # Closes connection and cleans up
        """
        if self.sock is not None:
            try:
                # Attempt to close the socket gracefully
                self.sock.close()
                logger.info(f"Disconnected from {self.ip_address}:{self.port}")
            except OSError as e:
                # Log the error but don't raise - cleanup should continue
                logger.warning(f"Error during socket close: {e}")
                raise ConnectionError(f"Failed to disconnect from meter: {e}") from e
            finally:
                # Always reset state variables, even if close() failed
                self._cleanup_connection()

    def send(self, data: bytes) -> int:
        """
        Send data to the connected meter over the network.

        This method transmits the provided data to the remote meter using the
        appropriate protocol (TCP or UDP). It includes comprehensive validation
        and error handling to ensure reliable data transmission.

        For TCP connections, this uses sendall() to ensure all data is transmitted.
        For UDP connections, this sends the data as a single datagram.

        Args:
            data (bytes): The data to send to the meter

        Returns:
            int: The number of bytes actually sent (should equal len(data))

        Raises:
            ConnectionError: If not connected or transmission fails
            ValueError: If data is not bytes or is empty
            TimeoutError: If transmission exceeds timeout
        """
        # Validate connection state
        if not self._is_connected or self.sock is None:
            raise ConnectionError("Cannot send data - connection not established")

        # Validate input data
        if not isinstance(data, bytes):
            raise ValueError("Data must be bytes type")

        if len(data) == 0:
            raise ValueError("Cannot send empty data")

        if len(data) > MAX_BUFFER_SIZE:
            raise ValueError(f"Data too large (max {MAX_BUFFER_SIZE} bytes)")

        try:
            # Send data using appropriate method for connection type
            if self.media_type == ConnectionMediaType.TCP:
                # TCP: Use sendall to ensure all data is transmitted
                self.sock.sendall(data)
                logger.debug(f"Sent {len(data)} bytes via TCP")

            elif self.media_type == ConnectionMediaType.UDP:
                # UDP: Send as single datagram
                if self._peer is None:
                    raise ConnectionError("UDP peer not set")
                self.sock.sendto(data, self._peer)
                logger.debug(f"Sent {len(data)} bytes via UDP")

            else:
                raise NotImplementedError(
                    f"Send not implemented for {self.media_type.name}"
                )

            return len(data)

        except socket.timeout as e:
            raise TimeoutError(f"Timeout while sending {len(data)} bytes: {e}") from e
        except OSError as e:
            raise ConnectionError(f"Failed to send data to meter: {e}") from e

    def receive(self, size: int, timeout: Optional[float] = None) -> bytes:
        """
        Receive data from the connected meter over the network.

        This method receives the specified amount of data from the remote meter
        using the appropriate protocol. For TCP, it ensures all requested data
        is received. For UDP, it receives a single datagram.

        The method includes comprehensive timeout handling and validation to
        ensure reliable data reception.

        Args:
            size (int): Number of bytes to receive (1 to MAX_BUFFER_SIZE)
            timeout (Optional[float]): Timeout in seconds (overrides default)

        Returns:
            bytes: The received data (exactly 'size' bytes for TCP)

        Raises:
            ConnectionError: If not connected or reception fails
            ValueError: If size is invalid
            TimeoutError: If reception exceeds timeout
        """
        # Validate connection state
        if not self._is_connected or self.sock is None:
            raise ConnectionError("Cannot receive data - connection not established")

        # Validate and normalize parameters
        size = self._validate_receive_size(size)
        timeout = self._validate_timeout(timeout) or self.timeout

        try:
            # Receive data using appropriate method for connection type
            if self.media_type == ConnectionMediaType.TCP:
                return self._receive_tcp(size, timeout)
            elif self.media_type == ConnectionMediaType.UDP:
                return self._receive_udp(size, timeout)
            else:
                raise NotImplementedError(
                    f"Receive not implemented for {self.media_type.name}"
                )

        except Exception as e:
            # Re-raise with additional context
            raise ConnectionError(f"Failed to receive data from meter: {e}") from e

    def is_connected(self) -> bool:
        """
        Check if the provider is currently connected to the meter.

        This method performs a comprehensive check of the connection state,
        including both internal state variables and actual socket status.
        For TCP connections, it also verifies the socket is still valid.

        Returns:
            bool: True if connected and socket is valid, False otherwise

        Example:
            >>> if provider.is_connected():
            ...     data = provider.receive(1024)
        """
        # Check internal state first (fastest check)
        if not self._is_connected or self.sock is None:
            return False

        # For UDP, internal state is sufficient
        if self.media_type == ConnectionMediaType.UDP:
            return True

        # For TCP, verify socket is still valid
        try:
            # This will raise OSError if socket is closed/invalid
            self.sock.getpeername()
            return True
        except OSError:
            # Socket is no longer valid, update internal state
            self._is_connected = False
            return False

    def _create_socket(self) -> None:
        """
        Create and configure the socket based on connection type.

        This private method creates the appropriate socket type (TCP or UDP)
        and configures it with the necessary parameters including timeout
        settings and address family.

        Raises:
            OSError: If socket creation fails
            NotImplementedError: If connection type is not supported
        """
        # Determine socket family and type based on connection interface
        if self.connection_type in (
            ConnectionMediaType.TCP,
            ConnectionMediaType.UDP,
        ):
            # Use IPv4 for now (could be extended to support IPv6)
            sock_family = socket.AF_INET

            # Choose socket type based on protocol
            if self.media_type == ConnectionMediaType.TCP:
                sock_type = socket.SOCK_STREAM  # Reliable, connection-oriented
            else:  # UDP
                sock_type = socket.SOCK_DGRAM  # Unreliable, connectionless

            # Create the socket
            self.sock = socket.socket(sock_family, sock_type)

            # Configure socket timeout
            self.sock.settimeout(self.timeout)

            # Set up remote endpoint
            self._peer = (self.ip_address, self.port)

            logger.debug(
                f"Created {self.connection_type.name} socket for {self.ip_address}:{self.port}"
            )

        else:
            raise NotImplementedError(
                f"Socket creation not implemented for {self.connection_type.name}"
            )

    def _receive_tcp(self, size: int, timeout: float) -> bytes:
        """
        Safely receive data from TCP socket with comprehensive error handling.

        This method implements reliable TCP data reception by reading data in
        chunks until the complete message is received. It includes protection
        against infinite loops, buffer overflow attacks, and timeout handling.

        TCP is a stream protocol, so data may arrive in multiple chunks. This
        method ensures all requested data is received before returning.

        Args:
            size (int): Number of bytes to receive
            timeout (float): Timeout in seconds for the entire operation

        Returns:
            bytes: Exactly 'size' bytes of data

        Raises:
            ConnectionError: If connection is lost or data is incomplete
            TimeoutError: If operation exceeds timeout
            ValueError: If size is invalid
        """
        # Validate size parameter
        if size <= 0:
            raise ValueError("Size must be positive")

        if size > MAX_BUFFER_SIZE:
            raise ValueError(
                f"Size too large, maximum allowed is {MAX_BUFFER_SIZE} bytes"
            )

        # Store original timeout to restore later
        original_timeout = self.sock.gettimeout()

        try:
            # Set timeout for this specific operation
            self.sock.settimeout(timeout)

            # Initialize reception variables
            buffer = bytearray()  # Mutable buffer for efficient appending
            bytes_received = 0
            max_iterations = size + 1000  # Safety limit to prevent infinite loops
            iteration_count = 0

            # Receive data in chunks until complete
            while len(buffer) < size and iteration_count < max_iterations:
                # Calculate remaining bytes to receive
                remaining = size - len(buffer)

                # Attempt to receive chunk
                chunk = self.sock.recv(remaining)

                # Check if connection was closed
                if not chunk:
                    raise ConnectionError("Connection closed by remote device")

                # Add chunk to buffer
                buffer.extend(chunk)
                bytes_received += len(chunk)
                iteration_count += 1

                # Reset timeout for subsequent recv calls
                self.sock.settimeout(timeout)

            # Check for infinite loop condition
            if iteration_count >= max_iterations:
                raise ConnectionError(
                    f"Maximum iterations ({max_iterations}) reached - possible infinite loop"
                )

            # Verify we received exactly the requested amount
            if len(buffer) != size:
                raise ConnectionError(
                    f"Received {len(buffer)} bytes, expected {size} bytes"
                )

            logger.debug(
                f"Received {size} bytes via TCP in {iteration_count} iterations"
            )
            return bytes(buffer)

        except socket.timeout as e:
            raise TimeoutError(
                f"TCP receive timeout after {bytes_received}/{size} bytes: {e}"
            ) from e
        except OSError as e:
            raise ConnectionError(f"TCP receive failed: {e}") from e
        finally:
            # Always restore original timeout
            self.sock.settimeout(original_timeout)

    def _receive_udp(self, size: int, timeout: float) -> bytes:
        """
        Receive a UDP datagram from the connected meter.

        UDP is a datagram protocol, so this method receives a single complete
        message. The size parameter is used as the maximum buffer size, but
        the actual received data may be smaller.

        Args:
            size (int): Maximum number of bytes to receive
            timeout (float): Timeout in seconds for the operation

        Returns:
            bytes: The received datagram data

        Raises:
            ConnectionError: If reception fails
            TimeoutError: If operation exceeds timeout
        """
        # Validate size parameter
        if size <= 0:
            raise ValueError("Size must be positive")

        if size > MAX_BUFFER_SIZE:
            raise ValueError(
                f"Size too large, maximum allowed is {MAX_BUFFER_SIZE} bytes"
            )

        # Store original timeout to restore later
        original_timeout = self.sock.gettimeout()

        try:
            # Set timeout for this operation
            self.sock.settimeout(timeout)

            # Receive UDP datagram
            data, addr = self.sock.recvfrom(size)

            # Verify we received data from the expected peer
            if self._peer is not None and addr != self._peer:
                logger.warning(f"Received data from {addr}, expected {self._peer}")

            logger.debug(f"Received {len(data)} bytes via UDP from {addr}")
            return data

        except socket.timeout as e:
            raise TimeoutError(f"UDP receive timeout: {e}") from e
        except OSError as e:
            raise ConnectionError(f"UDP receive failed: {e}") from e
        finally:
            # Always restore original timeout
            self.sock.settimeout(original_timeout)

    def _cleanup_connection(self) -> None:
        """
        Clean up connection resources and reset internal state.

        This method safely resets all connection-related variables and closes
        the socket if it exists. It's called during disconnection and error
        recovery to ensure proper resource cleanup.
        """
        # Close socket if it exists
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                # Ignore errors during cleanup
                pass
            finally:
                self.sock = None

        # Reset state variables
        self._peer = None
        self._is_connected = False

        logger.debug("Connection resources cleaned up")

    def _validate_ip_address(self, ip_address: str) -> None:
        """
        Validate that the provided IP address is valid.

        Args:
            ip_address (str): IP address to validate

        Raises:
            ValueError: If IP address is invalid
            TypeError: If IP address is not a string
        """
        if not isinstance(ip_address, str):
            raise TypeError("IP address must be a string")

        if not ip_address.strip():
            raise ValueError("IP address cannot be empty")

        try:
            # Use ipaddress module for robust validation
            ipaddress.ip_address(ip_address)
        except ValueError as e:
            raise ValueError(f"Invalid IP address '{ip_address}': {e}") from e

    def _validate_port(self, port: int) -> None:
        """
        Validate that the provided port number is valid.

        Args:
            port (int): Port number to validate

        Raises:
            ValueError: If port is out of valid range
            TypeError: If port is not an integer
        """
        if not isinstance(port, int):
            raise TypeError("Port must be an integer")

        if not (1 <= port <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got {port}")

    def _validate_timeout(self, timeout: Optional[float]) -> Optional[float]:
        """
        Validate that the provided timeout is within acceptable limits.

        Args:
            timeout (Optional[float]): Timeout to validate

        Returns:
            Optional[float]: Validated timeout value

        Raises:
            ValueError: If timeout is out of valid range
            TypeError: If timeout is not a number
        """
        if timeout is None:
            return None

        if not isinstance(timeout, (int, float)):
            raise TypeError("Timeout must be a number")

        if not (MIN_TIMEOUT <= timeout <= MAX_TIMEOUT):
            raise ValueError(
                f"Timeout must be between {MIN_TIMEOUT} and {MAX_TIMEOUT} seconds, got {timeout}"
            )

        return float(timeout)

    def _validate_receive_size(self, size: int) -> int:
        """
        Validate and normalize the receive size parameter.

        Args:
            size (int): Size to validate

        Returns:
            int: Validated size value

        Raises:
            ValueError: If size is invalid
            TypeError: If size is not an integer
        """
        if not isinstance(size, int):
            raise TypeError("Size must be an integer")

        if size <= 0:
            raise ValueError("Size must be positive")

        if size > MAX_BUFFER_SIZE:
            raise ValueError(
                f"Size too large, maximum allowed is {MAX_BUFFER_SIZE} bytes"
            )

        return size
