from __future__ import annotations

from .link_layer_factory import LinkLayerFactory
from ...factories.frame_codecs import HDLCFramerFactory
from ...factories.connections import SerialConnectionFactory, TCPConnectionFactory
from ...adapterss.link_layers.hdlc_link_layer import HDLCLinkLayer
from dlms_meter_communication.schemas import CommunicationEndpoint
from dlms_meter_communication.models.enums import Medium


class HDLCLinkLayerFactory(LinkLayerFactory):
    def create_link_layer(self, endpoint: CommunicationEndpoint) -> HDLCLinkLayer:
        codec_factory = HDLCFramerFactory()

        conn_factory = (
            SerialConnectionFactory()
            if endpoint.medium == Medium.SERIAL
            else TCPConnectionFactory()
        )

        return HDLCLinkLayer(
            codec=codec_factory.create_frame_codec(endpoint),
            connection=conn_factory.create_connection(endpoint),
        )
