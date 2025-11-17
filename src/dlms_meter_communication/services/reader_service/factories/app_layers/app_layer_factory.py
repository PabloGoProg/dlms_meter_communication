from __future__ import annotations

from abc import ABC, abstractmethod

from ...ports import IAppLayer
from dlms_meter_communication.schemas import CommunicationEndpoint


class AppLayerFactory(ABC):
    @abstractmethod
    def create_app_layer(self, endpoint: CommunicationEndpoint) -> IAppLayer:
        raise NotImplementedError
