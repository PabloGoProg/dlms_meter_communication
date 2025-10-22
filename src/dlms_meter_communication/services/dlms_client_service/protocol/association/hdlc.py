"""
DLMS/COSEM HDLC Protocol Implementation

This module implements the HDLC (High-Level Data Link Control) protocol required for
DLMS/COSEM communication over serial connections and HDLC tunneling over TCP/UDP.

WHAT IS HDLC?
=============
HDLC is a data link layer protocol that provides:
- Frame synchronization (start/end flags)
- Error detection (CRC)
- Flow control
- Addressing for multiple devices

HDLC FRAME STRUCTURE:
=====================
┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐
│  Flag   │ Address │ Control │   Data  │   CRC   │  Flag   │
│ (1 byte)│(1 byte) │(1 byte) │(n bytes)│(2 bytes)│(1 byte) │
└─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘

DETAILED FIELD EXPLANATION:
===========================

1. FLAG (0x7E):
   - Purpose: Frame delimiter (start and end of frame)
   - Value: Always 0x7E (01111110 in binary)
   - Why needed: Synchronizes frame boundaries

2. ADDRESS (1 byte):
   - Purpose: Identifies the destination device
   - Client address: Usually 0x01 (client sends to server)
   - Server address: Usually 0x81 (server sends to client)
   - Broadcast: 0xFF (all devices)

3. CONTROL (1 byte):
   - Purpose: Frame type and sequence number
   - Information frame: 0x10 (data transmission)
   - Supervisory frame: 0x00-0x0F (control)
   - Unnumbered frame: 0x03 (connection management)

4. DATA (variable):
   - Purpose: The actual DLMS protocol data
   - Contains: DLMS APDU (Application Protocol Data Unit)

5. CRC (2 bytes):
   - Purpose: Error detection
   - Algorithm: CRC-16-CCITT
   - Covers: Address, Control, and Data fields

BIT STUFFING:
============
To prevent flag patterns in data, HDLC uses bit stuffing:
- If 5 consecutive '1' bits are found, insert a '0' bit
- This ensures 0x7E flag pattern never appears in data

REAL-WORLD EXAMPLE:
==================
1. DLMS message: [DLMS data] (50 bytes)
2. Create HDLC frame:
   - Flag: 0x7E
   - Address: 0x81 (server address)
   - Control: 0x10 (information frame)
   - Data: [50 bytes of DLMS data]
   - CRC: [calculated CRC-16]
   - Flag: 0x7E
3. Apply bit stuffing to entire frame
4. Final frame: [0x7E][0x81][0x10][data+stuffing][CRC][0x7E]

WHY IS HDLC NEEDED?
===================
- Serial Communication: Essential for RS-232/RS-485 connections
- Error Detection: CRC ensures data integrity
- Frame Synchronization: Clear message boundaries
- Multi-drop Networks: Addressing allows multiple devices
- Standardization: Widely supported in industrial protocols
"""

import struct
from typing import Tuple


class HDLCFrame:
    """
    Represents an HDLC frame for DLMS/COSEM communication.

    This class handles the creation, parsing, and validation of HDLC frames
    used in DLMS/COSEM communication over serial connections and HDLC tunneling.
    """

    # HDLC constants
    FLAG = 0x7E
    ESCAPE = 0x7D
    ESCAPE_XOR = 0x20

    def __init__(
        self,
        address: int = 0x81,  # Default server address
        control: int = 0x10,  # Default information frame
    ) -> None:
        """
        Initialize HDLC frame handler.

        Args:
            address: HDLC address (0x01 for client, 0x81 for server)
            control: HDLC control field (0x10 for information frame)
        """
        self.address = address
        self.control = control

    def _calculate_crc16(self, data: bytes) -> int:
        """
        Calculate CRC-16-CCITT for HDLC frame.

        Args:
            data: Data to calculate CRC for

        Returns:
            int: 16-bit CRC value
        """
        crc = 0xFFFF

        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0x8408
                else:
                    crc >>= 1

        return crc & 0xFFFF

    def _stuff_bits(self, data: bytes) -> bytes:
        """
        Apply bit stuffing to prevent flag patterns in data.

        Args:
            data: Raw data to apply stuffing to

        Returns:
            bytes: Data with bit stuffing applied
        """
        stuffed = bytearray()
        consecutive_ones = 0

        for byte in data:
            for bit_pos in range(7, -1, -1):  # Process bits from MSB to LSB
                bit = (byte >> bit_pos) & 1

                if bit == 1:
                    consecutive_ones += 1
                    if consecutive_ones == 5:
                        # Insert stuffed bit (0) and reset counter
                        stuffed.append(1)  # Add the current bit
                        consecutive_ones = 0
                    else:
                        stuffed.append(bit)
                else:
                    consecutive_ones = 0
                    stuffed.append(bit)

        # Convert bit array back to bytes
        result = bytearray()
        for i in range(0, len(stuffed), 8):
            byte_val = 0
            for j in range(8):
                if i + j < len(stuffed):
                    byte_val |= stuffed[i + j] << (7 - j)
            result.append(byte_val)

        return bytes(result)

    def _unstuff_bits(self, data: bytes) -> bytes:
        """
        Remove bit stuffing from HDLC frame data.

        Args:
            data: Stuffed data to unstuff

        Returns:
            bytes: Data with bit stuffing removed
        """
        # Convert bytes to bit array
        bits = []
        for byte in data:
            for i in range(7, -1, -1):
                bits.append((byte >> i) & 1)

        # Remove stuffing
        unstuffed = []
        consecutive_ones = 0

        for bit in bits:
            if bit == 1:
                consecutive_ones += 1
                if consecutive_ones == 5:
                    # Skip stuffed bit and reset counter
                    consecutive_ones = 0
                else:
                    unstuffed.append(bit)
            else:
                consecutive_ones = 0
                unstuffed.append(bit)

        # Convert bit array back to bytes
        result = bytearray()
        for i in range(0, len(unstuffed), 8):
            byte_val = 0
            for j in range(8):
                if i + j < len(unstuffed):
                    byte_val |= unstuffed[i + j] << (7 - j)
            result.append(byte_val)

        return bytes(result)

    def create_frame(self, payload: bytes) -> bytes:
        """
        Create a complete HDLC frame from DLMS payload.

        Args:
            payload: Raw DLMS message data

        Returns:
            bytes: Complete HDLC frame ready for transmission

        Raises:
            ValueError: If payload is empty or too large
        """
        if len(payload) == 0:
            raise ValueError("Payload cannot be empty")

        if len(payload) > 4096:  # Reasonable limit for HDLC frames
            raise ValueError("Payload too large for HDLC frame")

        # Create frame without stuffing
        frame_data = (
            struct.pack("BBB", self.address, self.control, len(payload)) + payload
        )
        crc = self._calculate_crc16(
            frame_data[1:]
        )  # CRC covers address, control, and payload

        # Complete frame: flag + address + control + payload + crc + flag
        complete_frame = (
            struct.pack("B", self.FLAG)
            + frame_data
            + struct.pack(">H", crc)
            + struct.pack("B", self.FLAG)
        )

        # Apply bit stuffing
        return self._stuff_bits(complete_frame)

    def parse_frame(self, frame_data: bytes) -> Tuple[bytes, int, int]:
        """
        Parse an HDLC frame and extract the DLMS payload.

        Args:
            frame_data: Complete HDLC frame data

        Returns:
            Tuple containing:
            - bytes: Extracted DLMS payload
            - int: Source address
            - int: Control field

        Raises:
            ValueError: If frame is invalid or CRC check fails
        """
        if len(frame_data) < 7:  # Minimum frame size
            raise ValueError("Frame too short")

        # Remove bit stuffing
        unstuffed = self._unstuff_bits(frame_data)

        # Verify frame structure
        if unstuffed[0] != self.FLAG or unstuffed[-1] != self.FLAG:
            raise ValueError("Invalid frame flags")

        # Extract frame components
        frame_payload = unstuffed[1:-1]  # Remove flags
        if len(frame_payload) < 4:  # At least address + control + payload_len + crc
            raise ValueError("Frame payload too short")

        address = frame_payload[0]
        control = frame_payload[1]
        payload_length = frame_payload[2]

        if (
            len(frame_payload) < 3 + payload_length + 2
        ):  # payload_len + actual_payload + crc
            raise ValueError("Incomplete frame")

        payload = frame_payload[3 : 3 + payload_length]
        received_crc = struct.unpack(
            ">H", frame_payload[3 + payload_length : 5 + payload_length]
        )[0]

        # Verify CRC
        frame_for_crc = frame_payload[: 3 + payload_length]
        calculated_crc = self._calculate_crc16(
            frame_for_crc[1:]
        )  # Skip address for CRC calculation

        if received_crc != calculated_crc:
            raise ValueError("CRC check failed")

        return payload, address, control

    def is_hdlc_frame(self, data: bytes) -> bool:
        """
        Check if data appears to be an HDLC frame.

        Args:
            data: Data to check

        Returns:
            bool: True if data appears to be HDLC frame
        """
        print(data)
        return len(data) >= 2 and data[0] == self.FLAG and data[-1] == self.FLAG
