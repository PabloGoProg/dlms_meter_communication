"""
Device management API router.

This module provides REST API endpoints for managing DLMS devices,
including CRUD operations and communication endpoint management.
It handles device creation, retrieval, updates, deletion, and
communication endpoint associations.
"""

from fastapi import APIRouter, Body, status
from fastapi.responses import JSONResponse

from uuid import UUID

from dlms_meter_communication.api.dependencies import get_session_dependency
from dlms_meter_communication.db.database import Session
from dlms_meter_communication.repositories.device_repository import DeviceRepository
from dlms_meter_communication.repositories.comm_endpoints_repository import (
    CommunicationEndpointRepository,
)
from dlms_meter_communication.schemas.device import (
    DeviceList,
    Device,
    DeviceCreate,
    DeviceUpdate,
)
from dlms_meter_communication.schemas.communication_endpoints import (
    CommunicationEndpointList,
    CommunicationEndpoint,
)

# Create router with prefix and tags for API documentation
router = APIRouter(prefix="/devices", tags=["devices"])


@router.get(
    "/{device_id}/communication-endpoints", response_model=CommunicationEndpointList
)
async def get_communication_endpoints(
    device_id: UUID, session: Session = get_session_dependency()
) -> JSONResponse:
    """
    Retrieve all communication endpoints for a device.

    Returns a list of all communication endpoints associated with
    the specified device, including connection details and parameters.

    Args:
        device_id: UUID of the device.
        session: Database session dependency.

    Returns:
        JSONResponse: List of communication endpoints with HTTP 200 status.
    """
    communication_endpoint_repository = CommunicationEndpointRepository(session)
    communication_endpoints = communication_endpoint_repository.index_by_device_id(
        device_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=CommunicationEndpointList(
            communication_endpoints=[
                CommunicationEndpoint.model_validate(
                    communication_endpoint,
                    from_attributes=True,
                )
                for communication_endpoint in communication_endpoints
            ]
        ).model_dump(mode="json"),
    )


@router.get(
    "/{device_id}/communication-endpoints/primary", response_model=CommunicationEndpoint
)
async def get_primary_communication_endpoint(
    device_id: UUID,
    session: Session = get_session_dependency(),
) -> JSONResponse:
    """
    Retrieve the primary communication endpoint for a device.

    Returns the primary communication endpoint associated with the device.
    Each device should have one primary endpoint for main communication.

    Args:
        device_id: UUID of the device.
        session: Database session dependency.

    Returns:
        JSONResponse: Primary communication endpoint with HTTP 200 status,
        or HTTP 404 if no primary endpoint exists.
    """
    communication_endpoint_repository = CommunicationEndpointRepository(session)
    communication_endpoint = communication_endpoint_repository.get_primary_by_device_id(
        device_id
    )

    if not communication_endpoint:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "message": "There is no primary communication endpoint for this device"
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=CommunicationEndpoint.model_validate(
            communication_endpoint, from_attributes=True
        ).model_dump(mode="json"),
    )


@router.get("/", response_model=DeviceList)
async def index(session: Session = get_session_dependency()) -> JSONResponse:
    """
    Retrieve all devices.

    Returns a list of all devices in the system with their basic information.

    Args:
        session: Database session dependency.

    Returns:
        JSONResponse: List of devices with HTTP 200 status.
    """
    device_repository = DeviceRepository(session)
    devices = device_repository.index()
    print("devices", [d.communication_endpoints for d in devices])
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=DeviceList(
            devices=[
                Device.model_validate(device, from_attributes=True)
                for device in devices
            ]
        ).model_dump(mode="json"),
    )


@router.get("/{device_id}", response_model=Device)
async def show(
    device_id: UUID, session: Session = get_session_dependency()
) -> JSONResponse:
    """
    Retrieve a specific device by ID.

    Returns detailed information about a single device identified by its UUID.

    Args:
        device_id: UUID of the device to retrieve.
        session: Database session dependency.

    Returns:
        JSONResponse: Device details with HTTP 200 status, or HTTP 404 if not found.
    """
    device_repository = DeviceRepository(session)
    device = device_repository.show(device_id)

    print(device)
    if not device:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "message": "Device not found",
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=Device.model_validate(device, from_attributes=True).model_dump(
            mode="json"
        ),
    )


@router.post("/", response_model=Device)
async def create(
    session: Session = get_session_dependency(), data: DeviceCreate = Body(...)
) -> JSONResponse:
    """
    Create a new device.

    Creates a new DLMS device with the provided information including
    name, serial number, brand, and model.

    Args:
        session: Database session dependency.
        data: Device creation data containing device information.

    Returns:
        JSONResponse: Created device with HTTP 201 status, or HTTP 400 if creation fails.
    """
    repo = DeviceRepository(session)
    entity = repo.store(data)

    if not entity:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Failed to create device"},
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=Device.model_validate(entity, from_attributes=True).model_dump(
            mode="json"
        ),
    )


@router.put("/{device_id}", response_model=Device)
async def update(
    device_id: UUID,
    session: Session = get_session_dependency(),
    device: DeviceUpdate = Body(...),
) -> JSONResponse:
    """
    Update an existing device.

    Updates device information with the provided data. Only fields
    included in the request will be updated.

    Args:
        device_id: UUID of the device to update.
        session: Database session dependency.
        device: Device update data containing fields to modify.

    Returns:
        JSONResponse: Updated device with HTTP 200 status.
    """
    device_repository = DeviceRepository(session)
    device = device_repository.update(device_id, device)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=Device.model_validate(device).model_dump(),
    )


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    device_id: UUID, session: Session = get_session_dependency()
) -> JSONResponse:
    """
    Delete a device.

    Removes a device from the system permanently. This operation
    cannot be undone.

    Args:
        device_id: UUID of the device to delete.
        session: Database session dependency.

    Returns:
        JSONResponse: Empty response with HTTP 204 status.
    """
    device_repository = DeviceRepository(session)
    device_repository.delete(device_id)
    return JSONResponse(
        status_code=status.HTTP_204_NO_CONTENT,
        content=None,
    )
