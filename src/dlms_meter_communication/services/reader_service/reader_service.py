from .core import SessionManager, Session

from dlms_meter_communication.schemas.device import Device


class ReaderService:
    def __init__(self):
        self.session_manager = SessionManager()
