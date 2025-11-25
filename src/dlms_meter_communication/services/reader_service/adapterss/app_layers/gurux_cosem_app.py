from __future__ import annotations

from ...ports import IAppLayer
from datetime import datetime
from typing import Any
import time
import os

from gurux_dlms import (
    GXByteBuffer,
    GXDLMSAccessItem,
    GXDLMSClient,
    GXReplyData,
    GXDLMSTranslator,
    GXDLMSException,
)
from gurux_dlms.objects import (
    GXDLMSData,
    GXDLMSObject,
    GXDLMSRegister,
    GXDLMSExtendedRegister,
    GXDLMSDemandRegister,
    GXDLMSProfileGeneric,
    GXDLMSSecuritySetup,
    GXDLMSObjectCollection,
)
from gurux_dlms.enums import (
    InterfaceType,
    Security,
    Conformance,
    Authentication,
    AssociationResult,
    SourceDiagnostic,
    DataType,
    ObjectType,
    AccessServiceCommandType,
)
from gurux_net import GXNet
from gurux_common import GXCommon, ReceiveParameters, TimeoutException
from gurux_common.io import Parity, StopBits
from gurux_common.enums import TraceLevel
from gurux_dlms.ecdsa.enums.Ecc import Ecc
from gurux_dlms.objects.enums.CertificateType import CertificateType
from gurux_dlms.asn.GXAsn1Converter import GXAsn1Converter
from gurux_dlms.ecdsa.GXEcdsa import GXEcdsa
from gurux_dlms.asn.GXPkcs8 import GXPkcs8
from gurux_dlms.asn.GXPkcs10 import GXPkcs10
from gurux_dlms.asn.GXx509Certificate import GXx509Certificate
from gurux_dlms.asn.GXCertificateRequest import GXCertificateRequest
from gurux_dlms.objects.enums.CertificateEntity import CertificateEntity
from gurux_dlms.GXDLMSConverter import GXDLMSConverter

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
        """
        Establish application association with the meter device.

        This method initializes the complete DLMS connection, including HDLC
        and COSEM association layers.

        Args:
            device: Device configuration
            nps: Negotiated parameters from link layer
        """
        self._initialize_connection()

    def get(self, obis_code: str, attribute_index: int = 2) -> any:
        """
        Execute an xDLMS GET service to read an attribute value.

        This method reads a specific attribute from a DLMS object identified by
        its OBIS code. It automatically handles the object creation, request
        generation, response parsing, and multi-frame transfers if needed.

        Args:
            obis_code: OBIS code of the object to read (e.g., "0.0.1.0.0.255")
            attribute_index: Attribute index to read. Default is 2 (value attribute).
                            Common indices:
                            - 1: logical_name
                            - 2: value (for Data, Register objects)
                            - 3: scaler_unit (for Register objects)

        Returns:
            The value read from the meter. Type depends on the object type:
            - Scalar values for Data/Register objects
            - Lists for Profile Generic buffer
            - Complex types for structured attributes

        Raises:
            ValueError: If OBIS code format is invalid
            GXDLMSException: If the meter returns an error (access denied, object not found, etc.)
            TimeoutException: If the meter doesn't respond in time

        Example:
            >>> app.get("0.0.1.0.0.255")  # Read clock
            datetime(2024, 1, 15, 10, 30, 0)
            >>> app.get("1.0.1.8.0.255")  # Read active energy import
            12345.67
        """
        if not obis_code:
            raise ValueError("OBIS code cannot be empty")

        # Validate OBIS code format (should be X.X.X.X.X.X)
        parts = obis_code.split(".")
        if len(parts) != 6:
            raise ValueError(
                f"Invalid OBIS code format: {obis_code}. Expected format: A.B.C.D.E.F"
            )

        try:
            # Try to find the object in the client's object list (if association view was read)
            obj = self.client.objects.findByLN(ObjectType.NONE, obis_code)

            # If object not found in list, create a generic Data object
            # This allows reading without prior association view discovery
            if not obj:
                obj = GXDLMSData(obis_code)

            # Read the specified attribute
            value = self._read(obj, attribute_index)

            return value

        except GXDLMSException as e:
            # Re-raise DLMS exceptions with additional context
            raise GXDLMSException(
                f"Failed to read {obis_code} attribute {attribute_index}: {str(e)}"
            )
        except Exception as e:
            # Wrap other exceptions with context
            raise RuntimeError(
                f"Error reading {obis_code} attribute {attribute_index}: {str(e)}"
            )

    def set(self, obis_code: str, value: any, attribute_index: int = 2) -> None:
        """
        Execute an xDLMS SET service to write an attribute value.

        This method writes a value to a specific attribute of a DLMS object
        identified by its OBIS code. It handles object creation, value assignment,
        and request generation automatically.

        Args:
            obis_code: OBIS code of the object to write (e.g., "0.0.1.0.0.255")
            value: Value to write. Must be compatible with the attribute's data type:
                   - datetime for clock objects
                   - int/float for register values
                   - str for string attributes
                   - bytes/bytearray for octet-string attributes
            attribute_index: Attribute index to write. Default is 2 (value attribute).

        Raises:
            ValueError: If OBIS code is invalid or value type is incompatible
            PermissionError: If write access is denied (insufficient authentication)
            GXDLMSException: If the meter returns an error
            TimeoutException: If the meter doesn't respond in time

        Example:
            >>> from datetime import datetime
            >>> app.set("0.0.1.0.0.255", datetime.now())  # Set clock
            >>> app.set("1.0.0.2.0.255", 100)  # Set demand period
        """
        if not obis_code:
            raise ValueError("OBIS code cannot be empty")

        # Validate OBIS code format
        parts = obis_code.split(".")
        if len(parts) != 6:
            raise ValueError(
                f"Invalid OBIS code format: {obis_code}. Expected format: A.B.C.D.E.F"
            )

        if value is None:
            raise ValueError("Value to write cannot be None")

        try:
            # Try to find the object in the client's object list
            obj = self.client.objects.findByLN(ObjectType.NONE, obis_code)

            # If object not found, create a generic Data object
            if not obj:
                obj = GXDLMSData(obis_code)

            # Set the value in the object
            # For attribute 2 (value), we set it directly
            if attribute_index == 2:
                obj.value = value
            else:
                # For other attributes, use setDataType and setValue
                obj.setValue(self.client.settings, attribute_index, value)

            # Write the value to the meter
            self._write(obj, attribute_index)

        except GXDLMSException as e:
            # Check if it's an access denied error
            if "access" in str(e).lower() or "denied" in str(e).lower():
                raise PermissionError(f"Access denied writing to {obis_code}: {str(e)}")
            raise GXDLMSException(
                f"Failed to write {obis_code} attribute {attribute_index}: {str(e)}"
            )
        except Exception as e:
            raise RuntimeError(
                f"Error writing {obis_code} attribute {attribute_index}: {str(e)}"
            )

    def action(self, obis_code: str, method_index: int, parameters: any = None) -> any:
        """
        Execute an xDLMS ACTION service (method invocation).

        This method invokes a specific method on a DLMS object identified by its
        OBIS code. Methods perform operations like resetting counters, executing
        firmware updates, or triggering meter functions.

        Args:
            obis_code: OBIS code of the object (e.g., "0.0.1.0.0.255")
            method_index: Method index to invoke. Each object type has specific methods:
                         - Clock (0.0.1.0.0.255): Method 1 = adjust_to_quarter,
                                                  Method 2 = adjust_to_measuring_period,
                                                  Method 3 = adjust_to_minute,
                                                  Method 4 = adjust_to_preset_time,
                                                  Method 5 = preset_adjusting_time,
                                                  Method 6 = shift_time
                         - Activity Calendar: Method 1 = activate_passive_calendar
                         - Disconnect Control: Method 1 = remote_disconnect,
                                               Method 2 = remote_reconnect
            parameters: Optional parameters for the method, encoded according to
                       the method's parameter specification. Can be:
                       - None for methods without parameters
                       - Single value for methods with one parameter
                       - List/tuple for methods with multiple parameters

        Returns:
            The method's return value if any. Many methods return None (confirmation only).

        Raises:
            ValueError: If OBIS code or method_index is invalid
            PermissionError: If action execution requires higher authentication
            GXDLMSException: If the meter returns an error
            TimeoutException: If the meter doesn't respond in time

        Example:
            >>> # Adjust clock to quarter hour
            >>> app.action("0.0.1.0.0.255", 1)
            >>>
            >>> # Remote disconnect
            >>> app.action("0.0.96.3.10.255", 1)
            >>>
            >>> # Activate passive calendar
            >>> app.action("0.0.13.0.0.255", 1)
        """
        if not obis_code:
            raise ValueError("OBIS code cannot be empty")

        # Validate OBIS code format
        parts = obis_code.split(".")
        if len(parts) != 6:
            raise ValueError(
                f"Invalid OBIS code format: {obis_code}. Expected format: A.B.C.D.E.F"
            )

        if method_index < 1:
            raise ValueError(f"Method index must be >= 1, got {method_index}")

        try:
            # Try to find the object in the client's object list
            obj = self.client.objects.findByLN(ObjectType.NONE, obis_code)

            # If object not found, create a generic object
            if not obj:
                obj = GXDLMSObject(ObjectType.NONE, obis_code, 0)

            # Prepare method invocation parameters
            # The Gurux library expects parameters as a specific format
            data = self.client.method(obj, method_index, parameters, DataType.NONE)
            reply = GXReplyData()

            # Send action request and receive response
            self._read_data_block(data, reply)

            # Parse and return the response value if any
            if reply.value:
                return reply.value

            return None

        except GXDLMSException as e:
            # Check if it's an access/permission error
            if "access" in str(e).lower() or "denied" in str(e).lower():
                raise PermissionError(
                    f"Access denied executing action on {obis_code}: {str(e)}"
                )
            raise GXDLMSException(
                f"Failed to execute method {method_index} on {obis_code}: {str(e)}"
            )
        except Exception as e:
            raise RuntimeError(
                f"Error executing method {method_index} on {obis_code}: {str(e)}"
            )

    def disconnect(self) -> None:
        """
        Close the DLMS association and disconnect from the meter.

        This method performs a graceful disconnection sequence:
        1. Send Release Request (RLRQ) if using Wrapper or encryption
        2. Send Disconnect Request (DISC) to close HDLC connection
        3. Close the physical media connection

        Errors during disconnection are silently ignored to ensure cleanup
        completes even if the meter is unresponsive.
        """
        if self.media and self.media.isOpen():
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

    def get_clock(self) -> datetime:
        """
        Read the current time from the meter's clock object.

        This is a convenience method that reads the standard clock object
        (OBIS 0.0.1.0.0.255) and returns the meter's current time.

        Returns:
            datetime: The meter's current date and time

        Raises:
            GXDLMSException: If reading the clock fails

        Example:
            >>> meter_time = app.get_clock()
            >>> print(f"Meter time: {meter_time}")
        """
        return self.get("0.0.1.0.0.255", 2)

    def set_clock(self, new_time: datetime) -> None:
        """
        Set the meter's clock to a specific date and time.

        This method writes to the standard clock object (OBIS 0.0.1.0.0.255).
        Requires appropriate authentication level (typically HIGH or above).

        Args:
            new_time: The datetime to set in the meter

        Raises:
            PermissionError: If authentication level is insufficient
            GXDLMSException: If setting the clock fails

        Example:
            >>> from datetime import datetime
            >>> app.set_clock(datetime.now())
        """
        self.set("0.0.1.0.0.255", new_time, 2)

    def get_serial_number(self) -> str:
        """
        Read the meter's serial number.

        Reads from the standard serial number object (OBIS 0.0.96.1.0.255).

        Returns:
            str: The meter's serial number

        Example:
            >>> serial = app.get_serial_number()
            >>> print(f"Serial: {serial}")
        """
        return self.get("0.0.96.1.0.255", 2)

    def get_active_energy_import(self) -> float:
        """
        Read the total active energy import register.

        Reads from the standard active energy import total register
        (OBIS 1.0.1.8.0.255).

        Returns:
            float: The total active energy imported in kWh (scaled)

        Example:
            >>> energy = app.get_active_energy_import()
            >>> print(f"Energy consumed: {energy} kWh")
        """
        return self.get("1.0.1.8.0.255", 2)

    def synchronize_clock(self) -> None:
        """
        Synchronize the meter's clock with the client system time.

        This method adjusts the meter's clock to match the current system time.
        It's equivalent to calling set_clock(datetime.now()).

        Raises:
            PermissionError: If authentication level is insufficient
            GXDLMSException: If synchronization fails

        Example:
            >>> app.synchronize_clock()
            >>> print("Meter clock synchronized")
        """
        from datetime import datetime

        self.set_clock(datetime.now())

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
        """
        Synchronizes the invocation counter (frame counter) with the DLMS meter.

        This method is critical for secure communication with DLMS meters that use
        encryption. The invocation counter is an anti-replay security mechanism that
        ensures each encrypted message has a unique, incrementally increasing counter.
        Before establishing a secure connection, the client must synchronize its
        invocation counter with the meter's current value to prevent replay attacks.

        The method performs a temporary unsecured connection to read the current
        invocation counter value from the meter, then updates the client's counter
        to match. This process uses Public Client (address 16) with no authentication
        to avoid the chicken-and-egg problem of needing a valid counter to establish
        a secure connection in the first place.

        The synchronization is only performed when:
        - An invocation counter OBIS code is configured
        - Ciphering is enabled
        - Security level is not NONE

        Raises:
            Exception: If the temporary connection fails or the counter cannot be read.
        """
        # Only synchronize if invocation counter is configured and security is enabled
        if (
            self.invocation_counter
            and self.client.ciphering is not None
            and self.client.ciphering.security != Security.NONE
        ):
            self._initialize_optical_link()
            # Enable general protection conformance for security operations
            self.client.proposedConformance |= Conformance.GENERAL_PROTECTION

            # Backup current connection parameters that will be temporarily changed
            add = self.client.clientAddress
            auth = self.client.authentication
            security = self.client.ciphering.security
            challenge = self.client.ctoSChallenge

            try:
                # Temporarily switch to Public Client (address 16) with no security.
                # This is necessary because we need to read the current invocation counter
                # from the meter, but we can't establish a secure connection without already
                # knowing the correct invocation counter value (chicken-and-egg problem).
                self.client.clientAddress = 16  # Public Client address
                self.client.authentication = Authentication.NONE
                self.client.ciphering.security = Security.NONE

                reply = GXReplyData()
                # SNRM (Set Normal Response Mode): Initialize HDLC layer connection
                data = self.client.snrmRequest()

                if data:
                    self._read_dlms_packet(data, reply)
                    # Parse UA (Unnumbered Acknowledgment) response to get HDLC parameters
                    self.client.parseUAResponse(reply.data)
                    # Resize reply buffer based on negotiated maximum frame size
                    size = self.client.hdlcSettings.maxInfoTX + 40
                    self.reply_buff = bytearray(size)

                reply.clear()
                # AARQ (Association Request): Establish application layer association
                self._read_data_block(self.client.aarqRequest(), reply)
                self.client.parseUAResponse(reply.data)
                reply.clear()

                # Read the current invocation counter value from the meter.
                # The invocation counter is stored as a DLMS Data object at the configured OBIS code.
                # Attribute index 2 contains the actual counter value.
                d = GXDLMSData(self.invocation_counter)
                self._read(d, 2)
                # Update client's invocation counter to meter's value + 1.
                # We add 1 because the next secure message we send must have a counter
                # higher than the meter's current value.
                self.client.ciphering.invocationCounter = 1 + d.value

                # Close the temporary unsecured connection
                self.disconnect()
            finally:
                # Always restore original connection parameters, even if an error occurred.
                # This ensures the client is configured correctly for the subsequent secure connection.
                self.client.clientAddress = add
                self.client.authentication = auth
                self.client.ciphering.security = security
                self.client.ctoSChallenge = challenge

    def _initialize_connection(self):
        """
        Establishes a complete DLMS connection with the meter, including all protocol layers.

        This method orchestrates the full connection establishment sequence for DLMS/COSEM
        communication. It handles both the physical/data link layer initialization (HDLC)
        and the application layer association (COSEM), with support for secure encrypted
        connections and various authentication levels.

        The connection process follows these phases:
        1. Security preparation: Synchronizes invocation counter if encryption is enabled
        2. Physical layer: Initializes optical link if required (Mode E)
        3. Data link layer: Establishes HDLC connection using SNRM/UA exchange
        4. Application layer: Creates COSEM association using AARQ/AARE exchange
        5. Authentication: Performs additional authentication challenge if required

        The method automatically adjusts the connection parameters based on the configured
        authentication level and security settings, supporting scenarios from unsecured
        public client access to fully encrypted and authenticated connections.

        Raises:
            GXDLMSException: If association is rejected or authentication fails.
            Exception: If any phase of the connection establishment fails.
        """
        # If security is enabled, print cryptographic parameters for debugging/auditing.
        # This helps verify that the correct keys and security settings are being used.
        if self.client.ciphering.security != Security.NONE:
            print("Security Suite: " + str(self.client.ciphering.securitySuite))
            print("Security: " + str(self.client.ciphering.security))
            print("System title: " + GXCommon.toHex(self.client.ciphering.systemTitle))
            print(
                "Authentication key: "
                + GXCommon.toHex(self.client.ciphering.authenticationKey)
            )
            print(
                "Block cipher key: "
                + GXCommon.toHex(self.client.ciphering.blockCipherKey)
            )
            if self.client.ciphering.dedicatedKey:
                print(
                    "Dedicated key: "
                    + GXCommon.toHex(self.client.ciphering.dedicatedKey)
                )

        # Phase 1: Synchronize invocation counter for encrypted communication.
        # Must be done before establishing the secure connection to avoid replay attacks.
        self._update_frame_counter()

        # Phase 2: Initialize optical link if using Mode E (IEC 62056-21).
        # This negotiates baud rate and configures the serial port for optical communication.
        self._initialize_optical_link()

        reply = GXReplyData()
        # Phase 3: HDLC Data Link Layer Initialization
        # SNRM (Set Normal Response Mode) establishes the HDLC connection and negotiates
        # parameters like maximum frame size, window size, etc.
        snrm = self.client.snrmRequest()

        if snrm:
            self._read_dlms_packet(snrm, reply)
            # UA (Unnumbered Acknowledgment) contains negotiated HDLC parameters
            self.client.parseUAResponse(reply.data)
            # Allocate reply buffer based on negotiated maximum transmission size.
            # Adding 40 bytes for protocol overhead (headers, checksums, etc.)
            size = self.client.hdlcSettings.maxInfoTX + 40
            self.replyBuff = bytearray(size)

        reply.clear()
        # Phase 4: COSEM Application Layer Association
        # AARQ (Association Request) initiates the application-level association.
        # This is where authentication type and conformance blocks are negotiated.
        self.readDataBlock(self.client.aarqRequest(), reply)
        # AARE (Association Response) contains the meter's response, including
        # accepted conformance, authentication result, and any error diagnostics.
        self.client.parseAareResponse(reply.data)
        reply.clear()

        # Phase 5: High-Level Authentication (if required)
        # For authentication levels above LOW (e.g., HIGH, HIGH_GMAC, HIGH_ECDSA),
        # an additional challenge-response authentication exchange is required.
        if self.client.authentication > Authentication.LOW:
            try:
                # Send authentication challenge and receive response.
                # This typically involves cryptographic operations to prove identity.
                for item in self.client.getApplicationAssociationRequest():
                    self._read_dlms_packet(item, reply)
                self.client.parseApplicationAssociationResponse(reply.data)
            except GXDLMSException:
                # If authentication fails, wrap the exception with proper diagnostic codes
                # to indicate permanent rejection due to authentication failure.
                raise GXDLMSException(
                    AssociationResult.PERMANENT_REJECTED,
                    SourceDiagnostic.AUTHENTICATION_FAILURE,
                )

    def _read(self, item, attribute_index):
        """
        Reads a single attribute from a DLMS object.

        This is the basic read operation for DLMS/COSEM objects. It generates a read
        request for a specific attribute of an object, sends it to the meter, receives
        the response, and updates the object with the returned value.

        Args:
            item: The DLMS object to read from (e.g., GXDLMSData, GXDLMSRegister).
            attribute_index (int): The attribute index to read (e.g., 2 for value).

        Returns:
            The updated value that was read from the meter.
        """
        # Generate DLMS read request packet for the specific attribute
        data = self.client.read(item, attribute_index)
        reply = GXReplyData()

        # Send request and receive response (handles multi-frame if needed)
        self._read_data_block(data, reply)
        # If data type is unknown (NONE), infer it from the response.
        # This is useful for dynamic object discovery where types aren't known beforehand.
        if item.getDataType(attribute_index) == DataType.NONE:
            item.setDataType(attribute_index, reply.valueType)

        # Parse the response data and update the object's attribute value
        return self.client.updateValue(item, attribute_index, reply.data)

    def _read_list(self, _list):
        """
        Reads multiple attributes from multiple objects in a single operation.

        This method uses the DLMS "Read Multiple" service to efficiently read several
        attributes in one request-response cycle, reducing communication overhead compared
        to individual reads. This requires the meter to support MULTIPLE_REFERENCES
        conformance.

        Args:
            _list (list): List of tuples (object, attribute_index) to read.
                Example: [(register1, 2), (register2, 2), (data1, 2)]

        Raises:
            ValueError: If the number of returned values doesn't match the request count.
        """
        # Generate read request for multiple items (single DLMS packet or sequence)
        data = self.client.readList(_list)
        reply = GXReplyData()
        values = list()

        # Process each packet in the response sequence
        for item in data:
            self._read_data_block(item, reply)
            # Accumulate all returned values from the response
            if reply.value:
                values.extend(reply.value)

            # Clear reply for next iteration to prevent data mixing
            reply.clear()

        # Validate that we received exactly as many values as requested.
        # Mismatch indicates protocol error or incomplete response.
        if len(values) != len(_list):
            raise ValueError("Invalid Reply: Read items count mismatch.")

        # Update all objects with their corresponding values
        self.client.updateValue(_list, values)

    def _write(self, item, attribute_index):
        """
        Writes a value to a single attribute of a DLMS object.

        This is the basic write operation for DLMS/COSEM objects. It generates a write
        request with the object's current value and sends it to the meter. The object's
        value must be set before calling this method.

        Args:
            item: The DLMS object to write to (e.g., GXDLMSData, GXDLMSRegister).
            attribute_index (int): The attribute index to write (typically 2 for value).
        """
        # Generate DLMS write request packet with the object's current value
        data = self.client.write(item, attribute_index)
        # Send write request. Write operations typically don't return data,
        # only acknowledgment of success/failure.
        self._read_dlms_packet(data)

    def _read_rows_by_entry(self, pg, index: int, count: int):
        """
        Reads rows from a profile generic (load profile) by entry index.

        Profile Generic objects store time-series data (like load profiles, event logs).
        This method retrieves a specific range of entries by their sequential index number.
        Entry 1 is the oldest entry, and the highest index is the most recent.

        Args:
            pg: The Profile Generic object to read from.
            index (int): Starting entry index (1-based).
            count (int): Number of entries to read.

        Returns:
            The profile data buffer containing the requested entries.
        """
        if not pg:
            raise ValueError("Profile Generic object is required.")
        if index <= 0:
            raise ValueError("Starting entry index must be greater than 0.")
        if count <= 0:
            raise ValueError("Number of entries to read must be greater than 0.")

        # Generate request to read entries by index range
        data = self.client.readRowsByEntry(pg, index, count)
        reply = GXReplyData()
        self._read_data_block(data, reply)
        # Update the profile generic's buffer (attribute 2) with the returned entries
        return self.client.updateValue(pg, 2, reply.value)

    def _read_rows_by_range(self, pg, start: datetime, end: datetime):
        """
        Reads rows from a profile generic (load profile) by time range.

        This method retrieves entries from a profile based on timestamp range rather than
        entry index. This is useful for reading data within a specific time period
        (e.g., "all data from yesterday").

        Args:
            pg: The Profile Generic object to read from.
            start (datetime): Start timestamp of the range.
            end (datetime): End timestamp of the range.

        Returns:
            The profile data buffer containing entries within the time range.
        """
        if not pg:
            raise ValueError("Profile Generic object is required.")
        if start is None or end is None:
            raise ValueError("Start and end timestamps are required.")
        if start > end:
            raise ValueError("Start timestamp must be before end timestamp.")

        reply = GXReplyData()
        # Generate request to read entries by timestamp range
        data = self.client.readRowsByRange(pg, start, end)
        self._read_data_block(data, reply)
        # Update the profile generic's buffer (attribute 2) with the returned entries
        return self.client.updateValue(pg, 2, reply.value)

    def _read_by_access(self, list_):
        """
        Reads multiple attributes using the DLMS Access service.

        The Access service is a more advanced method for reading multiple attributes that
        provides better control and error handling compared to Read Multiple. Each item
        can specify different access types (GET, SET, ACTION). Requires the meter to
        support ACCESS conformance.

        This method is typically used as a fallback or for advanced scenarios where
        Read Multiple is not available or doesn't meet the requirements.

        Args:
            list_ (list): List of GXDLMSAccessItem objects specifying what to read.
                Each item contains: access type, object, and attribute index.
        """
        if list_:
            reply = GXReplyData()
            # Generate access request with the list of items.
            # First parameter (None) is for data to write; we're only reading here.
            data = self.client.accessRequest(None, list_)
            self._read_data_block(data, reply)
            # Parse access response and update each object with its returned value.
            # This handles per-item success/error status from the meter.
            self.client.parseAccessResponse(list_, reply.data)

    def _read_scaler_and_units(self):
        """
        Reads scaler and unit information for all register objects from the meter.

        This method retrieves the scaler (scale factor) and unit of measurement for all
        register-type objects (Register, Extended Register, and Demand Register) discovered
        in the meter. Scalers and units are essential for correctly interpreting raw values
        from registers (e.g., converting 12345 with scaler -2 to 123.45 kWh).

        The method implements a cascading fallback strategy to maximize compatibility:
        1. Try Access service (most efficient, best error handling)
        2. If Access fails, try Multiple References (efficient batch read)
        3. If Multiple References fails, fall back to individual reads (slowest but universal)

        This automatic fallback ensures the method works with meters of varying capabilities,
        from modern meters with full conformance support to legacy meters with limited features.

        Attribute indices read:
        - Register/ExtendedRegister: Attribute 3 (scaler_unit)
        - DemandRegister: Attribute 4 (scaler_unit for demand registers)

        The method silently handles failures, printing warnings but not raising exceptions,
        to allow partial success when some registers are inaccessible.
        """
        # Get all register-type objects from the client's object list.
        # These are objects that store measured values with associated scalers and units.
        objs = self.client.objects.getObjects(
            [
                ObjectType.REGISTER,
                ObjectType.EXTENDED_REGISTER,
                ObjectType.DEMAND_REGISTER,
            ]
        )

        _list = list()

        # Strategy 1: Try Access service (preferred method)
        # Access service provides the best error handling and flexibility.
        try:
            # Check if meter supports Access service via negotiated conformance
            if self.client.negotiatedConformance & Conformance.ACCESS != 0:
                for item in objs:
                    # Regular and Extended Registers store scaler_unit in attribute 3
                    if isinstance(item, (GXDLMSRegister, GXDLMSExtendedRegister)):
                        if item.canRead(3):  # Verify read permissions
                            _list.append(
                                GXDLMSAccessItem(AccessServiceCommandType.GET, item, 3)
                            )
                    # Demand Registers store scaler_unit in attribute 4
                    elif isinstance(item, (GXDLMSDemandRegister)):
                        if item.canRead(4):  # Verify read permissions
                            _list.append(
                                GXDLMSAccessItem(AccessServiceCommandType.GET, item, 4)
                            )

                self._read_by_access(_list)
        except Exception:
            # Access service failed. This is not critical; we'll try other methods.
            print("Failed to read scaler and units with access service.")

        # Strategy 2: Try Multiple References (fallback method)
        # Multiple References allows batch reading but with less granular error handling.
        try:
            # Check if meter supports Multiple References via negotiated conformance
            if self.client.negotiatedConformance & Conformance.MULTIPLE_REFERENCES != 0:
                for item in objs:
                    # Regular and Extended Registers: attribute 3
                    if isinstance(item, (GXDLMSRegister, GXDLMSExtendedRegister)):
                        if item.canRead(3):
                            _list.append((item, 3))
                    # Demand Registers: attribute 4
                    elif isinstance(item, (GXDLMSDemandRegister,)):
                        if item.canRead(4):
                            _list.append((item, 4))

                self._read_list(_list)
        except Exception:
            # Multiple References failed. Disable this conformance flag to prevent
            # future attempts and force fallback to individual reads.
            self.client.negotiatedConformance &= ~Conformance.MULTIPLE_REFERENCES

        # Strategy 3: Individual reads (last resort fallback)
        # This is the slowest method but guaranteed to work on all meters.
        # Only executed if Multiple References is not supported or has failed.
        if self.client.negotiatedConformance & Conformance.MULTIPLE_REFERENCES == 0:
            for item in objs:
                try:
                    # Read each register's scaler_unit individually
                    if isinstance(item, (GXDLMSRegister,)):
                        if item.canRead(3):
                            self._read(item, 3)
                    elif isinstance(item, (GXDLMSDemandRegister,)):
                        if item.canRead(4):
                            self._read(item, 4)
                except Exception:
                    # Silently ignore individual read failures. Some registers may be
                    # inaccessible due to permissions or meter state, but we want to
                    # read as many as possible.
                    pass

    def _get_profile_generic_cols(self):
        """
        Reads capture object definitions from all profile generic objects.

        Profile Generic objects store time-series data. Attribute 3 contains the capture
        objects list, which defines what data is stored in each column of the profile
        (e.g., timestamp, voltage, current). This metadata is required to correctly
        interpret the profile data rows.

        The method silently handles read failures to allow partial success when some
        profiles are inaccessible.
        """
        # Retrieve all Profile Generic objects from the meter's object list
        profile_generics = self.client.objects.getObjects(ObjectType.PROFILE_GENERIC)

        for pg in profile_generics:
            try:
                # Attribute 3 contains the capture_objects list (column definitions)
                if pg.canRead(3):
                    self._read(pg, 3)
            except Exception as e:
                print(f"Error reading profile generic: {e}")

    def _get_read_out(self):
        """
        Reads all readable attributes from all objects in the meter's object list.

        This method performs a comprehensive read-out of the meter, retrieving values
        from all accessible attributes of all DLMS objects (excluding Profile Generic
        objects, which are handled separately). It automatically identifies which
        attributes need to be read and displays their values.

        Errors are caught per attribute to allow continuing with remaining attributes
        even if some fail.
        """
        for item in self.client.objects:
            # Skip base GXDLMSObject instances (abstract, no readable attributes)
            if type(item) is GXDLMSObject:
                continue
            # Skip Profile Generic objects (handled separately by _get_profile_generic_data)
            elif isinstance(item, GXDLMSProfileGeneric):
                continue

            # Get list of attribute indices that should be read for this object type
            for pos in item.getAttributeIndexToRead(True):
                try:
                    if item.canRead(pos):
                        val = self._read(item, pos)
                        self._show_value(pos, val)
                    else:
                        print("Cannot read attribute")
                except Exception as e:
                    print("Error! Index: " + str(pos) + " " + str(e))

    def _show_value(self, pos, val):
        """
        Formats and displays an attribute value in a human-readable format.

        Args:
            pos (int): The attribute index being displayed.
            val: The value to display. Can be of any type (bytes, list, scalar, etc.).

        Returns:
            The formatted value (modified for display purposes).
        """
        # Convert binary data to hex representation for readability
        if isinstance(val, (bytes, bytearray)):
            val = GXByteBuffer(val)
        # Format lists as comma-separated values, with hex encoding for binary items
        elif isinstance(val, list):
            _str = ""

            for item in val:
                if _str:
                    _str += ", "

                if isinstance(item, bytes):
                    _str += GXByteBuffer.hex(item)
                else:
                    _str += str(item)

            val = _str

        print(f"Attribute {pos}: {val}")
        return val

    def _get_profile_generic_data(self):
        """
        Reads and displays time-series data from all profile generic objects.

        Profile Generic objects store load profiles, event logs, and other time-series
        data. This method retrieves today's data from each profile and displays it in
        a tabular format. It first checks how many entries are available, then attempts
        to read the data using time range filtering.

        Returns:
            list: The last successfully read profile data (cells from last profile).
        """
        cells = []
        profile_generics = self.client.objects.getObjects(ObjectType.PROFILE_GENERIC)

        for pg in profile_generics:
            # Attribute 7: entries_in_use (current number of stored entries)
            entries_in_use = self._read(pg, 7)
            # Attribute 8: profile_entries (maximum capacity)
            entires = self._read(pg, 8)

            print(f"Entires: {entries_in_use} / {entires}")

            # Skip empty profiles or profiles without capture object definitions
            if entries_in_use == 0 or not pg.captureObjects:
                continue

            # Test read first entry to verify profile is accessible
            try:
                _ = self._read_rows_by_entry(pg, 1, 1)
            except Exception:
                print("Error reading profile generic first entry")

            # Read today's data using time range (00:00:00 to 23:59:59)
            try:
                start = datetime.now()
                end = start

                # Set time range to cover entire current day
                start = start.replace(hour=0, minute=0, second=0, microsecond=0)
                end = end.replace(hour=23, minute=59, second=59, microsecond=999999)

                cells = self._read_rows_by_range(pg, start, end)

                # Display each row in pipe-separated format
                for rows in cells:
                    row = ""
                    for cell in rows:
                        if row:
                            row += " | "
                        # Convert binary data to hex for display
                        if isinstance(cell, bytearray):
                            row += GXByteBuffer.hex(cell)
                        else:
                            row += str(cell)
                    print(row)

            except Exception:
                print("Error reading profile generic data")

        return cells

    def _get_association_view(self):
        """
        Retrieves the association view (object list) from the meter.

        The association view is a comprehensive list of all DLMS objects available in
        the meter, including their OBIS codes, object types, and access rights. This
        information is essential for discovering what data and functionality the meter
        provides.

        For Short Name (SN) referencing meters, this method also attempts to read
        extended access rights information if available.
        """
        reply = GXReplyData()
        # Request the object list from the association object
        self._read_data_block(self.client.getObjectsRequest(), reply)
        # Parse the object list and populate the client's object collection
        self.client.parseObjects(reply.data, True, False)

        # For Short Name referencing, attempt to read detailed access rights
        if not self.client.useLogicalNameReferencing:
            # 0xFA00 is the standard SN for the association object
            sn = self.client.objects.findBySN(0xFA00)

            if sn and sn.version > 0:
                try:
                    # Attribute 3 contains extended access rights information
                    self._read(sn, 3)
                except Exception:
                    print("Access rights not implemented for the meter.")

    def _generate_certificates(self, logical_name: str):
        """
        Generates and exchanges security certificates with the meter for encrypted communication.

        This method implements the complete certificate management workflow for DLMS meters
        using ECDSA public key cryptography. It generates client and server certificates,
        exchanges them with the meter, and verifies the import/export operations.

        The process includes:
        1. Generate client key pair and certificate signing request
        2. Request meter to generate its own key pairs
        3. Obtain signed certificates from certificate authority
        4. Import certificates into meter
        5. Export and verify all certificates

        Args:
            logical_name (str): OBIS code of the Security Setup object (e.g., "0.0.43.0.0.255").

        Raises:
            Exception: If authentication level is insufficient or certificate operations fail.
        """
        certificates = []

        if not os.path.exists("Keys"):
            os.mkdir("Keys")
        if not os.path.exists("Certificates"):
            os.mkdir("Certificates")
        if not os.path.exists("Keys384"):
            os.mkdir("Keys384")
        if not os.path.exists("Certificates384"):
            os.mkdir("Certificates384")

        # Certificate operations require high-level authentication to prevent unauthorized changes
        if self.client.authentication == Authentication.NONE:
            raise Exception(
                "High Authentication level required to change certificate keys"
            )

        reply = GXReplyData()
        self._initialize_connection()
        # Security Setup object manages certificates and cryptographic keys
        security_setup = GXDLMSSecuritySetup(logical_name)

        certifications = []

        # Read security attributes: security policy, security suite, and certificates
        self._read(security_setup, 3)
        self._read(security_setup, 4)
        self._read(security_setup, 5)

        client_system_title = security_setup.clientSystemTitle

        # Validate client system title (must be 8 bytes). Use cipher system title as fallback.
        if len(client_system_title) != 8:
            client_system_title = self.client.ciphering.systemTitle

        # Step 1: Generate client-side key pair and certificate signing request
        subject = GXAsn1Converter.systemTitleToSubject(client_system_title)
        key_pair = GXEcdsa.generateKeyPair(Ecc.P256)
        key = GXPkcs8(key_pair)
        # Save private key to file for future use
        key.save(
            GXPkcs8.getFilePath(
                Ecc.P256, CertificateType.DIGITAL_SIGNATURE, client_system_title
            )
        )

        # Create PKCS#10 certificate signing request for digital signature certificate
        pkc10 = GXPkcs10.createCertificateSigningRequest(key_pair, subject)
        certifications.append(
            GXCertificateRequest(CertificateType.DIGITAL_SIGNATURE, pkc10)
        )

        # Step 2: Request meter to generate its digital signature key pair
        if not self._read_data_block(
            security_setup.generateKeyPair(
                self.client, CertificateType.DIGITAL_SIGNATURE
            ),
            reply,
        ):
            raise GXDLMSException(reply.error)
        reply.clear()

        # Step 3: Request meter to generate certificate signing request for digital signature
        if not self._read_data_block(
            security_setup.generateCertificate(
                self.client, CertificateType.DIGITAL_SIGNATURE
            ),
            reply,
        ):
            raise GXDLMSException(reply.error)

        # Parse meter's certificate request and validate system title
        pkc10 = GXPkcs10(reply.value)
        subject = GXAsn1Converter.systemTitleToSubject(security_setup.serverSystemTitle)

        # Verify that the meter's certificate request contains the correct system title
        if pkc10.subject.find(subject) == -1:
            raise Exception(
                "Server System Title "
                + GXCommon.toHex(security_setup.serverSystemTitle)
                + " is not the same as in the generated certificate request: "
                + GXAsn1Converter.hexSystemTitleFromSubject(pkc10.subject)
                + "."
            )

        certifications.append(
            GXCertificateRequest(CertificateType.DIGITAL_SIGNATURE, pkc10)
        )
        reply.clear()

        # Step 4: Request meter to generate certificate signing request for key agreement
        if not self._read_data_block(
            security_setup.generateCertificate(
                self.client, CertificateType.KEY_AGREEMENT
            ),
            reply,
        ):
            raise GXDLMSException(reply.error)

        # Parse and validate key agreement certificate request
        pkc10 = GXPkcs10(reply.value)

        if pkc10.subject.find(subject) == -1:
            raise Exception(
                "Server system title "
                + GXDLMSTranslator.toHex(security_setup.serverSystemTitle)
                + " is not the same as in the generated certificate request "
                + GXAsn1Converter.hexSystemTitleFromSubject(pkc10.subject)
                + ".",
            )

        certifications.append(
            GXCertificateRequest(CertificateType.KEY_AGREEMENT, pkc10)
        )
        reply.clear()

        # Step 5: Send all certificate requests to CA and obtain signed certificates
        address = "https://certificates.gurux.fi/api/CertificateGenerator"
        certificates = GXPkcs10.getCertificate(address, certifications)

        # Step 6: Import all signed certificates into the meter
        for cert in certificates:
            if not self._read_data_block(
                security_setup.importCertificate(self.client, cert), reply
            ):
                raise GXDLMSException(reply.error)

            reply.clear()

        # Step 7: Export certificates by entity (client/server) and verify they match
        for cert in certificates:
            # Determine if this certificate belongs to server or client based on system title
            if (
                cert.subject.find(
                    GXAsn1Converter.systemTitleToSubject(
                        security_setup.serverSystemTitle
                    )
                )
                != -1
            ):
                st = security_setup.serverSystemTitle
                entity = CertificateEntity.SERVER
            elif (
                cert.subject.find(
                    GXAsn1Converter.systemTitleToSubject(client_system_title)
                )
                != -1
            ):
                st = client_system_title
                entity = CertificateEntity.CLIENT
            else:
                continue

            # Export certificate from meter and verify it matches the imported one
            if not self._read_data_block(
                security_setup.exportCertificateByEntity(
                    self.client,
                    entity,
                    GXDLMSConverter.keyUsageToCertificateType(cert.keyUsage),
                    st,
                ),
                reply,
            ):
                raise GXDLMSException(reply.error)

            exported_cert = GXx509Certificate(reply.value)

            if exported_cert != cert:
                raise Exception(
                    "Exported certificate does not match the generated certificate."
                )

            reply.clear()

        # Step 8: Export certificates by serial number and verify (alternative verification method)
        for cert in certificates:
            if not self._read_data_block(
                security_setup.exportCertificateBySerial(
                    self.client, cert.serialNumber, cert.issuerRaw
                ),
                reply,
            ):
                raise GXDLMSException(reply.error)

            exported = GXx509Certificate(reply.value)

            if exported != cert:
                raise Exception(
                    "Exported certificate does not match the generated certificate."
                )
            reply.clear()

    def _export_meter_certificates(self, logical_name: str):
        """
        Exports all certificates stored in the meter and saves them to files.

        This method reads the meter's certificate list and exports each certificate
        to the local filesystem for backup or inspection purposes. Certificates are
        saved using a standardized file naming convention based on their attributes.

        Args:
            logical_name (str): OBIS code of the Security Setup object (e.g., "0.0.43.0.0.255").

        Raises:
            GXDLMSException: If certificate export operations fail.
        """
        try:
            security_setup = GXDLMSSecuritySetup(logical_name)

            # Read certificate-related attributes from the Security Setup object
            self._read(security_setup, 3)

            if not os.path.exists("Keys"):
                os.mkdir("Keys")
            if not os.path.exists("Certificates"):
                os.mkdir("Certificates")
            if not os.path.exists("Keys384"):
                os.mkdir("Keys384")
            if not os.path.exists("Certificates384"):
                os.mkdir("Certificates384")

            self._read(security_setup, 4)
            self._read(security_setup, 5)

            reply = GXReplyData()

            # Export each certificate from the meter and save to file
            for item in security_setup.certificates:
                reply.clear()

                # Request certificate export using serial number and issuer as identifier
                if not self._read_data_block(
                    security_setup.exportCertificateBySerial(
                        self.client, item.serialNumber, item.issuerRaw
                    ),
                    reply,
                ):
                    raise GXDLMSException(reply.error)

                # Parse certificate and save to filesystem
                certificate = GXx509Certificate(reply.value)
                path = GXx509Certificate.getFilePath(certificate)
                certificate.save(path)
        finally:
            self.disconnect()

    def _read_all(self, output: str):
        """
        Performs a complete read-out of all meter data and optionally caches object definitions.

        This is the main orchestration method that coordinates a full meter read operation.
        It establishes the connection, discovers or loads the meter's object list, reads
        all object metadata (scalers, units, profile definitions), and retrieves all
        available data values.

        The method supports caching the object list to a file, which can significantly
        speed up subsequent reads by skipping the discovery phase. If a cache file exists,
        it loads the object definitions from there; otherwise, it performs full discovery.

        Args:
            output (str): File path for caching object definitions. If provided and exists,
                objects are loaded from cache. After reading, updated objects are saved
                back to this file.

        Raises:
            KeyboardInterrupt: User interruption is propagated after cleanup.
            SystemExit: System exit is propagated after cleanup.
        """
        try:
            read = False
            self._initialize_connection()

            # Attempt to load cached object definitions if available
            if output and os.path.exists(output):
                try:
                    content = GXDLMSObjectCollection.load(output)
                    self.client.objects.extend(content)

                    if self.client.objects:
                        read = True
                except Exception:
                    read = False

            # If cache not available or loading failed, perform full discovery
            if not read:
                self._get_association_view()
                self._read_scaler_and_units()
                self._get_profile_generic_cols()

            # Read all object values and profile data
            self._get_read_out()
            self._get_profile_generic_data()

            # Save updated object definitions to cache file
            if output:
                self.client.objects.save(output)
        except (KeyboardInterrupt, SystemExit):
            # Clean up media on user interruption before propagating exception
            self.media = None
            raise
        finally:
            self.disconnect()
