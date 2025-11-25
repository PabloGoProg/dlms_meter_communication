"""
Factory for creating native COSEM application layer instances.

This module provides a concrete implementation of the AppLayerFactory
for creating native COSEM application layers with the appropriate link layer
(Wrapper or HDLC) based on the communication profile.
"""

from __future__ import annotations

from .app_layer_factory import AppLayerFactory
from ...factories.link_layers import TCPWrapperLinkLayerFactory, HDLCLinkLayerFactory
from ...adapterss.app_layers.cosem_app import COSEMApp
from dlms_meter_communication.schemas import CommunicationEndpoint
from dlms_meter_communication.models.enums import Profile


class COSEMNativeAppFactory(AppLayerFactory):
    """
    Factory for creating native COSEM application layer instances.

    This factory creates COSEM application layers using the native implementation,
    automatically selecting the appropriate link layer (Wrapper for TCP or HDLC
    for serial) based on the communication profile.
    """

    def create_app_layer(self, endpoint: CommunicationEndpoint) -> COSEMApp:
        """
        Create a native COSEM application layer instance.

        Args:
            endpoint: Communication endpoint configuration containing the profile
                     type (Wrapper or HDLC)

        Returns:
            COSEMApp: Configured native COSEM application layer with the appropriate
                     link layer
        """
        # Select link layer factory based on communication profile
        link_layer_factory = (
            TCPWrapperLinkLayerFactory()
            if endpoint.profile == Profile.WRAPPER
            else HDLCLinkLayerFactory()
        )

        # Create and return COSEM app with the configured link layer
        return COSEMApp(link_layer_factory.create_link_layer(endpoint))
