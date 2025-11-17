from __future__ import annotations

from .link_layer_factory import LinkLayerFactory
from ...factories.frame_codecs import WrapperFramerFactory
from ...factories.connections import SerialConnectionFactory, TCPConnectionFactory
from ...adapterss.link_layers.tcp_wrapper_link_layer import TCPWrapperLinkLayer
from dlms_meter_communication.schemas import CommunicationEndpoint
from dlms_meter_communication.models.enums import Medium


class TCPWrapperLinkLayerFactory(LinkLayerFactory):
    def create_link_layer(self, endpoint: CommunicationEndpoint) -> TCPWrapperLinkLayer:
        codec_factory = WrapperFramerFactory()

        conn_factory = (
            SerialConnectionFactory()
            if endpoint.medium == Medium.SERIAL
            else TCPConnectionFactory()
        )

        return TCPWrapperLinkLayer(
            codec=codec_factory.create_frame_codec(endpoint),
            connection=conn_factory.create_connection(endpoint),
        )
