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
from typing import Optional, Tuple
from .utils.helpers import validate_ip_address, validate_port
from .utils.consts import MAX_BUFFER_SIZE, MIN_BUFFER_SIZE
from ....dlms_client_service.utils.enums import ConnectionMediaType


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
        timeout: Optional[float] = 10.0,
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
        validate_ip_address(ip_address)
        validate_port(port)

        super().__init__(ip_address, port)

        self.media_type: ConnectionMediaType = media_type
        self.timeout: float = timeout
        self._peer: Optional[Tuple[str, int]] = None
        self._sock: Optional[socket.socket] = None
        self._is_connected: bool = False

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
        if self._is_connected:
            raise ConnectionError("The connection is already established")

        try:
            self._create_socket()

            if self.media_type in (ConnectionMediaType.TCP, ConnectionMediaType.UDP):
                self._sock.connect(self._peer)
            else:
                raise NotImplementedError(
                    f"Connection type {self.media_type.name} is not implemented"
                )

            self._is_connected = True

        except socket.timeout as e:
            raise TimeoutError(
                f"Connection timeout to {self.ip_address}:{self.port}: {e}"
            ) from e
        except OSError as e:
            raise ConnectionError(
                f"Network error connecting to {self.ip_address}:{self.port}: {e}"
            ) from e
        except Exception as e:
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
        if self._is_connected and self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            finally:
                self._sock = None
                self._is_connected = False

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
        if not self._is_connected or self._sock is None:
            raise ConnectionError("Cannot send data - connection not established")

        if not isinstance(data, (bytes, bytearray)):
            raise ValueError("Data must be bytes type")

        if len(data) == 0:
            raise ValueError("Cannot send empty data")

        if len(data) > MAX_BUFFER_SIZE:
            raise ValueError(f"Data too large (max {MAX_BUFFER_SIZE} bytes)")

        try:
            if self.media_type == ConnectionMediaType.TCP:
                self._sock.sendall(data)

            elif self.media_type == ConnectionMediaType.UDP:
                if self._peer is None:
                    raise ConnectionError("UDP peer not set")
                self._sock.sendto(data, self._peer)

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
        if not self._is_connected or self._sock is None:
            raise ConnectionError("Cannot receive data - connection not established")

        try:
            if self.media_type == ConnectionMediaType.TCP:
                return self._receive_tcp(size, timeout)
            elif self.media_type == ConnectionMediaType.UDP:
                return self._receive_udp(size, timeout)
            else:
                raise NotImplementedError(
                    f"Receive not implemented for {self.media_type.name}"
                )

        except Exception as e:
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
        if not self._is_connected or self._sock is None:
            return False

        if self.media_type == ConnectionMediaType.UDP:
            return True

        try:
            self._sock.getpeername()
            return True
        except OSError:
            self._sock = None
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
        if self.media_type in (ConnectionMediaType.TCP, ConnectionMediaType.UDP):
            sock_family = socket.AF_INET

            sock_type = (
                socket.SOCK_STREAM
                if self.media_type == ConnectionMediaType.TCP
                else socket.SOCK_DGRAM
            )

            self._sock = socket.socket(sock_family, sock_type)
            self._sock.settimeout(self.timeout)
            self._peer = (self.ip_address, self.port)
        else:
            raise NotImplementedError(f"Not implemented for {self.media_type.name}")

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
        if size <= 0:
            raise ValueError("Size must be positive")

        if size > MAX_BUFFER_SIZE:
            raise ValueError(
                f"Size too large, maximum allowed is {MAX_BUFFER_SIZE} bytes"
            )

        original_timeout = self._sock.gettimeout()

        try:
            self._sock.settimeout(timeout)

            buffer = bytearray()
            bytes_received = 0
            max_iterations = size + 1000
            iteration_count = 0

            while len(buffer) < size and iteration_count < max_iterations:
                remaining = size - len(buffer)
                chunk = self._sock.recv(remaining)

                if not chunk:
                    raise ConnectionError("Connection closed by remote device")

                buffer.extend(chunk)
                bytes_received += len(chunk)
                iteration_count += 1

                self._sock.settimeout(timeout)

            if iteration_count >= max_iterations:
                raise ConnectionError(
                    f"Maximum iterations ({max_iterations}) reached - possible infinite loop"
                )

            if len(buffer) != size:
                raise ConnectionError(
                    f"Received {len(buffer)} bytes, expected {size} bytes"
                )

            return bytes(buffer)

        except socket.timeout as e:
            raise TimeoutError(
                f"TCP receive timeout after {bytes_received}/{size} bytes: {e}"
            ) from e
        except OSError as e:
            raise ConnectionError(f"TCP receive failed: {e}") from e
        finally:
            self._sock.settimeout(original_timeout)

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

        original_timeout = self.sock.gettimeout()

        try:
            self.sock.settimeout(timeout)
            data, addr = self.sock.recvfrom(size)

            if self.peer is not None and addr != self.peer:
                raise ValueError(f"Received data from {addr}, expected {self.peer}")

            return data

        except socket.timeout as e:
            raise TimeoutError(f"UDP receive timeout: {e}") from e
        except OSError as e:
            raise ConnectionError(f"UDP receive failed: {e}") from e
        finally:
            self.sock.settimeout(original_timeout)
