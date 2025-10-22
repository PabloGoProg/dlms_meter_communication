from dlms_meter_communication.services.dlms_client_service.utils.enums import (
    CommunicationProfileType,
    ConnectionProviderType,
    ConnectionMediaType,
)
from .dlms_client import DLMSClient

client = DLMSClient(
    ip_address="172.31.32.1",
    port=4058,
    communication_profile=CommunicationProfileType.WRAPPER_PROFILE,
    connection_provider=ConnectionProviderType.SOCKET,
    connection_media=ConnectionMediaType.TCP,
)
