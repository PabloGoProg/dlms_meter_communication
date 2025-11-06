"""
DLMS/COSEM Wrapper Header for TCP/UDP Communication

This classs implements the wrapper header required for DLMS/COSEM communication over TCP/UDP networks. When communicating with smart meters using these protocols, the ctual DLMS data must be wrapped with a special header that provides addressing and routing information.

WHAT IS THE WRAPPER?
====================
Think of the wrapper as an "envelope" that contains your DLMS message. Just like
a postal envelope has a sender address, recipient address, and indicates the
size of the contents, the DLMS wrapper provides similar information for network
communication.

The wrapper is always 8 bytes long and consists of 4 fields, each 2 bytes (16 bits):

┌─────────────┬─────────────┬─────────────┬─────────────┐
│   Version   │ Source Port │ Dest. Port  │   Length    │
│  (2 bytes)  │  (2 bytes)  │  (2 bytes)  │  (2 bytes)  │
└─────────────┴─────────────┴─────────────┴─────────────┘

DETAILED FIELD EXPLANATION:
===========================

1. VERSION (2 bytes):
   - Purpose: Identifies the version of the wrapper protocol
   - Current Value: 0x0001 (version 1)
   - Why needed: Ensures compatibility between different implementations

2. SOURCE WPORT (2 bytes):
   - Purpose: Identifies WHO is sending the message (the client)
   - Think of it as: "Return address" on an envelope
   - Common values:
     * 0x0000 (0)    = No-station (not used)
     * 0x0001 (1)    = Client Management Process (system messages)
     * 0x0010 (16)   = Public Client (normal user operations)
     * 0x0002-0x000F (2-15) = Reserved for special purposes
     * 0x0011-0x00FF (17-255) = Available for custom client applications

3. DESTINATION WPORT (2 bytes):
   - Purpose: Identifies WHO should receive the message (the server/meter)
   - Think of it as: "Delivery address" on an envelope
   - Common values:
     * 0x0000 (0)    = No-station (not used)
     * 0x0001 (1)    = Management Logical Device (meter management)
     * 0x0002-0x000F (2-15) = Reserved for future use
     * 0x0010-0x007E (16-126) = Available for custom server applications
     * 0x007F (127)  = All-station (broadcast to all devices)

4. LENGTH (2 bytes):
   - Purpose: Tells the receiver how many bytes of DLMS data follow
   - Think of it as: "Package weight" - helps receiver know when message is complete
   - Value: Number of bytes in the actual DLMS message (not including the 8-byte wrapper)
"""

import struct

from ...ports import IFrameCodec


class WrapperCodec(IFrameCodec):
    """DLMS/COSEM wrapper frame codec.

    Encodes payloads by prepending an 8-byte header (version, source/destination
    wPorts, length) and decodes incoming buffers to extract complete frames.
    Validates version, wPorts, and payload length against configured values.
    """

    def __init__(
        self, source_wport: int, destination_wport: int, max_payload_length: int = 65535
    ) -> None:
        super().__init__()

        self._wrapper_version = 1
        self._src_wport = source_wport
        self._dst_wport = destination_wport
        self._max_payload_length = max_payload_length

    def encode(self, payload: bytes) -> bytes:
        """Encode payload by prepending 8-byte wrapper header.

        Returns payload unchanged if already wrapped. Validates payload size
        against max_payload_length.
        """
        if not payload:
            raise ValueError("Payload cannot be empty")

        if self.is_wrapped(payload):
            # Skip encoding if already wrapped to avoid double-wrapping
            return payload

        p_len = len(payload)
        if p_len > self._max_payload_length:
            raise ValueError(
                f"Payload too large (max {self._max_payload_length} bytes)"
            )

        # Pack header as 4 big-endian unsigned shorts (version, src, dst, length)
        header = struct.pack(
            ">4H", self._wrapper_version, self._src_wport, self._dst_wport, p_len
        )

        return header + payload

    def decode(self, buffer: bytes) -> tuple[bytes | None, bytes | None]:
        """Extract one complete frame from buffer.

        Returns (payload, remaining) if complete frame found, (None, buffer) if
        more data needed. Validates version, wPorts, and payload length.
        """
        if len(buffer) < 8:
            # Need at least 8 bytes for header
            return None, buffer

        ver, src_wport, dst_wport, p_len = struct.unpack(">4H", buffer[:8])

        if ver != 1:
            raise ValueError(f"Unsupported wrapper version: {ver}")
        if src_wport != self._src_wport:
            raise ValueError(f"Invalid source port: {src_wport}")
        if dst_wport != self._dst_wport:
            raise ValueError(f"Invalid destination port: {dst_wport}")
        if p_len == 0 or p_len > self._max_payload_length:
            raise ValueError(f"Invalid payload length: {p_len}")

        t_len = 8 + p_len
        if len(buffer) < t_len:
            # Header present but payload incomplete
            return None, buffer

        payload = buffer[8:t_len]
        # Return remaining bytes if any, None if buffer fully consumed
        remaining = buffer[t_len:] if len(buffer) > t_len else None
        return payload, remaining

    def is_wrapped(self, message: bytes) -> bool:
        """Check if message already has a valid wrapper header.

        Validates version, wPorts match configuration, and length matches
        message size.
        """
        if len(message) < 8:
            return False

        ver, src_wport, dst_wport, p_len = struct.unpack(">4H", message[:8])
        return (
            ver == 1
            and p_len == len(message) - 8
            and src_wport == self._src_wport
            and dst_wport == self._dst_wport
        )
