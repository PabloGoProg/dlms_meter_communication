import socket
import socketserver
import threading
import time
from typing import Tuple

import pytest

from dlms_meter_communication.services.reader_service.adapterss.connections.tcp_connection import (
    TCPConnection,
)


class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


class _EchoHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        data = self.request.recv(4096)
        if data:
            self.request.sendall(data)


class _NoSendHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        # Keep the connection open without sending data
        time.sleep(5)


def _run_server_in_thread(server: socketserver.TCPServer) -> threading.Thread:
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread


@pytest.fixture
def echo_server() -> Tuple[str, int, _ThreadingTCPServer]:
    server = _ThreadingTCPServer(("127.0.0.1", 0), _EchoHandler)
    _run_server_in_thread(server)
    host, port = server.server_address
    yield host, port, server
    server.shutdown()
    server.server_close()


@pytest.fixture
def no_send_server() -> Tuple[str, int, _ThreadingTCPServer]:
    server = _ThreadingTCPServer(("127.0.0.1", 0), _NoSendHandler)
    _run_server_in_thread(server)
    host, port = server.server_address
    yield host, port, server
    server.shutdown()
    server.server_close()


def test_open_and_close_connection(
    echo_server: Tuple[str, int, _ThreadingTCPServer],
) -> None:
    host, port, _ = echo_server
    conn = TCPConnection(host=host, port=port, connection_timeout=1.0, io_timeout=1.0)

    conn.open()
    assert conn.is_connected() is True

    conn.close()
    assert conn.is_connected() is False


def test_send_receive_echo_roundtrip(
    echo_server: Tuple[str, int, _ThreadingTCPServer],
) -> None:
    host, port, _ = echo_server
    conn = TCPConnection(host=host, port=port, connection_timeout=1.0, io_timeout=1.0)
    conn.open()

    try:
        payload = b"hello-dlms"
        conn.send(payload)
        data = conn.receive(size=len(payload), timeout=2.0)
        assert data == payload
    finally:
        conn.close()


def test_receive_timeout(no_send_server: Tuple[str, int, _ThreadingTCPServer]) -> None:
    host, port, _ = no_send_server
    conn = TCPConnection(host=host, port=port, connection_timeout=1.0, io_timeout=1.0)
    conn.open()

    try:
        with pytest.raises(TimeoutError):
            _ = conn.receive(size=16, timeout=0.2)
    finally:
        conn.close()


def test_connection_refused_raises_connection_error() -> None:
    # Find a random port that is not being listened to
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    host, port = sock.getsockname()
    sock.close()

    conn = TCPConnection(host=host, port=port, connection_timeout=0.5, io_timeout=0.5)

    with pytest.raises(ConnectionError):
        conn.open()
