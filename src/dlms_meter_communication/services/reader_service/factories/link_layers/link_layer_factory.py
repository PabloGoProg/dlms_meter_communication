from __future__ import annotations
from abc import ABC, abstractmethod

from dlms_meter_communication.services.reader_service.ports import ILinkLayer
from dlms_meter_communication.schemas import CommunicationEndpoint


class LinkLayerFactory(ABC):
    @abstractmethod
    def create_link_layer(self, endpoint: CommunicationEndpoint) -> ILinkLayer:
        raise NotImplementedError
