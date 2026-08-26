"""Read-only application-service workflows exposed by the local GUI."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from ewp_transcripts.application import dry_run, inspect_input
from ewp_transcripts.config import load_config
from ewp_transcripts.domain.errors import ApplicationError


class GuiOperation(BaseModel):
    """Bounded in-process evidence for one read-only GUI operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    operation_id: str
    kind: Literal["inspect", "dry-run"]
    status: Literal["completed", "failed"]
    input_path: str
    created_at: datetime
    result: dict[str, Any] | None = None
    error: dict[str, str] | None = None


Service = Callable[..., BaseModel]


@dataclass
class GuiWorkflowController:
    """Authorize paths and invoke existing application services directly."""

    allowed_roots: tuple[Path, ...]
    inspect_service: Service = inspect_input
    dry_run_service: Service = dry_run
    _operations: deque[GuiOperation] = field(default_factory=lambda: deque(maxlen=50))

    def run(self, kind: Literal["inspect", "dry-run"], document: dict[str, Any]) -> GuiOperation:
        raw_path = document.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            return self._failure(kind, "", "GUI_REQUEST_INVALID", "A non-empty path is required.")
        try:
            input_path = self.resolve_allowed_path(raw_path)
            config = load_config()
            if kind == "inspect":
                result = self.inspect_service(input_path, config=config)
            else:
                raw_output = document.get("output_directory")
                output = (
                    self.resolve_allowed_path(raw_output, directory=True)
                    if isinstance(raw_output, str) and raw_output.strip()
                    else None
                )
                result = self.dry_run_service(input_path, config=config, output_directory=output)
            operation = GuiOperation(
                operation_id=str(uuid4()),
                kind=kind,
                status="completed",
                input_path=str(input_path),
                created_at=datetime.now(UTC),
                result=result.model_dump(mode="json"),
            )
        except ApplicationError as error:
            operation = self._new_failure(kind, raw_path, error.code, str(error))
        except (FileNotFoundError, OSError, ValueError) as error:
            operation = self._new_failure(kind, raw_path, "GUI_PATH_REJECTED", str(error))
        self._operations.appendleft(operation)
        return operation

    def operations(self) -> tuple[GuiOperation, ...]:
        return tuple(self._operations)

    def resolve_allowed_path(self, raw_path: str, *, directory: bool = False) -> Path:
        candidate = Path(raw_path).expanduser()
        if candidate.is_symlink():
            raise ValueError("Symbolic-link paths are not allowed")
        resolved = candidate.resolve(strict=not directory)
        if not any(
            resolved == root or resolved.is_relative_to(root) for root in self.allowed_roots
        ):
            raise ValueError("Path is outside the configured allowed roots")
        if directory and resolved.exists() and not resolved.is_dir():
            raise ValueError("Output path must be a directory")
        return resolved

    def _failure(
        self, kind: Literal["inspect", "dry-run"], path: str, code: str, message: str
    ) -> GuiOperation:
        operation = self._new_failure(kind, path, code, message)
        self._operations.appendleft(operation)
        return operation

    @staticmethod
    def _new_failure(
        kind: Literal["inspect", "dry-run"], path: str, code: str, message: str
    ) -> GuiOperation:
        return GuiOperation(
            operation_id=str(uuid4()),
            kind=kind,
            status="failed",
            input_path=path,
            created_at=datetime.now(UTC),
            error={"code": code, "message": message},
        )
