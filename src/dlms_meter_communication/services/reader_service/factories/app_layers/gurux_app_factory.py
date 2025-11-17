from __future__ import annotations

from .app_layer_factory import AppLayerFactory
from ...adapterss.app_layers.gurux_cosem_app import GuruxCOSEMApp
from dlms_meter_communication.schemas import CommunicationEndpoint


class GuruxAppFactory(AppLayerFactory):
    def create_app_layer(self, endpoint: CommunicationEndpoint) -> GuruxCOSEMApp:
        return GuruxCOSEMApp(use_logical_name_referencing=True)
