from .core.session_manager import SessionManager

from dlms_meter_communication.schemas.device import Device
from datetime import datetime


class ReaderService:
    def __init__(self):
        self.session_manager = SessionManager()

    def get_association_view(self, device: Device) -> list[dict]:
        with self.session_manager as manager:
            try:
                _session = manager.get_or_create_session(device)
                _session.open()
                return _session.get_association_view()
            except Exception as e:
                raise RuntimeError(
                    f"Error getting association view from device {device.id}: {e}"
                )
            finally:
                manager.close_session(device)

    def read_single(self, device: Device, obis: str) -> bytes:
        with self.session_manager as manager:
            try:
                _session = manager.get_or_create_session(device)
                _session.open()
                # data = _session.get(obis)
                return "test data"
            except Exception as e:
                raise RuntimeError(
                    f"Error reading single attribute {obis} from device {device.id}: {e}"
                )
            finally:
                manager.close_session(device)

    def read_multiple(self, device: Device, obis: list[str]) -> bytes:
        pass

    def get_common_data(self, device: Device) -> dict:
        """
        Read common electrical measurement data from the meter.

        This method reads standard OBIS codes for:
        - Active energy (import/export)
        - Reactive energy (import/export)
        - Instantaneous values (power, voltage, current per phase)
        - Power factor
        - Frequency

        Args:
            device: Device to read from

        Returns:
            dict: Dictionary containing all common measurements organized by category
        """
        # Standard OBIS codes for common electrical measurements
        obis_codes = {
            # Active Energy (kWh)
            "active_energy_import": "1.1.1.8.0.255",  # Total active energy import
            "active_energy_export": "1.1.2.8.0.255",  # Total active energy export
            # Reactive Energy (kVArh)
            "reactive_energy_import": "1.1.3.8.0.255",  # Total reactive energy import
            "reactive_energy_export": "1.1.4.8.0.255",  # Total reactive energy export
            # Instantaneous Power (W, VAr, VA)
            "active_power_total": "1.1.1.7.0.255",  # Total instantaneous active power
            "reactive_power_total": "1.0.3.7.0.255",  # Total instantaneous reactive power
            "apparent_power_total": "1.0.9.7.0.255",  # Total instantaneous apparent power
            # Voltage per phase (V)
            "voltage_l1": "1.1.32.7.0.255",  # Instantaneous voltage L1
            "voltage_l2": "1.1.52.7.0.255",  # Instantaneous voltage L2
            "voltage_l3": "1.1.72.7.0.255",  # Instantaneous voltage L3
            # Current per phase (A)
            "current_l1": "1.1.31.7.0.255",  # Instantaneous current L1
            "current_l2": "1.1.51.7.0.255",  # Instantaneous current L2
            "current_l3": "1.1.71.7.0.255",  # Instantaneous current L3
            # Power per phase (W)
            "active_power_l1": "1.0.21.7.0.255",  # Instantaneous active power L1
            "active_power_l2": "1.0.41.7.0.255",  # Instantaneous active power L2
            "active_power_l3": "1.0.61.7.0.255",  # Instantaneous active power L3
            # Power Factor
            "power_factor_total": "1.0.13.7.0.255",  # Total power factor
            "power_factor_l1": "1.1.33.7.0.255",  # Power factor L1
            "power_factor_l2": "1.1.53.7.0.255",  # Power factor L2
            "power_factor_l3": "1.1.73.7.0.255",  # Power factor L3
            # Frequency (Hz)
            "frequency": "1.1.14.7.0.255",  # Frequency
        }

        with self.session_manager as manager:
            try:
                _session = manager.get_or_create_session(device)
                _session.open()

                results = {
                    "device_id": str(device.id),
                    "energy": {},
                    "instantaneous": {
                        "total": {},
                        "phase_l1": {},
                        "phase_l2": {},
                        "phase_l3": {},
                    },
                    "power_factor": {},
                    "frequency": None,
                    "errors": [],
                }

                # Read all OBIS codes
                for key, obis in obis_codes.items():
                    try:
                        value = _session.get(obis)
                        print(value)

                        # Organize values by category
                        if "energy" in key:
                            results["energy"][key] = value
                        elif key == "frequency":
                            results["frequency"] = value
                        elif "power_factor" in key:
                            results["power_factor"][key] = value
                        elif key.endswith("_total"):
                            results["instantaneous"]["total"][key] = value
                        elif key.endswith("_l1"):
                            results["instantaneous"]["phase_l1"][key] = value
                        elif key.endswith("_l2"):
                            results["instantaneous"]["phase_l2"][key] = value
                        elif key.endswith("_l3"):
                            results["instantaneous"]["phase_l3"][key] = value

                    except Exception as e:
                        # Log individual read errors but continue with other values
                        results["errors"].append(
                            {"obis": obis, "key": key, "error": str(e)}
                        )

                return results

            except Exception as e:
                raise RuntimeError(
                    f"Error reading common data from device {device.id}: {e}"
                )
            finally:
                manager.close_session(device)

    def get_profile_by_date_range(
        self, device: Device, obis: str, start_date: datetime, end_date: datetime
    ) -> list:
        """
        Extrae las lecturas de un perfil genérico por rango de fechas.

        Este método lee datos históricos de un perfil genérico (load profile, event log)
        dentro de un rango de fechas específico. Los perfiles genéricos almacenan series
        temporales de datos como consumo de energía, eventos del medidor, etc.

        Args:
            device: Dispositivo del cual leer el perfil
            obis: Código OBIS del perfil genérico (ej: "1.0.99.1.0.255")
            start_date: Fecha y hora de inicio del rango
            end_date: Fecha y hora de fin del rango

        Returns:
            list: Lista de filas (entries) del perfil. Cada fila es una lista de valores
                  correspondientes a las columnas definidas en el perfil (timestamp, valores).

        Raises:
            ValueError: Si los parámetros son inválidos
            RuntimeError: Si ocurre un error durante la lectura

        Example:
            >>> from datetime import datetime, timedelta
            >>> end = datetime.now()
            >>> start = end - timedelta(days=1)
            >>> data = service.get_profile_by_date_range(device, "1.0.99.1.0.255", start, end)
            >>> for row in data:
            ...     print(f"Timestamp: {row[0]}, Values: {row[1:]}")
        """
        with self.session_manager as manager:
            try:
                _session = manager.get_or_create_session(device)
                _session.open()

                # Validar parámetros
                if not obis:
                    raise ValueError("El código OBIS no puede estar vacío")
                if start_date is None or end_date is None:
                    raise ValueError("Las fechas de inicio y fin son requeridas")
                if start_date > end_date:
                    raise ValueError(
                        "La fecha de inicio debe ser anterior a la fecha de fin"
                    )

                # Llamar al método del adaptador de aplicación
                data = _session.get_profile_by_date_range(obis, start_date, end_date)

                return data

            except ValueError as e:
                # Re-lanzar errores de validación
                raise e
            except Exception as e:
                raise RuntimeError(
                    f"Error leyendo perfil {obis} del dispositivo {device.id} "
                    f"en rango {start_date} - {end_date}: {e}"
                )
            finally:
                manager.close_session(device)
