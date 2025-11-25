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

from dlms_meter_communication.db.database import get_context_session
from dlms_meter_communication.repositories import (
    CommunicationEndpointRepository,
)
from dlms_meter_communication.schemas import Device
from dlms_meter_communication.models.enums import Profile


class COSEMNativeAppFactory(AppLayerFactory):
    """
    Factory for creating native COSEM application layer instances.

    This factory creates COSEM application layers using the native implementation,
    automatically selecting the appropriate link layer (Wrapper for TCP or HDLC
    for serial) based on the communication profile.
    """

    def create_app_layer(self, device: Device) -> COSEMApp:
        """
        Create a native COSEM application layer instance.

        Args:
            device: Device configuration containing the profile
                     type (Wrapper or HDLC)

        Returns:
            COSEMApp: Configured native COSEM application layer with the appropriate
                     link layer
        """
        # Select link layer factory based on communication profile
        with get_context_session() as session:
            try:
                comm_endpoint_repo = CommunicationEndpointRepository(session=session)
                dv_primary_endpoint = comm_endpoint_repo.get_primary_by_device_id(
                    device.id
                )

                link_layer_factory = (
                    TCPWrapperLinkLayerFactory()
                    if dv_primary_endpoint.profile == Profile.WRAPPER
                    else HDLCLinkLayerFactory()
                )

                # Create and return COSEM app with the configured link layer
                return COSEMApp(
                    link_layer_factory.create_link_layer(dv_primary_endpoint)
                )
            except Exception as e:
                raise e
            finally:
                session.close()
