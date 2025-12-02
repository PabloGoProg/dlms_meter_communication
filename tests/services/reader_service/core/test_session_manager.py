"""
Tests for the SessionManager in the reader service core.

Tests that the SessionManager correctly implements the context manager protocol,
manages session lifecycle, handles session pooling, and performs automatic cleanup.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from dlms_meter_communication.schemas import Device
from dlms_meter_communication.services.reader_service.core.session_manager import (
    SessionManager,
)
from dlms_meter_communication.services.reader_service.core.session import Session
from dlms_meter_communication.services.reader_service.factories.sessions import (
    AppLayerProviderType,
)


def _build_device(**overrides) -> Device:
    """
    Builds a `Device` for testing with default values that
    can be overridden according to the use case.
    """

    data = {
        "id": uuid.uuid4(),
        "name": "Test Device",
        "description": "Test device description",
        "serial_number": "SN123456",
        "brand": "Test Brand",
        "model": "Test Model",
        "communication_endpoints": [],
        "device_addressings": [],
    }
    data.update(overrides)
    return Device(**data)


def test_session_manager_inicializa_con_valores_por_defecto() -> None:
    """
    Tests that SessionManager initializes with default values.
    """

    manager = SessionManager()

    assert manager.session_pool == {}
    assert manager.ttl_session_timeout == 10
    assert manager.default_app_layer_provider == AppLayerProviderType.GURUX_COSEM
    assert manager.session_factory is not None


def test_session_manager_inicializa_con_valores_personalizados() -> None:
    """
    Tests that SessionManager initializes with custom values.
    """

    manager = SessionManager(
        ttl_session_timeout=30,
        default_app_layer_provider=AppLayerProviderType.COSEM_NATIVE,
    )

    assert manager.ttl_session_timeout == 30
    assert manager.default_app_layer_provider == AppLayerProviderType.COSEM_NATIVE


def test_session_manager_implementa_protocolo_context_manager() -> None:
    """
    Tests that SessionManager implements the context manager protocol.
    """

    manager = SessionManager()

    assert hasattr(manager, "__enter__")
    assert hasattr(manager, "__exit__")
    assert callable(manager.__enter__)
    assert callable(manager.__exit__)


def test_session_manager_enter_retorna_self() -> None:
    """
    Tests that __enter__ returns the manager instance itself.
    """

    manager = SessionManager()

    result = manager.__enter__()

    assert result is manager


def test_session_manager_como_context_manager_usa_with() -> None:
    """
    Tests that SessionManager can be used with 'with' statement.
    """

    with SessionManager() as manager:
        assert isinstance(manager, SessionManager)
        assert manager.session_pool == {}


def test_open_session_crea_nueva_sesion_y_la_agrega_al_pool() -> None:
    """
    Tests that open_session creates a new session and adds it to the pool.
    """

    device = _build_device()
    manager = SessionManager()

    mock_session = MagicMock(spec=Session)

    with patch.object(
        manager.session_factory, "build_session", return_value=mock_session
    ) as mock_build:
        session = manager.open_session(device)

    mock_build.assert_called_once_with(device, AppLayerProviderType.GURUX_COSEM)
    assert session is mock_session
    assert device.id in manager.session_pool
    assert manager.session_pool[device.id] is mock_session


def test_open_session_usa_proveedor_especifico_cuando_se_proporciona() -> None:
    """
    Tests that open_session uses the specified app layer provider.
    """

    device = _build_device()
    manager = SessionManager()

    mock_session = MagicMock(spec=Session)

    with patch.object(
        manager.session_factory, "build_session", return_value=mock_session
    ) as mock_build:
        session = manager.open_session(
            device, app_layer_provider=AppLayerProviderType.COSEM_NATIVE
        )

    mock_build.assert_called_once_with(device, AppLayerProviderType.COSEM_NATIVE)
    assert session is mock_session


def test_open_session_lanza_error_si_sesion_ya_existe() -> None:
    """
    Tests that open_session raises ValueError if session already exists.
    """

    device = _build_device()
    manager = SessionManager()

    mock_session = MagicMock(spec=Session)

    with patch.object(
        manager.session_factory, "build_session", return_value=mock_session
    ):
        manager.open_session(device)

        # Try to open again - should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            manager.open_session(device)

    assert f"Session for device {device.id} already exists" in str(exc_info.value)


def test_get_session_retorna_sesion_existente() -> None:
    """
    Tests that get_session returns an existing session.
    """

    device = _build_device()
    manager = SessionManager()

    mock_session = MagicMock(spec=Session)

    with patch.object(
        manager.session_factory, "build_session", return_value=mock_session
    ):
        opened_session = manager.open_session(device)

    retrieved_session = manager.get_session(device)

    assert retrieved_session is opened_session
    assert retrieved_session is mock_session


def test_get_session_retorna_none_si_no_existe() -> None:
    """
    Tests that get_session returns None if session doesn't exist.
    """

    device = _build_device()
    manager = SessionManager()

    session = manager.get_session(device)

    assert session is None


def test_get_or_create_session_retorna_existente_si_ya_existe() -> None:
    """
    Tests that get_or_create_session returns existing session if it exists.
    """

    device = _build_device()
    manager = SessionManager()

    mock_session = MagicMock(spec=Session)

    with patch.object(
        manager.session_factory, "build_session", return_value=mock_session
    ) as mock_build:
        # First call creates the session
        first_session = manager.get_or_create_session(device)

        # Second call should return the same session
        second_session = manager.get_or_create_session(device)

    # build_session should only be called once
    mock_build.assert_called_once()
    assert first_session is second_session
    assert first_session is mock_session


def test_get_or_create_session_crea_nueva_si_no_existe() -> None:
    """
    Tests that get_or_create_session creates a new session if it doesn't exist.
    """

    device = _build_device()
    manager = SessionManager()

    mock_session = MagicMock(spec=Session)

    with patch.object(
        manager.session_factory, "build_session", return_value=mock_session
    ) as mock_build:
        session = manager.get_or_create_session(device)

    mock_build.assert_called_once_with(device, AppLayerProviderType.GURUX_COSEM)
    assert session is mock_session
    assert device.id in manager.session_pool


def test_has_session_retorna_true_si_existe() -> None:
    """
    Tests that has_session returns True if session exists.
    """

    device = _build_device()
    manager = SessionManager()

    mock_session = MagicMock(spec=Session)

    with patch.object(
        manager.session_factory, "build_session", return_value=mock_session
    ):
        manager.open_session(device)

    assert manager.has_session(device) is True


def test_has_session_retorna_false_si_no_existe() -> None:
    """
    Tests that has_session returns False if session doesn't exist.
    """

    device = _build_device()
    manager = SessionManager()

    assert manager.has_session(device) is False


def test_get_active_session_count_retorna_numero_correcto() -> None:
    """
    Tests that get_active_session_count returns correct number of sessions.
    """

    device1 = _build_device()
    device2 = _build_device()
    manager = SessionManager()

    assert manager.get_active_session_count() == 0

    mock_session = MagicMock(spec=Session)

    with patch.object(
        manager.session_factory, "build_session", return_value=mock_session
    ):
        manager.open_session(device1)
        assert manager.get_active_session_count() == 1

        manager.open_session(device2)
        assert manager.get_active_session_count() == 2


def test_close_session_cierra_y_remueve_sesion() -> None:
    """
    Tests that close_session closes and removes a session from the pool.
    """

    device = _build_device()
    manager = SessionManager()

    mock_app_layer = MagicMock()
    mock_session = MagicMock(spec=Session)
    mock_session.app_layer = mock_app_layer

    with patch.object(
        manager.session_factory, "build_session", return_value=mock_session
    ):
        manager.open_session(device)

    assert manager.has_session(device) is True

    result = manager.close_session(device)

    assert result is True
    assert manager.has_session(device) is False
    mock_app_layer.disconnect.assert_called_once()


def test_close_session_retorna_false_si_no_existe() -> None:
    """
    Tests that close_session returns False if session doesn't exist.
    """

    device = _build_device()
    manager = SessionManager()

    result = manager.close_session(device)

    assert result is False


def test_close_session_ignora_errores_en_disconnect() -> None:
    """
    Tests that close_session ignores errors when disconnecting.
    """

    device = _build_device()
    manager = SessionManager()

    mock_app_layer = MagicMock()
    mock_app_layer.disconnect.side_effect = Exception("Disconnect error")
    mock_session = MagicMock(spec=Session)
    mock_session.app_layer = mock_app_layer

    with patch.object(
        manager.session_factory, "build_session", return_value=mock_session
    ):
        manager.open_session(device)

    # Should not raise exception
    result = manager.close_session(device)

    assert result is True
    assert manager.has_session(device) is False


def test_close_all_sessions_cierra_todas_las_sesiones() -> None:
    """
    Tests that close_all_sessions closes all active sessions.
    """

    device1 = _build_device()
    device2 = _build_device()
    manager = SessionManager()

    mock_app_layer1 = MagicMock()
    mock_app_layer2 = MagicMock()
    mock_session1 = MagicMock(spec=Session)
    mock_session1.app_layer = mock_app_layer1
    mock_session2 = MagicMock(spec=Session)
    mock_session2.app_layer = mock_app_layer2

    with patch.object(
        manager.session_factory,
        "build_session",
        side_effect=[mock_session1, mock_session2],
    ):
        manager.open_session(device1)
        manager.open_session(device2)

    assert manager.get_active_session_count() == 2

    manager.close_all_sessions()

    assert manager.get_active_session_count() == 0
    mock_app_layer1.disconnect.assert_called_once()
    mock_app_layer2.disconnect.assert_called_once()


def test_close_all_sessions_ignora_errores() -> None:
    """
    Tests that close_all_sessions ignores errors during cleanup.
    """

    device1 = _build_device()
    device2 = _build_device()
    manager = SessionManager()

    mock_app_layer1 = MagicMock()
    mock_app_layer1.disconnect.side_effect = Exception("Error 1")
    mock_app_layer2 = MagicMock()
    mock_app_layer2.disconnect.side_effect = Exception("Error 2")

    mock_session1 = MagicMock(spec=Session)
    mock_session1.app_layer = mock_app_layer1
    mock_session2 = MagicMock(spec=Session)
    mock_session2.app_layer = mock_app_layer2

    with patch.object(
        manager.session_factory,
        "build_session",
        side_effect=[mock_session1, mock_session2],
    ):
        manager.open_session(device1)
        manager.open_session(device2)

    # Should not raise exception
    manager.close_all_sessions()

    assert manager.get_active_session_count() == 0


def test_context_manager_cierra_sesiones_al_salir() -> None:
    """
    Tests that context manager automatically closes sessions on exit.
    """

    device = _build_device()

    mock_app_layer = MagicMock()
    mock_session = MagicMock(spec=Session)
    mock_session.app_layer = mock_app_layer

    with SessionManager() as manager:
        with patch.object(
            manager.session_factory, "build_session", return_value=mock_session
        ):
            manager.open_session(device)
            assert manager.get_active_session_count() == 1

    # After exiting context, sessions should be closed
    assert manager.get_active_session_count() == 0
    mock_app_layer.disconnect.assert_called_once()


def test_context_manager_cierra_sesiones_incluso_con_excepcion() -> None:
    """
    Tests that context manager closes sessions even when exception occurs.
    """

    device = _build_device()

    mock_app_layer = MagicMock()
    mock_session = MagicMock(spec=Session)
    mock_session.app_layer = mock_app_layer

    try:
        with SessionManager() as manager:
            with patch.object(
                manager.session_factory, "build_session", return_value=mock_session
            ):
                manager.open_session(device)
                assert manager.get_active_session_count() == 1
                raise ValueError("Test exception")
    except ValueError:
        pass  # Expected exception

    # Sessions should still be closed
    assert manager.get_active_session_count() == 0
    mock_app_layer.disconnect.assert_called_once()


def test_context_manager_propaga_excepciones() -> None:
    """
    Tests that context manager propagates exceptions (doesn't suppress them).
    """

    device = _build_device()

    mock_session = MagicMock(spec=Session)

    with pytest.raises(ValueError) as exc_info:
        with SessionManager() as manager:
            with patch.object(
                manager.session_factory, "build_session", return_value=mock_session
            ):
                manager.open_session(device)
                raise ValueError("Test exception")

    assert "Test exception" in str(exc_info.value)


def test_open_session_con_multiples_dispositivos() -> None:
    """
    Tests opening sessions for multiple devices.
    """

    device1 = _build_device()
    device2 = _build_device()
    device3 = _build_device()

    manager = SessionManager()

    mock_session1 = MagicMock(spec=Session)
    mock_session2 = MagicMock(spec=Session)
    mock_session3 = MagicMock(spec=Session)

    with patch.object(
        manager.session_factory,
        "build_session",
        side_effect=[mock_session1, mock_session2, mock_session3],
    ):
        session1 = manager.open_session(device1)
        session2 = manager.open_session(device2)
        session3 = manager.open_session(device3)

    assert session1 is mock_session1
    assert session2 is mock_session2
    assert session3 is mock_session3
    assert manager.get_active_session_count() == 3


def test_session_manager_con_sesion_sin_app_layer() -> None:
    """
    Tests that session manager handles sessions without app_layer gracefully.
    """

    device = _build_device()
    manager = SessionManager()

    # Session without app_layer attribute
    mock_session = MagicMock(spec=Session)
    del mock_session.app_layer

    with patch.object(
        manager.session_factory, "build_session", return_value=mock_session
    ):
        manager.open_session(device)

    # Should not raise exception when closing
    result = manager.close_session(device)

    assert result is True
    assert manager.has_session(device) is False


def test_session_manager_con_app_layer_none() -> None:
    """
    Tests that session manager handles sessions with app_layer=None gracefully.
    """

    device = _build_device()
    manager = SessionManager()

    mock_session = MagicMock(spec=Session)
    mock_session.app_layer = None

    with patch.object(
        manager.session_factory, "build_session", return_value=mock_session
    ):
        manager.open_session(device)

    # Should not raise exception when closing
    result = manager.close_session(device)

    assert result is True
    assert manager.has_session(device) is False


def test_multiple_operations_en_mismo_manager() -> None:
    """
    Tests multiple operations on the same manager instance.
    """

    device1 = _build_device()
    device2 = _build_device()
    device3 = _build_device()

    manager = SessionManager()

    mock_session1 = MagicMock(spec=Session)
    mock_session2 = MagicMock(spec=Session)
    mock_session3 = MagicMock(spec=Session)

    with patch.object(
        manager.session_factory,
        "build_session",
        side_effect=[mock_session1, mock_session2, mock_session3],
    ):
        # Open multiple sessions
        manager.open_session(device1)
        manager.open_session(device2)
        assert manager.get_active_session_count() == 2

        # Get existing session
        retrieved = manager.get_session(device1)
        assert retrieved is mock_session1

        # Check session exists
        assert manager.has_session(device1) is True
        assert manager.has_session(device3) is False

        # Close one session
        manager.close_session(device1)
        assert manager.get_active_session_count() == 1

        # Get or create (should create)
        manager.get_or_create_session(device3)
        assert manager.get_active_session_count() == 2

        # Close all
        manager.close_all_sessions()
        assert manager.get_active_session_count() == 0
