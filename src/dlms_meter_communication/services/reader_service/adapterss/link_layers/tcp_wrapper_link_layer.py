"""TCP Wrapper link layer implementation for DLMS communication."""

from ...ports import ILinkLayer, IFrameCodec, IConnection

import time
from typing import Optional

from dlms_meter_communication.schemas.negotiated_params import NegotiatedParams


class TCPWrapperLinkLayer(ILinkLayer):
    """Link layer implementation using TCP with DLMS Wrapper protocol."""

    def __init__(self, codec: IFrameCodec, connection: IConnection) -> None:
        super().__init__(codec=codec, connection=connection)

    def negotiate(self, data: bytes) -> NegotiatedParams:
        """Return negotiated parameters for TCP Wrapper protocol.

        TCP Wrapper doesn't require actual negotiation, so returns fixed parameters.
        """
        return NegotiatedParams(
            max_info_rx=self._max_pdu_hint,
            max_info_tx=self._max_pdu_hint,
            win=1,
            max_pdu=self._max_pdu_hint,
        )

    def send_apdu(self, apdu: bytes) -> bytes:
        """Encode and send an APDU over the connection.

        Args:
            apdu: Application Protocol Data Unit to send

        Returns:
            The encoded frame that was sent

        Raises:
            ValueError: If APDU is empty or exceeds max PDU size
        """
        if not apdu:
            raise ValueError("APDU cannot be empty")

        if len(apdu) > self._max_pdu_hint:
            raise ValueError(f"APDU too large (max {self._max_pdu_hint} bytes)")

        frame = self._codec.encode(apdu)
        self._connection.send(frame)

        return frame

    def receive_apdu(self, timeout: float = 10.0) -> bytes:
        """Receive and decode an APDU from the connection.

        Uses internal buffering to handle partial frames. If a complete frame
        is already in the buffer, it returns immediately without blocking.

        Args:
            timeout: Maximum time in seconds to wait for a complete frame

        Returns:
            The decoded APDU payload

        Raises:
            TimeoutError: If no complete frame is received within timeout
            RuntimeError: If frame decoding fails
        """
        deadline = time.monotonic() + timeout

        # Check if buffer already contains a complete frame
        apdu, remaining = self._try_decode_buffer()
        if apdu is not None:
            self._rx_buffer = remaining or b""
            return apdu

        while True:
            # Calculate remaining time until deadline
            time_left = deadline - time.monotonic() if timeout is not None else None
            if time_left is not None and time_left <= 0:
                raise TimeoutError("Wrapper Frame not received within timeout")

            # Receive more data with adjusted timeout
            chunk = self._connection.receive(
                2048, timeout=time_left if time_left is None or time_left > 0 else 0.001
            )

            # Append to buffer and try decoding again
            self._rx_buffer.extend(chunk)
            apdu, remaining = self._try_decode_buffer()

            if apdu is not None:
                self._rx_buffer = remaining or b""
                return apdu

    def _try_decode_buffer(self) -> tuple[Optional[bytes], Optional[bytes]]:
        """Attempt to decode a complete frame from the receive buffer.

        Returns:
            Tuple of (decoded_payload, remaining_bytes). If no complete frame
            is available, returns (None, buffer_bytes).

        Raises:
            RuntimeError: If frame decoding fails, buffer is cleared
        """
        if not self._rx_buffer:
            return None, self._rx_buffer

        try:
            payload, remaining = self._codec.decode(self._rx_buffer)
        except Exception as e:
            # Clear buffer on decode error to avoid getting stuck
            self._rx_buffer = b""
            raise RuntimeError(f"Invalid frame in buffer: {e}") from e

        return payload, remaining
