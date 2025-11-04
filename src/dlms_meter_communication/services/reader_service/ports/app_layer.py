from abc import ABC, abstractmethod

from dlms_meter_communication.schemas import Device, NegotiatedParams


class IAppLayer(ABC):
    """
    xDLMS/COSEM application-layer abstraction.

    Implementations are responsible for constructing, sending, and parsing
    xDLMS APDUs (e.g., AARQ/AARE, GET/SET/ACTION) on top of a link/profile
    layer. This interface is transport-agnostic: it does not perform framing
    or I/O by itself; those are delegated to a link-layer component.

    Responsibilities:
        - Session association and release (AARQ/AARE, optional RLRE/ABORT).
        - Enforcing negotiated constraints (MaxPDU, conformance bits).
        - Executing GET/SET/ACTION services, including block transfer (GET-Next)
          and optional selective access if the implementation supports it.
        - Surface protocol and semantic errors with precise exceptions.

    Concurrency & state:
        - Instances are typically bound to a single logical session. Unless an
          implementation explicitly states otherwise, treat them as NOT
          thread-safe and avoid concurrent operations on the same instance.

    Notes on method signatures:
        - `get`, `set`, and `action` are intentionally generic here. Concrete
          implementations should document the expected parameters (e.g., OBIS,
          attribute id, value, selective-access descriptors) and return types.
    """

    @abstractmethod
    def associate(self, device: Device, nps: NegotiatedParams) -> None:
        """
        Establish the application association with the peer (AARQ/AARE).

        Expected behavior:
            - Build and send AARQ according to the device configuration
              (authentication/security) and the effective link parameters.
            - Receive and validate AARE; update internal state with negotiated
              application-layer constraints (e.g., MaxPDU, conformance).
            - Fail fast with a descriptive error if association is rejected or
              if the peer’s parameters are incompatible with the implementation.

        Args:
            device: Resolved device context (addressing, security, referencing mode).
            nps: Link-layer negotiated parameters (e.g., max_info, window)
                 that may influence application behavior (e.g., pacing).

        Raises:
            TimeoutError: If the association handshake does not complete in time.
            PermissionError: If authentication fails or is not permitted.
            ConnectionError: If the underlying link is not ready/usable.
            RuntimeError: For protocol violations or unsupported peer settings.
            ValueError: If required device configuration is missing/invalid.
        """
        raise NotImplementedError

    @abstractmethod
    def get(self) -> None:
        """
        Execute an xDLMS GET service.

        Contract (to be specified by implementations):
            - Typical parameters include: OBIS (Logical Name), attribute id,
              and optional selective-access descriptors (range/list).
            - The method should honor MaxPDU/conformance; if the response
              exceeds MaxPDU, it must perform block transfer (GET-Next) until
              the full payload is retrieved.
            - Return type should be the decoded application value, optionally
              accompanied by metadata (unit, scaler, status).

        Raises:
            TimeoutError: On read timeout or incomplete block transfer.
            ConnectionError: If the link becomes unusable.
            RuntimeError: For protocol errors, invalid state, or conformance mismatch.
            ValueError: For invalid arguments (e.g., unsupported OBIS/attribute).
        """
        raise NotImplementedError

    @abstractmethod
    def set(self) -> None:
        """
        Execute an xDLMS SET service.

        Contract (to be specified by implementations):
            - Typical parameters include: OBIS, attribute id, and the encoded
              value to write (conforming to the attribute’s data type).
            - Must validate that the peer’s conformance permits SET for the
              requested attribute and that security policy (e.g., LLS/HLS,
              general protection) is satisfied.

        Raises:
            TimeoutError: On write timeout.
            PermissionError: If security level or access rights are insufficient.
            ConnectionError: If the link becomes unusable.
            RuntimeError: For protocol errors or type/encoding mismatches.
            ValueError: For invalid arguments or unsupported targets.
        """
        raise NotImplementedError

    @abstractmethod
    def action(self) -> None:
        """
        Execute an xDLMS ACTION (method invocation).

        Contract (to be specified by implementations):
            - Typical parameters include: OBIS, method id, and optional
              invocation parameters (DLMS-encoded).
            - Must respect negotiated conformance and any required protection
              (e.g., encryption/authentication at the application layer).

        Raises:
            TimeoutError: If the invocation does not complete in time.
            PermissionError: If the method requires a higher security level.
            ConnectionError: If the link becomes unusable.
            RuntimeError: For protocol errors or invalid method semantics.
            ValueError: For invalid arguments or unsupported methods.
        """
        raise NotImplementedError
