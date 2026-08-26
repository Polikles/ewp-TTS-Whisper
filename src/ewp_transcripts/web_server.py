"""Loopback-only local web adapter for the browser GUI."""

from __future__ import annotations

import json
import subprocess
import threading
import webbrowser
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlsplit

from ewp_transcripts import __version__
from ewp_transcripts.web_workflows import GuiWorkflowController

API_VERSION = "1"
REPOSITORY_URL = "https://github.com/Polikles/ewp-transcripts"
ISSUES_URL = f"{REPOSITORY_URL}/issues"
_ASSET_TYPES = {"app.css": "text/css; charset=utf-8", "app.js": "text/javascript; charset=utf-8"}
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; "
        "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Cache-Control": "no-store",
}


@dataclass(frozen=True)
class WebConfiguration:
    """Validated runtime configuration exposed to the local web adapter."""

    host: str
    port: int
    allowed_roots: tuple[Path, ...]

    @classmethod
    def create(cls, *, port: int, allowed_roots: list[Path]) -> WebConfiguration:
        if not 0 <= port <= 65535:
            raise ValueError("port must be between 0 and 65535")
        roots = allowed_roots or [Path.cwd()]
        resolved: list[Path] = []
        for root in roots:
            candidate = root.expanduser().resolve(strict=True)
            if not candidate.is_dir():
                raise ValueError(f"allowed root is not a directory: {root}")
            if candidate not in resolved:
                resolved.append(candidate)
        return cls(host="127.0.0.1", port=port, allowed_roots=tuple(resolved))


@dataclass(frozen=True)
class WebResponse:
    status: HTTPStatus
    content_type: str | None
    body: bytes


def dispatch_get(
    config: WebConfiguration, *, server_port: int, host: str, target: str
) -> WebResponse:
    """Resolve one read-only GUI request without performing network I/O."""
    accepted = {f"127.0.0.1:{server_port}", f"localhost:{server_port}", f"[::1]:{server_port}"}
    if host not in accepted:
        return _json_response(
            HTTPStatus.MISDIRECTED_REQUEST,
            {
                "error": {
                    "code": "GUI_HOST_REJECTED",
                    "message": "The request Host is not allowed by the local GUI server.",
                }
            },
        )
    path = urlsplit(target).path
    if path == "/":
        return _asset_response("index.html", "text/html; charset=utf-8")
    if path == "/favicon.ico":
        return WebResponse(HTTPStatus.NO_CONTENT, None, b"")
    if path.startswith("/assets/") and path.removeprefix("/assets/") in _ASSET_TYPES:
        name = path.removeprefix("/assets/")
        return _asset_response(name, _ASSET_TYPES[name])
    if path == "/api/v1/health":
        return _json_response(
            HTTPStatus.OK,
            {"status": "ok", "api_version": API_VERSION, "application_version": __version__},
        )
    if path == "/api/v1/about":
        return _json_response(
            HTTPStatus.OK,
            {
                "application": "EWP Transcriber",
                "application_version": __version__,
                "api_version": API_VERSION,
                "license": "AGPL-3.0-only",
                "warranty": "Provided without warranty; see the bundled license.",
                "repository_url": REPOSITORY_URL,
                "issues_url": ISSUES_URL,
            },
        )
    if path == "/api/v1/roots":
        return _json_response(
            HTTPStatus.OK, {"roots": [str(root) for root in config.allowed_roots]}
        )
    return _json_response(
        HTTPStatus.NOT_FOUND,
        {"error": {"code": "GUI_ROUTE_NOT_FOUND", "message": "No such GUI route."}},
    )


def _asset_response(name: str, content_type: str) -> WebResponse:
    return WebResponse(
        HTTPStatus.OK, content_type, files("ewp_transcripts.web_assets").joinpath(name).read_bytes()
    )


def _json_response(status: HTTPStatus, document: dict[str, object]) -> WebResponse:
    return WebResponse(
        status,
        "application/json; charset=utf-8",
        json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode(),
    )


class LocalGuiServer(ThreadingHTTPServer):
    """HTTP server carrying immutable GUI configuration."""

    daemon_threads = True

    def __init__(self, config: WebConfiguration) -> None:
        self.gui_config = config
        self.gui_workflows = GuiWorkflowController(config.allowed_roots)
        super().__init__((config.host, config.port), LocalGuiRequestHandler)


class LocalGuiRequestHandler(BaseHTTPRequestHandler):
    """Serve the bundled shell and a small versioned read-only API."""

    server: LocalGuiServer
    server_version = "EWPTranscriberGUI"
    sys_version = ""
    _security_headers: ClassVar[dict[str, str]] = SECURITY_HEADERS

    def do_GET(self) -> None:  # noqa: N802
        if urlsplit(self.path).path == "/api/v1/operations":
            host = self.headers.get("Host", "")
            if host not in {
                f"127.0.0.1:{self.server.server_port}",
                f"localhost:{self.server.server_port}",
            }:
                self._write_response(
                    _json_response(
                        HTTPStatus.MISDIRECTED_REQUEST,
                        {
                            "error": {
                                "code": "GUI_HOST_REJECTED",
                                "message": (
                                    "The request Host is not allowed by the local GUI server."
                                ),
                            }
                        },
                    )
                )
                return
            self._write_response(
                _json_response(
                    HTTPStatus.OK,
                    {
                        "operations": [
                            item.model_dump(mode="json")
                            for item in self.server.gui_workflows.operations()
                        ]
                    },
                )
            )
            return
        response = dispatch_get(
            self.server.gui_config,
            server_port=self.server.server_port,
            host=self.headers.get("Host", ""),
            target=self.path,
        )
        self.send_response(response.status)
        self._headers(content_type=response.content_type, content_length=len(response.body))
        self.end_headers()
        self.wfile.write(response.body)

    def do_POST(self) -> None:  # noqa: N802
        host = self.headers.get("Host", "")
        expected_origin = f"http://127.0.0.1:{self.server.server_port}"
        if host not in {
            f"127.0.0.1:{self.server.server_port}",
            f"localhost:{self.server.server_port}",
        }:
            self._write_response(
                _json_response(
                    HTTPStatus.MISDIRECTED_REQUEST,
                    {
                        "error": {
                            "code": "GUI_HOST_REJECTED",
                            "message": "The request Host is not allowed by the local GUI server.",
                        }
                    },
                )
            )
            return
        if self.headers.get("Origin") not in {
            expected_origin,
            f"http://localhost:{self.server.server_port}",
        }:
            self._write_response(
                _json_response(
                    HTTPStatus.FORBIDDEN,
                    {
                        "error": {
                            "code": "GUI_ORIGIN_REJECTED",
                            "message": "The request Origin is not allowed by the local GUI server.",
                        }
                    },
                )
            )
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16_384:
                raise ValueError("Request body size is invalid")
            document = json.loads(self.rfile.read(length))
            if not isinstance(document, dict):
                raise ValueError("JSON body must be an object")
        except (ValueError, json.JSONDecodeError):
            self._write_response(
                _json_response(
                    HTTPStatus.BAD_REQUEST,
                    {
                        "error": {
                            "code": "GUI_REQUEST_INVALID",
                            "message": "The request must contain a valid bounded JSON object.",
                        }
                    },
                )
            )
            return
        path = urlsplit(self.path).path
        if path == "/api/v1/inspect":
            operation = self.server.gui_workflows.run("inspect", document)
        elif path == "/api/v1/dry-run":
            operation = self.server.gui_workflows.run("dry-run", document)
        else:
            self._write_response(
                _json_response(
                    HTTPStatus.NOT_FOUND,
                    {"error": {"code": "GUI_ROUTE_NOT_FOUND", "message": "No such GUI route."}},
                )
            )
            return
        status = HTTPStatus.OK if operation.status == "completed" else HTTPStatus.BAD_REQUEST
        self._write_response(_json_response(status, operation.model_dump(mode="json")))

    def log_message(self, format: str, *args: object) -> None:
        return

    def _headers(self, *, content_type: str | None, content_length: int) -> None:
        if content_type is not None:
            self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(content_length))
        for name, value in self._security_headers.items():
            self.send_header(name, value)

    def _write_response(self, response: WebResponse) -> None:
        self.send_response(response.status)
        self._headers(content_type=response.content_type, content_length=len(response.body))
        self.end_headers()
        self.wfile.write(response.body)


def serve_gui(*, port: int, allowed_roots: list[Path], open_browser: bool = True) -> None:
    """Run the local GUI until interrupted."""

    server = LocalGuiServer(WebConfiguration.create(port=port, allowed_roots=allowed_roots))
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"GUI {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.1, _open_browser, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _open_browser(url: str) -> None:
    """Open a host browser without leaking platform-launcher noise to the terminal."""

    try:
        release = Path("/proc/sys/kernel/osrelease").read_text(encoding="utf-8")
        if "microsoft" in release.casefold():
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", "Start-Process", url],
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        webbrowser.open(url)
    except (OSError, subprocess.SubprocessError):
        return
