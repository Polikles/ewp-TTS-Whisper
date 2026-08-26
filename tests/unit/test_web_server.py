import json
import subprocess
from email.message import Message
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from ewp_transcripts import __version__
from ewp_transcripts.web_server import (
    SECURITY_HEADERS,
    LocalGuiRequestHandler,
    WebConfiguration,
    _open_browser,
    dispatch_get,
)


def test_health_is_versioned_and_hardened(tmp_path: Path) -> None:
    config = WebConfiguration.create(port=8765, allowed_roots=[tmp_path])
    response = dispatch_get(
        config, server_port=8765, host="127.0.0.1:8765", target="/api/v1/health"
    )
    assert response.status == 200
    assert json.loads(response.body) == {
        "status": "ok",
        "api_version": "1.0",
        "application_version": __version__,
    }
    assert "default-src 'none'" in SECURITY_HEADERS["Content-Security-Policy"]
    assert SECURITY_HEADERS["X-Content-Type-Options"] == "nosniff"


def test_shell_and_allowed_roots_are_served(tmp_path: Path) -> None:
    config = WebConfiguration.create(port=8765, allowed_roots=[tmp_path])
    response = dispatch_get(config, server_port=8765, host="localhost:8765", target="/")
    assert response.status == 200
    assert b"EWP Transcriber" in response.body
    assert b'id="clear-workflow"' in response.body
    assert b"Add to queue" in response.body
    assert b"Start queue" in response.body
    help_response = dispatch_get(config, server_port=8765, host="localhost:8765", target="/help")
    assert help_response.status == 200
    assert b"Build and start a queue" in help_response.body
    response = dispatch_get(config, server_port=8765, host="localhost:8765", target="/api/v1/roots")
    assert json.loads(response.body) == {"roots": [str(tmp_path.resolve())]}


def test_untrusted_host_and_unknown_route_have_codes(tmp_path: Path) -> None:
    config = WebConfiguration.create(port=8765, allowed_roots=[tmp_path])
    response = dispatch_get(config, server_port=8765, host="attacker.example", target="/")
    assert response.status == 421
    assert json.loads(response.body)["error"]["code"] == "GUI_HOST_REJECTED"
    response = dispatch_get(config, server_port=8765, host="[::1]:8765", target="/missing")
    assert response.status == 404
    assert json.loads(response.body)["error"]["code"] == "GUI_ROUTE_NOT_FOUND"


def test_web_configuration_rejects_files_and_missing_roots(tmp_path: Path) -> None:
    source = tmp_path / "source.wav"
    source.write_bytes(b"")
    with pytest.raises(ValueError, match="not a directory"):
        WebConfiguration.create(port=8765, allowed_roots=[source])
    with pytest.raises(FileNotFoundError):
        WebConfiguration.create(port=8765, allowed_roots=[tmp_path / "missing"])


def test_wsl_browser_open_uses_windows_bridge_without_terminal_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Path, "read_text", lambda self, encoding: "microsoft-standard-WSL2")
    run = Mock()
    monkeypatch.setattr("ewp_transcripts.web_server.subprocess.run", run)

    _open_browser("http://127.0.0.1:8765/")

    assert run.call_args.args[0] == [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        "Start-Process",
        "http://127.0.0.1:8765/",
    ]
    assert run.call_args.kwargs["stderr"] is subprocess.DEVNULL


def test_post_rejects_cross_origin_before_reading_body() -> None:
    handler = LocalGuiRequestHandler.__new__(LocalGuiRequestHandler)
    headers = Message()
    headers["Host"] = "127.0.0.1:8765"
    headers["Origin"] = "https://attacker.example"
    handler.headers = headers
    handler.path = "/api/v1/inspect"
    handler.rfile = BytesIO(b"")
    handler.server = SimpleNamespace(server_port=8765)
    write_response = Mock()
    handler._write_response = write_response

    handler.do_POST()

    response = write_response.call_args.args[0]
    assert response.status == 403
    assert json.loads(response.body)["error"]["code"] == "GUI_ORIGIN_REJECTED"


def test_transcription_post_requires_active_csrf_token() -> None:
    body = b'{"path":"/tmp/source.wav","confirmed":true}'
    handler = LocalGuiRequestHandler.__new__(LocalGuiRequestHandler)
    headers = Message()
    headers["Host"] = "127.0.0.1:8765"
    headers["Origin"] = "http://127.0.0.1:8765"
    headers["Content-Length"] = str(len(body))
    handler.headers = headers
    handler.path = "/api/v1/transcriptions"
    handler.rfile = BytesIO(body)
    handler.server = SimpleNamespace(server_port=8765, gui_csrf_token="expected")
    write_response = Mock()
    handler._write_response = write_response

    handler.do_POST()

    response = write_response.call_args.args[0]
    assert response.status == 403
    assert json.loads(response.body)["error"]["code"] == "GUI_CSRF_REJECTED"
