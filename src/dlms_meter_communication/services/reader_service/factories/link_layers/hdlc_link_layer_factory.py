"""
Factory for creating HDLC link layer instances.

This module provides a concrete implementation of the LinkLayerFactory
for creating HDLC (High-Level Data Link Control) link layers with the appropriate
frame codec and connection type (Serial or TCP).
"""

from __future__ import annotations

from .link_layer_factory import LinkLayerFactory
from ...factories.frame_codecs import HDLCFramerFactory
from ...factories.connections import SerialConnectionFactory, TCPConnectionFactory
from ...adapterss.link_layers.hdlc_link_layer import HDLCLinkLayer
from dlms_meter_communication.schemas import CommunicationEndpoint
from dlms_meter_communication.models.enums import Medium


class HDLCLinkLayerFactory(LinkLayerFactory):
    """
    Factory for creating HDLC link layer instances.

    This factory creates link layers configured for HDLC protocol communication,
    automatically selecting the appropriate connection type (Serial or TCP) based
    on the communication medium specified in the endpoint.
    """

    def create_link_layer(self, endpoint: CommunicationEndpoint) -> HDLCLinkLayer:
        """
        Create an HDLC link layer instance with the appropriate connection.

        Args:
            endpoint: Communication endpoint configuration containing medium type
                     (Serial or TCP) and connection parameters

        Returns:
            HDLCLinkLayer: Configured HDLC link layer with codec and connection
        """
        # Create HDLC frame codec
        codec_factory = HDLCFramerFactory()

        # Select connection factory based on communication medium
        conn_factory = (
            SerialConnectionFactory()
            if endpoint.medium == Medium.SERIAL
            else TCPConnectionFactory()
        )

        # Build and return HDLC link layer with codec and connection
        return HDLCLinkLayer(
            codec=codec_factory.create_frame_codec(endpoint),
            connection=conn_factory.create_connection(endpoint),
        )
