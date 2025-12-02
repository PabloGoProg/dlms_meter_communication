from abc import ABC, abstractmethod
from typing import Optional


class IConnection(ABC):
    """
    Transport-agnostic byte-stream connection interface.

    Implementations encapsulate the mechanics of opening, closing, sending, and
    receiving raw bytes over a specific medium (e.g., TCP socket, serial port,
    cellular modem). This interface is intentionally DLMS/COSEM-agnostic: it
    does not perform framing, checksums, or protocol parsing.

    Thread-safety:
        Unless explicitly documented by an implementation, instances should be
        treated as NOT thread-safe. Coordinate concurrent access at a higher
        layer (e.g., per-session locking).
    """

    @abstractmethod
    def open(self) -> None:
        """
        Establish the underlying connection.

        Expected behavior:
            - Attempt to create and configure the transport (connect/bind/open).
            - Should be idempotent: calling `open()` on an already-open
              connection must not fail, and should keep the connection open.
            - Configure low-level timeouts according to the current default
              (see `set_timeout`).

        Raises:
            ConnectionError: If the connection cannot be established.
            OSError/IOError: For underlying system-level failures.
        """
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """
        Close the underlying connection and release resources.

        Expected behavior:
            - Gracefully flush and shutdown the transport if applicable.
            - Must be idempotent: calling `close()` multiple times is safe.

        Raises:
            OSError/IOError: For underlying system-level failures during close.
        """
        raise NotImplementedError

    @abstractmethod
    def send(self, data: bytes) -> None:
        """
        Send the entire `data` buffer over the connection.

        Expected behavior:
            - Transmit all bytes before returning (no partial-send on success).
            - Should block up to the configured write timeout.
            - Must raise on timeout or short write conditions.

        Args:
            data: The exact byte sequence to transmit.

        Raises:
            TimeoutError: If the operation exceeds the configured timeout.
            ConnectionError: If the connection is not open or becomes unusable.
            OSError/IOError: For underlying system-level failures.
        """
        raise NotImplementedError

    @abstractmethod
    def receive(self, size: int, timeout: Optional[float] = 10.0) -> bytes:
        """
        Receive up to `size` bytes from the connection.

        Expected behavior:
            - Block until at least one byte is available, the operation times
              out, or the connection is closed.
            - Return a `bytes` object of length 1..`size`.
            - Return b'' ONLY to indicate clean EOF/peer-closed conditions.
            - If `timeout` is provided, it overrides the default read timeout
              set via `set_timeout` for this call only.

        Args:
            size: Maximum number of bytes to read (must be > 0).
            timeout: Optional per-call read timeout (seconds). If None, use the
                     currently configured default timeout.

        Returns:
            bytes: The received data (possibly fewer than `size` bytes). b''
                   signals EOF/closed connection.

        Raises:
            TimeoutError: If no data is received before the timeout elapses.
            ConnectionError: If the connection is not open or becomes unusable.
            OSError/IOError: For underlying system-level failures.
            ValueError: If `size` <= 0.
        """
        raise NotImplementedError

    @abstractmethod
    def set_timeout(self, timeout: float) -> None:
        """
        Set the default I/O timeout (seconds) for subsequent operations.

        Notes:
            - Applies to future `send`/`receive` calls that do not specify an
              explicit `timeout` parameter.
            - Implementations may choose to apply the same value to both read
              and write operations, or maintain separate internal settings as
              appropriate.

        Args:
            timeout: Default timeout in seconds (must be > 0).

        Raises:
            ValueError: If `timeout` is not positive.
        """
        raise NotImplementedError

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Report whether the underlying transport is currently open and usable.

        Semantics:
            - Returns True if the connection is open and believed to be viable.
            - This is a best-effort check and NOT a guarantee that subsequent
              I/O will succeed (the peer may close immediately after).

        Returns:
            bool: True if open/usable, False otherwise.
        """
        raise NotImplementedError
