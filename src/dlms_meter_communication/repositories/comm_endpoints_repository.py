"""
Communication endpoint repository for database operations.

This module provides the CommunicationEndpointRepository class for managing
communication endpoint entities in the database. It implements the repository
pattern to abstract database operations and provides CRUD functionality for
communication endpoint management, including primary endpoint logic.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID
from sqlmodel import Session, select
from ..models.enums import Medium
from ..models.communication_endpoint import CommunicationEndpoint
from ..schemas.communication_endpoints import (
    CommunicationEndpointCreate,
    CommunicationEndpointUpdate,
)
from sqlalchemy.exc import NoResultFound, InvalidRequestError


class CommunicationEndpointRepository:
    """
    Repository class for communication endpoint database operations.

    Provides methods for creating, reading, updating, and deleting
    communication endpoint entities. Implements the repository pattern to
    separate data access logic from business logic. Includes special handling
    for primary endpoint management.

    Attributes:
        _session: SQLModel database session for executing queries.
    """

    def __init__(self, session: Session):
        """
        Initialize the communication endpoint repository with a database session.

        Args:
            session: SQLModel database session for executing queries.
        """
        self._session = session

    def index(
        self, *, offset: int = 0, limit: int = 50, order_desc: bool = True
    ) -> list[CommunicationEndpoint]:
        """
        Retrieve a paginated list of communication endpoints.

        Fetches communication endpoints from the database with optional
        pagination and ordering. Results are ordered by creation date
        (newest first by default).

        Args:
            offset: Number of records to skip for pagination.
            limit: Maximum number of records to return.
            order_desc: If True, order by creation date descending (newest first).

        Returns:
            list[CommunicationEndpoint]: List of communication endpoint entities.

        Raises:
            Exception: If database query fails.
        """
        try:
            stmt = select(CommunicationEndpoint)
            stmt = stmt.order_by(
                CommunicationEndpoint.created_at.desc()
                if order_desc
                else CommunicationEndpoint.created_at
            )
            stmt = stmt.offset(offset).limit(limit)
            communication_endpoints = self._session.exec(stmt).all()

            return communication_endpoints
        except Exception as e:
            raise e

    def index_by_device_id(self, device_id: UUID) -> list[CommunicationEndpoint]:
        """
        Retrieve all communication endpoints for a specific device.

        Fetches all communication endpoints associated with the given device ID.
        This is useful for managing multiple communication channels per device.

        Args:
            device_id: UUID of the device to get endpoints for.

        Returns:
            list[CommunicationEndpoint]: List of communication endpoints for the device.

        Raises:
            Exception: If database query fails.
        """
        try:
            stmt = select(CommunicationEndpoint).where(
                CommunicationEndpoint.device_id == device_id
            )
            communication_endpoints = self._session.exec(stmt).all()

            return communication_endpoints
        except Exception as e:
            raise e

    def get_primary_by_device_id(
        self, device_id: UUID
    ) -> Optional[CommunicationEndpoint]:
        """
        Retrieve the primary communication endpoint for a specific device.

        Fetches the communication endpoint marked as primary for the given device.
        Each device should have exactly one primary endpoint for main communication.

        Args:
            device_id: UUID of the device to get the primary endpoint for.

        Returns:
            Optional[CommunicationEndpoint]: Primary endpoint if found, None otherwise.

        Raises:
            Exception: If database query fails.
        """
        try:
            stmt = select(CommunicationEndpoint).where(
                CommunicationEndpoint.device_id == device_id,
                CommunicationEndpoint.is_primary.is_(True),
            )
            communication_endpoint = self._session.exec(stmt).first()
            return communication_endpoint if communication_endpoint else None
        except Exception as e:
            raise e

    def show(self, communication_endpoint_id: UUID) -> Optional[CommunicationEndpoint]:
        """
        Retrieve a single communication endpoint by its ID.

        Fetches a communication endpoint from the database using its UUID identifier.

        Args:
            communication_endpoint_id: UUID of the communication endpoint to retrieve.

        Returns:
            Optional[CommunicationEndpoint]: Communication endpoint entity if found, None otherwise.
        """
        entity = self._session.get(CommunicationEndpoint, communication_endpoint_id)
        return entity if entity else None

    def store(self, data: CommunicationEndpointCreate) -> CommunicationEndpoint:
        """
        Create a new communication endpoint in the database.

        Creates a new communication endpoint entity using the provided data and persists
        it to the database. Handles primary endpoint logic automatically:
        - If no endpoints exist for the device, the first one becomes primary
        - If setting a new primary, the previous primary is demoted
        - The endpoint ID is auto-generated

        Args:
            data: Communication endpoint creation data containing endpoint information.

        Returns:
            CommunicationEndpoint: The created communication endpoint entity with generated ID.
        """
        # Get current communication endpoints for the device
        device_id = data.device_id
        device_comm_endpoints = self.index_by_device_id(device_id)

        if data.medium == Medium.TCP and (data.ip is None or data.port is None):
            raise InvalidRequestError("IP and port are required for TCP communication")
        if data.medium == Medium.SERIAL and (
            data.serial_port is None or data.baud_rate is None
        ):
            raise InvalidRequestError(
                "Serial port and baud rate are required for serial communication"
            )

        if len(device_comm_endpoints) == 0:
            # If no communication endpoints for the device, set the first one as primary
            data.is_primary = True
        else:
            if data.is_primary is None or data.is_primary is False:
                # If is_primary is not set or is False, set it to False
                data.is_primary = False
            else:
                # If is_primary is True, get the current primary communication endpoint and set it to False
                # then set the new communication endpoint as primary
                current_primary = self.get_primary_by_device_id(device_id)
                if current_primary:
                    current_primary.is_primary = False
                    self._session.add(current_primary)
                    self._session.commit()

                data.is_primary = True

        # Create the communication endpoint
        entity = CommunicationEndpoint(**data.model_dump())
        self._session.add(entity)
        self._session.commit()
        return entity

    def update(
        self, communication_endpoint_id: UUID, data: CommunicationEndpointUpdate
    ) -> CommunicationEndpoint:
        """
        Update an existing communication endpoint.

        Updates communication endpoint fields with the provided data. Only fields
        included in the update data will be updated. Handles primary endpoint
        logic when updating the is_primary field.

        Args:
            communication_endpoint_id: UUID of the communication endpoint to update.
            data: Communication endpoint update data containing fields to modify.

        Returns:
            CommunicationEndpoint: The updated communication endpoint entity.

        Raises:
            CommunicationEndpointNotFoundError: If the endpoint with the given ID doesn't exist.
        """
        entity = self.show(communication_endpoint_id)

        if not entity:
            raise NoResultFound(
                f"Communication endpoint with id {communication_endpoint_id} not found"
            )

        # Handle primary endpoint logic
        if data.is_primary is not None and data.is_primary is True:
            current_primary = self.get_primary_by_device_id(entity.device_id)
            if current_primary:
                current_primary.is_primary = False
                self._session.add(current_primary)
                self._session.commit()

            data.is_primary = True

        # Update entity fields
        for key, value in data.model_dump().items():
            setattr(entity, key, value)

        self._session.add(entity)
        self._session.flush()
        self._session.refresh(entity)
        return entity

    def destroy(self, communication_endpoint_id: UUID) -> None:
        """
        Delete a communication endpoint from the database.

        Removes a communication endpoint entity from the database. This operation
        requires the endpoint to exist and prevents deletion of primary endpoints.
        Primary endpoints must be demoted before deletion.

        Args:
            communication_endpoint_id: UUID of the communication endpoint to delete.

        Returns:
            bool: True if deletion was successful.

        Raises:
            CommunicationEndpointNotFoundError: If the endpoint with the given ID doesn't exist.
            CommunicationEndpointPrimaryCannotBeDeletedError: If attempting to delete a primary endpoint.
        """
        entity = self.show(communication_endpoint_id)

        if not entity:
            raise NoResultFound(
                f"Communication endpoint with id {communication_endpoint_id} not found"
            )

        # Prevent deletion of primary endpoints
        if entity.is_primary:
            raise InvalidRequestError(
                f"Communication endpoint with id {communication_endpoint_id} is primary and cannot be deleted. Please set another one as primary first."
            )

        try:
            self._session.delete(entity)
            self._session.flush()
        except Exception as e:
            raise e
