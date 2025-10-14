from .dlms_client import DLMSClient
from .utils.enums import (
    CommunicationProfileType,
    ConnectionProviderType,
    ConnectionMediaType,
)

client = DLMSClient(
    ip_address="192.168.1.100",
    port=4059,
    communication_profile=CommunicationProfileType.WRAPPER_PROFILE,
    connection_provider=ConnectionProviderType.GURUX,
    connection_media=ConnectionMediaType.TCP,
)

client.connect()
