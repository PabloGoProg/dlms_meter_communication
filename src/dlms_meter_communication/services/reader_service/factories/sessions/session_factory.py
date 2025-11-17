from __future__ import annotations

from ...ports import IAppLayer, ILinkLayer, IConnection, IFrameCodec, IAddressResolver
from ...utils.enums import AppLayerProviderType
from ..app_layers import COSEMNativeAppFactory, GuruxAppFactory

from dlms_meter_communication.db import get_session
from dlms_meter_communication.schemas import Device
from dlms_meter_communication.repositories import (
    CommunicationEndpointRepository,
)


class Session:
    def __init__(self, device: Device):
        self.device = device
        self.app_layer: IAppLayer = None
        self.link_layer: ILinkLayer = None
        self.connection: IConnection = None
        self.frame_codec: IFrameCodec = None
        self.address_resolver: IAddressResolver = None


class SessionFactory:
    def build_session(self, device: Device) -> Session:
        session = get_session()
        comm_endpoint_repo = CommunicationEndpointRepository(session=session)
        dv_primary_endpoint = comm_endpoint_repo.get_primary_by_device_id(device.id)

        cosem_app_layer: IAppLayer = None

        if dv_primary_endpoint.profile == AppLayerProviderType.COSEM_NATIVE:
            cosem_app_layer = COSEMNativeAppFactory().create_app_layer(
                dv_primary_endpoint
            )
        elif dv_primary_endpoint.profile == AppLayerProviderType.GURUX_COSEM:
            cosem_app_layer = GuruxAppFactory().create_app_layer(dv_primary_endpoint)
        else:
            raise ValueError(
                f"Unsupported app layer provider type: {dv_primary_endpoint.profile}"
            )

        return Session(device, cosem_app_layer)
