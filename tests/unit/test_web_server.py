import json
from pathlib import Path

import pytest

from ewp_transcripts import __version__
from ewp_transcripts.web_server import SECURITY_HEADERS, WebConfiguration, dispatch_get


def test_health_is_versioned_and_hardened(tmp_path: Path) -> None:
    config = WebConfiguration.create(port=8765, allowed_roots=[tmp_path])
    response = dispatch_get(
        config, server_port=8765, host="127.0.0.1:8765", target="/api/v1/health"
    )
    assert response.status == 200
    assert json.loads(response.body) == {
        "status": "ok",
        "api_version": "1",
        "application_version": __version__,
    }
    assert "default-src 'none'" in SECURITY_HEADERS["Content-Security-Policy"]
    assert SECURITY_HEADERS["X-Content-Type-Options"] == "nosniff"


def test_shell_and_allowed_roots_are_served(tmp_path: Path) -> None:
    config = WebConfiguration.create(port=8765, allowed_roots=[tmp_path])
    response = dispatch_get(config, server_port=8765, host="localhost:8765", target="/")
    assert response.status == 200
    assert b"EWP Transcriber" in response.body
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
