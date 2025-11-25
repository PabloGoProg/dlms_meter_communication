"""
Abstract factory for creating application layer instances.

This module defines the base factory interface for creating different types of
application layers used in DLMS/COSEM communication (Native COSEM, Gurux, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...ports import IAppLayer
from dlms_meter_communication.schemas import Device


class AppLayerFactory(ABC):
    """
    Abstract base class for application layer factories.

    This factory is responsible for creating application layer instances that handle
    the DLMS/COSEM protocol communication at the application level, including
    association management, data access, and COSEM object operations.
    """

    @abstractmethod
    def create_app_layer(self, device: Device) -> IAppLayer:
        """
        Create an application layer instance for the given device.

        Args:
            device: Device configuration

        Returns:
            IAppLayer: Application layer instance

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError
