"""
Negotiated parameters seeder for creating DLMS connection parameters.
"""

from sqlmodel import Session
from ..models import NegotiatedParams, Device, CommunicationEndpoint


class NegotiatedParamsSeeder:
    """Seeds negotiated parameters with typical DLMS/HDLC values."""

    @staticmethod
    def seed(
        session: Session,
        devices: list[Device],
        endpoints: list[CommunicationEndpoint],
    ) -> list[NegotiatedParams]:
        """
        Creates sample negotiated parameters records for device-endpoint pairs.

        Args:
            session: SQLModel session for database operations.
            devices: List of device instances.
            endpoints: List of communication endpoint instances.

        Returns:
            list[NegotiatedParams]: List of created negotiated params instances.
        """
        negotiated_params = []

        # Create negotiated params for primary endpoints of each device
        # Group endpoints by device
        device_endpoints = {}
        for endpoint in endpoints:
            if endpoint.device_id not in device_endpoints:
                device_endpoints[endpoint.device_id] = []
            device_endpoints[endpoint.device_id].append(endpoint)

        # Create params for each device's primary endpoint
        for device in devices:
            if device.id in device_endpoints:
                # Get primary endpoint or first endpoint
                endpoint = next(
                    (ep for ep in device_endpoints[device.id] if ep.is_primary),
                    device_endpoints[device.id][0],
                )

                # Different parameter sets based on connection type and capabilities
                if endpoint.medium.value == "TCP":
                    # TCP connections typically support larger frame sizes
                    params = NegotiatedParams(
                        device_id=device.id,
                        endpoint_id=endpoint.id,
                        max_info_rx=2048,  # Max receive info field size (bytes)
                        max_info_tx=2048,  # Max transmit info field size (bytes)
                        win=1,  # Window size (typically 1 for DLMS)
                        max_pdu=65535,  # Maximum PDU size for TCP
                    )
                else:
                    # SERIAL connections use smaller frame sizes
                    params = NegotiatedParams(
                        device_id=device.id,
                        endpoint_id=endpoint.id,
                        max_info_rx=128,  # Smaller for serial
                        max_info_tx=128,
                        win=1,
                        max_pdu=512,  # Limited PDU for serial
                    )

                negotiated_params.append(params)
                session.add(params)

        session.commit()

        # Refresh to get generated IDs
        for params in negotiated_params:
            session.refresh(params)

        return negotiated_params
