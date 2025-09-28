"""Regression tests for the bundled ``requests`` compatibility shim."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict

import pytest

import requests


class _Handler(BaseHTTPRequestHandler):
    """Serve a minimal JSON payload and capture request headers."""

    latest_headers: Dict[str, str] = {}

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler naming
        type(self).latest_headers = {k: v for k, v in self.headers.items()}
        payload = json.dumps({"ok": True}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):  # noqa: A003 - base signature
        # Suppress noisy stderr output during the test suite
        return


@pytest.fixture()
def http_server(tmp_path: Path):
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_session_round_trip(http_server: HTTPServer):
    session = requests.Session()
    session.headers.update({"X-Test": "shim"})
    url = f"http://{http_server.server_address[0]}:{http_server.server_address[1]}/"

    response = session.get(url, timeout=5)

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    # Ensure default headers and session headers were transmitted.
    sent_headers = _Handler.latest_headers
    assert sent_headers["User-Agent"].startswith("TenosAI-HTTP/")
    assert sent_headers["X-Test"] == "shim"

    # ``close`` should be a no-op that still exists for compatibility.
    session.close()
    assert session.headers == {}
