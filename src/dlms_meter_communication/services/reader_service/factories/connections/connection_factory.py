from abc import ABC, abstractmethod

from ...ports import IConnection
from dlms_meter_communication.schemas import CommunicationEndpoint


class ConnectionFactory(ABC):
    @abstractmethod
    def create_connection(self, endpoint: CommunicationEndpoint) -> IConnection:
        raise NotImplementedError
