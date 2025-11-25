from ..factories.sessions import SessionFactory, Session

from dlms_meter_communication.schemas import Device


class SessionManager:
    def __init__(self):
        self.sission_pool = {}
        self.session_factory = SessionFactory()
        self.tll_session_timeout = 10

    def get_session(self, device: Device) -> Session:
        if device.id in self.sission_pool:
            raise ValueError(f"Session for device {device.id} already exists")

        session = self.session_factory.build_session(device)
        self.sission_pool[device.id] = session

        return session
