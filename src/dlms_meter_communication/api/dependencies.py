from fastapi import Depends
from dlms_meter_communication.db.database import get_session, Session
from dlms_meter_communication.repositories.device_repository import DeviceRepository


def get_session_dependency() -> Session:
    return Depends(get_session)
