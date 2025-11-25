"""
Factory for creating HDLC frame codec instances.

This module provides a concrete implementation of the FrameCodecFactory
for creating HDLC (High-Level Data Link Control) frame codecs.
"""

from __future__ import annotations

from .frame_codec_factory import FrameCodecFactory
from ...adapterss.codecs.hdlc_frame_codec import HDLCFrameCodec
from dlms_meter_communication.schemas import CommunicationEndpoint


class HDLCFramerFactory(FrameCodecFactory):
    """
    Factory for creating HDLC frame codec instances.

    This factory creates frame codecs that handle HDLC protocol framing,
    which is commonly used in serial and optical port communications.
    """

    def create_frame_codec(self, endpoint: CommunicationEndpoint) -> HDLCFrameCodec:
        """
        Create an HDLC frame codec instance.

        Args:
            endpoint: Communication endpoint configuration (not used for HDLC)

        Returns:
            HDLCFrameCodec: HDLC frame codec instance with default configuration
        """
        return HDLCFrameCodec()
