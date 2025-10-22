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

from gurux_dlms.enums import Authentication, InterfaceType
from gurux_dlms import GXDLMSClient, GXReplyData


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

        print(f"Communication profile: {self.communication_profile}")
        print(f"Connection provider: {self.connection_provider}")
        print(f"Connection media: {self.connection_media}")

        self.media: MediaLinkStrategy = None

    def connect(self) -> None:
        try:
            self._set_communication_profile()
            self.media.open()

            if self.communication_profile in (
                CommunicationProfileType.HDLC_SERIAL_PROFILE,
                CommunicationProfileType.HDLC_TUNNELING_PROFILE,
            ):
                snrm_req = self.snrmRequest()
                ua_raw: bytes = self.media.transact(snrm_req)
                ua_reply: GXReplyData = self._get_gxreply_from_bytes(ua_raw)
                self.parseSnrmResponse(ua_reply.data)

            aarq_req = self.aarqRequest()
            print(f"AARQ request: {aarq_req}")
            aarq_raw: bytes = self.media.transact(aarq_req[0])
            aarq_reply: GXReplyData = self._get_gxreply_from_bytes(aarq_raw)
            self.parseAarqResponse(aarq_reply.data)

        except Exception as e:
            raise ConnectionError(f"Failed to connect: {e}") from e

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
        # Common parameters for all strategies
        common_params = {
            "ip_address": self.ip_address,
            "port": self.port,
            "client_address": self.client_address,
            "server_address": self.server_address,
            "connection_provider_type": self.connection_provider,
            "connection_media_type": self.connection_media,
        }

        return config.strategy_class(**common_params)

    def _get_gxreply_from_bytes(self, raw_reply: bytes) -> GXReplyData:
        reply = GXReplyData()
        self.getData(reply.data, reply)
        return reply
