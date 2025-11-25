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
