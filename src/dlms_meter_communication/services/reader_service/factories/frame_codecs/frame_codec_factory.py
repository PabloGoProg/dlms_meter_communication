from __future__ import annotations

from abc import ABC, abstractmethod

from ...ports import IFrameCodec
from dlms_meter_communication.schemas import CommunicationEndpoint


class FrameCodecFactory(ABC):
    @abstractmethod
    def create_frame_codec(self, endpoint: CommunicationEndpoint) -> IFrameCodec:
        raise NotImplementedError
