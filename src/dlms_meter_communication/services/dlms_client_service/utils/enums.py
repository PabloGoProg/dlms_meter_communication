from enum import Enum


class ConnectionInterfaceType(Enum):
    """
    Enumeration of available connection interface types for DLMS meter communication.

    This enum defines the different communication protocols that can be used
    to establish connections with DLMS meters.
    """

    HDLC = 1  # High-Level Data Link Control protocol
    TCP = 2  # Transmission Control Protocol
    UDP = 3  # User Datagram Protocol


class ConnectionProviderType(Enum):
    """
    Enumeration of available connection provider types for DLMS meter communication.

    This enum defines the different implementation providers that can be used
    to handle the actual connection establishment and data transmission.
    """

    GURUX = 1  # Gurux library provider for DLMS communication
    SOCKET = 2  # Native socket-based provider
