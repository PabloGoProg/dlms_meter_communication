from dlms_meter_communication.services.dlms_client_service.utils.enums import (
    CommunicationProfileType,
    ConnectionProviderType,
    ConnectionMediaType,
)
from .dlms_client import DLMSClient

client = DLMSClient(
    ip_address="10.105.39.91",
    port=4060,
    communication_profile=CommunicationProfileType.HDLC_TUNNELING_PROFILE,
    connection_provider=ConnectionProviderType.SOCKET,
    connection_media=ConnectionMediaType.TCP,
)
