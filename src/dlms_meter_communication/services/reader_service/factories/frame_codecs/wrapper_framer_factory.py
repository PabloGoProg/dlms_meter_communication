"""
Factory for creating Wrapper frame codec instances.

This module provides a concrete implementation of the FrameCodecFactory
for creating Wrapper protocol frame codecs, typically used in TCP/IP communications.
"""

from __future__ import annotations

from .frame_codec_factory import FrameCodecFactory
from ...adapterss.codecs.wrapper_codec import WrapperCodec
from dlms_meter_communication.schemas import CommunicationEndpoint


class WrapperFramerFactory(FrameCodecFactory):
    """
    Factory for creating Wrapper frame codec instances.

    This factory creates frame codecs that handle the Wrapper protocol framing,
    which is commonly used in TCP/IP network communications for DLMS/COSEM.
    """

    def create_frame_codec(self, endpoint: CommunicationEndpoint) -> WrapperCodec:
        """
        Create a Wrapper frame codec instance.

        Args:
            endpoint: Communication endpoint configuration (not used for Wrapper)

        Returns:
            WrapperCodec: Wrapper frame codec with default port configuration
                         (source_wport=16, destination_wport=1)
        """
        # Default Wrapper ports: client=16, server=1
        return WrapperCodec(
            source_wport=16,
            destination_wport=1,
        )
