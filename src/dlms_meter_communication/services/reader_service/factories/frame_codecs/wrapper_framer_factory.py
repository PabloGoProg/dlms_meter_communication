from __future__ import annotations

from .frame_codec_factory import FrameCodecFactory
from ...adapterss.codecs.wrapper_codec import WrapperCodec
from dlms_meter_communication.schemas import CommunicationEndpoint


class WrapperFramerFactory(FrameCodecFactory):
    def create_frame_codec(self, endpoint: CommunicationEndpoint) -> WrapperCodec:
        return WrapperCodec(
            source_wport=16,
            destination_wport=1,
        )
