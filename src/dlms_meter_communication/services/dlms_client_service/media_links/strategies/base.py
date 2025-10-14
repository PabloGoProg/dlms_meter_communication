"""
Base interface for DLMS/COSEM media-link Strategies.

This module defines the abstract contract that transport strategies must
implement to provide network connectivity and message translation for
DLMS/COSEM APDUs. Concrete implementations (e.g., GuruX TCP Wrapper,
HDLC serial, etc.) should subclass `MediaLinkService` and implement all
abstract methods.
"""

from abc import ABC, abstractmethod
from typing import Optional
from ....dlms_client_service.utils.enums import (
    ConnectionProviderType,
    ConnectionMediaType,
)
from ..providers import ConnectionProvider, GuruxProvider, SocketProvider


class MediaLinkStrategy(ABC):
    """
    Abstract Strategy for DLMS/COSEM transport and framing.

    Implementations are responsible for:
    - Opening and closing the underlying media (TCP/UDP, serial, etc.).
    - Performing request/response transactions.
    - Applying the appropriate framing (e.g., Wrapper header, HDLC) to raw
      DLMS APDUs.
    """

    def __init__(
        self,
        connection_media_type: ConnectionMediaType = ConnectionMediaType.TCP,
        connection_provider_type: ConnectionProviderType = ConnectionProviderType.GURUX,
    ) -> None:
        self.connection_media_type = connection_media_type
        self.connection_provider_type = connection_provider_type
        self._connection_provider: Optional["ConnectionProvider"] = None

    def open(self) -> None:
        """
        Open the underlying media connection.

        Implementations must establish the transport link and prepare any
        necessary resources to send and receive bytes.
        """
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """
        Close the underlying media connection.

        Implementations must release resources and make the instance safe to
        dispose or re-open later.
        """
        raise NotImplementedError

    @abstractmethod
    def transact(self, payload: bytes, timeout: float = 10.0) -> bytes:
        """
        Send a DLMS APDU and return the response APDU.

        Implementations must frame the outgoing `payload` according to the
        transport profile, send it, wait for the response up to `timeout`
        seconds, deframe the incoming message, and return the inner DLMS APDU.

        Args:
          payload: Raw DLMS APDU to send.
          timeout: Maximum time in seconds to wait for the response.

        Returns:
          The raw DLMS APDU received in the response.
        """
        raise NotImplementedError

    @abstractmethod
    def is_open(self) -> bool:
        """
        Check if the underlying media connection is open.

        Returns:
          True if the connection is open, False otherwise.
        """
        raise NotImplementedError

    def _mount_connection_provider(self, ip_address: str, port: int) -> None:
        """
        Mount the connection provider based on the connection provider type.

        Args:
            ip_address: IP address for the connection
            port: Port number for the connection

        Returns:
            None

        Raises:
            ValueError: If the connection provider type is not supported
        """
        if self.connection_provider_type == ConnectionProviderType.GURUX:
            self._connection_provider = GuruxProvider(ip_address, port)
            self._connection_provider.connection_type = self.connection_media_type
        elif self.connection_provider_type == ConnectionProviderType.SOCKET:
            self._connection_provider = SocketProvider(ip_address, port)
            self._connection_provider.connection_type = self.connection_media_type
        else:
            raise ValueError(
                f"Unsupported connection provider type: {self.connection_provider_type}"
            )
