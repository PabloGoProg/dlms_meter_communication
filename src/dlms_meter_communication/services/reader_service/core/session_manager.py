"""
Session manager for handling DLMS meter communication sessions.

This module provides a context manager for managing the lifecycle of communication
sessions with DLMS meters, including session pooling and automatic cleanup.
"""

from typing import Optional, Dict
from uuid import UUID

from ..factories.sessions.session_factory import SessionFactory
from ..factories.sessions import AppLayerProviderType
from .session import Session
from dlms_meter_communication.schemas import Device


class SessionManager:
    """
    Context manager for managing DLMS communication sessions.

    This class handles the lifecycle of communication sessions, including:
    - Session creation and pooling
    - Session retrieval and validation
    - Automatic cleanup on context exit

    Usage:
        with SessionManager() as manager:
            session = manager.open_session(device)
            # Use session...
        # Sessions are automatically closed when exiting the context

    Attributes:
        session_pool: Dictionary mapping device IDs to active sessions
        session_factory: Factory for creating new sessions
        ttl_session_timeout: Time-to-live timeout for sessions in seconds
    """

    def __init__(
        self,
        ttl_session_timeout: int = 10,
        default_app_layer_provider: AppLayerProviderType = AppLayerProviderType.GURUX_COSEM,
    ):
        """
        Initialize the session manager.

        Args:
            ttl_session_timeout: Time-to-live timeout for sessions in seconds.
                                Default is 10 seconds.
            default_app_layer_provider: Default application layer provider to use
                                       when opening sessions. Default is GURUX_COSEM.
        """
        self.session_pool: Dict[UUID, Session] = {}
        self.session_factory = SessionFactory()
        self.ttl_session_timeout = ttl_session_timeout
        self.default_app_layer_provider = default_app_layer_provider

    def __enter__(self) -> "SessionManager":
        """
        Enter the context manager.

        Returns:
            SessionManager: Self instance for use in 'with' statement
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        Exit the context manager and cleanup all sessions.

        This method is called automatically when exiting the 'with' block.
        It closes and removes all active sessions from the pool.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred

        Returns:
            bool: False to propagate exceptions, True to suppress them
        """
        self.close_all_sessions()
        # Return False to propagate any exceptions that occurred
        return False

    def open_session(
        self, device: Device, app_layer_provider: Optional[AppLayerProviderType] = None
    ) -> Session:
        """
        Open a new communication session for a device.

        Creates a new session and adds it to the session pool. If a session
        for the device already exists, raises a ValueError.

        Args:
            device: Device schema containing device configuration
            app_layer_provider: Application layer provider to use (COSEM_NATIVE or
                               GURUX_COSEM). If not specified, uses the default
                               provider set during initialization.
        Returns:
            Session: Newly created communication session

        Raises:
            ValueError: If a session for the device already exists
        """
        if device.id in self.session_pool:
            raise ValueError(f"Session for device {device.id} already exists")

        provider = app_layer_provider or self.default_app_layer_provider
        session = self.session_factory.build_session(device, provider)

        self.session_pool[device.id] = session

        return session

    def get_session(self, device: Device) -> Optional[Session]:
        """
        Get an existing session for a device.

        Args:
            device: Device schema containing device configuration

        Returns:
            Session: Existing session if found, None otherwise
        """
        return self.session_pool.get(device.id)

    def get_or_create_session(
        self,
        device: Device,
        app_layer_provider: Optional[AppLayerProviderType] = None,
    ) -> Session:
        """
        Get an existing session or create a new one if it doesn't exist.

        This is a convenience method that combines get_session and open_session.

        Args:
            device: Device schema containing device configuration
            app_layer_provider: Application layer provider to use if creating a new
                               session. If not specified, uses the default provider.

        Returns:
            Session: Existing or newly created communication session
        """
        session = self.get_session(device)
        if session is None:
            session = self.open_session(device, app_layer_provider)
        return session

    def close_session(self, device: Device) -> bool:
        """
        Close and remove a session for a device.

        Args:
            device: Device schema containing device configuration

        Returns:
            bool: True if session was closed, False if no session existed
        """
        session = self.session_pool.pop(device.id, None)
        if session is not None:
            # Close the session's app layer connection if it exists
            if hasattr(session, "app_layer") and session.app_layer:
                try:
                    session.app_layer.disconnect()
                except Exception:
                    pass  # Ignore errors during cleanup
            return True
        return False

    def close_all_sessions(self) -> None:
        """
        Close and remove all active sessions.

        This method is automatically called when exiting the context manager.
        It attempts to close all sessions gracefully, ignoring any errors.
        """
        device_ids = list(self.session_pool.keys())
        for device_id in device_ids:
            session = self.session_pool.pop(device_id, None)
            if session is not None:
                # Attempt to disconnect gracefully
                if hasattr(session, "app_layer") and session.app_layer:
                    try:
                        session.app_layer.disconnect()
                    except Exception:
                        pass  # Ignore errors during cleanup

    def has_session(self, device: Device) -> bool:
        """
        Check if a session exists for a device.

        Args:
            device: Device schema containing device configuration

        Returns:
            bool: True if session exists, False otherwise
        """
        return device.id in self.session_pool

    def get_active_session_count(self) -> int:
        """
        Get the number of active sessions.

        Returns:
            int: Number of active sessions in the pool
        """
        return len(self.session_pool)
