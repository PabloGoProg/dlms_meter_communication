from ...ports import IConnection

from typing import Optional


class SerialConnection(IConnection):
    def __init__(
        self,
        baudrate: int,
        max_tx_pdu: int = 1024,
        max_rx_pdu: int = 1024,
        timeout: float = 10.0,
    ):
        self.baudrate = baudrate
        self.max_tx_pdu = max_tx_pdu
        self.max_rx_pdu = max_rx_pdu
        self.timeout = timeout

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def send(self, data: bytes) -> None:
        pass

    def receive(self, size: int, timeout: Optional[float] = 10.0) -> bytes:
        pass

    def set_timeout(self, timeout: float) -> None:
        pass

    def is_connected(self) -> bool:
        pass
