"""TCP connection utility used by the reader service.

This module provides a small, focused wrapper around Python's socket API to
open, use and close a TCP connection with sensible defaults (timeouts, TCP
options) and consistent error translation.
"""

import socket
import errno
from typing import Optional

from ...ports import IConnection


class TCPConnection(IConnection):
    """Simple TCP client connection.

    - Resolves DNS and tries all returned addresses until one succeeds.
    - Applies IO and connect timeouts, TCP_NODELAY and SO_KEEPALIVE (optional).
    - Maps socket errors to TimeoutError/ConnectionError for clearer handling.

    Attributes:
        _host (str): The host to connect to.
        _port (int): The port to connect to.
        _connection_timeout (float): The timeout for the connection attempt.
        _io_timeout (float): The timeout for the Input and Output operations.
        _tcp_nodelay (bool): Whether to enable TCP_NODELAY.
        _tcp_keepalive (bool): Whether to enable SO_KEEPALIVE.
        _sock (Optional[socket.socket]): The socket object.
    """

    def __init__(
        self,
        host: str,
        port: int,
        connection_timeout: float = 10.0,
        io_timeout: float = 10.0,
        tcp_nodelay: bool = True,
        tcp_keepalive: bool = True,
    ) -> None:
        super().__init__()

        self._host = host
        self._port = port
        self._connection_timeout = connection_timeout
        self._io_timeout = io_timeout
        self._tcp_nodelay = tcp_nodelay
        self._tcp_keepalive = tcp_keepalive

        self._sock: Optional[socket.socket] = None

    def open(self) -> None:
        """Open the TCP connection if not already connected.

        Tries all resolved addresses for the provided host/port until one
        successfully connects. Sets timeouts and optional TCP options.
        """
        if self._sock is not None:
            return

        last_error: Optional[Exception] = None
        peer_infos = socket.getaddrinfo(
            self._host,
            self._port,
            type=socket.SOCK_STREAM,
        )

        for family, socktype, proto, _, sockaddr in peer_infos:
            s = socket.socket(family, socktype, proto)

            try:
                s.settimeout(self._connection_timeout)

                if self._tcp_nodelay:
                    # Disable Nagle to minimize latency on small writes
                    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

                if self._tcp_keepalive:
                    # Ask OS to send keepalives to detect dead peers
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

                s.connect(sockaddr)
                s.settimeout(self._io_timeout)

                self._sock = s
                return
            except (socket.timeout,):
                last_error = TimeoutError(f"TCP connect timeout to {sockaddr}")
            except OSError as e:
                last_error = ConnectionError(f"TCP connection error to {sockaddr}: {e}")
            finally:
                if self._sock is None:
                    # Close unsuccessful attempt to avoid leaking file descriptors
                    try:
                        s.close()
                    except Exception:
                        pass

        if last_error is not None:
            raise last_error

        raise ConnectionError(f"Failed to connect to {self._host}:{self._port}")

    def close(self) -> None:
        """Close the connection if open and release resources."""
        if self._sock is None:
            return

        try:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            self._sock.close()
        finally:
            self._sock = None

    def send(self, data: bytes) -> None:
        """Send all bytes on the open TCP socket.

        Raises ConnectionError if not connected, TimeoutError on IO timeout.
        """
        if not self.is_connected():
            raise ConnectionError("Socket is not connected")

        try:
            # Send all assured that all bytes are sent before returning or raising an error
            self._sock.sendall(data)
        except socket.timeout as e:
            raise TimeoutError(f"TCP send timeout: {e}") from e
        except OSError as e:
            raise ConnectionError(f"TCP send error: {e}") from e

    def receive(self, size: int, timeout: Optional[float] = 10) -> bytes:
        """Receive up to "size" bytes.

        If a per-call timeout is provided, it temporarily overrides the socket
        timeout and is restored afterwards. Returns bytes read or raises on
        timeout/connection errors.
        """
        if size <= 0:
            raise ValueError("Size must be positive and non-zero")
        if not self.is_connected():
            raise ConnectionError("Socket is not connected")

        sock = self._sock
        prev = sock.gettimeout()

        try:
            if timeout is not None:
                # Temporarily override IO timeout for this receive
                sock.settimeout(timeout)

            chunk = sock.recv(size)
            if chunk == b"":
                raise ConnectionError("Connection closed by remote device")

            return chunk
        except socket.timeout as e:
            raise TimeoutError(f"TCP receive timeout: {e}") from e
        except OSError as e:
            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                raise TimeoutError(f"TCP receive timeout: {e}") from e
            raise ConnectionError(f"TCP receive error: {e}") from e
        finally:
            # Restore previous timeout even if an exception occurred
            try:
                sock.settimeout(prev)
            except Exception:
                pass

    def set_timeout(self, timeout: float) -> None:
        """Set default IO timeout for the socket and future operations."""
        if timeout <= 0:
            raise ValueError("Timeout must be positive and non-zero")

        self._io_timeout = timeout

        if self._sock is not None:
            self._sock.settimeout(timeout)

    def is_connected(self) -> bool:
        """Return True if the socket is currently open."""
        return self._sock is not None
