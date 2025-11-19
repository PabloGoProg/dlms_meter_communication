"""
Communication endpoint seeder for creating device connection configurations.
"""

from sqlmodel import Session
from dlms_meter_communication.models import CommunicationEndpoint, Device
from dlms_meter_communication.models.enums import Medium, Profile


class CommunicationEndpointSeeder:
    """Seeds communication endpoint records with various connection types."""

    @staticmethod
    def seed(session: Session, devices: list[Device]) -> list[CommunicationEndpoint]:
        """
        Creates sample communication endpoint records for devices.

        Args:
            session: SQLModel session for database operations.
            devices: List of device instances to create endpoints for.

        Returns:
            list[CommunicationEndpoint]: List of created endpoint instances.
        """
        endpoints = [
            # Main Building Meter - TCP with WRAPPER profile (primary)
            CommunicationEndpoint(
                device_id=devices[0].id,
                medium=Medium.TCP,
                profile=Profile.WRAPPER,
                ip="172.31.46.196",
                port=4058,
                is_primary=True,
            ),
            CommunicationEndpoint(
                device_id=devices[1].id,
                medium=Medium.TCP,
                profile=Profile.WRAPPER,
                ip="127.0.0.1",
                port=4061,
                is_primary=True,
            ),
            CommunicationEndpoint(
                device_id=devices[2].id,
                medium=Medium.TCP,
                profile=Profile.WRAPPER,
                ip="10.18.132.218",
                port=5000,
                is_primary=True,
            ),
        ]

        # Add all endpoints to session
        for endpoint in endpoints:
            session.add(endpoint)

        session.flush()

        # Refresh to get generated IDs
        for endpoint in endpoints:
            session.refresh(endpoint)

        return endpoints
