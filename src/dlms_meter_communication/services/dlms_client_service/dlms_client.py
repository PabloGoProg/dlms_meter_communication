from dataclasses import dataclass
from typing import Type, Tuple

from .media_links import (
    MediaLinkStrategy,
    WrapperProfileStrategy,
    HDLCProfileStrategy,
)
from .utils.enums import (
    CommunicationProfileType,
    ConnectionProviderType,
    ConnectionMediaType,
)

from gurux_dlms import GXDLMSClient, GXDLMSTranslator, GXReplyData, GXByteBuffer
from gurux_dlms.objects import GXDLMSObject
from gurux_dlms.enums import Authentication, ObjectType, InterfaceType


@dataclass(frozen=True)
class StrategyConfig:
    """Configuration for a communication strategy."""

    strategy_class: Type
    allowed_media: Tuple[ConnectionMediaType, ...]
    error_message: str


class DLMSClient(GXDLMSClient):
    def __init__(
        self,
        ip_address: str,
        port: int,
        client_address: int = 16,
        server_address: int = 1,
        authentication: Authentication = Authentication.NONE,
        meter_password: str = None,
        communication_profile: CommunicationProfileType = CommunicationProfileType.HDLC_TUNNELING_PROFILE,
        connection_provider: ConnectionProviderType = ConnectionProviderType.GURUX,
        connection_media: ConnectionMediaType = ConnectionMediaType.TCP,
        auto_detect_addresses: bool = False,
    ):
        super().__init__(
            useLogicalNameReferencing=True,
            clientAddress=client_address,
            serverAddress=server_address,
            forAuthentication=authentication,
            password=meter_password,
            interfaceType=InterfaceType.WRAPPER
            if communication_profile == CommunicationProfileType.WRAPPER_PROFILE
            else InterfaceType.HDLC,
        )

        self.ip_address = ip_address
        self.port = port
        self.client_address = client_address
        self.server_address = server_address
        self.authentication = authentication
        self.meter_password = meter_password
        self.communication_profile = communication_profile
        self.connection_provider = connection_provider
        self.connection_media = connection_media
        self.auto_detect_addresses = auto_detect_addresses

        self.media: MediaLinkStrategy = None
        self._translator = GXDLMSTranslator()

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
                self.media.open()
                aarq = self.aarqRequest()
                aare_raw: bytes = self.media.transact(aarq[0])
                aare_reply: GXReplyData = self._get_gxreply_from_bytes(aare_raw)
                self.parseAareResponse(aare_reply.data)

                print(f"✓ Connection successful with server_address={addr}")
                return True

            except Exception as e:
                print(f"✗ Connection failed with server_address={addr}: {e}")
                if self.media.is_open():
                    self.media.close()
                continue

        return False

    def connect(self) -> None:
        """
        Establish DLMS connection with automatic address detection if enabled
        """
        self._set_communication_profile()

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
            try:
                self.media.open()

                snrm = self.snrmRequest()
                if snrm:
                    self.media.transact(snrm)
                    print(f"SNRM: {snrm}")
                    ua_raw: bytes = self.media.transact(snrm)
                    print(f"UA: {ua_raw}")
                    self.parseUAResponse(ua_raw)
                    print(f"UA response: {ua_raw}")

                aarq = self.aarqRequest()
                print(f"AARQ request: {aarq[0]}")
                aare_raw: bytes = self.media.transact(aarq[0])
                print(f"AARE raw: {aare_raw}")
                aare_reply: GXReplyData = self._get_gxreply_from_bytes(aare_raw)
                print(f"AARE reply: {aare_reply}")
                self.parseAareResponse(aare_reply.data)
                print("DLMS connection established successfully")

            except Exception as e:
                print(f"Error establishing connection: {e}")
                raise

    def disconnect(self) -> None:
        """Safely close the DLMS connection"""
        try:
            if self.media.is_open():
                # Send DLMS disconnect message
                disconnect_request = self.disconnectRequest()
                if disconnect_request:
                    self.media.transact(disconnect_request)

                # Close the communication link
                self.media.close()
                print("DLMS connection closed successfully")
        except Exception as e:
            print(f"Error closing connection: {e}")
            # Force close the communication link
            if self.media.is_open():
                self.media.close()

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
            response_raw: bytes = self.media.transact(read_request[0])
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
            response_raw: bytes = self.media.transact(read_request[0])
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

    def _set_communication_profile(self) -> None:
        """Set the appropriate communication profile strategy based on configuration."""
        if self.media and self.media.is_open():
            self.media.close()

        strategy_config = self._get_strategy_config()
        self.media = self._create_strategy(strategy_config)

    def _get_strategy_config(self) -> StrategyConfig:
        """Get strategy configuration based on communication profile."""
        profile_configs = {
            CommunicationProfileType.WRAPPER_PROFILE: StrategyConfig(
                strategy_class=WrapperProfileStrategy,
                allowed_media=(ConnectionMediaType.TCP, ConnectionMediaType.UDP),
                error_message="Only TCP and UDP are supported for Wrapper Profile",
            ),
            CommunicationProfileType.HDLC_TUNNELING_PROFILE: StrategyConfig(
                strategy_class=HDLCProfileStrategy,
                allowed_media=(ConnectionMediaType.TCP, ConnectionMediaType.UDP),
                error_message="Only TCP and UDP are supported for HDLC Tunneling Profile",
            ),
            CommunicationProfileType.HDLC_SERIAL_PROFILE: StrategyConfig(
                strategy_class=HDLCProfileStrategy,
                allowed_media=(ConnectionMediaType.SERIAL,),
                error_message="Only SERIAL is supported for HDLC Serial Profile",
            ),
        }

        if self.communication_profile not in profile_configs:
            raise ValueError(
                f"Invalid communication profile: {self.communication_profile}"
            )

        config = profile_configs[self.communication_profile]

        if self.connection_media not in config.allowed_media:
            raise ValueError(
                f"Invalid connection media: {self.connection_media} for "
                f"{self.communication_profile.name.lower().replace('_', ' ')}: {config.error_message}"
            )

        return config

    def _create_strategy(self, config: StrategyConfig):
        """Create and return the appropriate strategy instance."""
        common_params = {
            "ip_address": self.ip_address,
            "port": self.port,
            "client_address": self.client_address,
            "server_address": self.server_address,
            "connection_media_type": self.connection_media,
            "connection_provider_type": self.connection_provider,
        }

        return config.strategy_class(**common_params)
