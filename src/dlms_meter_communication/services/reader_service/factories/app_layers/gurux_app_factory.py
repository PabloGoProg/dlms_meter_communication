"""
Factory for creating Gurux COSEM application layer instances.

This module provides a concrete implementation of the AppLayerFactory
for creating Gurux-based COSEM application layers. Gurux is a third-party
library that provides comprehensive DLMS/COSEM protocol implementation.
"""

from __future__ import annotations

from .app_layer_factory import AppLayerFactory
from ...adapterss.app_layers.gurux_cosem_app import GuruxCOSEMApp

from dlms_meter_communication.models.enums import Profile
from dlms_meter_communication.schemas import Device
from dlms_meter_communication.db.database import get_context_session
from dlms_meter_communication.repositories import (
    CommunicationEndpointRepository,
    DeviceAddressingRepository,
)

from gurux_dlms.enums import InterfaceType, Authentication
from gurux_dlms.secure.GXDLMSSecureClient import GXDLMSSecureClient
from gurux_net import GXNet
from gurux_net.enums import NetworkType
from gurux_common.enums import TraceLevel


class GuruxAppFactory(AppLayerFactory):
    """
    Factory for creating Gurux COSEM application layer instances.

    This factory creates COSEM application layers using the Gurux DLMS library,
    which provides a robust implementation of the DLMS/COSEM protocol. It configures
    the Gurux client with the appropriate interface type, addressing, and authentication
    based on the device configuration stored in the database.
    """

    def create_app_layer(self, device: Device) -> GuruxCOSEMApp:
        """
        Create a Gurux COSEM application layer instance.

        This method:
        1. Retrieves the device's communication endpoint and addressing from the database
        2. Configures a Gurux DLMS client with the appropriate settings
        3. Creates a Gurux network media adapter for TCP communication
        4. Returns a configured GuruxCOSEMApp instance

        Args:
            device: Device configuration containing device identification

        Returns:
            GuruxCOSEMApp: Configured Gurux COSEM application layer with client
                          and media adapter

        Raises:
            Exception: If there's an error retrieving device configuration or
                      creating the Gurux components
        """
        with get_context_session() as session:
            try:
                # Get repositories for device configuration
                comm_endpoint_repo = CommunicationEndpointRepository(session=session)
                device_addressing_repo = DeviceAddressingRepository(session=session)

                # Retrieve device communication configuration
                primary_comm_endpoint = comm_endpoint_repo.get_primary_by_device_id(
                    device.id
                )
                addressings = device_addressing_repo.index_by_device_id(device.id)

                if len(addressings) == 0:
                    raise ValueError(f"No addressing found for device {device.id}")

                addressing = addressings[0]

                # Configure Gurux DLMS client with device settings
                gurux_client = GXDLMSSecureClient(
                    interfaceType=InterfaceType.HDLC
                    if primary_comm_endpoint.profile == Profile.WRAPPER
                    else InterfaceType.HDLC,
                    clientAddress=addressing.client_address,
                    serverAddress=addressing.server_address,
                    forAuthentication=Authentication.LOW,
                    password=addressing.password,
                    useLogicalNameReferencing=addressing.use_logical_name,
                )

                # Create Gurux network media for TCP communication
                gx_media = GXNet(
                    networkType=NetworkType.TCP,
                    name=primary_comm_endpoint.ip,
                    portNo=primary_comm_endpoint.port,
                )

                gx_media.open()

                # Return configured Gurux COSEM application layer
                # trace_level=OFF for production, invocation_counter starts at 0
                return GuruxCOSEMApp(
                    client=gurux_client,
                    media=gx_media,
                    trace_level=TraceLevel.VERBOSE,
                    invocation_counter=0,
                )
            except Exception as e:
                raise e
            finally:
                session.close()
