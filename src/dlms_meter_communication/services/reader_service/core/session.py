from ..ports import IAppLayer, ILinkLayer, IConnection, IFrameCodec, IAddressResolver

from dlms_meter_communication.schemas.device import Device
from datetime import datetime


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

    def get_profile_by_date_range(
        self, obis: str, start_date: datetime, end_date: datetime
    ) -> list:
        """
        Extrae las lecturas de un perfil genérico por rango de fechas.

        Args:
            obis: Código OBIS del perfil genérico
            start_date: Fecha y hora de inicio del rango
            end_date: Fecha y hora de fin del rango

        Returns:
            list: Lista de filas del perfil dentro del rango especificado
        """
        return self.app_layer.get_profile_by_date_range(obis, start_date, end_date)

    def close(self):
        self.app_layer.disconnect()
