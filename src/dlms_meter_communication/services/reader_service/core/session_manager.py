from .session_factory import Session, SessionFactory


class SessionManager:
    def __init__(self):
        self.sission_pool = {}
        self.session_factory = SessionFactory()
        self.tll_session_timeout = 10
