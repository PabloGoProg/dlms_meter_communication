"""
Abstract factory for creating frame codec instances.

This module defines the base factory interface for creating different types of
frame codecs used in DLMS communication (HDLC, Wrapper, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...ports import IFrameCodec
from dlms_meter_communication.schemas import CommunicationEndpoint


class FrameCodecFactory(ABC):
    """
    Abstract base class for frame codec factories.

    This factory is responsible for creating frame codec instances that handle
    the encoding and decoding of frames in DLMS communication protocols.
    """

    @abstractmethod
    def create_frame_codec(self, endpoint: CommunicationEndpoint) -> IFrameCodec:
        """
        Create a frame codec instance for the given communication endpoint.

        Args:
            endpoint: Communication endpoint configuration

        Returns:
            IFrameCodec: Frame codec instance

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError
