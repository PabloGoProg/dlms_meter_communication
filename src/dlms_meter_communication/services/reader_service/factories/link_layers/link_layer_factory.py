"""
Abstract factory for creating link layer instances.

This module defines the base factory interface for creating different types of
link layers used in DLMS communication (HDLC, Wrapper, etc.).
"""

from __future__ import annotations
from abc import ABC, abstractmethod

from dlms_meter_communication.services.reader_service.ports import ILinkLayer
from dlms_meter_communication.schemas import CommunicationEndpoint


class LinkLayerFactory(ABC):
    """
    Abstract base class for link layer factories.

    This factory is responsible for creating link layer instances that manage
    the data link layer of the communication stack, including framing and connection handling.
    """

    @abstractmethod
    def create_link_layer(self, endpoint: CommunicationEndpoint) -> ILinkLayer:
        """
        Create a link layer instance for the given communication endpoint.

        Args:
            endpoint: Communication endpoint configuration

        Returns:
            ILinkLayer: Link layer instance

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError
