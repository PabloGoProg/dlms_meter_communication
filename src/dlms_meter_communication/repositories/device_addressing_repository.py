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
from ..repositories.comm_endpoints_repository import CommunicationEndpointRepository
from ..models import DeviceAddressing
from ..schemas import (
    DeviceAddressingCreate,
    DeviceAddressingUpdate,
)
from sqlalchemy.exc import NoResultFound, InvalidRequestError


class DeviceAddressingRepository:
    """
    Repository class for device addressing database operations.

    Provides methods for creating, reading, updating, and deleting
    device addressing entities. Implements the repository pattern to
    separate data access logic from business logic.
    """

    def __init__(self, session: Session):
        """
        Initialize the device addressing repository with a database session.

        Args:
            session: SQLModel database session for executing queries.
        """
        self._session = session

    def index(
        self, *, offset: int = 0, limit: int = 50, order_desc: bool = True
    ) -> list[DeviceAddressing]:
        """
        Retrieve a paginated list of device addressing configurations.

        Fetches device addressing configurations from the database with optional pagination and ordering. Results are ordered by creation date (newest first by default).

        Args:
            offset: Number of records to skip for pagination.
            limit: Maximum number of records to return.
            order_desc: If True, order by creation date descending (newest first).

        Returns:
            list[DeviceAddressing]: List of device addressing configurations.
        """
        try:
            stmt = select(DeviceAddressing)

            stmt = stmt.order_by(
                DeviceAddressing.created_at.desc()
                if order_desc
                else DeviceAddressing.created_at
            )

            stmt = stmt.offset(offset).limit(limit)
            device_addressings = self._session.exec(stmt).all()

            return device_addressings
        except Exception as e:
            raise e

    def index_by_endpoint_id(self, endpoint_id: UUID) -> list[DeviceAddressing]:
        """
        Retrieve a list of device addressing configurations by endpoint ID.

        Fetches device addressing configurations from the database by endpoint ID.
        Args:
            endpoint_id: UUID of the endpoint to retrieve device addressing configurations for.
        Returns:
            list[DeviceAddressing]: List of device addressing configurations.
        """
        try:
            comm_endpoint_repository = CommunicationEndpointRepository(self._session)
            comm_endpoint = comm_endpoint_repository.show(endpoint_id)

            if comm_endpoint is None:
                raise NoResultFound(
                    f"Communication endpoint with id {endpoint_id} not found"
                )

            return [
                DeviceAddressing(**device_addressing.model_dump())
                for device_addressing in comm_endpoint.device_addressings
            ]
        except Exception as e:
            raise e

    def show(self, device_addressing_id: UUID) -> Optional[DeviceAddressing]:
        """
        Retrieve a single device addressing by its ID.

        Fetches a device addressing from the database using its UUID identifier.
        Args:
            device_addressing_id: UUID of the device addressing to retrieve.

        Returns:
            Optional[DeviceAddressing]: Device addressing entity if found, None otherwise.
        """
        entity = self._session.get(DeviceAddressing, device_addressing_id)
        return entity if entity else None

    def store(self, data: DeviceAddressingCreate) -> DeviceAddressing:
        """
        Create a new device addressing in the database.

        Creates a new device addressing entity using the provided data and persists
        it to the database. The device addressing ID is auto-generated.
        Args:
            data: DeviceAddressing creation data containing device addressing information.

        Returns:
            DeviceAddressing: The created device addressing entity with generated ID.
        """
        server_address, client_address = data.server_address, data.client_address

        already_exists = self._session.exec(
            select(DeviceAddressing).where(
                DeviceAddressing.endpoint_id == data.endpoint_id,
                DeviceAddressing.server_address == server_address,
                DeviceAddressing.client_address == client_address,
            )
        ).first()

        if already_exists:
            raise InvalidRequestError(
                statement=f"Device addressing already exists for endpoint {data.endpoint_id} with server address {server_address} and client address {client_address}"
            )

        comm_endpoint_repository = CommunicationEndpointRepository(self._session)
        comm_endpoint = comm_endpoint_repository.show(data.endpoint_id)

        if comm_endpoint is None:
            raise NoResultFound(
                f"Communication endpoint with id {data.endpoint_id} not found"
            )

        comm_endpoint.device_addressings.append(data)
        self._session.add(comm_endpoint)
        self._session.commit()

        return comm_endpoint.device_addressings[-1]

    def update(
        self, device_addressing_id: UUID, data: DeviceAddressingUpdate
    ) -> DeviceAddressing:
        """
        Update an existing device addressing.

        Updates device addressing fields with the provided data. Only fields
        included in the patch data will be updated.
        Args:
            device_addressing_id: UUID of the device addressing to update.
            data: DeviceAddressing update data containing fields to modify.
        Returns:
            DeviceAddressing: The updated device addressing entity.
        """

        entity = self.show(device_addressing_id)
        if entity is None:
            raise NoResultFound(
                f"Device addressing with id {device_addressing_id} not found"
            )

        server_address, client_address = data.server_address, data.client_address

        already_exists = self._session.exec(
            select(DeviceAddressing).where(
                DeviceAddressing.endpoint_id == data.endpoint_id,
                DeviceAddressing.server_address == server_address,
                DeviceAddressing.client_address == client_address,
            )
        ).first()

        if already_exists:
            raise InvalidRequestError(
                statement=f"Device addressing already exists for endpoint {data.endpoint_id} with server address {server_address} and client address {client_address}"
            )

        update_data = data.model_dump(exclude_unset=True)

        for k, v in update_data.items():
            setattr(entity, k, v)

        self._session.flush()
        self._session.refresh(entity)
        return entity

    def destroy(self, device_addressing_id: UUID) -> None:
        """
        Destroy a device addressing from the database.

        Deletes a device addressing entity from the database. This operation
        requires the device addressing to exist.
        Args:
            device_addressing_id: UUID of the device addressing to destroy.
        """
        entity = self.show(device_addressing_id)

        if entity is None:
            raise NoResultFound(
                f"Device addressing with id {device_addressing_id} not found"
            )

        self._session.delete(entity)
        self._session.flush()
