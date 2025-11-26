from fastapi import Depends, Request
from dlms_meter_communication.db.database import get_session, Session
from dlms_meter_communication.services.reader_service import ReaderService


def get_session_dependency() -> Session:
    return Depends(get_session)


def get_reader_service_dependency(request: Request) -> ReaderService:
    return request.app.state.reader_service
