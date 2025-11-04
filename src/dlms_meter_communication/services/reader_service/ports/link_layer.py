from abc import ABC, abstractmethod
from dlms_meter_communication.schemas.negotiated_params import NegotiatedParams


class ILinkLayer(ABC):
    """
    Link-layer abstraction for DLMS/COSEM.

    Implementations encapsulate the framing/transport details required to
    transmit and receive xDLMS APDUs over a specific communication profile,
    e.g., HDLC tunneling (flag-based frames, HCS/FCS, sequence numbers) or
    Wrapper over TCP/UDP (length-prefixed frames).

    Scope:
        - The link layer is responsible for APDU encapsulation/decapsulation,
          link negotiation (when applicable), basic flow control, and integrity
          checks at the frame level.
        - It is intentionally application-agnostic: it does not construct xDLMS
          APDUs (AARQ/GET/SET/etc.)—it only transports them as payload.
        - Implementations typically depend on an underlying transport (e.g.,
          an IConnection) and, in HDLC, a frame codec to serialize/parse frames.

    Lifecycle and state:
        - `negotiate()` must be called before regular APDU exchange when the
          profile requires it (e.g., HDLC SNRM/UA). For profiles without link
          negotiation (e.g., Wrapper), the method should be idempotent and
          return sensible defaults.
        - After negotiation succeeds, `send_apdu()` and `receive_apdu()` are
          used to exchange application PDUs.
        - Implementations should be considered non–thread-safe unless stated
          otherwise. Coordinate concurrent access at a higher level (Session).
    """

    @abstractmethod
    def negotiate(self, data: bytes) -> NegotiatedParams:
        """
        Perform link-layer negotiation and return the agreed parameters.

        Semantics:
            - For HDLC: build and exchange SNRM/UA (or equivalent) and derive
              negotiated values (e.g., max_info_rx/tx, window size). Validate
              link integrity and transition the link to a ready state.
            - For Wrapper: may act as a no-op and return default/static values.

        Args:
            data: Opaque, profile-specific input that may carry optional hints
                  or vendor extensions for negotiation. Implementations that do
                  not require it must ignore the value (e.g., Wrapper).

        Returns:
            NegotiatedParams: The effective link parameters to be used by the
            upper layer (e.g., for sizing buffers and pacing).

        Raises:
            TimeoutError: If negotiation does not complete within internal timeouts.
            ConnectionError: If the underlying transport is not usable/open.
            ValueError: If `data` is malformed for the profile in use.
            RuntimeError: For protocol violations or invalid peer responses.
        """
        raise NotImplementedError

    @abstractmethod
    def send_apdu(self, apdu: bytes) -> bytes:
        """
        Encapsulate and transmit one application PDU over the link.

        Expected behavior:
            - Frame the `apdu` according to the active profile (HDLC/Wrapper),
              apply any required integrity protection (e.g., HCS/FCS in HDLC),
              and send it over the underlying transport.
            - Block until the complete frame has been transmitted or a timeout/
              error occurs.
            - Return the exact raw bytes that were placed on the wire (encoded
              frame). This is useful for logging, tracing, and testing.

        Args:
            apdu: The xDLMS application PDU to be sent (already formed by the
                  application layer).

        Returns:
            bytes: The fully encoded frame that was actually transmitted.

        Raises:
            TimeoutError: If transmission cannot be completed in time.
            ConnectionError: If the link/transport is not ready or becomes unusable.
            ValueError: If the APDU size exceeds negotiated limits or framing rules.
            RuntimeError: For profile-specific framing errors.
        """
        raise NotImplementedError

    @abstractmethod
    def receive_apdu(self, timeout: float = 10.0) -> bytes:
        """
        Receive and return one complete application PDU from the link.

        Expected behavior:
            - Read raw bytes from the underlying transport until a complete
              frame is assembled (per profile rules), validate integrity
              (e.g., HCS/FCS in HDLC), remove link-layer headers, and return
              the inner APDU payload to the caller.
            - Must handle profile-specific flow control (e.g., HDLC RR/RNR/REJ)
              and reassembly if the profile splits payloads at the link level.

        Args:
            timeout: Maximum time to wait for a complete frame (seconds).
                     Implementations may fall back to a default if not provided.

        Returns:
            bytes: The received xDLMS APDU payload.

        Raises:
            TimeoutError: If a complete frame is not received in time.
            ConnectionError: If the transport is closed or unusable.
            RuntimeError: If frame validation fails (CRC/HCS/FCS) or the frame
                          is otherwise malformed/violates the profile.
        """
        raise NotImplementedError
