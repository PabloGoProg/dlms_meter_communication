"""
Database seeders for populating test/demo data.

This module provides seeders for all models in the application, allowing easy
population of the database with realistic test data for development and testing.
"""

from sqlmodel import Session
from .device_seeder import DeviceSeeder
from .communication_endpoint_seeder import CommunicationEndpointSeeder
from .device_addressing_seeder import DeviceAddressingSeeder
from .negotiated_params_seeder import NegotiatedParamsSeeder


class DatabaseSeeder:
    """
    Main seeder class that orchestrates all individual seeders.

    This class ensures seeders run in the correct order to respect
    foreign key relationships between tables.
    """

    @staticmethod
    def seed_all(session: Session) -> dict:
        """
        Runs all seeders in the correct order.

        The seeding order is:
        1. Devices (no dependencies)
        2. Communication Endpoints (depends on Devices)
        3. Device Addressing (depends on Endpoints)
        4. Negotiated Params (depends on Devices and Endpoints)

        Args:
            session: SQLModel session for database operations.

        Returns:
            dict: Dictionary containing all created records by type.
        """
        print("🌱 Starting database seeding...")

        # Seed devices first (no dependencies)
        print("  📱 Seeding devices...")
        devices = DeviceSeeder.seed(session)
        print(f"    ✓ Created {len(devices)} devices")

        # Seed communication endpoints (depends on devices)
        print("  🔌 Seeding communication endpoints...")
        endpoints = CommunicationEndpointSeeder.seed(session, devices)
        print(f"    ✓ Created {len(endpoints)} endpoints")

        # Seed device addressing (depends on endpoints)
        print("  📍 Seeding device addressing...")
        addressing = DeviceAddressingSeeder.seed(session, endpoints)
        print(f"    ✓ Created {len(addressing)} addressing records")

        # Seed negotiated parameters (depends on devices and endpoints)
        print("  ⚙️  Seeding negotiated parameters...")
        params = NegotiatedParamsSeeder.seed(session, devices, endpoints)
        print(f"    ✓ Created {len(params)} negotiated params")

        print("✅ Database seeding completed successfully!\n")

        return {
            "devices": devices,
            "endpoints": endpoints,
            "addressing": addressing,
            "negotiated_params": params,
        }


__all__ = [
    "DatabaseSeeder",
    "DeviceSeeder",
    "CommunicationEndpointSeeder",
    "DeviceAddressingSeeder",
    "NegotiatedParamsSeeder",
]
