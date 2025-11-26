from abc import ABC, abstractmethod

from dlms_meter_communication.schemas import Device, NegotiatedParams
from datetime import datetime


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
    def associate(self, device: Device) -> None:
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
    def get_association_view(self) -> None:
        """
        Get the association view from the peer.

        Returns:
            The association view from the peer.
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, obis: str) -> None:
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

    @abstractmethod
    def get_profile_by_date_range(
        self, obis: str, start_date: datetime, end_date: datetime
    ) -> list:
        """
        Extrae las lecturas de un perfil genérico por rango de fechas.

        Este método ejecuta una lectura selectiva de un objeto Profile Generic
        usando el método de acceso por rango de fechas. Los perfiles genéricos
        almacenan series temporales de datos (load profiles, event logs, etc.)
        y este método permite extraer únicamente los registros dentro de un
        período específico.

        Contract (to be specified by implementations):
            - Debe construir y enviar una petición GET con selective access
              usando el access descriptor apropiado para rango de fechas (range).
            - Debe manejar automáticamente el block transfer si la respuesta
              excede el MaxPDU negociado.
            - El resultado debe ser una lista de filas donde cada fila contiene
              los valores correspondientes a los capture objects definidos en
              el perfil (típicamente: timestamp, valores medidos).

        Args:
            obis: Código OBIS del objeto Profile Generic (ej: "1.0.99.1.0.255")
            start_date: Fecha y hora de inicio del rango
            end_date: Fecha y hora de fin del rango

        Returns:
            list: Lista de filas del perfil. Cada fila es una lista de valores
                  correspondientes a las columnas definidas en captureObjects.
                  Típicamente: [datetime, value1, value2, ...].
                  Retorna lista vacía si no hay datos en el rango.

        Raises:
            TimeoutError: Si la lectura no se completa a tiempo o el block
                         transfer no finaliza.
            ConnectionError: Si el enlace se vuelve inusable durante la operación.
            RuntimeError: Si hay errores de protocolo, el perfil no soporta
                         acceso selectivo, o hay problemas con la conformance.
            ValueError: Si los argumentos son inválidos (OBIS incorrecto,
                       fechas inválidas, start_date > end_date).
        """
        raise NotImplementedError
