# Note: SessionManager is not exported here to avoid circular imports
# Import SessionManager directly from .session_manager when needed
from .session import Session

__all__ = ["Session"]
