from enum import Enum


class ConnectionProviderType(Enum):
    GURUX = "gurux"
    SOCKET = "socket"


class MediaLinkStrategyType(Enum):
    HDLC = "hdlc"
    TCP = "tcp"
    UDP = "udp"
