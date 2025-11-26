from ..ports import IAppLayer, ILinkLayer, IConnection, IFrameCodec, IAddressResolver

from dlms_meter_communication.schemas.device import Device


class Session:
    def __init__(self, device: Device):
        self.device = device
        self.app_layer: IAppLayer = None
        self.link_layer: ILinkLayer = None
        self.connection: IConnection = None
        self.frame_codec: IFrameCodec = None
        self.address_resolver: IAddressResolver = None

    def open(self):
        self.app_layer.associate(self.device)

    def get(self, obis: str) -> bytes:
        self.app_layer.get(obis)

    def get_association_view(self) -> list[dict]:
        return self.app_layer.get_association_view()

    def close(self):
        self.app_layer.disconnect()
