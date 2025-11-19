"""
Device addressing seeder for creating DLMS addressing configurations.
"""

from sqlmodel import Session
from ..models import DeviceAddressing, CommunicationEndpoint


class DeviceAddressingSeeder:
    """Seeds device addressing records with DLMS client/server address pairs."""

    @staticmethod
    def seed(
        session: Session, endpoints: list[CommunicationEndpoint]
    ) -> list[DeviceAddressing]:
        """
        Creates sample device addressing records for endpoints.

        Args:
            session: SQLModel session for database operations.
            endpoints: List of communication endpoint instances to create addressing for.

        Returns:
            list[DeviceAddressing]: List of created addressing instances.
        """
        addressing_records = []

        # Create addressing for each endpoint with typical DLMS configurations
        for i, endpoint in enumerate(endpoints):
            # Alternate between different client addresses for variety
            # Client addresses: 16 (Public), 1 (Management), 32 (Data read)
            client_addresses = [16, 1, 32, 48, 64]
            client_address = client_addresses[i % len(client_addresses)]

            # Server addresses typically use format: physical_address * 2 + logical_address
            # Common patterns: 1, 17, 33 (physical 0, 1, 2 with logical 1)
            server_addresses = [1, 17, 33, 49, 65]
            server_address = server_addresses[i % len(server_addresses)]

            # Most modern meters use Logical Name referencing
            # Older meters may use Short Name (use_logical_name=False)
            use_logical_name = i < 6  # First 6 use LN, last 2 use SN for testing

            addressing = DeviceAddressing(
                endpoint_id=endpoint.id,
                client_address=client_address,
                server_address=server_address,
                use_logical_name=use_logical_name,
            )

            addressing_records.append(addressing)
            session.add(addressing)

        session.commit()

        # Refresh to get generated IDs
        for addressing in addressing_records:
            session.refresh(addressing)

        return addressing_records
