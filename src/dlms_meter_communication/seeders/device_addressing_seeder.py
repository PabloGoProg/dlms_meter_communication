"""
Device addressing seeder for creating DLMS addressing configurations.
"""

from sqlmodel import Session
from dlms_meter_communication.models import DeviceAddressing, Device


class DeviceAddressingSeeder:
    """Seeds device addressing records with DLMS client/server address pairs."""

    @staticmethod
    def seed(session: Session, devices: list[Device]) -> list[DeviceAddressing]:
        """
        Creates sample device addressing records for devices.

        Args:
            session: SQLModel session for database operations.
            endpoints: List of communication endpoint instances to create addressing for.

        Returns:
            list[DeviceAddressing]: List of created addressing instances.
        """
        addressing_records = [
            DeviceAddressing(
                device_id=devices[0].id,
                client_address=16,
                server_address=1,
                use_logical_name=True,
            ),
            DeviceAddressing(
                device_id=devices[1].id,
                client_address=18,
                server_address=1,
                use_logical_name=True,
                password="Gurux",
            ),
            DeviceAddressing(
                device_id=devices[2].id,
                client_address=32,
                server_address=1,
                use_logical_name=True,
                password="11111111",
            ),
        ]

        for addressing in addressing_records:
            session.add(addressing)

        session.flush()

        # Refresh to get generated IDs
        for addressing in addressing_records:
            session.refresh(addressing)

        return addressing_records
