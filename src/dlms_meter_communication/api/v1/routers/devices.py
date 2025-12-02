"""
Device management API router.

This module provides REST API endpoints for managing DLMS devices,
including CRUD operations and communication endpoint management.
It handles device creation, retrieval, updates, deletion, and
communication endpoint associations.
"""

from fastapi import APIRouter, Body, status, Depends
from fastapi.responses import JSONResponse

from uuid import UUID
import json

from dlms_meter_communication.api.dependencies import (
    get_session_dependency,
    get_reader_service_dependency,
)
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
from dlms_meter_communication.schemas.readings import (
    ReadSingleRequest,
    ProfileByDateRangeRequest,
)
from dlms_meter_communication.schemas.communication_endpoints import (
    CommunicationEndpointList,
    CommunicationEndpoint,
)
from dlms_meter_communication.services.reader_service import ReaderService

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


@router.get("/{device_id}/association-view")
async def get_association_view(
    device_id: UUID,
    session: Session = get_session_dependency(),
    reader_service: ReaderService = Depends(get_reader_service_dependency),
) -> JSONResponse:
    """
    Get the association view from a device.
    """
    try:
        device_repository = DeviceRepository(session)
        device = device_repository.show(device_id)

        if not device:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "Device not found"},
            )

        object_collection = reader_service.get_association_view(device)

        # Ssav content to file
        with open("object_collection.json", "w") as f:
            f.write(json.dumps(object_collection, indent=4))

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"data": object_collection},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": str(e)},
        )


@router.post("/{device_id}/read-single")
async def read_single(
    device_id: UUID,
    payload: ReadSingleRequest = Body(...),
    session: Session = get_session_dependency(),
    reader_service: ReaderService = Depends(get_reader_service_dependency),
) -> JSONResponse:
    """A
    Read a single attribute from a device.
    """
    try:
        device_repository = DeviceRepository(session)
        device = device_repository.show(device_id)

        if not device:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "Device not found"},
            )

        data = reader_service.read_single(device, payload.obis)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"data": data},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": str(e)},
        )


@router.post("/{device_id}/get-common-data")
async def get_common_data(
    device_id: UUID,
    session: Session = get_session_dependency(),
    reader_service: ReaderService = Depends(get_reader_service_dependency),
) -> JSONResponse:
    """
    Get common data from a device.
    """
    try:
        device_repository = DeviceRepository(session)
        device = device_repository.show(device_id)

        if not device:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "Device not found"},
            )

        data = reader_service.get_common_data(device)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"data": data},
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": str(e)},
        )


@router.post("/{device_id}/profile-by-date-range")
async def get_profile_by_date_range(
    device_id: UUID,
    payload: ProfileByDateRangeRequest = Body(...),
    session: Session = get_session_dependency(),
    reader_service: ReaderService = Depends(get_reader_service_dependency),
) -> JSONResponse:
    """
    Extrae las lecturas de un perfil genérico por rango de fechas.

    Este endpoint permite obtener datos históricos de perfiles genéricos (load profiles,
    event logs, etc.) dentro de un período de tiempo específico. Es útil para extraer
    datos de consumo, eventos o cualquier serie temporal almacenada en el medidor.

    Args:
        device_id: UUID del dispositivo
        payload: Datos de la petición con código OBIS y rango de fechas
        session: Sesión de base de datos (inyectada)
        reader_service: Servicio de lectura (inyectado)

    Returns:
        JSONResponse: Datos del perfil dentro del rango especificado con HTTP 200,
        o mensajes de error con códigos HTTP apropiados.

    Example Request Body:
        {
            "obis": "1.0.99.1.0.255",
            "start_date": "2024-01-01T00:00:00",
            "end_date": "2024-01-31T23:59:59"
        }

    Example Response:
        {
            "data": [
                ["2024-01-01T00:00:00", 100.5, 230.2, 1.5],
                ["2024-01-01T00:15:00", 102.3, 231.1, 1.6],
                ...
            ],
            "count": 2880,
            "obis": "1.0.99.1.0.255",
            "start_date": "2024-01-01T00:00:00",
            "end_date": "2024-01-31T23:59:59"
        }
    """
    try:
        device_repository = DeviceRepository(session)
        device = device_repository.show(device_id)

        if not device:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "Dispositivo no encontrado"},
            )

        # Llamar al servicio de lectura con los parámetros
        data = reader_service.get_profile_by_date_range(
            device, payload.obis, payload.start_date, payload.end_date
        )

        # Formatear la respuesta con metadatos adicionales
        response_content = {
            "data": data,
            "count": len(data) if data else 0,
            "obis": payload.obis,
            "start_date": payload.start_date.isoformat(),
            "end_date": payload.end_date.isoformat(),
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_content,
        )
    except ValueError as e:
        # Errores de validación (400 Bad Request)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": f"Error de validación: {str(e)}"},
        )
    except Exception as e:
        # Errores del servidor (500 Internal Server Error)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"Error al leer el perfil: {str(e)}"},
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
