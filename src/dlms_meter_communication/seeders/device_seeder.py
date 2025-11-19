"""
Device seeder for populating test/demo devices in the database.
"""

from sqlmodel import Session
from dlms_meter_communication.models import Device


class DeviceSeeder:
    """Seeds device records with realistic meter data."""

    @staticmethod
    def seed(session: Session) -> list[Device]:
        """
        Creates sample device records in the database.

        Args:
            session: SQLModel session for database operations.

        Returns:
            list[Device]: List of created device instances.
        """
        devices = [
            Device(
                name="UCS Simmulated Meter",
                description="UCS Simmulated Meter for testing and development",
                serial_number="UCS-SIM-001",
                brand="UCS",
                model="E650",
            ),
            Device(
                name="Gurux .Net Simmulated Meter",
                description="Gurux .Net Simmulated Meter for testing and development",
                serial_number="GURUX-NET-SIM-001",
                brand="Gurux",
                model="E650",
            ),
            Device(
                name="CHEC CUBO Meter",
                description="CHEC CUBO Meter for testing real life communication",
                serial_number="CHEC-CUBO-001",
                brand="CHEC",
                model="CUBO",
            ),
        ]

        # Add all devices to session
        for device in devices:
            session.add(device)

        session.flush()

        # Refresh to get generated IDs
        for device in devices:
            session.refresh(device)

        return devices
