from .base import ConnectionProvider
import socket
from typing import Optional


class SocketProvider(ConnectionProvider):
    def __init__(
        self,
        ip_address: str,
        port: int,
    ) -> None:
        super().__init__(ip_address, port)
        self.socket = None

    def connect(self) -> None:
        return super().connect()

    def disconnect(self) -> None:
        return super().disconnect()

    def send(self, data: bytes) -> int:
        return super().send(data)

    def receive(self, size: int, timeout: Optional[float] = 10.0) -> bytes:
        return super().receive(size, timeout)

    def is_connected(self) -> bool:
        return super().is_connected()
