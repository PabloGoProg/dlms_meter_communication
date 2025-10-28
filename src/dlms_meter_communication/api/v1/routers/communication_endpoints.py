from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from ...dependencies import get_session_dependency
from dlms_meter_communication.repositories.comm_endpoints_repository import (
    CommunicationEndpointRepository,
)
from sqlmodel import Session
from dlms_meter_communication.schemas.communication_endpoints import (
    CommunicationEndpointList,
    CommunicationEndpoint,
)

router = APIRouter(prefix="/communication-endpoints", tags=["communication-endpoints"])


@router.get("/")
async def get_communication_endpoints(
    session: Session = get_session_dependency(),
):
    repository = CommunicationEndpointRepository(session)
    communication_endpoints = repository.index()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=CommunicationEndpointList(
            communication_endpoints=[
                CommunicationEndpoint.model_validate(
                    communication_endpoint, from_attributes=True
                )
                for communication_endpoint in communication_endpoints
            ]
        ).model_dump(mode="json"),
    )
