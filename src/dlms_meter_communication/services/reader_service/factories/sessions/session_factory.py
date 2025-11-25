"""
Factory for creating communication session instances.

This module provides the factory for creating complete communication sessions
that include the device configuration and the appropriate application layer
based on the device's communication profile.
"""

from __future__ import annotations

from ...ports import IAppLayer
from ...utils.enums import AppLayerProviderType
from ..app_layers import COSEMNativeAppFactory, GuruxAppFactory
from ...core import Session

from dlms_meter_communication.db import get_session
from dlms_meter_communication.schemas import Device
from dlms_meter_communication.repositories import (
    CommunicationEndpointRepository,
)


class SessionFactory:
    """
    Factory for creating communication sessions.

    This factory builds complete communication sessions by:
    1. Retrieving the device's primary communication endpoint
    2. Selecting the appropriate application layer provider (COSEM Native or Gurux)
    3. Creating and configuring the session with the device and app layer
    """

    def build_session(self, device: Device) -> Session:
        """
        Build a complete communication session for the given device.

        This method retrieves the device's primary communication endpoint from
        the database and creates the appropriate application layer based on the
        endpoint's profile configuration (COSEM Native or Gurux COSEM).

        Args:
            device: Device schema containing device identification and configuration

        Returns:
            Session: Configured communication session ready for meter communication

        Raises:
            ValueError: If the endpoint profile is not supported (not COSEM_NATIVE
                       or GURUX_COSEM)
        """
        # Get database session and repository
        session = get_session()
        comm_endpoint_repo = CommunicationEndpointRepository(session=session)
        dv_primary_endpoint = comm_endpoint_repo.get_primary_by_device_id(device.id)

        cosem_app_layer: IAppLayer = None

        # Select and create the appropriate application layer based on profile
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

        # Create and return the session with device and app layer
        return Session(device, cosem_app_layer)
