"""
Device repository for database operations.

This module provides the DeviceRepository class for managing device entities
in the database. It implements the repository pattern to abstract database
operations and provides CRUD functionality for device management.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from ..models.device import Device
from ..schemas.device import DeviceCreate, DeviceUpdate
from sqlalchemy.exc import NoResultFound


class DeviceRepository:
    """
    Repository class for device database operations.

    Provides methods for creating, reading, updating, and deleting
    device entities. Implements the repository pattern to separate
    data access logic from business logic.

    Attributes:
        _session: SQLModel database session for executing queries.
    """

    def __init__(self, session: Session):
        """
        Initialize the device repository with a database session.

        Args:
            session: SQLModel database session for executing queries.
        """
        self._session = session

    def index(
        self, *, offset: int = 0, limit: int = 50, order_desc: bool = True
    ) -> list[Device]:
        """
        Retrieve a paginated list of devices.

        Fetches devices from the database with optional pagination and ordering.
        Results are ordered by creation date (newest first by default).

        Args:
            offset: Number of records to skip for pagination.
            limit: Maximum number of records to return.
            order_desc: If True, order by creation date descending (newest first).

        Returns:
            list[Device]: List of device entities.

        Raises:
            Exception: If database query fails.
        """
        try:
            stmt = select(Device).options(
                selectinload(Device.communication_endpoints),
                selectinload(Device.device_addressings),
            )
            stmt = stmt.order_by(
                Device.created_at.desc() if order_desc else Device.created_at.asc(),
            )
            stmt = stmt.offset(offset).limit(limit)
            devices = self._session.exec(stmt).all()

            return devices
        except Exception as e:
            raise e

    def show(self, device_id: UUID) -> Optional[Device]:
        """
        Retrieve a single device by its ID.

        Fetches a device from the database using its UUID identifier.

        Args:
            device_id: UUID of the device to retrieve.

        Returns:
            Optional[Device]: Device entity if found, None otherwise.
        """
        entity = self._session.get(Device, device_id).options(
            selectinload(Device.communication_endpoints),
            selectinload(Device.device_addressings),
        )
        return entity if entity else None

    def store(self, data: DeviceCreate) -> Device:
        """
        Create a new device in the database.

        Creates a new device entity using the provided data and persists
        it to the database. The device ID is auto-generated.

        Args:
            data: Device creation data containing device information.

        Returns:
            Device: The created device entity with generated ID.
        """
        entity = Device(**data.model_dump())
        self._session.add(entity)
        self._session.flush()
        self._session.refresh(entity)
        return entity

    def update(self, device_id: UUID, patch: DeviceUpdate) -> Device:
        """
        Update an existing device.

        Updates device fields with the provided data. Only fields
        included in the patch data will be updated.

        Args:
            device_id: UUID of the device to update.
            patch: Device update data containing fields to modify.

        Returns:
            Device: The updated device entity.

        Raises:
            NoResultFound: If the device with the given ID doesn't exist.
        """
        entity = self.show(device_id)

        if entity is None:
            raise NoResultFound(f"Device with id {device_id} not found")

        update_data = patch.model_dump(exclude_unset=True)

        for k, v in update_data.items():
            setattr(entity, k, v)

        self._session.flush()
        self._session.refresh(entity)
        return entity

    def remove(self, device_id: UUID) -> None:
        """
        Remove a device from the database.

        Deletes a device entity from the database. This operation
        requires the device to exist.

        Args:
            device_id: UUID of the device to remove.

        Raises:
            NoResultFound: If the device with the given ID doesn't exist.
        """
        entity = self.show(device_id)

        if entity is None:
            raise NoResultFound(f"Device with id {device_id} not found")

        self._session.delete(entity)
        self._session.flush()

    def destroy(self, device_id: UUID) -> None:
        """
        Destroy a device from the database.

        Alternative method for deleting a device entity. This method
        provides the same functionality as remove() but with a different
        naming convention.

        Args:
            device_id: UUID of the device to destroy.

        Raises:
            NoResultFound: If the device with the given ID doesn't exist.
        """
        entity = self.show(device_id)

        if entity is None:
            raise NoResultFound(f"Device with id {device_id} not found")

        try:
            self._session.delete(entity)
            self._session.flush()
        except Exception as e:
            raise e
