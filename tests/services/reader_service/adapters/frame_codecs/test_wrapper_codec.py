"""Tests for WrapperCodec frame codec implementation.

This module tests the DLMS/COSEM wrapper header encoding and decoding
functionality, including edge cases and error conditions.
"""

import pytest
import struct

from dlms_meter_communication.services.reader_service.adapterss.codecs.wrapper_codec import (
    WrapperCodec,
)


def test_encode_basic_payload() -> None:
    """Test encoding a basic payload with correct header structure."""
    codec = WrapperCodec(source_wport=16, destination_wport=1)
    payload = b"\x01\x02\x03\x04"
    encoded = codec.encode(payload)

    assert len(encoded) == 12  # 8 bytes header + 4 bytes payload
    ver, src, dst, p_len = struct.unpack(">4H", encoded[:8])
    assert ver == 1
    assert src == 16
    assert dst == 1
    assert p_len == 4
    assert encoded[8:] == payload


def test_encode_empty_payload_raises_error() -> None:
    """Test that encoding an empty payload raises ValueError."""
    codec = WrapperCodec(source_wport=16, destination_wport=1)
    with pytest.raises(ValueError, match="Payload cannot be empty"):
        codec.encode(b"")


def test_encode_already_wrapped_returns_unchanged() -> None:
    """Test that encoding an already wrapped payload returns it unchanged."""
    codec = WrapperCodec(source_wport=16, destination_wport=1)
    payload = b"\x00\x01\x00\x10\x00\x01\x00\x04\x01\x02\x03\x04"
    encoded = codec.encode(payload)
    assert encoded == payload


def test_encode_payload_exceeds_max_length_raises_error() -> None:
    """Test that encoding a payload exceeding max length raises ValueError."""
    codec = WrapperCodec(source_wport=16, destination_wport=1, max_payload_length=100)
    large_payload = b"x" * 101
    with pytest.raises(ValueError, match="Payload too large"):
        codec.encode(large_payload)


def test_decode_complete_frame() -> None:
    """Test decoding a complete frame from buffer."""
    codec = WrapperCodec(source_wport=16, destination_wport=1)
    payload = b"\x01\x02\x03\x04"
    header = struct.pack(">4H", 1, 16, 1, len(payload))
    buffer = header + payload

    decoded, remaining = codec.decode(buffer)
    assert decoded == payload
    assert remaining is None or remaining == b""


def test_decode_incomplete_header_returns_none() -> None:
    """Test that decoding with incomplete header returns None and original buffer."""
    codec = WrapperCodec(source_wport=16, destination_wport=1)
    incomplete_buffer = b"\x00\x01\x00\x10"
    decoded, remaining = codec.decode(incomplete_buffer)
    assert decoded is None
    assert remaining == incomplete_buffer


def test_decode_incomplete_payload_returns_none() -> None:
    """Test that decoding with incomplete payload returns None and original buffer."""
    codec = WrapperCodec(source_wport=16, destination_wport=1)
    header = struct.pack(">4H", 1, 16, 1, 10)
    incomplete_buffer = header + b"\x01\x02"
    decoded, remaining = codec.decode(incomplete_buffer)
    assert decoded is None
    assert remaining == incomplete_buffer


def test_decode_multiple_frames() -> None:
    """Test decoding first frame when multiple frames are present in buffer."""
    codec = WrapperCodec(source_wport=16, destination_wport=1)
    payload1 = b"\x01\x02"
    payload2 = b"\x03\x04"
    header1 = struct.pack(">4H", 1, 16, 1, len(payload1))
    header2 = struct.pack(">4H", 1, 16, 1, len(payload2))
    buffer = header1 + payload1 + header2 + payload2

    decoded, remaining = codec.decode(buffer)
    assert decoded == payload1
    assert remaining == header2 + payload2


def test_decode_invalid_version_raises_error() -> None:
    """Test that decoding with invalid version raises ValueError."""
    codec = WrapperCodec(source_wport=16, destination_wport=1)
    invalid_header = struct.pack(">4H", 2, 16, 1, 4)
    buffer = invalid_header + b"\x01\x02\x03\x04"
    with pytest.raises(ValueError, match="Unsupported wrapper version"):
        codec.decode(buffer)


def test_decode_invalid_source_port_raises_error() -> None:
    """Test that decoding with invalid source port raises ValueError."""
    codec = WrapperCodec(source_wport=16, destination_wport=1)
    invalid_header = struct.pack(">4H", 1, 17, 1, 4)
    buffer = invalid_header + b"\x01\x02\x03\x04"
    with pytest.raises(ValueError, match="Invalid source port"):
        codec.decode(buffer)


def test_decode_invalid_destination_port_raises_error() -> None:
    """Test that decoding with invalid destination port raises ValueError."""
    codec = WrapperCodec(source_wport=16, destination_wport=1)
    invalid_header = struct.pack(">4H", 1, 16, 2, 4)
    buffer = invalid_header + b"\x01\x02\x03\x04"
    with pytest.raises(ValueError, match="Invalid destination port"):
        codec.decode(buffer)


def test_decode_zero_length_raises_error() -> None:
    """Test that decoding with zero payload length raises ValueError."""
    codec = WrapperCodec(source_wport=16, destination_wport=1)
    invalid_header = struct.pack(">4H", 1, 16, 1, 0)
    buffer = invalid_header
    with pytest.raises(ValueError, match="Invalid payload length"):
        codec.decode(buffer)


def test_decode_exceeds_max_length_raises_error() -> None:
    """Test that decoding with payload length exceeding max raises ValueError."""
    codec = WrapperCodec(source_wport=16, destination_wport=1, max_payload_length=100)
    invalid_header = struct.pack(">4H", 1, 16, 1, 101)
    buffer = invalid_header + b"x" * 101
    with pytest.raises(ValueError, match="Invalid payload length"):
        codec.decode(buffer)


def test_is_wrapped_valid_message_returns_true() -> None:
    """Test that is_wrapped returns True for a valid wrapped message."""
    codec = WrapperCodec(source_wport=16, destination_wport=1)
    payload = b"\x01\x02\x03\x04"
    header = struct.pack(">4H", 1, 16, 1, len(payload))
    wrapped = header + payload
    assert codec.is_wrapped(wrapped) is True


def test_is_wrapped_short_message_returns_false() -> None:
    """Test that is_wrapped returns False for messages shorter than 8 bytes."""
    codec = WrapperCodec(source_wport=16, destination_wport=1)
    short_message = b"\x01\x02\x03"
    assert codec.is_wrapped(short_message) is False


def test_is_wrapped_invalid_version_returns_false() -> None:
    """Test that is_wrapped returns False for invalid version."""
    codec = WrapperCodec(source_wport=16, destination_wport=1)
    invalid_header = struct.pack(">4H", 2, 16, 1, 4)
    message = invalid_header + b"\x01\x02\x03\x04"
    assert codec.is_wrapped(message) is False


def test_is_wrapped_invalid_ports_returns_false() -> None:
    """Test that is_wrapped returns False for invalid source/destination ports."""
    codec = WrapperCodec(source_wport=16, destination_wport=1)
    invalid_header = struct.pack(">4H", 1, 17, 1, 4)
    message = invalid_header + b"\x01\x02\x03\x04"
    assert codec.is_wrapped(message) is False


def test_is_wrapped_length_mismatch_returns_false() -> None:
    """Test that is_wrapped returns False when length doesn't match message size."""
    codec = WrapperCodec(source_wport=16, destination_wport=1)
    invalid_header = struct.pack(">4H", 1, 16, 1, 10)
    message = invalid_header + b"\x01\x02\x03\x04"
    assert codec.is_wrapped(message) is False


def test_encode_decode_roundtrip() -> None:
    """Test that encode followed by decode returns original payload."""
    codec = WrapperCodec(source_wport=16, destination_wport=1)
    original_payload = b"\x01\x02\x03\x04\x05\x06\x07\x08"
    encoded = codec.encode(original_payload)
    decoded, remaining = codec.decode(encoded)
    assert decoded == original_payload
    assert remaining is None or remaining == b""
