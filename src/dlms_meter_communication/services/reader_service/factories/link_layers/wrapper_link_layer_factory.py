"""
Factory for creating TCP Wrapper link layer instances.

This module provides a concrete implementation of the LinkLayerFactory
for creating Wrapper protocol link layers with the appropriate frame codec
and connection type (Serial or TCP).
"""

from __future__ import annotations

from .link_layer_factory import LinkLayerFactory
from ...factories.frame_codecs import WrapperFramerFactory
from ...factories.connections import SerialConnectionFactory, TCPConnectionFactory
from ...adapterss.link_layers.tcp_wrapper_link_layer import TCPWrapperLinkLayer
from dlms_meter_communication.schemas import CommunicationEndpoint
from dlms_meter_communication.models.enums import Medium


class TCPWrapperLinkLayerFactory(LinkLayerFactory):
    """
    Factory for creating TCP Wrapper link layer instances.

    This factory creates link layers configured for Wrapper protocol communication,
    automatically selecting the appropriate connection type (Serial or TCP) based
    on the communication medium specified in the endpoint.
    """

    def create_link_layer(self, endpoint: CommunicationEndpoint) -> TCPWrapperLinkLayer:
        """
        Create a TCP Wrapper link layer instance with the appropriate connection.

        Args:
            endpoint: Communication endpoint configuration containing medium type
                     (Serial or TCP) and connection parameters

        Returns:
            TCPWrapperLinkLayer: Configured Wrapper link layer with codec and connection
        """
        # Create Wrapper frame codec
        codec_factory = WrapperFramerFactory()

        # Select connection factory based on communication medium
        conn_factory = (
            SerialConnectionFactory()
            if endpoint.medium == Medium.SERIAL
            else TCPConnectionFactory()
        )

        # Build and return Wrapper link layer with codec and connection
        return TCPWrapperLinkLayer(
            codec=codec_factory.create_frame_codec(endpoint),
            connection=conn_factory.create_connection(endpoint),
        )
