"""
Command line interface for administrative tasks.

Currently provides commands to seed the database with demo data.
"""

import argparse
from typing import Optional

from dlms_meter_communication.db.database import init_db
from dlms_meter_communication.seeders import DatabaseSeeder


def _run_seed(skip_init_db: bool) -> None:
    """
    Execute the database seeders in sequence.

    Args:
        skip_init_db: When True, the CLI will not attempt to create database
            tables before seeding. Useful if tables already exist or when
            migrations are managed externally.
    """
    if not skip_init_db:
        print("Ensuring database schema is created...")
        init_db()

    DatabaseSeeder.seed_all()


def _run_clean() -> None:
    """
    Cleans all data from the database.
    """
    DatabaseSeeder.clean_all()


def build_parser() -> argparse.ArgumentParser:
    """Create the root CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="dlms",
        description="Administrative tools for DLMS Meter Communication.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser(
        "seed",
        help="Execute the seeders and load demo data.",
    )
    seed_parser.add_argument(
        "--skip-init-db",
        action="store_true",
        help="Don't create the database tables before seeding.",
    )
    seed_parser.set_defaults(handler=lambda args: _run_seed(args.skip_init_db))

    clean_parser = subparsers.add_parser(
        "clean",
        help="Cleans all data from the database.",
    )
    clean_parser.set_defaults(handler=lambda args: _run_clean())

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """
    Entry point for the CLI.

    Args:
        argv: Lista de argumentos. Si es None se usará sys.argv.

    Returns:
        Código de salida del proceso.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)

    if handler is None:
        parser.print_help()
        return 1

    handler(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
