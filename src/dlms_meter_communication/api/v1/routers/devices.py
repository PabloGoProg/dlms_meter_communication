from fastapi import APIRouter, Body, status
from fastapi.responses import JSONResponse

from uuid import UUID

from dlms_meter_communication.api.dependencies import get_session_dependency
from dlms_meter_communication.db.database import Session
from dlms_meter_communication.repositories.device_repository import DeviceRepository
from dlms_meter_communication.schemas.device import (
    DeviceList,
    Device,
    DeviceCreate,
    DeviceUpdate,
)

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("/", response_model=DeviceList)
async def index(session: Session = get_session_dependency()) -> JSONResponse:
    device_repository = DeviceRepository(session)
    devices = device_repository.index()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=DeviceList(
            devices=[Device.model_validate(device) for device in devices]
        ).model_dump(),
    )


@router.get("/{device_id}", response_model=Device)
async def show(
    device_id: UUID, session: Session = get_session_dependency()
) -> JSONResponse:
    device_repository = DeviceRepository(session)
    device = device_repository.show(device_id)

    if not device:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "Device not found"},
            ),
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=Device.model_validate(device).model_dump(),
    )


@router.post("/", response_model=Device)
async def create(
    session: Session = get_session_dependency(), device: DeviceCreate = Body(...)
) -> JSONResponse:
    device_repository = DeviceRepository(session)
    device = device_repository.create(device)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=Device.model_validate(device).model_dump(),
    )


@router.put("/{device_id}", response_model=Device)
async def update(
    device_id: UUID,
    session: Session = get_session_dependency(),
    device: DeviceUpdate = Body(...),
) -> JSONResponse:
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
    device_repository = DeviceRepository(session)
    device_repository.delete(device_id)
    return JSONResponse(
        status_code=status.HTTP_204_NO_CONTENT,
        content=None,
    )
