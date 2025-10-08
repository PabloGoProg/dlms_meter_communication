"""
Base interface for DLMS/COSEM media-link Strategies.

This module defines the abstract contract that transport strategies must
implement to provide network connectivity and message translation for
DLMS/COSEM APDUs. Concrete implementations (e.g., GuruX TCP Wrapper,
HDLC serial, etc.) should subclass `MediaLinkService` and implement all
abstract methods.
"""

from abc import ABC, abstractmethod


class MediaLinkStrategy(ABC):
    """
    Abstract Strategy for DLMS/COSEM transport and framing.

    Implementations are responsible for:
    - Opening and closing the underlying media (TCP/UDP, serial, etc.).
    - Performing request/response transactions.
    - Applying the appropriate framing (e.g., Wrapper header, HDLC) to raw
      DLMS APDUs.
    """

    @abstractmethod
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
