from fastapi import Depends
from dlms_meter_communication.db.database import get_session, Session


def get_session_dependency() -> Session:
    return Depends(get_session)
