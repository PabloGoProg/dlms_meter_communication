from fastapi import APIRouter, status, Body
from fastapi.responses import JSONResponse
from uuid import UUID


from ...dependencies import get_session_dependency
from dlms_meter_communication.repositories import (
    CommunicationEndpointRepository,
    DeviceAddressingRepository,
)
from sqlmodel import Session
from dlms_meter_communication.schemas import (
    CommunicationEndpoint,
    CommunicationEndpointCreate,
    CommunicationEndpointUpdate,
    DeviceAddressing,
    DeviceAddressingList,
)

router = APIRouter(prefix="/communication-endpoints", tags=["communication-endpoints"])


@router.get("/{communication_endpoint_id}/device-addressings")
async def get_device_addressings(
    communication_endpoint_id: UUID,
    session: Session = get_session_dependency(),
) -> JSONResponse:
    """
    Get device addressings for a communication endpoint.
    """
    repository = DeviceAddressingRepository(session)
    device_addressings = repository.index_by_endpoint_id(communication_endpoint_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=DeviceAddressingList(
            device_addressings=[
                DeviceAddressing.model_validate(device_addressing)
                for device_addressing in device_addressings
            ]
        ).model_dump(mode="json"),
    )


@router.get("/{communication_endpoint_id}")
async def show(
    communication_endpoint_id: UUID,
    session: Session = get_session_dependency(),
):
    """
    Get a communication endpoint by ID.

    Args:
        communication_endpoint_id: UUID of the communication endpoint to get.
        session: Database session dependency.

    Returns:
        JSONResponse: Communication endpoint with HTTP 200 status, or HTTP 404 if not found.
    """
    repository = CommunicationEndpointRepository(session)
    communication_endpoint = repository.show(communication_endpoint_id)

    if not communication_endpoint:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "message": f"Communication endpoint with id {communication_endpoint_id} not found"
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=CommunicationEndpoint.model_validate(
            communication_endpoint, from_attributes=True
        ).model_dump(mode="json"),
    )


@router.post("/")
async def create(
    session: Session = get_session_dependency(),
    data: CommunicationEndpointCreate = Body(...),
) -> JSONResponse:
    """
    Create a new communication endpoint.

    Creates a new communication endpoint with the provided information.

    Args:
        session: Database session dependency.
        data: Communication endpoint creation data.

    Returns:
        JSONResponse: Created communication endpoint with HTTP 201 status, or HTTP 400 if creation fails.
    """
    repository = CommunicationEndpointRepository(session)
    communication_endpoint = repository.store(data)

    if not communication_endpoint:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Failed to create communication endpoint"},
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=CommunicationEndpoint.model_validate(
            communication_endpoint, from_attributes=True
        ).model_dump(mode="json"),
    )


@router.put("/{communication_endpoint_id}")
async def update(
    communication_endpoint_id: UUID,
    session: Session = get_session_dependency(),
    data: CommunicationEndpointUpdate = Body(...),
) -> JSONResponse:
    """
    Update a communication endpoint.

    Updates a communication endpoint with the provided information.

    Args:
        communication_endpoint_id: UUID of the communication endpoint to update.
        session: Database session dependency.
        data: Communication endpoint update data.

    Returns:
        JSONResponse: Updated communication endpoint with HTTP 200 status, or HTTP 400 if update fails.
    """
    repository = CommunicationEndpointRepository(session)
    communication_endpoint = repository.update(communication_endpoint_id, data)

    if not communication_endpoint:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Failed to update communication endpoint"},
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=CommunicationEndpoint.model_validate(
            communication_endpoint, from_attributes=True
        ).model_dump(mode="json"),
    )


@router.delete("/{communication_endpoint_id}")
async def delete(
    communication_endpoint_id: UUID,
    session: Session = get_session_dependency(),
) -> JSONResponse:
    """
    Delete a communication endpoint.

    Deletes a communication endpoint with the provided information.
    """
    repository = CommunicationEndpointRepository(session)
    repository.destroy(communication_endpoint_id)

    return JSONResponse(
        status_code=status.HTTP_204_NO_CONTENT,
        content=None,
    )
