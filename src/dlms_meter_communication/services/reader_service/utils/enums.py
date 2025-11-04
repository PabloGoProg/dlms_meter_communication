from enum import Enum


class CommunicationProfileType(Enum):
    """
    Enumeration of available communication profiles for DLMS meter communication.

    This enum defines the different communication profiles that can be used to establish connections with DLMS meters.
    """

    WRAPPER_PROFILE = 1  # IP-Oriented communication profile
    HDLC_SERIAL_PROFILE = 2  # High-Level Data Link Control on serial port
    HDLC_TUNNELING_PROFILE = 3  # High-Level Data Link Control on TCP/UDP


class ConnectionProviderType(Enum):
    """
    Enumeration of available connection provider types for DLMS meter communication.

    This enum defines the different implementation providers that can be used
    to handle the actual connection establishment and data transmission.
    """

    GURUX = 1  # Gurux library provider for DLMS communication
    SOCKET = 2  # Native socket-based provider


class ConnectionMediaType(Enum):
    """
    Enumeration of available connection media types for DLMS meter communication.

    This enum defines the different media types that can be used to establish connections with DLMS meters.
    """

    TCP = 1  # Transmission Control Protocol
    UDP = 2  # User Datagram Protocol
    SERIAL = 3  # Serial port
