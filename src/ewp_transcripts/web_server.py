"""Loopback-only local web adapter for the browser GUI."""

from __future__ import annotations

import json
import secrets
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
from ewp_transcripts.config import load_config
from ewp_transcripts.domain.errors import ApplicationError
from ewp_transcripts.web_jobs import GuiTranscriptionQueue
from ewp_transcripts.web_reviews import GuiReviewController
from ewp_transcripts.web_workflows import GuiWorkflowController

API_VERSION = "1.0"
REPOSITORY_URL = "https://github.com/Polikles/ewp-transcripts"
ISSUES_URL = f"{REPOSITORY_URL}/issues"
LICENSE_URL = f"{REPOSITORY_URL}/blob/main/LICENSE"
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
    if path == "/help":
        return _asset_response("help.html", "text/html; charset=utf-8")
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
                "license_url": LICENSE_URL,
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
        application_config = load_config()
        self.gui_config = config
        self.gui_workflows = GuiWorkflowController(config.allowed_roots)
        self.gui_reviews = GuiReviewController(
            config=application_config,
            resolve_path=self.gui_workflows.resolve_allowed_path,
        )
        self.gui_csrf_token = secrets.token_urlsafe(32)
        super().__init__((config.host, config.port), LocalGuiRequestHandler)
        self.gui_transcriptions = GuiTranscriptionQueue(config=application_config)

    def server_close(self) -> None:
        self.gui_transcriptions.close()
        super().server_close()


class LocalGuiRequestHandler(BaseHTTPRequestHandler):
    """Serve the bundled shell and a small versioned read-only API."""

    server: LocalGuiServer
    server_version = "EWPTranscriberGUI"
    sys_version = ""
    _security_headers: ClassVar[dict[str, str]] = SECURITY_HEADERS

    def do_GET(self) -> None:  # noqa: N802
        if urlsplit(self.path).path in {"/api/v1/session", "/api/v1/transcriptions"}:
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
            if urlsplit(self.path).path == "/api/v1/session":
                payload: dict[str, object] = {"csrf_token": self.server.gui_csrf_token}
            else:
                payload = {
                    "jobs": [
                        job.model_dump(mode="json") for job in self.server.gui_transcriptions.jobs()
                    ]
                }
            self._write_response(_json_response(HTTPStatus.OK, payload))
            return
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
            if not 0 < length <= 1_048_576:
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
        if path.startswith("/api/v1/reviews/"):
            supplied = self.headers.get("X-EWP-CSRF", "")
            if not secrets.compare_digest(supplied, self.server.gui_csrf_token):
                self._write_response(
                    _json_response(
                        HTTPStatus.FORBIDDEN,
                        {
                            "error": {
                                "code": "GUI_CSRF_REJECTED",
                                "message": "The review request lacks the active session token.",
                            }
                        },
                    )
                )
                return
            try:
                result = str(document.get("result_path", ""))
                if path == "/api/v1/reviews/prepare":
                    payload = self.server.gui_reviews.prepare(
                        result, str(document.get("review_output_directory", ""))
                    )
                elif path == "/api/v1/reviews/load":
                    payload = self.server.gui_reviews.document(
                        str(document.get("review_path", "")), result
                    )
                elif path == "/api/v1/reviews/session/save":
                    payload = self.server.gui_reviews.remember_session(
                        project_output_directory=str(document.get("project_output_directory", "")),
                        result=result,
                        review=str(document.get("review_path", "")),
                        review_output_directory=str(document.get("review_output_directory", "")),
                        revision_output_directory=str(
                            document.get("revision_output_directory", "")
                        ),
                        export_output_directory=str(document.get("export_output_directory", "")),
                        applied_revision=str(document.get("applied_revision_path", "")),
                    )
                elif path == "/api/v1/reviews/session/restore":
                    payload = self.server.gui_reviews.restore_session(
                        str(document.get("project_output_directory", ""))
                    )
                elif path == "/api/v1/reviews/save":
                    anchors = document.get("anchors")
                    if not isinstance(anchors, list):
                        raise ValueError("Review anchors must be an array")
                    payload = self.server.gui_reviews.save(
                        str(document.get("review_path", "")),
                        result,
                        expected_sha256=str(document.get("review_sha256", "")),
                        anchors=anchors,
                    )
                elif path == "/api/v1/reviews/preview":
                    payload = self.server.gui_reviews.preview(
                        str(document.get("review_path", "")), result
                    )
                elif path == "/api/v1/reviews/apply":
                    if document.get("confirmed") is not True:
                        raise ValueError("Manual verification confirmation is required")
                    payload = self.server.gui_reviews.apply(
                        str(document.get("review_path", "")),
                        result,
                        str(document.get("revision_output_directory", "")),
                    )
                elif path == "/api/v1/reviews/export":
                    formats = document.get("formats")
                    if not isinstance(formats, list) or not all(
                        isinstance(item, str) for item in formats
                    ):
                        raise ValueError("Export formats must be an array of names")
                    payload = self.server.gui_reviews.export(
                        result,
                        str(document.get("revision_path", "")),
                        str(document.get("export_output_directory", "")),
                        formats,
                    )
                else:
                    self._write_response(
                        _json_response(
                            HTTPStatus.NOT_FOUND,
                            {
                                "error": {
                                    "code": "GUI_ROUTE_NOT_FOUND",
                                    "message": "No such GUI route.",
                                }
                            },
                        )
                    )
                    return
            except ApplicationError as error:
                self._write_response(
                    _json_response(
                        HTTPStatus.BAD_REQUEST,
                        {"error": {"code": error.code, "message": str(error)}},
                    )
                )
                return
            except (FileNotFoundError, OSError, ValueError) as error:
                self._write_response(
                    _json_response(
                        HTTPStatus.BAD_REQUEST,
                        {"error": {"code": "GUI_REVIEW_REQUEST_INVALID", "message": str(error)}},
                    )
                )
                return
            self._write_response(_json_response(HTTPStatus.OK, payload))
            return
        if path == "/api/v1/inspect":
            operation = self.server.gui_workflows.run("inspect", document)
        elif path == "/api/v1/dry-run":
            operation = self.server.gui_workflows.run("dry-run", document)
        elif path.startswith("/api/v1/transcriptions"):
            supplied = self.headers.get("X-EWP-CSRF", "")
            if not secrets.compare_digest(supplied, self.server.gui_csrf_token):
                self._write_response(
                    _json_response(
                        HTTPStatus.FORBIDDEN,
                        {
                            "error": {
                                "code": "GUI_CSRF_REJECTED",
                                "message": (
                                    "The transcription request lacks the active session token."
                                ),
                            }
                        },
                    )
                )
                return
            if path == "/api/v1/transcriptions/start":
                count = self.server.gui_transcriptions.start()
                self._write_response(_json_response(HTTPStatus.ACCEPTED, {"queued": count}))
                return
            if path == "/api/v1/transcriptions/remove":
                job_id = document.get("job_id")
                removed = (
                    self.server.gui_transcriptions.remove(job_id)
                    if isinstance(job_id, str)
                    else False
                )
                if not removed:
                    self._write_response(
                        _json_response(
                            HTTPStatus.CONFLICT,
                            {
                                "error": {
                                    "code": "GUI_QUEUE_ITEM_IMMUTABLE",
                                    "message": "Only an existing staged queue item can be removed.",
                                }
                            },
                        )
                    )
                    return
                self._write_response(_json_response(HTTPStatus.OK, {"removed": job_id}))
                return
            if path != "/api/v1/transcriptions":
                self._write_response(
                    _json_response(
                        HTTPStatus.NOT_FOUND,
                        {"error": {"code": "GUI_ROUTE_NOT_FOUND", "message": "No such GUI route."}},
                    )
                )
                return
            if document.get("confirmed") is not True:
                self._write_response(
                    _json_response(
                        HTTPStatus.BAD_REQUEST,
                        {
                            "error": {
                                "code": "GUI_CONFIRMATION_REQUIRED",
                                "message": "Explicit transcription confirmation is required.",
                            }
                        },
                    )
                )
                return
            try:
                input_path = self.server.gui_workflows.resolve_allowed_path(
                    str(document.get("path", ""))
                )
                output_path = self.server.gui_workflows.resolve_allowed_path(
                    str(document.get("output_directory", "")), directory=True
                )
                if not input_path.is_file():
                    raise ValueError("The first transcription slice accepts one file")
                active_output = self.server.gui_transcriptions.active_output_directory()
                if active_output is not None and active_output != str(output_path):
                    self._write_response(
                        _json_response(
                            HTTPStatus.CONFLICT,
                            {
                                "error": {
                                    "code": "GUI_QUEUE_OUTPUT_MISMATCH",
                                    "message": (
                                        "All active queue jobs must use the same output directory."
                                    ),
                                }
                            },
                        )
                    )
                    return
                if self.server.gui_transcriptions.contains_active_input(input_path):
                    self._write_response(
                        _json_response(
                            HTTPStatus.CONFLICT,
                            {
                                "error": {
                                    "code": "GUI_QUEUE_DUPLICATE",
                                    "message": "This input is already staged, queued, or running.",
                                }
                            },
                        )
                    )
                    return
                plan = self.server.gui_workflows.completed_plan(input_path, output_path)
                if plan is None:
                    self._write_response(
                        _json_response(
                            HTTPStatus.BAD_REQUEST,
                            {
                                "error": {
                                    "code": "GUI_DRY_RUN_REQUIRED",
                                    "message": (
                                        "Run and review dry-run for this exact input and output."
                                    ),
                                }
                            },
                        )
                    )
                    return
                planned_jobs = plan.get("jobs")
                if not isinstance(planned_jobs, list) or len(planned_jobs) != 1:
                    raise ValueError("The staged dry-run must contain exactly one job")
                planned_job = planned_jobs[0]
                if not isinstance(planned_job, dict):
                    raise ValueError("The staged dry-run has no valid job plan")
                planned_outputs = planned_job.get("outputs")
                if not isinstance(planned_outputs, dict):
                    raise ValueError("The staged dry-run has no valid output plan")
                planned_job_id = planned_job.get("job_id")
                planned_result_path = planned_outputs.get("results")
                if not isinstance(planned_job_id, str) or not isinstance(planned_result_path, str):
                    raise ValueError("The staged dry-run has no valid result identity")
                if self.server.gui_transcriptions.contains_active_planned_job(planned_job_id):
                    self._write_response(
                        _json_response(
                            HTTPStatus.CONFLICT,
                            {
                                "error": {
                                    "code": "GUI_QUEUE_JOB_ID_COLLISION",
                                    "message": (
                                        "An active queue item already uses this job ID. "
                                        "Rename one source before staging it."
                                    ),
                                }
                            },
                        )
                    )
                    return
                job = self.server.gui_transcriptions.stage(
                    input_path,
                    output_path,
                    planned_job_id=planned_job_id,
                    planned_result_path=planned_result_path,
                )
            except (FileNotFoundError, OSError, ValueError) as error:
                self._write_response(
                    _json_response(
                        HTTPStatus.BAD_REQUEST,
                        {"error": {"code": "GUI_PATH_REJECTED", "message": str(error)}},
                    )
                )
                return
            self._write_response(_json_response(HTTPStatus.ACCEPTED, job.model_dump(mode="json")))
            return
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
