from abc import ABC, abstractmethod


class IFrameCodec(ABC):
    """
    Frame-level encoder/decoder abstraction.

    Implementations convert a raw payload (e.g., an xDLMS APDU) into a
    link-layer frame suitable for transmission on the wire, and parse incoming
    byte buffers to extract exactly one complete frame at a time.

    Scope:
        - Responsible for framing/deframing and frame-level integrity checks
          (e.g., HDLC HCS/FCS, length-prefix validation in Wrapper).
        - Stateless by default: no transport I/O, no buffering beyond what is
          passed in, and no session state (sequence numbers/flow control belong
          to the link layer, not the codec).
        - Does NOT interpret application payloads (APDUs); it only wraps/unwraps
          them in frames as defined by the profile.

    Common examples:
        - HDLC: add 0x7E flags, address/control fields (as instructed by the
          link layer), frame format with length, HCS/FCS calculation, and
          byte-stuffing if required by the variant.
        - Wrapper: prepend the fixed-length header (version, src/dst wPort,
          length), verify length against the available bytes.
    """

    @abstractmethod
    def encode(self, payload: bytes) -> bytes:
        """
        Encode a payload into one complete outbound frame.

        Expected behavior:
            - Produce a fully formed frame that is ready to be sent over the
              underlying transport, including any required headers, length,
              and integrity fields.
            - Validate payload size against profile limits if applicable and
              raise on violations (do not silently truncate).

        Args:
            payload: Opaque inner payload (typically an application PDU) to be
                     encapsulated in a single link-layer frame.

        Returns:
            bytes: The wire-ready, fully encoded frame.

        Raises:
            ValueError: If the payload is invalid for the profile or exceeds
                        negotiated/static size limits.
            RuntimeError: For profile-specific framing errors (e.g., integrity
                          calculation failure).
        """
        raise NotImplementedError

    @abstractmethod
    def decode(self, buffer: bytes) -> tuple[bytes | None, bytes | None]:
        """
        Attempt to extract exactly one complete frame from `buffer`.

        Contract:
            - If `buffer` contains a well-formed, complete frame at its start:
              return (frame_bytes, remaining_buffer), where `frame_bytes` is the
              *decoded frame payload* (i.e., the inner bytes after removing the
              link-layer header/trailer) **or** the *raw frame* depending on
              the codec’s documented behavior. Implementations must document
              which of the two they return; a common pattern is to return the
              *raw frame bytes* and leave payload extraction to the link layer.
            - If `buffer` does NOT yet contain a complete frame (i.e., more
              bytes are required), return (None, buffer) to signal the caller
              to append more data and retry.
            - If the leading bytes are irrecoverably malformed (e.g., bad
              header, invalid length, CRC/HCS/FCS mismatch) and cannot be
              recovered by discarding a prefix, raise an exception rather than
              looping indefinitely.

        Partial and multi-frame input:
            - The method must never block; it operates purely on the provided
              bytes.
            - If multiple frames are present, only the first complete frame is
              returned; the remainder stays in `remaining_buffer` for subsequent
              calls.

        Args:
            buffer: A byte buffer that may contain zero, partial, or multiple
                    back-to-back frames.

        Returns:
            tuple[bytes | None, bytes | None]:
                - First element:
                    * `bytes` → one complete frame (payload or raw frame, per
                      implementation’s contract).
                    * `None`  → incomplete; need more data.
                - Second element:
                    * `bytes` → the unconsumed remainder of `buffer` after the
                      extracted frame (or the original `buffer` if incomplete).
                    * `None`  → may be used by implementations that manage the
                      buffer externally; typical implementations should return
                      a `bytes` remainder.

        Raises:
            ValueError: For structurally invalid frames (e.g., impossible length).
            RuntimeError: For integrity check failures (CRC/HCS/FCS) or other
                          profile-specific violations that cannot be recovered
                          by simply waiting for more data.
        """
        raise NotImplementedError
