from ...ports import IFrameCodec


class HDLCFrameCodec(IFrameCodec):
    def __init__(self):
        self.address = 0x81
        self.control = 0x10

    def encode(self, payload: bytes) -> bytes:
        pass

    def decode(self, buffer: bytes) -> tuple[bytes, bytes]:
        pass
