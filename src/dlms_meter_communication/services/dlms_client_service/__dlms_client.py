from gurux_dlms import GXDLMSClient, GXDLMSTranslator, GXReplyData, GXByteBuffer
from gurux_dlms.objects import GXDLMSObject
from gurux_dlms.enums import Authentication, ObjectType
from .media_links import (
    MediaLinkStrategy,
    HDLCProfileStrategy,
    WrapperProfileStrategy,
)
from .utils.enums import (
    CommunicationProfileType,
    ConnectionProviderType,
    ConnectionMediaType,
)


class DLMSClient(GXDLMSClient):
    """
    This class represents a DLMS/COSEM Clint which can handle comunications with COSEM servers.

    Args:
      ip_address: The IP address where the DLMS/COSEM server is located.
      port: The port where the DLMS/COSEM server is listening.
      client_address: The client address of the DLMS/COSEM server.
      server_address: The server address of the DLMS/COSEM server.
      authentication: The authentication of the DLMS/COSEM server.
      interface_type: The interface type of the DLMS/COSEM server.
      meter_password: The password of the DLMS/COSEM server.
    """

    def __init__(
        self,
        ip_address: str,
        port: int,
        client_address: int = 16,  # For most meters, the default client address is 16.
        server_address: int = 1,  # For most meters, the default server address is 1.
        authentication: Authentication = Authentication.NONE,
        meter_password: str = None,
        auto_detect_addresses: bool = True,  # Detectar direcciones automáticamente
        communication_profile_type: CommunicationProfileType = CommunicationProfileType.HDLC_TUNNELING_PROFILE,
    ) -> None:
        # Initialize the GXDLMSClient
        super().__init__(
            useLogicalNameReferencing=True,
            clientAddress=client_address,
            serverAddress=server_address,
            forAuthentication=authentication,
            password=meter_password,
        )
        self.ip_address = ip_address
        self.port = port
        self.client_address = client_address
        self.server_address = server_address
        self.authentication = authentication
        self.meter_password = meter_password
        self.auto_detect_addresses = auto_detect_addresses
        self.communication_profile_type = communication_profile_type

        self.media: MediaLinkStrategy = None
        self.translator = GXDLMSTranslator()

    def set_addresses(
        self, client_address: int = None, server_address: int = None
    ) -> None:
        """
        Set the addresses of the DLMS client and server

        Args:
          client_address: New client address (optional)
          server_address: New server address (optional)
        """
        if client_address is not None:
            self.clientAddress = client_address
            self.client_address = client_address
            print(f"Client address set to: {client_address}")

        if server_address is not None:
            self.serverAddress = server_address
            self.server_address = server_address
            print(f"Server address set to: {server_address}")

    def get_current_addresses(self) -> dict:
        """
        Get the current addresses of the DLMS client and server

        Returns:
          Dictionary with the current addresses
        """
        return {
            "client_address": self.client_address,
            "server_address": self.server_address,
            "client_address_internal": self.clientAddress,
            "server_address_internal": self.serverAddress,
        }

    def _get_gxreply_from_bytes(self, raw_reply: bytes) -> GXReplyData:
        parsed_reply = GXReplyData()
        parsed_reply.data = GXByteBuffer(raw_reply)
        print(f"Raw reply: {raw_reply}")
        print(f"Parsed reply: {parsed_reply}")
        return parsed_reply

    def try_connect_with_addresses(self, server_addresses: list) -> bool:
        """
        Try to connect with different server addresses

        Args:
          server_addresses: List of server addresses to try

        Returns:
          True if the connection was successful, False otherwise
        """
        for addr in server_addresses:
            try:
                print(f"Trying to connect with server_address={addr}")

                # Update the server address
                self.serverAddress = addr
                self.server_address = addr

                # Try to connect
                self.media_link.open()
                aarq = self.aarqRequest()
                aare_raw: bytes = self.media_link.transact(aarq[0])
                aare_reply: GXReplyData = self._get_gxreply_from_bytes(aare_raw)
                self.parseAareResponse(aare_reply.data)

                print(f"✓ Connection successful with server_address={addr}")
                return True

            except Exception as e:
                print(f"✗ Connection failed with server_address={addr}: {e}")
                if self.media_link.is_open():
                    self.media_link.close()
                continue

        return False

    def connect(self) -> None:
        """
        Establish DLMS connection with automatic address detection if enabled
        """
        if self.auto_detect_addresses:
            # Common addresses to try
            common_addresses = [
                1,  # Standard address
                129,  # 128 + 1 (logical + physical address)
                17,  # 16 + 1
                33,  # 32 + 1
                65,  # 64 + 1
                97,  # 96 + 1
                161,  # 160 + 1
            ]

            print("Detecting DLMS addresses automatically...")
            if self.try_connect_with_addresses(common_addresses):
                print("DLMS connection established successfully")
                return
            else:
                raise Exception(
                    "No connection could be established with any common address"
                )

        else:
            # Traditional connection with configured addresses
            try:
                self.media_link.open()
                aarq = self.aarqRequest()
                aare_raw: bytes = self.media_link.transact(aarq[0])
                aare_reply: GXReplyData = self._get_gxreply_from_bytes(aare_raw)
                self.parseAareResponse(aare_reply.data)
                print("DLMS connection established successfully")

            except Exception as e:
                print(f"Error establishing connection: {e}")
                self.media_link.close()
                raise

    def disconnect(self) -> None:
        """Safely close the DLMS connection"""
        try:
            if self.media_link.is_open():
                # Send DLMS disconnect message
                disconnect_request = self.disconnectRequest()
                if disconnect_request:
                    self.media_link.transact(disconnect_request)

                # Close the communication link
                self.media_link.close()
                print("DLMS connection closed successfully")
        except Exception as e:
            print(f"Error closing connection: {e}")
            # Force close the communication link
            if self.media_link.is_open():
                self.media_link.close()

    def read_cosem_object(self, obis_code: str, attribute_index: int = 2) -> any:
        """
        Read a COSEM object using its OBIS code

        Args:
          obis_code: OBIS code of the object (e.g: "1.0.1.8.0.255")
          attribute_index: Index of the attribute to read (default 2 = value)

        Returns:
          The value read from the COSEM object
        """
        try:
            # Create read request using the inherited method from GXDLMSClient
            obj = GXDLMSObject(ObjectType.DATA, obis_code)
            read_request = super().read(obj, attribute_index)

            # Send request and receive response
            response_raw: bytes = self.media_link.transact(read_request[0])
            response: GXReplyData = self._get_gxreply_from_bytes(response_raw)

            # Process response
            self.getData(response.data, response)

            return response.value

        except Exception as e:
            print(f"Error reading object {obis_code}: {e}")
            return None

    def read_object(
        self,
        obis_code: str,
        object_type: ObjectType = ObjectType.DATA,
        attribute_index: int = 2,
    ) -> any:
        """
        Read a specific COSEM object

        Args:
          obis_code: OBIS code of the object (e.g: "1.0.1.8.0.255")
          object_type: Type of the COSEM object
          attribute_index: Index of the attribute to read

        Returns:
          The value read from the COSEM object
        """
        try:
            # Create read request using the inherited method from GXDLMSClient
            obj = GXDLMSObject(object_type, obis_code)
            read_request = super().read(obj, attribute_index)
            print(f"Read request: {read_request}")

            # Send request
            response_raw: bytes = self.media_link.transact(read_request[0])
            response: GXReplyData = self._get_gxreply_from_bytes(response_raw)

            # Process response
            self.getData(response.data, response)

            return response.value

        except Exception as e:
            print(f"Error reading COSEM object {obis_code}: {e}")
            return None

    def get_objects(self) -> list:
        """
        Get the list of available COSEM objects in the meter

        Returns:
          List of available COSEM objects
        """
        try:
            # Read the list of objects (Association LN object: 0.0.40.0.0.255)
            objects_list = self.read_object(
                "0.0.40.0.0.255", ObjectType.ASSOCIATION_LOGICAL_NAME, 2
            )
            print(f"List of available COSEM objects: {objects_list}")
            return objects_list

        except Exception as e:
            print(f"Error getting list of objects: {e}")
            return []

    def read_energy_registers(self) -> dict:
        """
        Read the most common energy registers

        Returns:
          Dictionary with the energy values
        """
        energy_registers = {
            "active_energy_import": "1.0.1.8.0.255",  # Energía activa importada total
            "active_energy_export": "1.0.2.8.0.255",  # Energía activa exportada total
            "reactive_energy_import": "1.0.3.8.0.255",  # Energía reactiva importada total
            "reactive_energy_export": "1.0.4.8.0.255",  # Energía reactiva exportada total
        }

        results = {}
        for name, obis_code in energy_registers.items():
            value = self.read_object(obis_code)
            results[name] = value
            print(f"{name}: {value}")

        return results

    def read_instantaneous_values(self) -> dict:
        """
        Lee valores instantáneos del medidor

        Returns:
          Diccionario con valores instantáneos
        """
        instantaneous_registers = {
            "voltage_l1": "1.0.32.7.0.255",  # Voltage L1
            "voltage_l2": "1.0.52.7.0.255",  # Voltage L2
            "voltage_l3": "1.0.72.7.0.255",  # Voltage L3
            "current_l1": "1.0.31.7.0.255",  # Current L1
            "current_l2": "1.0.51.7.0.255",  # Current L2
            "current_l3": "1.0.71.7.0.255",  # Current L3
            "active_power": "1.0.1.7.0.255",  # Active power total
            "reactive_power": "1.0.3.7.0.255",  # Reactive power total
            "frequency": "1.0.14.7.0.255",  # Frequency
        }

        results = {}
        for name, obis_code in instantaneous_registers.items():
            value = self.read_object(obis_code, ObjectType.REGISTER, 2)
            results[name] = value
            print(f"{name}: {value}")

        return results

    def _set_communication_profile_strategy(self) -> None:
        if self.communication_profile_type == CommunicationProfileType.WRAPPER_PROFILE:
            self.media = WrapperProfileStrategy(
                ip_address=self.ip_address,
                port=self.port,
                client_address=self.client_address,
                server_address=self.server_address,
                connection_provider_type=ConnectionProviderType.GURUX,
                connection_media_type=ConnectionMediaType.TCP,
            )
        elif self.communication_profile_type == CommunicationProfileType.HDLC_PROFILE:
            self.media = HDLCProfileStrategy(
                ip_address=self.ip_address,
                port=self.port,
                client_address=self.client_address,
                server_address=self.server_address,
                connection_provider_type=ConnectionProviderType.GURUX,
                connection_media_type=ConnectionMediaType.TCP,
            )
        else:
            raise ValueError(
                f"Invalid communication profile type: {self.communication_profile_type}"
            )
