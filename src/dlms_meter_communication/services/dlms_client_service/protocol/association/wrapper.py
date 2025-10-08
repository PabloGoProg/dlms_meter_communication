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
│   (2 bytes) │  (2 bytes)  │  (2 bytes)  │  (2 bytes)  │
└─────────────┴─────────────┴─────────────┴─────────────┘

DETAILED FIELD EXPLANATION:
===========================

1. VERSION (2 bytes):
   - Purpose: Identifies the version of the wrapper protocol
   - Current Value: 0x0001 (version 1)
   - Why needed: Ensures compatibility between different implementations
   - Example: 0x0001 means "I'm using wrapper version 1"

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
   - Example: If DLMS message is 100 bytes, length = 100

REAL-WORLD EXAMPLE:
===================
Let's say you want to read the serial number from a meter:

1. Your DLMS message might be: [DLMS data to read serial number] (50 bytes)
2. You wrap it with header:
   - Version: 0x0001 (I'm using version 1)
   - Source: 0x0010 (I'm a public client)
   - Destination: 0x0001 (Send to meter management)
   - Length: 0x0032 (50 bytes of DLMS data follow)

3. Final message sent over network:
   [0x0001][0x0010][0x0001][0x0032][50 bytes of DLMS data]

WHY IS THIS NEEDED?
===================
- Network Routing: Helps network equipment route messages correctly
- Protocol Identification: Distinguishes DLMS from other protocols
- Message Boundaries: Length field helps receiver know when message ends
- Addressing: Allows multiple clients/servers on same network
- Compatibility: Ensures different DLMS implementations can communicate

This wrapper is mandatory for all DLMS/COSEM communication over TCP/UDP networks
and must be present before any actual DLMS protocol data.
"""


class Wrapper:
    """
    Represents the 8-byte wrapper header required for DLMS/COSEM TCP/UDP communication.

    This class encapsulates the wrapper header that must be prepended to all DLMS
    messages when communicating over TCP or UDP networks. It provides a convenient
    way to create, validate, and serialize the header fields.

    The wrapper header serves as an "envelope" for DLMS messages, providing:
    - Protocol version information
    - Source and destination addressing
    - Message length information

    Attributes:
        source_wport (int): Source port identifier (who is sending)
        destination_wport (int): Destination port identifier (who should receive)
        version (int): Wrapper protocol version (currently 1)
    """

    HEADER_LENGTH = 8

    def __init__(
        self,
        source_wport: int,
        destination_wport: int,
        version: int = 1,
    ) -> None:
        """
        Initialize the wrapper with source and destination port information.

        This constructor sets up the wrapper with the necessary addressing information
        for DLMS/COSEM communication. The length field is calculated automatically
        when wrapping messages, so it's not stored as an instance variable.

        Args:
            source_wport (int): Source port identifier (who is sending the message)
            destination_wport (int): Destination port identifier (who should receive)
            version (int, optional): Wrapper protocol version. Defaults to 1.
                Currently only version 1 is supported by the DLMS/COSEM standard.
        """
        self.version = version
        self.source_wport = source_wport
        self.destination_wport = destination_wport

    def wrap_dlms_message(self, payload: bytes) -> bytes:
        """
        Wrap a DLMS message with the 8-byte header for network transmission.

        This method takes raw DLMS data and prepends the wrapper header to create
        a complete message ready for transmission over TCP/UDP networks. The header
        includes version, source/destination ports, and the length of the payload.

        Args:
            payload (bytes): The raw DLMS message data to wrap
                This is the actual DLMS protocol data without any wrapper header.

        Returns:
            bytes: Complete wrapped message ready for network transmission
                Format: [8-byte header][payload data]

        Raises:
            TypeError: If payload is not bytes
            ValueError: If payload is empty or too large
        """
        if not isinstance(payload, bytes):
            raise TypeError("Payload must be bytes")

        if len(payload) == 0:
            raise ValueError("Payload cannot be empty")

        if len(payload) > 65535:
            raise ValueError("Payload too large (max 65535 bytes)")

        _version_bytes = self.version.to_bytes(2, byteorder="big")
        _source_bytes = self.source_wport.to_bytes(2, byteorder="big")
        _dest_bytes = self.destination_wport.to_bytes(2, byteorder="big")
        _length_bytes = len(payload).to_bytes(2, byteorder="big")

        return _version_bytes + _source_bytes + _dest_bytes + _length_bytes + payload

    def unwrap_dlms_message(
        self, wrapped_message: bytes
    ) -> tuple[tuple[int, int, int, int], bytes]:
        """
        Unwrap a DLMS message by separating the header from the payload.

        This method takes a complete wrapped message (header + payload) and separates
        it into its component parts. It extracts the 8-byte header and returns both
        the parsed header information and the original DLMS payload.

        Args:
            wrapped_message (bytes): Complete wrapped message from network
                Format: [8-byte header][payload data]

        Returns:
            tuple: A tuple containing:
                - tuple[int, int, int, int]: Parsed header (version, source, dest, length)
                - bytes: The original DLMS payload data

        Raises:
            TypeError: If wrapped_message is not bytes
            ValueError: If message is too short or header is invalid
        """
        if not isinstance(wrapped_message, bytes):
            raise TypeError("Wrapped message must be bytes")

        if len(wrapped_message) < self.HEADER_LENGTH:
            raise ValueError(
                f"Message too short: {len(wrapped_message)} bytes (minimum 8)"
            )

        header_bytes = wrapped_message[0 : self.HEADER_LENGTH]
        payload = wrapped_message[self.HEADER_LENGTH :]

        return self._from_bytes(header_bytes), payload

    def is_wrapped(self, message: bytes) -> bool:
        """
        Check if a message is properly wrapped with this wrapper's configuration.

        This method validates that a received message has the correct wrapper header
        that matches this wrapper's configuration. It checks all header fields and
        verifies that the length field matches the actual payload size.

        Args:
            message (bytes): The message to validate
                This should be a complete wrapped message from the network.

        Returns:
            bool: True if the message is properly wrapped with matching configuration,
                  False otherwise
        """
        if len(message) < 8:
            return False

        header = message[0 : self.HEADER_LENGTH]
        payload = message[self.HEADER_LENGTH :]

        try:
            _version, _source_wport, _destination_wport, _length = self._from_bytes(
                header
            )
        except ValueError:
            return False

        return (
            _version == self.version
            and _source_wport == self.source_wport
            and _destination_wport == self.destination_wport
            and _length == len(payload)
        )

    def _from_bytes(self, data: bytes) -> tuple[int, int, int, int]:
        """
        Parse a 8-byte header into individual field values.

        This private method converts raw header bytes into the individual field
        values. It's used internally by other methods to parse received headers.

        Args:
            data (bytes): Raw header data (must be exactly 8 bytes)

        Returns:
            tuple[int, int, int, int]: Parsed header fields as (version, source, dest, length)

        Raises:
            TypeError: If data is not bytes
            ValueError: If data is not exactly 8 bytes
        """
        if not isinstance(data, bytes):
            raise TypeError("Header data must be bytes")

        if len(data) != self.HEADER_LENGTH:
            raise ValueError(
                f"Wrapper header must be exactly 8 bytes, got {len(data)} bytes"
            )

        _version = int.from_bytes(data[0:2], byteorder="big")
        _source_wport = int.from_bytes(data[2:4], byteorder="big")
        _destination_wport = int.from_bytes(data[4:6], byteorder="big")
        _length = int.from_bytes(data[6:8], byteorder="big")

        return (_version, _source_wport, _destination_wport, _length)
