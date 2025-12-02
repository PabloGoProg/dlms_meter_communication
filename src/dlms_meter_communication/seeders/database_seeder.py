"""
Database seeders for populating test/demo data.

This module provides seeders for all models in the application, allowing easy
population of the database with realistic test data for development and testing.
"""

from sqlalchemy import text
from dlms_meter_communication.db.database import get_context_session

from .device_seeder import DeviceSeeder
from .communication_endpoint_seeder import CommunicationEndpointSeeder
from .device_addressing_seeder import DeviceAddressingSeeder


class DatabaseSeeder:
    """
    Main seeder class that orchestrates all individual seeders.

    This class ensures seeders run in the correct order to respect
    foreign key relationships between tables.
    """

    @staticmethod
    def seed_all():
        """
        Runs all seeders in the correct order.

        The seeding order is:
        1. Devices (no dependencies)
        2. Communication Endpoints (depends on Devices)
        3. Device Addressing (depends on Endpoints)

        Args:
            session: SQLModel session for database operations.

        Returns:
            dict: Dictionary containing all created records by type.
        """
        print("Starting database seeding...")

        with get_context_session() as session:
            try:
                # Seed devices first (no dependencies)
                print("--------------------------------------------------------------")
                print("Seeding devices...")
                devices = DeviceSeeder.seed(session)
                print(f"Created {len(devices)} devices")

                # Seed communication endpoints (depends on devices)
                print("--------------------------------------------------------------")
                print("Seeding communication endpoints...")
                endpoints = CommunicationEndpointSeeder.seed(session, devices)
                print(f"Created {len(endpoints)} endpoints")

                # Seed device addressing (depends on endpoints)
                print("--------------------------------------------------------------")
                print("Seeding device addressing...")
                addressing = DeviceAddressingSeeder.seed(session, devices)
                print(f"Created {len(addressing)} addressing records")

                print("--------------------------------------------------------------")
                print("Database seeding completed successfully!")
                print("--------------------------------------------------------------")
            except Exception as e:
                print(f"Error during seeding: {e}")
                session.rollback()
                raise
            finally:
                session.commit()
                session.close()

    @staticmethod
    def clean_all():
        """
        Cleans all data from the database.

        This method will delete all data from the database, including all tables.
        """
        print("Starting database cleaning...")
        with get_context_session() as session:
            try:
                session.exec(text("DELETE FROM devices CASCADE"))
                session.exec(text("DELETE FROM comm_endpoints CASCADE"))
                session.exec(text("DELETE FROM device_addressing CASCADE"))
                print("--------------------------------------------------------------")
                print("Database cleaning completed successfully!")
                print("--------------------------------------------------------------")
            except Exception as e:
                print(f"Error during database cleaning: {e}")
                session.rollback()
                raise
            finally:
                session.commit()
                session.close()
