"""
Script to run database seeders.

Usage:
    python -m dlms_meter_communication.seeders.run_seeders
"""

from sqlmodel import create_engine, Session
from . import DatabaseSeeder
import os


def main():
    """
    Main function to run all database seeders.

    Reads database URL from environment variable and executes all seeders.
    """
    # Get database URL from environment variable
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/dlms_meter_communication",
    )

    print(f"Connecting to database: {database_url}\n")

    # Create engine and session
    engine = create_engine(database_url, echo=False)

    with Session(engine) as session:
        try:
            # Run all seeders
            results = DatabaseSeeder.seed_all(session)

            # Print summary
            print("\n📊 Seeding Summary:")
            print(f"  • Devices: {len(results['devices'])}")
            print(f"  • Endpoints: {len(results['endpoints'])}")
            print(f"  • Addressing: {len(results['addressing'])}")
            print(f"  • Negotiated Params: {len(results['negotiated_params'])}")
            print("\n🎉 All data has been seeded successfully!")

        except Exception as e:
            print(f"\n❌ Error during seeding: {e}")
            session.rollback()
            raise


if __name__ == "__main__":
    main()
