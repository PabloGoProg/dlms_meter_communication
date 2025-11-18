from __future__ import annotations

from ...ports import IAppLayer
from typing import Any
import time

from gurux_dlms import (
    GXByteBuffer,
    GXDLMSClient,
    GXReplyData,
    GXDLMSTranslator,
    GXDLMSException,
)
from gurux_dlms.enums import InterfaceType, Security, Conformance, Authentication
from gurux_net import GXNet
from gurux_common import ReceiveParameters, TimeoutException
from gurux_common.io import Parity, StopBits
from gurux_common.enums import TraceLevel

from dlms_meter_communication.schemas import Device, NegotiatedParams


class GuruxCOSEMApp(IAppLayer):
    def __init__(
        self,
        client: GXDLMSClient,
        media: GXNet,
        trace_level: TraceLevel,
        invocation_counter: int,
    ):
        self.reply_buff = bytearray(8 + 1024)
        self.wait_time = 5000
        self.trace = trace_level
        self.media = media
        self.invocation_counter = invocation_counter
        self.client = client

        if self.trace > TraceLevel.WARNING:
            print(f"Authentication: {self.client.authentication}")
            print(f"ClientAddress: {hex(self.client.clientAddress)}")
            print(f"ServerAddress: {hex(self.client.serverAddress)}")

    def associate(self, device: Device, nps: NegotiatedParams) -> None:
        pass

    def get(self, obis_code: str) -> any:
        pass

    def set(self, obis_code: str, value: any) -> None:
        pass

    def action(self, obis_code: str, action: str) -> None:
        pass

    def disconnect(self) -> None:
        if self.nedia and self.media.isOpen():
            reply = GXReplyData()

            try:
                if (
                    self.client.interfaceType == InterfaceType.WRAPPER
                    or self.client.ciphering.security != Security.NONE
                ):
                    self._read_data_block(self.client.releaseRequest(), reply)
            except Exception:
                pass  # All meters do not support this request

            reply.clear()
            self._read_dlms_packet(self.client.disconnectRequest(), reply)
            self.media.close()

    def _read_dlms_packet(self, data: Any, reply: GXReplyData = None) -> None:
        """
        Processes DLMS (Device Language Message Specification) data packets and extracts
        response data from the meter device.

        This method acts as a dispatcher that handles both single and multiple DLMS packet
        scenarios. It normalizes the input data format and delegates the actual communication
        with the device to the `_extract_data_block` method, which performs the low-level
        send/receive operations.

        The method supports two input formats:
        1. A single bytearray containing one DLMS packet
        2. A list of bytearray objects, each containing a separate DLMS packet

        When processing multiple packets, the reply object is cleared between each packet
        to ensure that responses from previous packets do not contaminate subsequent ones.

        Args:
            data (Any): The DLMS packet(s) to process. Can be either:
                - A single bytearray: Contains one complete DLMS packet ready to be sent
                - A list of bytearray: Contains multiple DLMS packets that need to be
                  processed sequentially
            reply (GXReplyData, optional): A GXReplyData object that will store the response
                data received from the device. If not provided, a new GXReplyData instance
                will be created. This object accumulates the parsed response data including
                any error codes, payload data, and streaming status flags.

        Returns:
            None: This method does not return a value. The response data is stored in the
                `reply` parameter object, which is modified in-place. Any errors encountered
                during communication will be raised as exceptions by the underlying
                `_extract_data_block` method.

        Raises:
            GXDLMSException: Raised by `_extract_data_block` if the device returns an error
                code in the response.
            TimeoutException: Raised by `_extract_data_block` if the device does not respond
                within the configured timeout period.

        Note:
            - The `reply` object is reused across multiple packet processing if provided.
            - For list inputs, the reply is cleared before processing each packet to prevent
              data mixing between sequential operations.
            - This method does not validate the structure or content of the DLMS packets;
              it assumes they are properly formatted according to DLMS/COSEM standards.
            - The actual network communication (sending data and receiving responses) is
              handled by the `_extract_data_block` method, which this method calls.
        """
        if not reply:
            reply = GXReplyData()

        if isinstance(data, bytearray):
            # Single bytearray packet
            self._extract_data_block(data, reply)
        elif isinstance(data, list) and all(
            isinstance(item, bytearray) for item in data
        ):
            # List of bytearray packets
            for item in data:
                reply.clear()
                self._extract_data_block(item, reply)

    def _extract_data_block(self, data: bytearray, reply: GXReplyData) -> None:
        """
        Performs low-level communication with a DLMS meter device, sending a request packet
        and receiving/parsing the response.

        This is the core method that handles the actual network I/O operations for DLMS
        communication. It manages the complete request-response cycle including:
        - Configuring communication parameters based on interface type (HDLC vs WRAPPER)
        - Sending the request packet to the device
        - Receiving and accumulating response data (which may arrive in multiple frames)
        - Handling retries on communication failures (up to 3 attempts)
        - Processing unsolicited notifications from the device
        - Parsing the complete response into the reply object

        The method implements a state machine that continues receiving data until the
        DLMS client indicates that a complete message has been received. It handles both
        streaming and non-streaming responses, as well as multi-frame messages that require
        multiple receive operations.

        Args:
            data (bytearray): The DLMS request packet to send to the device. Must be
                properly formatted according to DLMS/COSEM protocol specification.
            reply (GXReplyData): The reply object that will be populated with the parsed
                response data. Modified in-place and contains the complete response after
                successful execution.

        Returns:
            None: Response data is stored in the `reply` parameter object. Errors are
                raised as exceptions.

        Raises:
            TimeoutException: If the device does not respond after 3 retry attempts.
            GXDLMSException: If the device returns an error code in the response.
        """
        if not data:
            return

        # Separate handler for unsolicited notifications that may arrive from the device
        # (e.g., alarm conditions). These are asynchronous messages not directly related
        # to our request.
        notify = GXReplyData()

        reply.error = 0
        # EOP (End-of-Packet) marker: 0x7E is the standard HDLC flag byte used to delimit
        # frames in serial/HDLC communications. For network connections (WRAPPER over TCP),
        # frames are delimited by length fields instead, so EOP is not used.
        eop = 0x7E

        # In network connection terminator is not used.
        if self.client.interfaceType == InterfaceType.WRAPPER and isinstance(
            self.media, GXNet
        ):
            eop = None

        params = ReceiveParameters()
        params.eop = eop
        params.allData = True
        params.waitTime = self.waitTime

        # For network connections (eop=None), we need 8 bytes to read the frame length
        # header. For HDLC (with EOP marker), 5 bytes are sufficient for the initial
        # frame header.
        if eop is None:
            params.Count = 8  # Wrapper Conn
        else:
            params.Count = 5  # HDLC Conn

        self.media.eop = eop
        # Byte buffer to accumulate raw bytes received from the device. The DLMS client
        # will parse this buffer incrementally as data arrives.
        rd = GXByteBuffer()

        # Synchronous context ensures all send/receive operations are performed atomically
        # without interruption from other threads. Critical for maintaining protocol state.
        with self.media.getSynchronous():
            # Only send if not in streaming mode. In streaming mode, data was already sent
            # in a previous operation and we're continuing to receive the response.
            if not reply.isStreaming():
                self.media.send(data)

            pos = 0

            try:
                # Main receive loop: continues until client.getData() returns True, indicating
                # that a complete DLMS message has been received and parsed. Handles incremental
                # parsing of multi-frame messages and extraction of DLMS objects from byte stream.
                while not self.client.getData(rd, reply, notify):
                    # Handle unsolicited notifications from the device. These are separate from
                    # the response to our request and need to be processed independently.
                    if notify.data.size != 0:
                        # If notification is complete (no more data expected), convert to XML
                        # for debugging/monitoring and clear the buffer.
                        if not notify.isMoreData():
                            t = GXDLMSTranslator()
                            xml = t.dataToXml(notify.data)
                            print(xml)
                            notify.clear()
                        continue

                    # For network connections without EOP markers, frame size must be determined
                    # dynamically by reading the length field from received data. getFrameSize()
                    # parses the DLMS wrapper header to determine how many bytes to read.
                    if not params.eop:
                        params.count = self.client.getFrameSize(rd)

                    # Receive loop with retry logic: attempts to receive data from device.
                    # If receive() fails (timeout), retry up to 3 times before giving up.
                    # On each retry, re-send the request to ensure device is still listening.
                    while not self.media.receive(params):
                        pos += 1
                        if pos == 3:
                            raise TimeoutException(
                                "Failed to receive reply from the device in given time."
                            )
                        print(f"Data send failed. Try to resend {pos}/3")
                        self.media.send(data, None)

                    # Add received bytes to buffer for parsing. Clear params.reply to free
                    # memory and prepare for next receive operation (important for multi-frame).
                    rd.set(params.reply)
                    params.reply = None
            except Exception as e:
                self.writeTrace("RX: " + self.now() + "\t" + str(rd), TraceLevel.ERROR)
                raise e

            self.writeTrace("RX: " + self.now() + "\t" + str(rd), TraceLevel.VERBOSE)
            # Even if communication succeeded, DLMS protocol may indicate application-level
            # errors (e.g., object not found, access denied). Check and raise if present.
            if reply.error != 0:
                raise GXDLMSException(reply.error)

    def _read_data_block(self, data, reply):
        """
        Reads DLMS data blocks, handling both single and multi-frame responses.

        This method orchestrates the reading of DLMS data that may arrive in multiple frames.
        It supports two scenarios:
        1. Multiple independent packets (list): Processes each packet sequentially
        2. Single packet with multi-frame response: Sends initial request and handles
           subsequent frames using receiverReady commands or streaming mode

        The method automatically handles the DLMS fragmentation mechanism where large
        responses are split across multiple frames. It continues requesting additional
        frames until the complete message is received.

        Args:
            data: The DLMS packet(s) to send. Can be:
                - A list of bytearray: Multiple independent packets to process
                - A single bytearray or similar: One packet that may trigger multi-frame response
            reply (GXReplyData): The reply object that accumulates the complete response
                across all frames. Modified in-place.

        Returns:
            bool: True if all operations completed without errors, False otherwise.
                Only returned when processing a list of packets. For single packets,
                errors are raised as exceptions by _read_dlms_packet.
        """
        if data:
            # Handle multiple independent packets: process each one sequentially
            if isinstance(data, (list)):
                for item in data:
                    # Clear reply between packets to prevent data contamination
                    reply.clear()
                    self._read_data_block(item, reply)
                # Return success status for list processing
                return reply.error == 0
            else:
                # Single packet: send initial request and handle multi-frame response
                self._read_dlms_packet(data, reply)

                # Continue receiving frames until complete message is assembled
                # isMoreData() indicates that additional frames are expected
                while reply.isMoreData():
                    # In streaming mode, no additional request is needed - device continues
                    # sending data automatically. In normal mode, we must explicitly request
                    # the next frame using receiverReady command.
                    if reply.isStreaming():
                        data = None  # No data to send, just continue receiving
                    else:
                        # Generate receiverReady command to request the next frame of data
                        # This is the standard DLMS mechanism for multi-frame transfers
                        data = self.client.receiverReady(reply)
                    # Receive and accumulate the next frame into the reply object
                    self._read_dlms_packet(data, reply)

    def _initialize_optical_link(self) -> None:
        """
        Initializes an optical link connection using IEC 62056-21 Mode E protocol.

        This method implements the optical port initialization sequence required for
        communicating with DLMS meters via infrared (IR) or optical interface. The
        process follows the Mode E handshake protocol:

        1. Send identification request ("/?!\\r\\n") to the meter
        2. Receive meter's identification string containing preferred baud rate
        3. Parse the baud rate from the response (character at position 4)
        4. Send acknowledgment with selected communication parameters
        5. Configure serial port with negotiated baud rate and parameters

        The method only executes for HDLC_WITH_MODE_E interface type, which uses
        optical communication. The baud rate negotiation allows the meter to specify
        its preferred communication speed, which is then used for subsequent operations.

        Raises:
            Exception: If the meter does not respond, returns invalid identification,
                or specifies an unsupported baud rate.
        """
        if self.client.InterfaceType == InterfaceType.HDLC_WITH_MODE_E:
            params = ReceiveParameters()

            params.allData = True
            # Mode E uses newline character as end-of-packet marker
            params.eop = "\n"
            params.waitTime = self.wait_time

            with self.media.getSynchronous():
                # IEC 62056-21 Mode E identification request: "/?!" requests identification,
                # followed by carriage return and line feed
                data = "/?!\r\n"
                self.media.send(data)

                if not self.media.receive(params):
                    raise Exception("Failed to received reply from the media.")

                # Some meters echo the request back before sending their identification.
                # If we receive our own command, wait for the actual identification response.
                if data.encode() == params.reply:
                    params.reply = None
                    if not self.media.receive(params):
                        raise Exception("Failed to received reply from the media.")

            # Validate response format: must start with "/" character
            if not params.reply or params.reply[0] != ord("/"):
                raise Exception("Invalid responce : " + str(params.reply))

            # Extract baud rate character from position 4 of the identification string.
            # Format: "/XXXXX..." where character at index 4 indicates preferred baud rate
            baud_rate = chr(params.reply[4])
            bit_rate = None

            # Map baud rate character to actual baud rate value according to IEC 62056-21
            # standard. The meter specifies its preferred speed using a single digit.
            if baud_rate == "0":
                bit_rate = 300
            elif baud_rate == "1":
                bit_rate = 600
            elif baud_rate == "2":
                bit_rate = 1200
            elif baud_rate == "3":
                bit_rate = 2400
            elif baud_rate == "4":
                bit_rate = 4800
            elif baud_rate == "5":
                bit_rate = 9600
            elif baud_rate == "6":
                bit_rate = 19200
            else:
                raise Exception("Unknown baud rate.")

            # Control characters for Mode E acknowledgment:
            # - control_chr (2): Protocol control character
            # - mode_control_chr (2): Mode control character
            control_chr = ord("2")
            mode_control_chr = ord("2")

            # Build acknowledgment packet: ACK (0x06) + control chars + baud rate + CR + LF
            # This confirms to the meter that we accept the negotiated parameters
            tmp = bytearray(
                [0x06, control_chr, ord(baud_rate), mode_control_chr, 13, 10]
            )

            params.reply = None

            with self.media.getSynchronous():
                self.media.send(tmp)

                # Wait for meter to process acknowledgment before changing port settings
                time.sleep(0.5)
                params.waitTime = 200
                # Configure serial port parameters for Mode E communication:
                # - 8 data bits, no parity, 1 stop bit (standard Mode E configuration)
                # - Baud rate set to the value negotiated with the meter
                self.media.dataBits = 8
                self.media.parity = Parity.NONE
                self.media.stopBits = StopBits.ONE
                self.media.baudRate = bit_rate
                # Additional delay to ensure port settings are applied and stabilized
                time.sleep(1)

    def _update_frame_counter(self) -> None:
        if (
            self.invocation_counter
            and self.client.ciphering is not None
            and self.client.ciphering.security != Security.NONE
        ):
            self._initialize_optical_link()
            self.client.proposedConformance |= Conformance.GENERAL_PROTECTION

            add = self.client.clientAddress
            auth = self.client.authentication
            security = self.client.ciphering.security
            challenge = self.client.ctoSChallenge

            try:
                self.client.clientAddress = 16
                self.client.authentication = Authentication.NONE
                self.client.ciphering.security = Security.NONE

                reply = GXReplyData()
                data = self.client.snrmRequest()

                if data:
                    self._read_dlms_packet(data, reply)
                    self.client.parseUAResponse(reply.data
            finally:
                pass
