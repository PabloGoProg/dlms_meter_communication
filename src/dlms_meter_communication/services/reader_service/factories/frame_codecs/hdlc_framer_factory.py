from __future__ import annotations

from .frame_codec_factory import FrameCodecFactory
from ...adapterss.codecs.hdlc_frame_codec import HDLCFrameCodec
from dlms_meter_communication.schemas import CommunicationEndpoint


class HDLCFramerFactory(FrameCodecFactory):
    def create_frame_codec(self, endpoint: CommunicationEndpoint) -> HDLCFrameCodec:
        return HDLCFrameCodec()
