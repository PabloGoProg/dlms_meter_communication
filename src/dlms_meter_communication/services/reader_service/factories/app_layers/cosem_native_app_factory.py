from __future__ import annotations

from .app_layer_factory import AppLayerFactory
from ...factories.link_layers import TCPWrapperLinkLayerFactory, HDLCLinkLayerFactory
from ...adapterss.app_layers.cosem_app import COSEMApp
from dlms_meter_communication.schemas import CommunicationEndpoint
from dlms_meter_communication.models.enums import Profile


class COSEMNativeAppFactory(AppLayerFactory):
    def create_app_layer(self, endpoint: CommunicationEndpoint) -> COSEMApp:
        link_layer_factory = (
            TCPWrapperLinkLayerFactory()
            if endpoint.profile == Profile.WRAPPER
            else HDLCLinkLayerFactory()
        )

        return COSEMApp(link_layer_factory.create_link_layer(endpoint))
