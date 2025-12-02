from abc import ABC, abstractmethod
from dlms_meter_communication.schemas.device import Device


class IAddressResolver(ABC):
    """
    Addressing resolver for DLMS/COSEM sessions.

    Implementations provide the addressing parameters required by the link and
    application layers for a given device/endpoint context. Typical usages:

      - HDLC tunneling: resolve **client** and **server** HDLC addresses (SAPs).
      - Application layer: decide **referencing mode** (Logical Name vs Short Name).
      - Wrapper/IP profiles: SAPs may not appear on the wire, but the
        application layer can still depend on these values for association.

    Design notes:
      - Implementations should be pure/resolutive (no side effects) and may read
        from configuration, per-endpoint overrides, or vendor-specific rules.
      - Prefer determinism: given the same `Device`, results should be stable.
      - Thread-safety is implementation-defined; assume NOT thread-safe unless
        otherwise documented.
    """

    @abstractmethod
    def resolve_client_address(self, device: Device) -> int:
        """
        Return the client (initiator) HDLC address (SAP C) to use for this device.

        Resolution guidelines:
            - Use endpoint-specific overrides if present; otherwise fall back to
              device defaults or organizational policy (e.g., 16 is common).
            - Validate the numeric range accepted by your stack (1- or 2-byte SAPs,
              depending on meter/vendor). Do not silently coerce invalid values.

        Args:
            device: Fully populated device/endpoint descriptor.

        Returns:
            int: The client HDLC address (SAP C).

        Raises:
            ValueError: If the resolved address is out of supported range or not
                        permitted by the device/profile configuration.
        """
        raise NotImplementedError

    @abstractmethod
    def resolve_server_address(self, device: Device) -> int:
        """
        Return the server (meter) HDLC address (SAP S) for this device/endpoint.

        Resolution guidelines:
            - Check endpoint-specific configuration first (many meters expose
              different SAPs depending on medium/profile).
            - Apply vendor-specific addressing rules where required (e.g., 1 vs 2 bytes).
            - Do not guess if configuration is ambiguous—raise a clear error.

        Args:
            device: Fully populated device/endpoint descriptor.

        Returns:
            int: The server HDLC address (SAP S).

        Raises:
            ValueError: If the resolved address is invalid or cannot be determined.
        """
        raise NotImplementedError

    @abstractmethod
    def resolve_logical_name(self, device: Device) -> bool:
        """
        Indicate whether the session should use Logical Name (LN) referencing.

        Semantics:
            - True  → use LN referencing (recommended for MVP).
            - False → use Short Name (SN) referencing.
            - Implementations may derive this from endpoint-level flags, device
              capabilities, or policy. When in doubt, prefer explicit config.

        Args:
            device: Fully populated device/endpoint descriptor.

        Returns:
            bool: True for LN referencing, False for SN.

        Raises:
            ValueError: If the referencing mode cannot be determined unambiguously.
        """
        raise NotImplementedError
